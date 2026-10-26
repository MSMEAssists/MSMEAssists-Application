"""
Automated Government Source Discovery and Crawling.

Discovers relevant official Indian government websites and scheme pages via:
1. robots.txt sitemap declarations and crawl-delay directives.
2. XML sitemap indexes and urlsets with lastmod timestamps.
3. Official scheme/loan/policy directories on government portals.
4. Validated cross-portal government links (.gov.in, .nic.in, and verified allowlists).

Strictly enforces SSRF protection, robots.txt compliance, rate limiting,
URL deduplication, and repository source registration.
"""
import gzip
import io
import logging
import re
import time
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import requests

from app.core.config import settings
from app.core.source_registry import ApprovedSource, create_discovered_source
from app.core.url_validator import (
    is_allowed_government_hostname,
    validate_discovered_url,
    validate_url,
)

logger = logging.getLogger(__name__)

# Keywords identifying high-value MSME, business, loan, scheme, and policy pages
RELEVANCE_KEYWORDS: Set[str] = {
    "scheme", "schemes", "loan", "loans", "credit", "subsidy", "subsidies",
    "grant", "grants", "financial-assistance", "msme", "micro", "small", "medium",
    "enterprise", "enterprises", "industry", "industries", "entrepreneur",
    "entrepreneurship", "cluster", "clusters", "incubation", "incubator",
    "technology-upgradation", "guarantee", "collateral-free", "margin-money",
    "udyam", "pmegp", "cgtmse", "mudra", "startup", "startups", "seed-fund",
    "policy", "policies", "guideline", "guidelines", "incentive", "incentives",
    "export", "dgft", "procurement", "zed", "odr", "delayed-payment",
    "champions", "circular", "circulars", "notification", "notifications",
    "act", "acts", "rules", "e-services", "tenders", "sub-scheme",
}

# Patterns indicating irrelevant pages that should be filtered out
IRRELEVANT_PATTERNS: List[str] = [
    "/login", "/signin", "/signup", "/register/user", "/forgot-password",
    "/feedback", "/contact-us", "/contact", "/terms-of-use", "/privacy-policy",
    "/disclaimer", "/sitemap.xml", "/robots.txt", "/wp-json", "/wp-admin",
    "/gallery", "/photo-gallery", "/video-gallery", "/photogallery",
    "/staff-directory", "/employee-corner", "/recruitment", "/careers",
    "/vacancy", "/admit-card", "/result", "/holiday-list", "/tenders/housekeeping",
]

# Standard scheme directory endpoints probed on discovered government portals
OFFICIAL_SCHEME_DIRECTORIES: List[str] = [
    "/schemes",
    "/all-schemes",
    "/schemes-programmes",
    "/services",
    "/policies",
    "/guidelines",
    "/notifications",
    "/acts-rules",
    "/loans",
    "/credit-support",
    "/subsidies",
    "/msme-schemes",
]


@dataclass
class DiscoveredUrl:
    url: str
    normalized_url: str
    hostname: str
    source_type: str  # "sitemap" | "robots" | "directory" | "cross_link"
    matched_source_id: Optional[str] = None
    lastmod: Optional[str] = None
    title: Optional[str] = None
    relevance_score: float = 1.0


@dataclass
class RobotsTxtInfo:
    hostname: str
    sitemaps: List[str] = field(default_factory=list)
    crawl_delay: Optional[float] = None
    parser: Optional[urllib.robotparser.RobotFileParser] = None
    fetched_at: float = field(default_factory=time.time)


class RateLimiter:
    """Per-domain rate limiter respecting configurable crawl delays and robots.txt."""

    def __init__(self, default_delay: float = 0.5):
        self.default_delay = default_delay
        self.domain_delays: Dict[str, float] = {}
        self._last_access: Dict[str, float] = {}
        self.enabled: bool = True

    def set_domain_delay(self, hostname: str, delay: float):
        if delay > 0:
            self.domain_delays[hostname.lower()] = delay

    def acquire(self, hostname: str):
        if not self.enabled:
            return
        hostname = hostname.lower()
        delay = self.domain_delays.get(hostname, self.default_delay)
        if delay <= 0:
            return

        now = time.time()
        last = self._last_access.get(hostname, 0.0)
        elapsed = now - last
        if elapsed < delay:
            sleep_time = delay - elapsed
            time.sleep(sleep_time)
        self._last_access[hostname] = time.time()


