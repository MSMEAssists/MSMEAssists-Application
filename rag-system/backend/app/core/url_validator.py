"""
Strict source/URL validation with SSRF protection.

Every URL must pass ALL checks below before the ingestion pipeline is
allowed to fetch it:

  1. Parse URL
  2. Validate protocol (http/https only)
  3. Validate domain (must match an approved, enabled source's allowed_domains)
  4. Validate path scope (must match one of that source's allowed_path_prefixes)
  5. Reject SSRF targets (localhost, private/link-local/loopback IPs,
     cloud metadata endpoints, non-http(s) schemes)
"""
import ipaddress
import socket
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from app.core.config import settings
from app.core.source_registry import ApprovedSource, create_discovered_source

ALLOWED_PROTOCOLS = {"http", "https"}

# Known cloud metadata / dangerous endpoints, blocked outright regardless of
# what DNS resolution says.
BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "169.254.169.254",
    "metadata",
}


@dataclass
class ValidationResult:
    is_valid: bool
    reason: Optional[str] = None
    matched_source: Optional[ApprovedSource] = None
    normalized_url: Optional[str] = None


# Well-Known Prefix for IPv4/IPv6 translation (RFC 6052)
NAT64_WELL_KNOWN_PREFIX = ipaddress.ip_network("64:ff9b::/96")


