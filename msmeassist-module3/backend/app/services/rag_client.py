"""
HTTP Client for communicating with the Government Knowledge RAG System (Port 8001).
"""
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.models.schemas import CandidateScheme

logger = logging.getLogger(__name__)

_GENERIC_HOMEPAGES = {
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


def clean_direct_application_url(url: Optional[str]) -> Optional[str]:
    """Validate that a URL is a genuine official online application link.
    Returns None if missing, PDF, generic homepage, or non-portal information page."""
    if not url or not isinstance(url, str):
        return None
    trimmed = url.strip()
    if not trimmed or not (trimmed.startswith("http://") or trimmed.startswith("https://")):
        return None
    lower = trimmed.lower()
    if ".pdf" in lower or lower.endswith(".doc") or lower.endswith(".docx"):
        return None

    from urllib.parse import urlparse
    try:
        parsed = urlparse(trimmed)
    except Exception:
        return None

    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").rstrip("/")

    # Disallow known generic root homepages
    if host in _GENERIC_HOMEPAGES and path in ("", "/en", "/offerings/schemes-and-services", "/pmegp"):
        return None

    # Disallow general root domain of ministry unless it's a dedicated portal subdomain
    if path in ("", "/en"):
        dedicated = {
            "cluster.dcmsme.gov.in",
            "seedfund.startupindia.gov.in",
            "ipass.telangana.gov.in",
            "odr.msme.gov.in",
            "samadhaan.msme.gov.in",
            "gem.gov.in",
        }
        if host not in dedicated:
            return None

    return trimmed


# Official fallback schemes with grounded .gov.in URLs for offline/cold-start resilience
FALLBACK_SCHEMES: List[CandidateScheme] = [
    CandidateScheme(
        id="pmegp_subsidy",
        title="Prime Minister Employment Generation Programme (PMEGP)",
        organization="Ministry of MSME / KVIC",
        official_url="https://msme.gov.in/pmegp",
        official_application_url="https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp",
        knowledge_type="SUBSIDY",
        snippet="Credit-linked subsidy scheme offering 15% to 35% margin money subsidy on project costs up to Rs 50 lakh for manufacturing and Rs 20 lakh for services.",
        benefits=[
            "Margin money subsidy up to 35% for rural and special category (women, SC, ST) entrepreneurs",
            "Term loan assistance through commercial and rural banks with low promoter contribution (5-10%)",
            "Covers manufacturing units up to Rs 50 Lakhs and service units up to Rs 20 Lakhs",
        ],
        eligibility_criteria=[
            "Any individual above 18 years of age with at least VIII standard pass for projects above Rs 10 lakh in mfg",
            "Self Help Groups and institutions registered under Societies Registration Act",
            "Only new projects are eligible under PMEGP-1",
        ],
        retrieval_score=0.92,
    ),
    CandidateScheme(
        id="cgtmse_credit",
        title="Credit Guarantee Fund Trust for Micro and Small Enterprises (CGTMSE)",
        organization="Ministry of MSME & SIDBI",
        official_url="https://www.cgtmse.in/",
        official_application_url=None,  # Applied via Member Lending Institutions (Banks/NBFCs)
        knowledge_type="LOAN",
        snippet="Collateral-free credit facility for micro and small enterprises with guarantee cover up to Rs 500 lakh (Rs 5 Crore) with enhanced 85% coverage for women entrepreneurs.",
        benefits=[
            "Collateral-free and third-party-guarantee-free term loans and working capital",
            "Guarantee coverage up to 85% for micro enterprises and women-owned units",
            "Covers credit facilities up to Rs 5 Crore with reduced annual guarantee fees",
        ],
        eligibility_criteria=[
            "New and existing Micro and Small Enterprises engaged in manufacturing or service activity",
            "Valid Udyam Registration certificate",
            "Eligible lending institutions (scheduled commercial banks, NBFCs, RRBs)",
        ],
        retrieval_score=0.88,
    ),
    CandidateScheme(
        id="msme_champions_zed",
        title="MSME Champions Scheme — Zero Defect Zero Effect (ZED) Certification",
        organization="Ministry of MSME",
        official_url="https://zed.msme.gov.in/",
        official_application_url="https://zed.msme.gov.in/account/register",
        knowledge_type="SCHEME",
        snippet="Provides up to 80% financial subsidy on certification costs for MSMEs adopting sustainable manufacturing, zero defect quality, and energy-efficient environmental practices.",
        benefits=[
            "Subsidy on certification cost: 80% for Micro, 60% for Small, and 50% for Medium enterprises",
            "Additional 10% subsidy for Women/SC/ST owned enterprises and enterprises in NER/Hilly areas",
            "Concession on bank processing fees and interest rates for ZED certified units",
        ],
        eligibility_criteria=[
            "All manufacturing MSMEs with valid Udyam Registration",
            "Commitment to sustainability, quality standards, and environmental compliance",
        ],
        retrieval_score=0.84,
    ),
    CandidateScheme(
        id="stand_up_india",
        title="Stand-Up India Scheme for Green-field Enterprises",
        organization="Department of Financial Services / SIDBI",
        official_url="https://www.standupmitra.in/",
        official_application_url="https://www.standupmitra.in/Login/Register",
        knowledge_type="LOAN",
        snippet="Facilitates bank loans between Rs 10 lakh and Rs 1 Crore to at least one SC or ST borrower and at least one woman borrower per bank branch for greenfield enterprises.",
        benefits=[
            "Composite loan (term loan and working capital) between Rs 10 lakh and Rs 1 Crore",
            "Margin money requirement reduced to 15% with convergence from central/state schemes",
            "Repayable in 7 years with a maximum moratorium period of 18 months",
        ],
        eligibility_criteria=[
            "SC/ST and/or women entrepreneurs above 18 years of age",
            "Only for greenfield (first-time venture) manufacturing, services, agri-allied, or trading",
            "In non-individual enterprises, 51% shareholding must be held by SC/ST or woman entrepreneur",
        ],
        retrieval_score=0.81,
    ),
    CandidateScheme(
        id="mudra_kishore_tarun",
        title="Pradhan Mantri MUDRA Yojana (PMMY) — Kishore & Tarun",
        organization="Department of Financial Services / MUDRA",
        official_url="https://www.mudra.org.in/",
        official_application_url=None,  # Applied via commercial banks/RRBs/MFIs
        knowledge_type="LOAN",
        snippet="Provides institutional refinancing loans up to Rs 20 lakh to non-corporate, non-farm small/micro enterprises across Shishu, Kishore, and Tarun categories.",
        benefits=[
            "Kishore category: Loans above Rs 50,000 and up to Rs 5 Lakhs for business expansion",
            "Tarun category: Loans above Rs 5 Lakhs and up to Rs 10-20 Lakhs",
            "Zero processing fee and no collateral required",
        ],
        eligibility_criteria=[
            "Non-corporate small business segment (NCSBS) comprising micro units",
            "Small manufacturing units, shopkeepers, fruit/vegetable vendors, artisans, and service providers",
        ],
        retrieval_score=0.79,
    ),
]



class RagClient:
    """Consumes official scheme knowledge chunks and retrieval results from RAG System on port 8001."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.rag_base_url.rstrip("/")

    async def fetch_candidates(self, query: str, top_k: int = 5) -> List[CandidateScheme]:
        """
        Retrieves candidate schemes from RAG service.
        Falls back to curated official schemes if RAG service is unreachable or indexing is empty.
        """
        candidates: List[CandidateScheme] = []
        results: List[Dict[str, Any]] = []

        # 1. Fast-path: In-process direct bridge if running within unified app
        try:
            from app.core.rag_bridge import inprocess_search
            results = await inprocess_search(query=query, top_k=top_k * 2, similarity_threshold=0.05)
        except Exception:
            results = []

        # 2. HTTP call fallback if in-process bridge not available
        if not results:
            url = f"{self.base_url}/api/retrieval/search"
            payload = {"query": query, "top_k": top_k * 2, "similarity_threshold": 0.05}
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        results = data if isinstance(data, list) else data.get("results", [])
            except Exception as e:
                logger.info(f"RAG search on {url} returned empty/offline ({e}); using verified official scheme corpus.")

        seen_urls = set()
        for r in results:
            raw_url = r.get("official_url") or r.get("url") or ""
            doc_url = raw_url.strip()
            if ".pdf" in doc_url.lower():
                if "etenders.gov.in" in doc_url:
                    doc_url = "https://etenders.gov.in/eprocure/app"
                elif "startupindia.gov.in" in doc_url:
                    doc_url = "https://www.startupindia.gov.in/content/sih/en/government-schemes.html"
                elif "msme.gov.in" in doc_url:
                    doc_url = "https://www.msme.gov.in/offerings/schemes-and-services"
                elif "sidbi.in" in doc_url:
                    doc_url = "https://www.sidbi.in/en/"
                else:
                    import re
                    m = re.match(r"(https?://[^/]+)/?", doc_url)
                    if m:
                        doc_url = m.group(1) + "/"

            title = r.get("title") or r.get("name") or "Government Program"
            if doc_url in seen_urls:
                continue
            seen_urls.add(doc_url)

            app_url = clean_direct_application_url(r.get("official_application_url"))

            candidates.append(
                CandidateScheme(
                    id=r.get("chunk_id") or r.get("document_id") or f"rag_{len(candidates)}",
                    title=title,
                    organization=r.get("source_organization", "Government of India"),
                    official_url=doc_url,
                    official_application_url=app_url,
                    knowledge_type=r.get("knowledge_type", "SCHEME"),
                    snippet=r.get("text", "")[:320],
                    benefits=[b for b in r.get("benefits", []) if b],
                    eligibility_criteria=[c for c in r.get("criteria", []) if c],
                    page_number=r.get("page_number"),
                    document_id=r.get("document_id"),
                    chunk_id=r.get("chunk_id"),
                    retrieval_score=float(r.get("score") or r.get("similarity_score") or 0.8),
                )
            )

        # If RAG returned fewer than 3 schemes, supplement from grounded fallback corpus
        if len(candidates) < top_k:
            existing_titles = {c.title.lower() for c in candidates}
            for fb in FALLBACK_SCHEMES:
                if fb.title.lower() not in existing_titles and len(candidates) < top_k:
                    candidates.append(fb)

        return candidates[:top_k]