class RobotsTxtManager:
    """Fetches, parses, and caches robots.txt with disallow checking and sitemap extraction."""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter(settings.discovery_crawl_delay_seconds)
        self._cache: Dict[str, RobotsTxtInfo] = {}

    def get_robots_info(
        self,
        base_url_or_domain: str,
        resolve_dns: bool = True,
        custom_content: Optional[str] = None,
    ) -> RobotsTxtInfo:
        target = base_url_or_domain.strip()
        if "://" not in target:
            target = f"https://{target}"
        parsed = urlparse(target)
        hostname = (parsed.hostname or base_url_or_domain).lower()

        if hostname in self._cache and custom_content is None:
            return self._cache[hostname]

        info = RobotsTxtInfo(hostname=hostname)

        # Allow tests to inject mock robots.txt directly
        if custom_content is not None:
            self._parse_robots_text(custom_content, info)
            self._cache[hostname] = info
            return info

        robots_url = f"{parsed.scheme}://{hostname}/robots.txt"
        val = validate_discovered_url(robots_url, resolve_dns=resolve_dns)
        if not val.is_valid:
            logger.debug("Skipping robots.txt for %s: %s", hostname, val.reason)
            self._cache[hostname] = info
            return info

        try:
            self.rate_limiter.acquire(hostname)
            resp = requests.get(
                val.normalized_url,
                headers={"User-Agent": settings.user_agent},
                timeout=settings.request_timeout_seconds,
                allow_redirects=True,
            )
            if resp.status_code == 200:
                self._parse_robots_text(resp.text, info)
            else:
                logger.debug("robots.txt for %s returned status %d", hostname, resp.status_code)
        except Exception as e:
            logger.debug("Could not fetch robots.txt for %s: %s", hostname, e)

        self._cache[hostname] = info
        return info

    def _parse_robots_text(self, text: str, info: RobotsTxtInfo):
        lines = text.splitlines()
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(lines)
        info.parser = parser

        # Extract Sitemap: directives
        sitemaps = []
        for line in lines:
            line_str = line.strip()
            if line_str.lower().startswith("sitemap:"):
                parts = line_str.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    sm = parts[1].strip()
                    if sm.startswith("http://") or sm.startswith("https://"):
                        sitemaps.append(sm)

        info.sitemaps = sitemaps

        # Extract Crawl-delay
        for line in lines:
            line_str = line.strip()
            if line_str.lower().startswith("crawl-delay:"):
                parts = line_str.split(":", 1)
                if len(parts) == 2:
                    try:
                        delay = float(parts[1].strip())
                        info.crawl_delay = delay
                        self.rate_limiter.set_domain_delay(info.hostname, delay)
                    except ValueError:
                        pass

    def can_fetch(self, url: str, user_agent: Optional[str] = None) -> bool:
        """Check whether fetching this URL complies with robots.txt."""
        if not settings.discovery_respect_robots_txt:
            return True
        ua = user_agent or settings.user_agent
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        info = self._cache.get(hostname)
        if not info or not info.parser:
            return True
        try:
            return info.parser.can_fetch(ua, url)
        except Exception:
            return True