def _is_private_or_reserved_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    # Check IPv4-mapped IPv6 (::ffff:0:0/96, RFC 4291)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        v4 = ip.ipv4_mapped
        return (
            v4.is_private
            or v4.is_loopback
            or v4.is_link_local
            or v4.is_reserved
            or v4.is_multicast
            or v4.is_unspecified
        )

    # Check NAT64 Well-Known Prefix (64:ff9b::/96, RFC 6052)
    # The last 32 bits embed the destination IPv4 address.
    # Evaluate the embedded IPv4 address to prevent SSRF against private/loopback/reserved targets,
    # while allowing legitimate public destinations reached through NAT64 translation.
    if isinstance(ip, ipaddress.IPv6Address) and ip in NAT64_WELL_KNOWN_PREFIX:
        v4 = ipaddress.IPv4Address(ip.packed[-4:])
        return (
            v4.is_private
            or v4.is_loopback
            or v4.is_link_local
            or v4.is_reserved
            or v4.is_multicast
            or v4.is_unspecified
        )

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _resolves_to_disallowed_ip(hostname: str) -> bool:
    """Best-effort SSRF guard: resolve the hostname and reject if it maps to
    a private/loopback/link-local/reserved address (protects against DNS
    rebinding to internal infrastructure)."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # Cannot resolve -> cannot safely allow.
        return True
    if not infos:
        return True
    for info in infos:
        addr = info[4][0]
        if _is_private_or_reserved_ip(addr):
            return True
    return False


def _hostname_matches(hostname: str, allowed_domains: List[str]) -> bool:
    hostname = hostname.lower().rstrip(".")
    for domain in allowed_domains:
        domain = domain.lower().rstrip(".")
        if hostname == domain or hostname.endswith("." + domain):
            return True
    return False


def _path_matches(path: str, allowed_prefixes: List[str]) -> bool:
    if not allowed_prefixes:
        return True
    for prefix in allowed_prefixes:
        if prefix == "" or path.startswith(prefix):
            return True
    return False


def is_allowed_government_hostname(
    hostname: str,
    approved_sources: Optional[List[ApprovedSource]] = None,
) -> bool:
    """Check whether a hostname belongs to an allowed official Indian government domain:
    1. Ends with configured government suffixes (e.g., .gov.in, .nic.in).
    2. Matches verified non-gov.in government entities (e.g., sidbi.in, cgtmse.in, mudra.org.in).
    3. Matches any explicitly approved source domain.
    Rejects IP literals, private IPs, and blocked SSRF hostnames."""
    if not hostname:
        return False
    hostname = hostname.lower().rstrip(".")

    if hostname in BLOCKED_HOSTNAMES or hostname in ("localhost", "0.0.0.0"):
        return False
    if _is_private_or_reserved_ip(hostname):
        return False

    # 1. Configured government suffixes (.gov.in, .nic.in)
    for suffix in settings.allowed_gov_suffixes_list:
        clean_suffix = suffix.lower().rstrip(".")
        if not clean_suffix.startswith("."):
            clean_suffix = "." + clean_suffix
        if hostname.endswith(clean_suffix) or hostname == clean_suffix.lstrip("."):
            return True

    # 2. Configured extra allowed government domains
    for domain in settings.allowed_gov_domains_list:
        clean_domain = domain.lower().rstrip(".")
        if hostname == clean_domain or hostname.endswith("." + clean_domain):
            return True

    # 3. Existing approved sources
    if approved_sources:
        for source in approved_sources:
            if not source.enabled:
                continue
            if _hostname_matches(hostname, source.allowed_domains):
                return True

    return False


def validate_url(
    url: str,
    approved_sources: List[ApprovedSource],
    resolve_dns: bool = True,
    allow_gov_discovery: bool = False,
) -> ValidationResult:
    """Run the full validation chain against a candidate URL."""
    # 1. Parse
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return ValidationResult(False, "URL could not be parsed")

    if not parsed.scheme or not parsed.netloc:
        return ValidationResult(False, "Malformed URL (missing scheme/host)")

    # 2. Protocol
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_PROTOCOLS:
        return ValidationResult(False, f"Protocol '{scheme}' is not allowed")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return ValidationResult(False, "URL has no hostname")

    # SSRF: explicit blocklist + loopback names
    if hostname in BLOCKED_HOSTNAMES or hostname in ("localhost", "0.0.0.0"):
        return ValidationResult(False, f"Hostname '{hostname}' is blocked (SSRF protection)")

    # SSRF: literal IP in the URL that is private/loopback/reserved
    if _is_private_or_reserved_ip(hostname):
        return ValidationResult(False, f"Host '{hostname}' resolves to a disallowed IP range")

    # 3. Domain match against approved registry (enabled sources only)
    matched_source = None
    for source in approved_sources:
        if not source.enabled:
            continue
        if _hostname_matches(hostname, source.allowed_domains):
            matched_source = source
            break

    # If not in approved sources, check discovery allowlist if enabled
    if matched_source is None and allow_gov_discovery:
        if is_allowed_government_hostname(hostname, approved_sources):
            matched_source = create_discovered_source(hostname)

    if matched_source is None:
        return ValidationResult(False, f"Domain '{hostname}' is not an approved government source")

    # 4. Path scope
    if not _path_matches(parsed.path or "/", matched_source.allowed_path_prefixes):
        return ValidationResult(False, "URL path is outside the approved scope for this source")

    # 5. SSRF via DNS resolution (best-effort; skip in offline/test environments)
    if resolve_dns and _resolves_to_disallowed_ip(hostname):
        return ValidationResult(False, "Hostname resolves to a private/internal IP address")

    normalized = parsed._replace(fragment="").geturl()
    return ValidationResult(True, matched_source=matched_source, normalized_url=normalized)


def validate_discovered_url(
    url: str,
    approved_sources: Optional[List[ApprovedSource]] = None,
    resolve_dns: bool = True,
) -> ValidationResult:
    """Validate candidate URLs discovered during automated government discovery.
    Ensures domain matches official government allowlists and passes full SSRF
    and protocol validation."""
    return validate_url(
        url,
        approved_sources=approved_sources or [],
        resolve_dns=resolve_dns,
        allow_gov_discovery=True,
    )


# Root homepages and informational portals that must NEVER be used as direct application links
_GENERIC_HOMEPAGE_DOMAINS = {
    "msme.gov.in",
    "www.msme.gov.in",
    "cgtmse.in",
    "www.cgtmse.in",
    "mudra.org.in",
    "www.mudra.org.in",
    "sidbi.in",
    "www.sidbi.in",
    "doe.gov.in",
    "www.doe.gov.in",
    "mca.gov.in",
    "www.mca.gov.in",
    "gst.gov.in",
    "www.gst.gov.in",
    "industries.telangana.gov.in",
    "dcmsme.gov.in",
    "www.dcmsme.gov.in",
    "startupindia.gov.in",
    "www.startupindia.gov.in",
}


def verify_direct_application_url(
    url: Optional[str],
    approved_sources: Optional[List[ApprovedSource]] = None,
) -> Optional[str]:
    """Verify that a URL represents a genuine, official direct application portal
    for a scheme.

    Rules:
      1. Must be a valid string starting with http:// or https://.
      2. Must NOT be empty or whitespace.
      3. Must NOT end with .pdf or be a static document.
      4. Must belong to an official government or approved scheme domain.
      5. Must NOT be a general information page, government homepage, or root domain
         (e.g., https://msme.gov.in/, https://www.cgtmse.in/, https://www.mudra.org.in/).
      6. If it cannot be verified as a direct application link, returns None.
    """
    if not url or not isinstance(url, str):
        return None
    trimmed = url.strip()
    if not trimmed:
        return None

    try:
        parsed = urlparse(trimmed)
    except Exception:
        return None

    if parsed.scheme.lower() not in ALLOWED_PROTOCOLS:
        return None

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return None

    # Check SSRF/blocked
    if hostname in BLOCKED_HOSTNAMES or hostname in ("localhost", "0.0.0.0") or _is_private_or_reserved_ip(hostname):
        return None

    # Check domain is official government / authorized scheme portal
    if not is_allowed_government_hostname(hostname, approved_sources):
        return None

    # Rejection 1: PDF or document files
    path = parsed.path or ""
    path_lower = path.lower()
    if (
        path_lower.endswith(".pdf")
        or ".pdf" in path_lower
        or path_lower.endswith(".doc")
        or path_lower.endswith(".docx")
    ):
        return None

    # Rejection 2: General homepage or general information page
    norm_path = path.rstrip("/")
    if hostname in _GENERIC_HOMEPAGE_DOMAINS:
        if norm_path in ("", "/en", "/offerings/schemes-and-services", "/pmegp"):
            return None

    # Generic check: if path is root and domain is purely a top-level ministry or organization site
    if norm_path in ("", "/en"):
        # Specific subdomains that are themselves dedicated online portals
        # are valid application systems.
        dedicated_portal_hosts = {
            "cluster.dcmsme.gov.in",
            "seedfund.startupindia.gov.in",
            "ipass.telangana.gov.in",
            "odr.msme.gov.in",
            "samadhaan.msme.gov.in",
            "gem.gov.in",
            "pmegp.msme.gov.in",
            "zed.msme.gov.in",
            "kviconline.gov.in",
            "www.kviconline.gov.in",
        }
        if hostname not in dedicated_portal_hosts:
            return None

    return trimmed

