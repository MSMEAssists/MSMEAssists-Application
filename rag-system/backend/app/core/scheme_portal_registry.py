"""
Official Government Scheme Application Portal and Metadata Registry.

Provides authoritative resolution of:
1. Direct online application portals (e.g. PMEGP, ZED, Samadhaan, TS-iPASS, Startup India Seed Fund)
2. Scheme details and guidelines URLs (preserving scheme-specific links, never domain homepages)
3. Issuing ministry / nodal authority
4. Verification status ("verified" | "verified_offline" | "unverified")

Ensures:
- Scheme application URLs are never replaced with generic homepages (e.g., msme.gov.in).
- Offline / bank-routed schemes (e.g., CGTMSE, MUDRA) evaluate to None for application_portal_url.
- Dynamic link extraction from scraped HTML pages / guidelines finds genuine application portals.
- Schemes only receive their own verified application URLs, never another scheme's URL.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

from app.core.url_validator import verify_direct_application_url


@dataclass
class SchemePortalMetadata:
    scheme_name: str
    official_source_url: str
    scheme_details_url: str
    application_portal_url: Optional[str]
    issuing_authority: str
    verification_status: str  # "verified" | "verified_offline" | "unverified"
    aliases: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


# Authoritative Registry of Central and State MSME Schemes
CANONICAL_SCHEME_REGISTRY: Dict[str, SchemePortalMetadata] = {
    "pmegp": SchemePortalMetadata(
        scheme_name="Prime Minister's Employment Generation Programme (PMEGP)",
        official_source_url="https://www.msme.gov.in/offerings/schemes-and-services",
        scheme_details_url="https://www.msme.gov.in/offerings/schemes-and-services/details/prime-ministers-employment-generation-programme-pmegp-xITN2YDN2QWa",
        application_portal_url="https://pmegp.msme.gov.in/Home/Homepage",
        issuing_authority="Ministry of Micro, Small and Medium Enterprises, Govt. of India",
        verification_status="verified",
        aliases=[
            "pmegp",
            "prime minister employment generation",
            "prime minister's employment generation programme",
            "prime minister employment generation programme",
            "kvic pmegp",
            "pmegpeportal",
        ],
        keywords=["pmegp", "margin money subsidy", "kvic", "coir board", "dic", "50 lakh", "20 lakh"],
    ),
    "zed": SchemePortalMetadata(
        scheme_name="MSME Sustainable (ZED) Certification Scheme",
        official_source_url="https://zed.msme.gov.in/",
        scheme_details_url="https://zed.msme.gov.in/",
        application_portal_url="https://zed.msme.gov.in/account/register",
        issuing_authority="Ministry of Micro, Small and Medium Enterprises, Govt. of India",
        verification_status="verified",
        aliases=[
            "zed",
            "zero defect zero effect",
            "zero defect",
            "msme sustainable zed",
            "zed certification",
        ],
        keywords=["zed", "zero defect", "sustainable manufacturing", "bronze silver gold", "certification subsidy"],
    ),
    "samadhaan": SchemePortalMetadata(
        scheme_name="MSME Samadhaan — Delayed Payment Monitoring System (MSEFC)",
        official_source_url="https://samadhaan.msme.gov.in/",
        scheme_details_url="https://odr.msme.gov.in/",
        application_portal_url="https://samadhaan.msme.gov.in/MyMsme/MSEFC/MSEFC_Welcome.aspx",
        issuing_authority="Ministry of Micro, Small and Medium Enterprises, Govt. of India",
        verification_status="verified",
        aliases=[
            "samadhaan",
            "msme samadhaan",
            "delayed payment",
            "delayed payments",
            "msefc",
            "section 16",
            "online dispute resolution",
            "odr",
        ],
        keywords=["samadhaan", "delayed payment", "msefc", "buyer dues", "45 days", "compound interest"],
    ),
    "mse_cdp": SchemePortalMetadata(
        scheme_name="Micro and Small Enterprises Cluster Development Programme (MSE-CDP)",
        official_source_url="https://cluster.dcmsme.gov.in/",
        scheme_details_url="https://cluster.dcmsme.gov.in/",
        application_portal_url="https://cluster.dcmsme.gov.in/",
        issuing_authority="Office of Development Commissioner (MSME), Govt. of India",
        verification_status="verified",
        aliases=[
            "mse-cdp",
            "mse cdp",
            "cluster development programme",
            "common facility center",
            "cfc",
        ],
        keywords=["cluster development", "mse-cdp", "common facility", "infrastructure development"],
    ),
    "sisfs": SchemePortalMetadata(
        scheme_name="Startup India Seed Fund Scheme (SISFS)",
        official_source_url="https://seedfund.startupindia.gov.in/",
        scheme_details_url="https://seedfund.startupindia.gov.in/",
        application_portal_url="https://seedfund.startupindia.gov.in/",
        issuing_authority="Department for Promotion of Industry and Internal Trade (DPIIT)",
        verification_status="verified",
        aliases=[
            "sisfs",
            "startup india seed fund",
            "seed fund scheme",
        ],
        keywords=["seed fund", "sisfs", "proof of concept", "prototype", "incubator grant"],
    ),
    "ts_ipass": SchemePortalMetadata(
        scheme_name="Telangana State Industrial Project Approval and Self-Certification System (TS-iPASS)",
        official_source_url="https://ipass.telangana.gov.in/",
        scheme_details_url="https://ipass.telangana.gov.in/",
        application_portal_url="https://ipass.telangana.gov.in/",
        issuing_authority="Department of Industries & Commerce, Government of Telangana",
        verification_status="verified",
        aliases=[
            "ts-ipass",
            "ts ipass",
            "ipass",
            "t-idea",
            "t-pride",
            "telangana industrial policy",
        ],
        keywords=["ts-ipass", "t-idea", "t-pride", "single window clearance", "telangana industrial"],
    ),
    "standup_india": SchemePortalMetadata(
        scheme_name="Stand-Up India Scheme for Greenfield Enterprises",
        official_source_url="https://www.standupmitra.in/",
        scheme_details_url="https://www.standupmitra.in/",
        application_portal_url="https://www.standupmitra.in/Login/Register",
        issuing_authority="Department of Financial Services & SIDBI",
        verification_status="verified",
        aliases=[
            "stand-up india",
            "standup india",
            "standupmitra",
        ],
        keywords=["stand-up india", "standup india", "sc st women entrepreneurs", "greenfield enterprise", "10 lakh to 1 crore"],
    ),
    "cgtmse": SchemePortalMetadata(
        scheme_name="Credit Guarantee Fund Trust for Micro and Small Enterprises (CGTMSE)",
        official_source_url="https://cgtmse.in/",
        scheme_details_url="https://cgtmse.in/",
        application_portal_url=None,  # Applied via Member Lending Institutions (Banks/NBFCs)
        issuing_authority="Credit Guarantee Fund Trust for Micro and Small Enterprises (CGTMSE)",
        verification_status="verified_offline",
        aliases=[
            "cgtmse",
            "credit guarantee fund trust",
            "credit guarantee scheme",
        ],
        keywords=["cgtmse", "collateral-free loan", "credit guarantee", "member lending institutions", "mli"],
    ),
    "mudra": SchemePortalMetadata(
        scheme_name="Pradhan Mantri MUDRA Yojana (PMMY)",
        official_source_url="https://www.mudra.org.in/",
        scheme_details_url="https://www.mudra.org.in/",
        application_portal_url=None,  # Applied via Scheduled Commercial Banks, RRBs, MFIs
        issuing_authority="Micro Units Development and Refinance Agency Ltd. (MUDRA)",
        verification_status="verified_offline",
        aliases=[
            "mudra",
            "pmmy",
            "pradhan mantri mudra yojana",
            "shishu kishore tarun",
        ],
        keywords=["mudra", "pmmy", "shishu", "kishore", "tarun", "micro units refinance"],
    ),
    "sfurti": SchemePortalMetadata(
        scheme_name="Scheme of Fund for Regeneration of Traditional Industries (SFURTI)",
        official_source_url="https://cluster.dcmsme.gov.in/",
        scheme_details_url="https://cluster.dcmsme.gov.in/",
        application_portal_url="https://cluster.dcmsme.gov.in/",
        issuing_authority="Ministry of Micro, Small and Medium Enterprises, Govt. of India",
        verification_status="verified",
        aliases=["sfurti", "regeneration of traditional industries"],
        keywords=["sfurti", "artisans", "traditional industries", "khadi cluster"],
    ),
}


def _match_single_text(target: str) -> Optional[SchemePortalMetadata]:
    if not target:
        return None
    target_lower = target.lower()

    # Exact scheme token checks
    if re.search(r"\b(pmegp|prime\s*minister(?:'s)?\s*employment\s*generation)\b", target_lower):
        return CANONICAL_SCHEME_REGISTRY["pmegp"]
    if re.search(r"\b(cgtmse|credit\s*guarantee\s*(?:fund\s*trust|scheme))\b", target_lower):
        return CANONICAL_SCHEME_REGISTRY["cgtmse"]
    if re.search(r"\b(mudra|pmmy|pradhan\s*mantri\s*mudra)\b", target_lower):
        return CANONICAL_SCHEME_REGISTRY["mudra"]
    if re.search(r"\b(zed|zero\s*defect(?:\s*zero\s*effect)?)\b", target_lower):
        return CANONICAL_SCHEME_REGISTRY["zed"]
    if re.search(r"\b(samadhaan|msefc|delayed\s*payment(?:s)?|online\s*dispute\s*resolution)\b", target_lower):
        return CANONICAL_SCHEME_REGISTRY["samadhaan"]
    if re.search(r"\b(sisfs|seed\s*fund\s*scheme|startup\s*india\s*seed)\b", target_lower):
        return CANONICAL_SCHEME_REGISTRY["sisfs"]
    if re.search(r"\b(ts-?ipass|t-?idea|t-?pride)\b", target_lower):
        return CANONICAL_SCHEME_REGISTRY["ts_ipass"]
    if re.search(r"\b(stand-?up\s*india|standupmitra)\b", target_lower):
        return CANONICAL_SCHEME_REGISTRY["standup_india"]
    if re.search(r"\b(mse-?cdp|cluster\s*development\s*programme)\b", target_lower):
        return CANONICAL_SCHEME_REGISTRY["mse_cdp"]
    if re.search(r"\b(sfurti|regeneration\s*of\s*traditional)\b", target_lower):
        return CANONICAL_SCHEME_REGISTRY["sfurti"]

    # Match against aliases
    for scheme_meta in CANONICAL_SCHEME_REGISTRY.values():
        for alias in scheme_meta.aliases:
            if re.search(rf"\b{re.escape(alias)}\b", target_lower):
                return scheme_meta

    return None


def match_canonical_scheme(
    title: Optional[str] = None,
    text: Optional[str] = None,
    url: Optional[str] = None,
) -> Optional[SchemePortalMetadata]:
    """Matches title, url, or text against the canonical scheme registry.
    Title has highest priority to prevent cross-scheme URL pollution."""
    # 1. Match title first (highest authority on document subject)
    if title:
        m = _match_single_text(title)
        if m:
            return m

    # 2. Match URL second
    if url:
        m = _match_single_text(url)
        if m:
            return m

    # 3. Match text snippet third
    if text:
        m = _match_single_text(text[:500])
        if m:
            return m

    return None


def extract_candidate_application_urls(
    links: List[str],
    text: Optional[str] = None,
) -> List[str]:
    """Extracts candidate application portal URLs from extracted HTML links and text.
    Looks for links containing application indicators (apply, register, portal, etc.)
    or pointing to dedicated official application subdomains."""
    candidates = []
    seen = set()

    # 1. Inspect extracted links
    for link in links:
        if not link or not isinstance(link, str):
            continue
        trimmed = link.strip()
        if trimmed in seen:
            continue
        try:
            parsed = urlparse(trimmed)
            host = (parsed.hostname or "").lower()
            path = (parsed.path or "").lower()
            full_lower = trimmed.lower()

            # Dedicated application portal hosts
            if (
                host.startswith("pmegp.")
                or "kviconline.gov.in" in host
                or "zed.msme.gov.in" in host
                or "samadhaan.msme.gov.in" in host
                or "standupmitra.in" in host
                or "seedfund.startupindia.gov.in" in host
                or "ipass.telangana.gov.in" in host
                or "cluster.dcmsme.gov.in" in host
            ):
                candidates.append(trimmed)
                seen.add(trimmed)
                continue

            # General links with application keywords in path/query
            if any(k in path or k in full_lower for k in ("apply", "application", "register", "registration", "portal")):
                if not (path.endswith(".pdf") or path.endswith(".doc")):
                    candidates.append(trimmed)
                    seen.add(trimmed)
        except Exception:
            continue

    # 2. Extract potential URL strings embedded in page text
    if text:
        text_urls = re.findall(r"https?://[^\s<>\"'()]+", text)
        for u in text_urls:
            u_clean = u.rstrip(".,;:)")
            if u_clean not in seen:
                try:
                    p = urlparse(u_clean)
                    h = (p.hostname or "").lower()
                    if h.endswith(".gov.in") or h.endswith(".nic.in") or "standupmitra.in" in h or "cgtmse.in" in h:
                        candidates.append(u_clean)
                        seen.add(u_clean)
                except Exception:
                    continue

    return candidates


def resolve_scheme_metadata(
    title: Optional[str] = None,
    text: Optional[str] = None,
    url: Optional[str] = None,
    candidate_links: Optional[List[str]] = None,
    local_meta: Optional[Any] = None,
) -> SchemePortalMetadata:
    """Authoritative, dynamic resolution of scheme metadata and verified application portal.

    Priority order:
    1. Canonical scheme match (PMEGP, ZED, Samadhaan, etc.) with verified official portal.
    2. Local metadata attached to registered local PDF documents.
    3. Extracted candidate links validated against verify_direct_application_url.
    4. Fallback to unverified / offline status, preserving the exact original source URL.
    """
    canonical = match_canonical_scheme(title=title, text=text, url=url)
    if canonical:
        # Canonical match found — return verified metadata
        details_url = url or canonical.scheme_details_url
        if details_url.endswith(".pdf") or "offerings" in (url or ""):
            details_url = canonical.scheme_details_url or url or canonical.official_source_url

        return SchemePortalMetadata(
            scheme_name=canonical.scheme_name,
            official_source_url=canonical.official_source_url,
            scheme_details_url=details_url,
            application_portal_url=canonical.application_portal_url,
            issuing_authority=canonical.issuing_authority,
            verification_status=canonical.verification_status,
            aliases=canonical.aliases,
            keywords=canonical.keywords,
        )

    # Check local metadata if provided
    if local_meta:
        app_url = getattr(local_meta, "official_application_url", None)
        verified_app = verify_direct_application_url(app_url) if app_url else None
        return SchemePortalMetadata(
            scheme_name=getattr(local_meta, "title", title or "Government Scheme"),
            official_source_url=getattr(local_meta, "official_url", url or ""),
            scheme_details_url=getattr(local_meta, "provenance_webpage_url", None) or getattr(local_meta, "official_url", url or ""),
            application_portal_url=verified_app,
            issuing_authority=getattr(local_meta, "organization", "Government of India"),
            verification_status="verified" if verified_app else "unverified",
        )

    # Check candidate links if provided (e.g. from scraping a new scheme page)
    if candidate_links:
        for link in extract_candidate_application_urls(candidate_links, text):
            verified = verify_direct_application_url(link)
            if verified:
                return SchemePortalMetadata(
                    scheme_name=title or "Government Scheme",
                    official_source_url=url or "",
                    scheme_details_url=url or "",
                    application_portal_url=verified,
                    issuing_authority="Government of India",
                    verification_status="verified",
                )

    # Default fallback: preserve original source, clearly unverified online application link
    return SchemePortalMetadata(
        scheme_name=title or "Government Scheme",
        official_source_url=url or "",
        scheme_details_url=url or "",
        application_portal_url=None,
        issuing_authority="Government of India",
        verification_status="unverified",
    )