class SitemapParser:
    """Parses XML sitemaps and sitemap indexes, recursively extracting URLs."""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter(settings.discovery_crawl_delay_seconds)

    def parse_sitemap_content(self, raw_bytes: bytes, sitemap_url: str) -> Tuple[List[str], List[Dict[str, str]]]:
        """Parse raw sitemap XML bytes. Returns (sub_sitemaps, url_entries)."""
        # Decompress gzip if applicable
        if raw_bytes[:2] == b"\x1f\x8b":
            try:
                raw_bytes = gzip.decompress(raw_bytes)
            except Exception as e:
                logger.warning("Failed decompressing gzip sitemap %s: %e", sitemap_url, e)
                return [], []

        try:
            text = raw_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return [], []

        sub_sitemaps: List[str] = []
        url_entries: List[Dict[str, str]] = []

        # XML parsing with stripped namespaces
        try:
            root = ET.fromstring(text)
            tag_name = root.tag.split("}")[-1].lower() if "}" in root.tag else root.tag.lower()

            if tag_name == "sitemapindex":
                for elem in root:
                    elem_tag = elem.tag.split("}")[-1].lower() if "}" in elem.tag else elem.tag.lower()
                    if elem_tag == "sitemap":
                        loc = None
                        for child in elem:
                            c_tag = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
                            if c_tag == "loc" and child.text:
                                loc = child.text.strip()
                                break
                        if loc:
                            sub_sitemaps.append(loc)

            elif tag_name == "urlset":
                for elem in root:
                    elem_tag = elem.tag.split("}")[-1].lower() if "}" in elem.tag else elem.tag.lower()
                    if elem_tag == "url":
                        loc = None
                        lastmod = None
                        for child in elem:
                            c_tag = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
                            if c_tag == "loc" and child.text:
                                loc = child.text.strip()
                            elif c_tag == "lastmod" and child.text:
                                lastmod = child.text.strip()
                        if loc:
                            url_entries.append({"loc": loc, "lastmod": lastmod or ""})
        except Exception as e:
            # Fallback regex extraction if XML contains malformed elements
            logger.debug("Falling back to regex sitemap parsing for %s: %s", sitemap_url, e)
            locs = re.findall(r"<loc>\s*(https?://[^\s<]+)\s*</loc>", text, flags=re.IGNORECASE)
            for loc in locs:
                if "sitemap" in loc.lower() and loc.lower().endswith(".xml"):
                    sub_sitemaps.append(loc)
                else:
                    url_entries.append({"loc": loc, "lastmod": ""})

        return sub_sitemaps, url_entries

    def fetch_and_parse(
        self,
        sitemap_url: str,
        max_depth: int = 2,
        resolve_dns: bool = True,
        seen_sitemaps: Optional[Set[str]] = None,
    ) -> List[Dict[str, str]]:
        """Fetch and recursively parse a sitemap hierarchy up to max_depth."""
        if seen_sitemaps is None:
            seen_sitemaps = set()

        if sitemap_url in seen_sitemaps or max_depth < 0:
            return []
        seen_sitemaps.add(sitemap_url)

        val = validate_discovered_url(sitemap_url, resolve_dns=resolve_dns)
        if not val.is_valid:
            logger.debug("Sitemap URL rejected by validator: %s (%s)", sitemap_url, val.reason)
            return []

        parsed = urlparse(val.normalized_url)
        self.rate_limiter.acquire(parsed.hostname or "")

        try:
            resp = requests.get(
                val.normalized_url,
                headers={"User-Agent": settings.user_agent},
                timeout=settings.request_timeout_seconds,
                allow_redirects=True,
            )
            if resp.status_code != 200:
                logger.debug("Sitemap %s returned %d", sitemap_url, resp.status_code)
                return []
            raw_bytes = resp.content
        except Exception as e:
            logger.warning("Failed fetching sitemap %s: %s", sitemap_url, e)
            return []

        sub_sitemaps, urls = self.parse_sitemap_content(raw_bytes, sitemap_url)
        all_urls = list(urls)

        for sub_sm in sub_sitemaps:
            sub_urls = self.fetch_and_parse(
                sub_sm,
                max_depth=max_depth - 1,
                resolve_dns=resolve_dns,
                seen_sitemaps=seen_sitemaps,
            )
            all_urls.extend(sub_urls)

        return all_urls


def is_scheme_or_policy_relevant(url: str, text: Optional[str] = None) -> bool:
    """Filter candidate URLs for MSME, business, scheme, loan, and regulatory relevance."""
    url_lower = url.lower()

    # Reject known irrelevant paths immediately
    for bad in IRRELEVANT_PATTERNS:
        if bad in url_lower:
            return False

    # Check for direct scheme directory markers in path
    path = urlparse(url_lower).path
    for directory in OFFICIAL_SCHEME_DIRECTORIES:
        if directory in path:
            return True

    # Check relevance keywords against URL path tokens and anchor text
    tokens = set(re.findall(r"[a-z0-9-]+", path))
    if text:
        tokens.update(re.findall(r"[a-z0-9-]+", text.lower()))

    return bool(tokens.intersection(RELEVANCE_KEYWORDS))


