import logging
from typing import List, Optional
from urllib.parse import urlparse

from app.collectors.discovery import GovernmentDiscoveryService, is_scheme_or_policy_relevant
from app.core.config import settings
from app.core.source_registry import ApprovedSource
from app.core.url_validator import is_allowed_government_hostname, validate_url
from app.extractors.html_extractor import extract_html
from app.models.entities import ContentFormat, RawFetchResult
from app.utils.http import fetch

logger = logging.getLogger(__name__)


def collect_from_source(
    source: ApprovedSource,
    approved_sources: List[ApprovedSource],
    max_pages: int = None,
    resolve_dns: bool = True,
    discovery_service: Optional[GovernmentDiscoveryService] = None,
    enable_discovery: bool = True,
) -> List[RawFetchResult]:
    """Breadth-first crawl within an approved source's allowed domains/paths,
    with automated sitemap discovery, robots.txt compliance, and rate limiting.
    Returns validated, fetched raw content only."""
    max_pages = max_pages or settings.max_pages_per_source_per_run
    discovery = discovery_service or GovernmentDiscoveryService() if (enable_discovery and settings.discovery_enabled) else None

    seen = set()
    queue = [source.base_url]

    # Pre-populate queue with high-value sitemap URLs and scheme directories if discovery enabled
    if discovery:
        try:
            sitemap_urls = discovery.discover_from_sitemaps(source.base_url, resolve_dns=resolve_dns, max_urls=max_pages)
            for item in sitemap_urls:
                if item.normalized_url not in seen and len(queue) < max_pages * 2:
                    queue.append(item.normalized_url)
        except Exception as e:
            logger.debug("Sitemap discovery skipped for %s: %s", source.base_url, e)

    results: List[RawFetchResult] = []
    errors: List[str] = []

    parsed_base = urlparse(source.base_url)
    base_hostname = (parsed_base.hostname or "").lower()

    while queue and len(results) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        # 1. Full URL and SSRF validation
        validation = validate_url(url, approved_sources, resolve_dns=resolve_dns, allow_gov_discovery=bool(discovery))
        if not validation.is_valid:
            errors.append(f"REJECTED {url}: {validation.reason}")
            continue

        normalized_url = validation.normalized_url
        parsed_target = urlparse(normalized_url)
        target_hostname = (parsed_target.hostname or "").lower()

        # 2. Check robots.txt compliance
        if discovery and not discovery.robots_manager.can_fetch(normalized_url):
            errors.append(f"ROBOTS_DISALLOWED {url}")
            continue

        # 3. Apply rate limiter
        if discovery:
            discovery.rate_limiter.acquire(target_hostname)

        # 4. Fetch content
        try:
            raw = fetch(normalized_url)
        except Exception as e:
            errors.append(f"FETCH_FAILED {url}: {e}")
            continue

        results.append(raw)

        # 5. Extract links & discover cross-portal government links
        if raw.content_format == ContentFormat.HTML:
            try:
                extracted = extract_html(raw.raw_bytes.decode("utf-8", errors="ignore"), raw.final_url)
            except Exception as e:
                errors.append(f"PARSE_FAILED {url}: {e}")
                continue

            for link in extracted.links:
                if link in seen:
                    continue

                link_host = (urlparse(link).hostname or "").lower()

                # Case A: Same source / approved source domain
                if link_host == target_hostname or link_host == base_hostname:
                    queue.append(link)
                # Case B: Cross-portal government discovery
                elif discovery and is_allowed_government_hostname(link_host):
                    if is_scheme_or_policy_relevant(link):
                        # Register the newly discovered portal
                        new_source = discovery.register_or_get_source(link_host)
                        if new_source and new_source not in approved_sources:
                            approved_sources.append(new_source)
                        queue.append(link)

    if errors:
        logger.info("Collection errors/skips for source %s: %d", source.source_id, len(errors))
    return results

