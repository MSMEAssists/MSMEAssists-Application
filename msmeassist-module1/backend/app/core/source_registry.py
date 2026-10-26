"""
Approved Government Source Registry.

This is the single source of truth for which domains/paths the ingestion
pipeline is permitted to fetch content from.

Nothing outside this registry (and passing app.core.url_validator checks)
may contribute knowledge to the vector database, no matter how it was
discovered (including via search engines, which may only be used for
discovery, never as a knowledge source themselves).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ApprovedSource:
    source_id: str
    name: str
    organization: str
    base_url: str
    allowed_domains: list
    allowed_path_prefixes: list
    enabled: bool = True
    notes: Optional[str] = None


# NOTE:
# This in-memory list is the seed/default registry used on first run.
#
# The admin API and DEFAULT_SOURCE_REPOSITORY allow enabling/disabling
# and adding further sources at runtime. Every addition must still pass
# the same domain/protocol/SSRF validation in app.core.url_validator.


DEFAULT_APPROVED_SOURCES = [

    # ============================================================
    # MINISTRY OF MSME
    # ============================================================

    ApprovedSource(
        source_id="msme",
        name="Ministry of MSME",
        organization="Ministry of Micro, Small and Medium Enterprises, Govt. of India",
        base_url="https://www.msme.gov.in/",
        allowed_domains=[
            "msme.gov.in",
            "www.msme.gov.in",
            "mudra.org.in",
            "www.mudra.org.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official Ministry of MSME website containing schemes, services, guidelines and notifications.",
    ),

    # ============================================================
    # DEVELOPMENT COMMISSIONER - MSME
    # ============================================================

    ApprovedSource(
        source_id="dcmsme",
        name="Development Commissioner - MSME",
        organization="Office of Development Commissioner, Ministry of MSME, Govt. of India",
        base_url="https://dcmsme.gov.in/",
        allowed_domains=[
            "dcmsme.gov.in",
            "www.dcmsme.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official Development Commissioner MSME website containing scheme guidelines and implementation information.",
    ),

    # ============================================================
    # SIDBI
    # ============================================================

    ApprovedSource(
        source_id="sidbi",
        name="Small Industries Development Bank of India (SIDBI)",
        organization="SIDBI",
        base_url="https://www.sidbi.in/",
        allowed_domains=[
            "sidbi.in",
            "www.sidbi.in",
            "cgtmse.in",
            "www.cgtmse.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official SIDBI website containing MSME loan, working capital, project funding and green finance products.",
    ),

    # ============================================================
    # DGFT
    # ============================================================

    ApprovedSource(
        source_id="dgft",
        name="Directorate General of Foreign Trade (DGFT)",
        organization="Ministry of Commerce and Industry, Govt. of India",
        base_url="https://www.dgft.gov.in/",
        allowed_domains=[
            "dgft.gov.in",
            "www.dgft.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official DGFT website containing foreign trade, export/import and regulatory information.",
    ),

    # ============================================================
    # GST
    # ============================================================

    ApprovedSource(
        source_id="gst",
        name="Goods and Services Tax (GST) Portal",
        organization="Goods and Services Tax Network, Govt. of India",
        base_url="https://www.gst.gov.in/",
        allowed_domains=[
            "gst.gov.in",
            "www.gst.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official GST portal containing registration, compliance and tax-related information.",
    ),

    # ============================================================
    # MINISTRY OF CORPORATE AFFAIRS
    # ============================================================

    ApprovedSource(
        source_id="mca",
        name="Ministry of Corporate Affairs (MCA)",
        organization="Ministry of Corporate Affairs, Govt. of India",
        base_url="https://www.mca.gov.in/",
        allowed_domains=[
            "mca.gov.in",
            "www.mca.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official MCA website containing company, LLP and corporate compliance information.",
    ),

    # ============================================================
    # DEPARTMENT OF EXPENDITURE
    # ============================================================

    ApprovedSource(
        source_id="doe",
        name="Department of Expenditure",
        organization="Ministry of Finance, Govt. of India",
        base_url="https://doe.gov.in/",
        allowed_domains=[
            "doe.gov.in",
            "www.doe.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official Department of Expenditure website containing government financial and procurement information.",
    ),

    # ============================================================
    # GOVERNMENT E-PROCUREMENT
    # ============================================================

    ApprovedSource(
        source_id="eprocure",
        name="Government e-Procurement System (GePNIC / e-Tenders)",
        organization="National Informatics Centre, Govt. of India",
        base_url="https://etenders.gov.in/eprocure/app",
        allowed_domains=[
            "etenders.gov.in",
            "www.etenders.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official Government e-Procurement portal.",
    ),

    # ============================================================
    # UDYAM REGISTRATION
    # ============================================================

    ApprovedSource(
        source_id="udyam",
        name="Udyam Registration",
        organization="Ministry of Micro, Small and Medium Enterprises, Govt. of India",
        base_url="https://udyamregistration.gov.in/",
        allowed_domains=[
            "udyamregistration.gov.in",
            "www.udyamregistration.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official Udyam Registration portal for MSME registration and related information.",
    ),

    # ============================================================
    # MSME ONLINE DISPUTE RESOLUTION
    # ============================================================

    ApprovedSource(
        source_id="odr_msme",
        name="MSME Online Dispute Resolution",
        organization="Ministry of Micro, Small and Medium Enterprises, Govt. of India",
        base_url="https://odr.msme.gov.in/",
        allowed_domains=[
            "odr.msme.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official MSME Online Dispute Resolution portal.",
    ),

    # ============================================================
    # MY MSME
    # ============================================================

    ApprovedSource(
        source_id="my_msme",
        name="MyMSME",
        organization="Ministry of Micro, Small and Medium Enterprises, Govt. of India",
        base_url="https://my.msme.gov.in/",
        allowed_domains=[
            "my.msme.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official MyMSME portal providing MSME scheme and service-related information.",
    ),

    # ============================================================
    # STARTUP INDIA
    # ============================================================

    ApprovedSource(
        source_id="startupindia",
        name="Startup India",
        organization="Department for Promotion of Industry and Internal Trade, Govt. of India",
        base_url="https://www.startupindia.gov.in/",
        allowed_domains=[
            "startupindia.gov.in",
            "www.startupindia.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official Startup India portal containing startup schemes, policies, regulatory updates and support information.",
    ),

    # ============================================================
    # STARTUP INDIA SEED FUND
    # ============================================================

    ApprovedSource(
        source_id="seedfund",
        name="Startup India Seed Fund",
        organization="Government of India",
        base_url="https://seedfund.startupindia.gov.in/",
        allowed_domains=[
            "seedfund.startupindia.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official Startup India Seed Fund portal.",
    ),

    # ============================================================
    # TELANGANA GOVERNMENT
    # ============================================================

    ApprovedSource(
        source_id="telangana",
        name="Telangana Government Services",
        organization="Government of Telangana",
        base_url="https://www.telangana.gov.in/",
        allowed_domains=[
            "telangana.gov.in",
            "www.telangana.gov.in",
            "industries.telangana.gov.in",
        ],
        allowed_path_prefixes=[""],
        notes="Official Telangana Government services and industries portal.",
    ),
]


def derive_source_id(hostname: str) -> str:
    """Generate a clean, deterministic identifier from a government hostname."""
    clean = hostname.lower().strip(".").removeprefix("www.")
    # Strip known suffixes for concise IDs where practical
    for suffix in [".gov.in", ".nic.in"]:
        if clean.endswith(suffix):
            clean = clean[:-len(suffix)]
            break
    parts = [p for p in clean.replace("-", "_").replace(".", "_").split("_") if p]
    base_name = "_".join(parts) if parts else "portal"
    return f"gov_{base_name}"[:32]


def derive_source_name(hostname: str) -> str:
    """Generate a human-readable title from a government hostname."""
    clean = hostname.lower().strip(".").removeprefix("www.")
    parts = clean.split(".")
    domain_part = parts[0] if parts else clean
    words = [w.capitalize() for w in domain_part.replace("-", " ").replace("_", " ").split()]
    title = " ".join(words)
    return f"{title} ({hostname})" if title else f"Government Portal ({hostname})"


def create_discovered_source(
    url_or_domain: str,
    name: Optional[str] = None,
    organization: Optional[str] = None,
) -> ApprovedSource:
    """Construct an ApprovedSource record for a newly discovered government portal."""
    from urllib.parse import urlparse

    target = url_or_domain.strip()
    if "://" not in target:
        target = f"https://{target}"
    parsed = urlparse(target)
    hostname = (parsed.hostname or url_or_domain).lower().strip(".")

    sid = derive_source_id(hostname)
    source_name = name or derive_source_name(hostname)
    source_org = organization or "Government of India / State Government"
    base_url = f"{parsed.scheme or 'https'}://{hostname}/"

    domains = [hostname]
    if hostname.startswith("www."):
        domains.append(hostname[4:])
    else:
        domains.append(f"www.{hostname}")

    return ApprovedSource(
        source_id=sid,
        name=source_name,
        organization=source_org,
        base_url=base_url,
        allowed_domains=domains,
        allowed_path_prefixes=[""],
        enabled=True,
        notes="Automatically discovered official government source",
    )