class GovernmentDiscoveryService:
    """Orchestrates automatic discovery of official government portals, sitemaps, and scheme pages."""

    def __init__(
        self,
        repository: Optional[Any] = None,
        rate_limiter: Optional[RateLimiter] = None,
        robots_manager: Optional[RobotsTxtManager] = None,
        sitemap_parser: Optional[SitemapParser] = None,
    ):
        self.repository = repository
        self.rate_limiter = rate_limiter or RateLimiter(settings.discovery_crawl_delay_seconds)
        self.robots_manager = robots_manager or RobotsTxtManager(self.rate_limiter)
        self.sitemap_parser = sitemap_parser or SitemapParser(self.rate_limiter)

    def register_or_get_source(
        self,
        url_or_hostname: str,
        name: Optional[str] = None,
        organization: Optional[str] = None,
    ) -> Optional[ApprovedSource]:
        """Deduplicate and register a newly discovered official government portal in the repository."""
        target = url_or_hostname.strip()
        if "://" not in target:
            target = f"https://{target}"
        parsed = urlparse(target)
        hostname = (parsed.hostname or url_or_hostname).lower().strip(".")

        if not is_allowed_government_hostname(hostname):
            return None

        # Check existing sources from repository
        existing_sources: List[ApprovedSource] = []
        if self.repository and hasattr(self.repository, "list_sources"):
            rows = self.repository.list_sources()
            for r in rows:
                if isinstance(r, dict) and "allowed_domains" in r:
                    existing_sources.append(ApprovedSource(**r))

        for src in existing_sources:
            for d in src.allowed_domains:
                if hostname == d.lower() or hostname.endswith("." + d.lower()):
                    return src

        # New source: create and persist
        new_source = create_discovered_source(hostname, name=name, organization=organization)
        if self.repository and hasattr(self.repository, "upsert_source"):
            self.repository.upsert_source(new_source)
            logger.info("Registered newly discovered government source: %s (%s)", new_source.source_id, hostname)

        return new_source

    def discover_from_sitemaps(
        self,
        base_url: str,
        resolve_dns: bool = True,
        max_urls: int = 100,
    ) -> List[DiscoveredUrl]:
        """Discover scheme and policy URLs via robots.txt sitemap declarations and /sitemap.xml."""
        parsed = urlparse(base_url)
        hostname = (parsed.hostname or "").lower()

        robots_info = self.robots_manager.get_robots_info(base_url, resolve_dns=resolve_dns)
        sitemap_targets = list(robots_info.sitemaps)

        # Common sitemap fallback if robots.txt did not declare any
        if not sitemap_targets:
            sitemap_targets.append(f"{parsed.scheme}://{hostname}/sitemap.xml")

        discovered: List[DiscoveredUrl] = []
        seen_urls: Set[str] = set()

        for sm_url in sitemap_targets:
            entries = self.sitemap_parser.fetch_and_parse(
                sm_url,
                max_depth=settings.discovery_max_sitemap_depth,
                resolve_dns=resolve_dns,
            )
            for item in entries:
                u = item["loc"]
                if u in seen_urls:
                    continue
                seen_urls.add(u)

                if not is_scheme_or_policy_relevant(u):
                    continue

                val = validate_discovered_url(u, resolve_dns=resolve_dns)
                if not val.is_valid:
                    continue

                if not self.robots_manager.can_fetch(val.normalized_url):
                    continue

                discovered.append(
                    DiscoveredUrl(
                        url=u,
                        normalized_url=val.normalized_url,
                        hostname=urlparse(val.normalized_url).hostname or "",
                        source_type="sitemap",
                        matched_source_id=val.matched_source.source_id if val.matched_source else None,
                        lastmod=item.get("lastmod"),
                        relevance_score=1.0,
                    )
                )

                if len(discovered) >= max_urls:
                    break
            if len(discovered) >= max_urls:
                break

        return discovered

    def discover_cross_portal_links(
        self,
        html_links: List[str],
        current_hostname: str,
        resolve_dns: bool = True,
    ) -> Tuple[List[ApprovedSource], List[DiscoveredUrl]]:
        """Identify outbound official government links and register new portals."""
        new_sources: List[ApprovedSource] = []
        discovered_urls: List[DiscoveredUrl] = []
        registered_hostnames: Set[str] = set()

        for link in html_links:
            parsed = urlparse(link)
            target_host = (parsed.hostname or "").lower()
            if not target_host or target_host == current_hostname.lower():
                continue

            if not is_allowed_government_hostname(target_host):
                continue

            # Validate URL with discovery allowlist
            val = validate_discovered_url(link, resolve_dns=resolve_dns)
            if not val.is_valid:
                continue

            # Register portal as a new approved source if not seen before
            if target_host not in registered_hostnames:
                src = self.register_or_get_source(target_host)
                if src:
                    new_sources.append(src)
                    registered_hostnames.add(target_host)

            if is_scheme_or_policy_relevant(link):
                discovered_urls.append(
                    DiscoveredUrl(
                        url=link,
                        normalized_url=val.normalized_url,
                        hostname=target_host,
                        source_type="cross_link",
                        matched_source_id=val.matched_source.source_id if val.matched_source else None,
                    )
                )

        return new_sources, discovered_urls
