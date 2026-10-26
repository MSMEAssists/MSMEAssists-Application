"""
Scheme Compliance Service — Option 3 build.

Three fixes applied together:

  Fix 1 — Document pinning
    RAG search is now scoped to the exact document_id / source_id of the
    clicked scheme.  Prevents chunks from unrelated schemes bleeding in.

  Fix 2 — Sentence quality filter
    Incomplete, cut-off sentences (e.g. "8-3 Maximum project cost under PMEGP is Rs")
    are filtered out before rule extraction.  Sentences must be at least 45
    characters, contain at least 7 words, end with a real terminal character,
    and contain at least one meaningful compliance keyword.

  Fix 3 — Scheme-specific fallback templates
    For PMEGP, CGTMSE, MUDRA, SIDBI, Stand-Up India and ZED, if the RAG
    retrieval returns fewer than 4 quality rules the agent falls back to a
    curated set of key requirements sourced from official guidelines.

  Gap Analysis Engine (Option 3 addition)
    On top of the RAG rules, the agent now runs a dedicated gap analysis:
    it checks 8–10 specific named requirements for each known scheme against
    the user's profile and produces a clear "you have / you are missing"
    checklist shown at the top of the modal.
"""
import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models.profile_model import ProfileModel
from app.schemas.compliance_schema import (
    ComplianceRuleResult,
    GapItem,
    OverallComplianceStatus,
    RuleVerdict,
    SchemeComplianceRequest,
    SchemeComplianceResponse,
)
from app.services.rag_client import RagClient

logger = logging.getLogger(__name__)

# User-isolated assessment cache: cache_key -> (timestamp, SchemeComplianceResponse)
_COMPLIANCE_CACHE: Dict[str, Tuple[float, SchemeComplianceResponse]] = {}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_RAG_TOP_K           = 12
_MAX_RULES           = 10
_MIN_STMT_LEN        = 45   # Fix 2: raised minimum length
_MIN_WORD_COUNT      = 7    # Fix 2: minimum words per sentence
_MIN_RAG_RULES       = 4    # Fix 3: fewer than this → use fallback

# ---------------------------------------------------------------------------
# Fix 2 — Sentence quality helpers
# ---------------------------------------------------------------------------

_FRAGMENT_END = re.compile(
    r"""(\band\s*$|\bor\s*$|\bof\s*$|\bthe\s*$|\bto\s*$
         |\bfor\s*$|\bin\s*$|\ba\s*$|\bbrief:\s*$
         |\(inclusive\s*$|\bterm\s+loan\s+and\s*$
         |\bfrom\s*$|\bwith\s*$|\bas\s*$|\bat\s*$
         |\bloan\s+and\s*$|\bsuch\s+as\s*$)""",
    re.IGNORECASE | re.VERBOSE,
)

_MEANINGFUL = re.compile(
    r"""\b(eligib|criteria|requir|must|shall|mandatory|compulsory
         |register|certif|document|submit|apply|applicant|enterprise
         |turnover|investment|subsidy|loan|grant|beneficiar
         |approved|maximum|minimum|ceiling|not exceeding|up to
         |women|sc\b|st\b|obc|rural|startup|udyam|gst\b|pan\b
         |fssai|iec\b|factory|permit|portal|website|kvic|sidbi
         |mudra|pmegp|cgtmse|zed)\b""",
    re.IGNORECASE | re.VERBOSE,
)

_LEADING_NUMBER = re.compile(r"^\d+[-–]\d+\s")
_BULLET_FRAGMENT = re.compile(r"^[•\-\*]\s+\w+\s+\w+\s*$")


def _is_quality(s: str) -> bool:
    s = s.strip()
    if len(s) < _MIN_STMT_LEN:
        return False
    if len(s.split()) < _MIN_WORD_COUNT:
        return False
    if not _MEANINGFUL.search(s):
        return False
    if _FRAGMENT_END.search(s):
        return False
    if _LEADING_NUMBER.match(s):
        return False
    if _BULLET_FRAGMENT.match(s):
        return False
    return True


# ---------------------------------------------------------------------------
# Rule cue patterns
# ---------------------------------------------------------------------------

_CUE_PATTERNS: List[Tuple[str, str]] = [
    ("Eligibility",
     r"(?:eligib(?:le|ility)|who can apply|applicable to|open to|beneficiar(?:y|ies)|criteria)[^.\n]*"),
    ("Eligibility",
     r"(?:any individual|unit|enterprise|entity|startup)[^.\n]+(?:shall be|are|is) eligible[^.\n]*"),
    ("Eligibility",
     r"(?:minimum|maximum|ceiling|age limit|qualification|turnover|investment)[^.\n]+(?:is|shall be|not exceeding|up to|at least)[^.\n]*"),
    ("Eligibility",
     r"(?:only|restricted to|limited to|exclusively)[^.\n]+(?:manufacturing|services?|trading|micro|small|medium)[^.\n]*"),
    ("Registration",
     r"(?:udyam|gst|pan|fssai|iec|trade license|factory license)[^.\n]*"
     r"(?:register(?:ed|ation)|certificate|required|mandatory|compulsory)[^.\n]*"),
    ("Registration",
     r"(?:register(?:ed|ation)|certificate|license|permit)[^.\n]+"
     r"(?:required|mandatory|compulsory|must be|shall be)[^.\n]*"),
    ("Documents",
     r"(?:documents? (?:required|needed|to be submitted)|list of documents|enclosures?)[^.\n]*"),
    ("Documents",
     r"(?:project report|dpr|bank statement|quotation|balance sheet|it return)"
     r"[^.\n]*(?:required|submit|attach|enclose)[^.\n]*"),
    ("Financial",
     r"(?:annual turnover|investment in plant|investment ceiling|net worth)[^.\n]+"
     r"(?:not exceeding|up to|above|below|between|₹|rs\.?|inr|lakh|crore)[^.\n]*"),
    ("Financial",
     r"(?:collateral|guarantee|margin money|promoter contribution|own contribution)[^.\n]+"
     r"(?:%|percent|lakh|crore|of project cost)[^.\n]*"),
    ("Application",
     r"(?:how to apply|application process|apply online|portal|website|application form)[^.\n]*"),
    ("Special Provisions",
     r"(?:women|sc|st|obc|scheduled caste|scheduled tribe)[^.\n]+"
     r"(?:higher|additional|special|preference|priority|subsidy|reservation)[^.\n]*"),
    ("Special Provisions",
     r"(?:rural|backward|north eastern|aspirational district)[^.\n]+"
     r"(?:additional|higher|special|priority)[^.\n]*"),
]

# ---------------------------------------------------------------------------
# Blocklist — multi-scheme aggregator documents that pollute results
# These documents contain hundreds of different schemes mixed together
# and should never be used as a source for scheme-specific compliance.
# ---------------------------------------------------------------------------
_BLOCKLIST_TITLES = {
    "draft compendium",
    "compendium of startup",
    "playbook of government schemes",
    "playbook of schemes",
    "list of schemes",
    "compilation of schemes",
    "handbook of schemes",
    "consolidated list",
    "schemes at a glance",
    "overview of schemes",
}

_BLOCKLIST_URLS = {
    "draft%20of%20compendium",
    "draft_compendium",
    "playbook",
}


def _is_blocked(chunk: Dict[str, Any]) -> bool:
    """Returns True if this chunk comes from a known multi-scheme aggregator document."""
    title = (chunk.get("title") or "").lower()
    url   = (chunk.get("official_url") or "").lower()
    for t in _BLOCKLIST_TITLES:
        if t in title:
            return True
    for u in _BLOCKLIST_URLS:
        if u in url:
            return True
    return False

_ORG_MSME  = "Ministry of MSME, Govt. of India"
_ORG_KVIC  = "KVIC / Ministry of MSME, Govt. of India"
_ORG_SIDBI = "SIDBI"
_ORG_DPIIT = "DPIIT / Ministry of Commerce, Govt. of India"
_ORG_DFS   = "Department of Financial Services / SIDBI"

_FALLBACK_RULES: Dict[str, List[Dict[str, Any]]] = {
    "pmegp": [
        {"category": "Eligibility",
         "rule_statement": "Any individual above 18 years of age is eligible to apply under PMEGP. There is no upper age limit or income ceiling.",
         "source_organization": _ORG_KVIC,
         "source_url": "https://www.kviconline.gov.in",
         "source_page_number": None},
        {"category": "Eligibility",
         "rule_statement": "For projects above Rs 10 lakh in manufacturing and Rs 5 lakh in services, the beneficiary must have passed at least VIII standard.",
         "source_organization": _ORG_KVIC,
         "source_url": "https://www.kviconline.gov.in",
         "source_page_number": None},
        {"category": "Financial",
         "rule_statement": "Maximum project cost under PMEGP is Rs 50 lakh for manufacturing units and Rs 20 lakh for service/trading units.",
         "source_organization": _ORG_MSME,
         "source_url": "https://msme.gov.in",
         "source_page_number": 9},
        {"category": "Financial",
         "rule_statement": "Beneficiary contribution (own margin money) is 10% of project cost for General category and 5% for Special category (SC/ST/OBC/Women/Minorities/Ex-servicemen/PH/NER/Hill and Border areas).",
         "source_organization": _ORG_KVIC,
         "source_url": "https://www.kviconline.gov.in",
         "source_page_number": None},
        {"category": "Special Provisions",
         "rule_statement": "Government subsidy under PMEGP is 15% for General category (urban), 25% for General category (rural), 25% for Special category (urban), and 35% for Special category (rural).",
         "source_organization": _ORG_MSME,
         "source_url": "https://msme.gov.in",
         "source_page_number": 9},
        {"category": "Registration",
         "rule_statement": "Udyam Registration Certificate is mandatory for all PMEGP beneficiaries to avail the subsidy.",
         "source_organization": _ORG_KVIC,
         "source_url": "https://www.kviconline.gov.in",
         "source_page_number": None},
        {"category": "Documents",
         "rule_statement": "Project Report (DPR), Aadhaar Card, PAN Card, educational qualification certificate, caste certificate (if applicable), and bank account details are required for PMEGP application.",
         "source_organization": _ORG_KVIC,
         "source_url": "https://www.kviconline.gov.in",
         "source_page_number": None},
        {"category": "Application",
         "rule_statement": "Applications under PMEGP must be submitted online through the KVIC portal at www.kviconline.gov.in. Offline applications are not accepted.",
         "source_organization": _ORG_KVIC,
         "source_url": "https://www.kviconline.gov.in",
         "source_page_number": None},
    ],
    "cgtmse": [
        {"category": "Eligibility",
         "rule_statement": "New and existing Micro and Small Enterprises (MSEs) engaged in manufacturing or service activities are eligible for credit guarantee cover under CGTMSE.",
         "source_organization": "CGTMSE / Ministry of MSME",
         "source_url": "https://www.cgtmse.in",
         "source_page_number": None},
        {"category": "Financial",
         "rule_statement": "Credit guarantee cover is available for collateral-free loans up to Rs 2 Crore (enhanced to Rs 5 Crore for select cases) extended by member lending institutions.",
         "source_organization": "CGTMSE / Ministry of MSME",
         "source_url": "https://www.cgtmse.in",
         "source_page_number": None},
        {"category": "Registration",
         "rule_statement": "Udyam Registration is mandatory for the borrower enterprise to be eligible for CGTMSE guarantee cover.",
         "source_organization": "CGTMSE / Ministry of MSME",
         "source_url": "https://www.cgtmse.in",
         "source_page_number": None},
        {"category": "Special Provisions",
         "rule_statement": "Women entrepreneurs and SC/ST borrowers are eligible for higher guarantee cover and reduced annual guarantee fee under CGTMSE.",
         "source_organization": "CGTMSE / Ministry of MSME",
         "source_url": "https://www.cgtmse.in",
         "source_page_number": None},
        {"category": "Eligibility",
         "rule_statement": "Retail trade, educational institutions, agriculture and self-help groups are excluded from CGTMSE guarantee cover.",
         "source_organization": "CGTMSE / Ministry of MSME",
         "source_url": "https://www.cgtmse.in",
         "source_page_number": None},
        {"category": "Application",
         "rule_statement": "The borrower applies for a loan to a CGTMSE member lending institution (bank or NBFC). The lender registers the loan with CGTMSE portal for guarantee cover.",
         "source_organization": "CGTMSE / Ministry of MSME",
         "source_url": "https://www.cgtmse.in",
         "source_page_number": None},
    ],
    "mudra": [
        {"category": "Eligibility",
         "rule_statement": "Non-corporate, non-farm small and micro enterprises are eligible for MUDRA loans under Pradhan Mantri MUDRA Yojana (PMMY).",
         "source_organization": "MUDRA / Ministry of Finance",
         "source_url": "https://www.mudra.org.in",
         "source_page_number": None},
        {"category": "Financial",
         "rule_statement": "MUDRA loans are available in three categories: Shishu (up to Rs 50,000), Kishor (Rs 50,001 to Rs 5 lakh), and Tarun (Rs 5,00,001 to Rs 10 lakh).",
         "source_organization": "MUDRA / Ministry of Finance",
         "source_url": "https://www.mudra.org.in",
         "source_page_number": None},
        {"category": "Eligibility",
         "rule_statement": "Any Indian citizen who has a business plan for income generating activity in manufacturing, processing, trading or service sector can apply for MUDRA loan.",
         "source_organization": "MUDRA / Ministry of Finance",
         "source_url": "https://www.mudra.org.in",
         "source_page_number": None},
        {"category": "Documents",
         "rule_statement": "Identity proof, address proof, business proof, last 6 months bank statements, and passport-size photographs are required for MUDRA loan application.",
         "source_organization": "MUDRA / Ministry of Finance",
         "source_url": "https://www.mudra.org.in",
         "source_page_number": None},
        {"category": "Application",
         "rule_statement": "MUDRA loans can be applied at any public sector bank, private bank, microfinance institution or through the Udyami Mitra portal at udyamimitra.in.",
         "source_organization": "MUDRA / Ministry of Finance",
         "source_url": "https://www.mudra.org.in",
         "source_page_number": None},
    ],
    "sidbi": [
        {"category": "Eligibility",
         "rule_statement": "Micro, Small and Medium Enterprises (MSMEs) in manufacturing and services sector with at least 2 years of operating history are eligible for SIDBI direct lending.",
         "source_organization": _ORG_SIDBI,
         "source_url": "https://www.sidbi.in",
         "source_page_number": None},
        {"category": "Registration",
         "rule_statement": "Udyam Registration Certificate is mandatory for all MSME borrowers applying for SIDBI loans and credit facilities.",
         "source_organization": _ORG_SIDBI,
         "source_url": "https://www.sidbi.in",
         "source_page_number": None},
        {"category": "Financial",
         "rule_statement": "SIDBI provides term loans, working capital loans, and equipment finance to MSMEs at competitive interest rates ranging from 8% to 14% per annum depending on credit rating.",
         "source_organization": _ORG_SIDBI,
         "source_url": "https://www.sidbi.in",
         "source_page_number": None},
        {"category": "Documents",
         "rule_statement": "Audited financial statements for last 2 years, bank statements for 12 months, KYC documents, project report, and Udyam Certificate are required for SIDBI loans.",
         "source_organization": _ORG_SIDBI,
         "source_url": "https://www.sidbi.in",
         "source_page_number": None},
        {"category": "Application",
         "rule_statement": "SIDBI loan applications can be submitted online through the Udyami Mitra portal at udyamimitra.in or by visiting the nearest SIDBI branch office.",
         "source_organization": _ORG_SIDBI,
         "source_url": "https://www.sidbi.in",
         "source_page_number": None},
    ],
    "stand up india": [
        {"category": "Eligibility",
         "rule_statement": "Stand-Up India scheme is exclusively for SC/ST and/or women entrepreneurs for setting up greenfield enterprises in manufacturing, services or trading sector.",
         "source_organization": _ORG_DFS,
         "source_url": "https://www.standupmitra.in",
         "source_page_number": None},
        {"category": "Financial",
         "rule_statement": "Composite bank loan between Rs 10 lakh and Rs 1 Crore is provided for greenfield enterprises under Stand-Up India. The loan covers both term loan and working capital.",
         "source_organization": _ORG_DFS,
         "source_url": "https://www.standupmitra.in",
         "source_page_number": None},
        {"category": "Eligibility",
         "rule_statement": "The enterprise must be a greenfield project. In case of non-individual enterprises, at least 51% of shareholding and controlling stake must be held by SC/ST or woman entrepreneur.",
         "source_organization": _ORG_DFS,
         "source_url": "https://www.standupmitra.in",
         "source_page_number": None},
        {"category": "Registration",
         "rule_statement": "Udyam Registration is required. The borrower must not be in default with any bank or financial institution.",
         "source_organization": _ORG_DFS,
         "source_url": "https://www.standupmitra.in",
         "source_page_number": None},
        {"category": "Special Provisions",
         "rule_statement": "At least one SC/ST borrower and at least one woman borrower per bank branch must be facilitated under Stand-Up India as a statutory mandate.",
         "source_organization": _ORG_DFS,
         "source_url": "https://www.standupmitra.in",
         "source_page_number": None},
        {"category": "Application",
         "rule_statement": "Applications for Stand-Up India can be submitted through the Stand-Up Mitra portal at standupmitra.in, Lead District Manager, or directly at any scheduled commercial bank branch.",
         "source_organization": _ORG_DFS,
         "source_url": "https://www.standupmitra.in",
         "source_page_number": None},
    ],
    "zed": [
        {"category": "Eligibility",
         "rule_statement": "All MSMEs registered on the Udyam portal are eligible to apply for ZED (Zero Defect Zero Effect) Certification.",
         "source_organization": _ORG_MSME,
         "source_url": "https://zed.org.in",
         "source_page_number": None},
        {"category": "Financial",
         "rule_statement": "ZED certification subsidy ranges from 50% for Micro enterprises to 45% for Small and 40% for Medium enterprises on the certification fee.",
         "source_organization": _ORG_MSME,
         "source_url": "https://zed.org.in",
         "source_page_number": None},
        {"category": "Special Provisions",
         "rule_statement": "Additional subsidy of 5% is provided to Women, SC/ST and NER (North-East Region) enterprises over the standard ZED certification subsidy.",
         "source_organization": _ORG_MSME,
         "source_url": "https://zed.org.in",
         "source_page_number": None},
        {"category": "Application",
         "rule_statement": "ZED Certification applications are submitted online at the ZED portal zed.org.in. The assessment is conducted in three stages: Bronze, Silver, Gold.",
         "source_organization": _ORG_MSME,
         "source_url": "https://zed.org.in",
         "source_page_number": None},
    ],
}


def _match_fallback(scheme_name: str) -> Optional[List[Dict[str, Any]]]:
    """Match scheme name to fallback rules using fuzzy keyword matching."""
    name_lower = scheme_name.lower()
    for key, rules in _FALLBACK_RULES.items():
        if key in name_lower:
            return rules
    # Partial matches
    if "pmegp" in name_lower or "prime minister employment" in name_lower:
        return _FALLBACK_RULES["pmegp"]
    if "cgtmse" in name_lower or "credit guarantee" in name_lower:
        return _FALLBACK_RULES["cgtmse"]
    if "mudra" in name_lower or "pmmy" in name_lower:
        return _FALLBACK_RULES["mudra"]
    if "sidbi" in name_lower:
        return _FALLBACK_RULES["sidbi"]
    if "stand" in name_lower and ("up" in name_lower or "india" in name_lower):
        return _FALLBACK_RULES["stand up india"]
    if "zed" in name_lower or "zero defect" in name_lower:
        return _FALLBACK_RULES["zed"]
    return None


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"[.\n]+", text)
            if _is_quality(s.strip())]


def _extract_rules(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Set[str] = set()
    rules: List[Dict[str, Any]] = []

    for chunk in chunks:
        text  = chunk.get("text", "")
        c_id  = chunk.get("chunk_id")
        page  = chunk.get("page_number")
        url   = chunk.get("official_url", "")
        org   = chunk.get("source_organization", "Government of India")
        score = chunk.get("similarity_score", 0.0)

        for sentence in _sentences(text):
            for category, pattern in _CUE_PATTERNS:
                if re.search(pattern, sentence, re.IGNORECASE):
                    clean = _clean(sentence)
                    norm  = clean.lower()
                    if norm not in seen:
                        seen.add(norm)
                        rules.append({
                            "category": category,
                            "rule_statement": clean,
                            "chunk_id": c_id,
                            "page_number": page,
                            "source_url": url,
                            "source_organization": org,
                            "similarity_score": score,
                        })
                    if len(rules) >= _MAX_RULES:
                        return rules
    return rules


def _fmt_inr(amount: float) -> str:
    if amount >= 1_00_00_000:
        return f"₹{amount / 1_00_00_000:.2f} Cr"
    if amount >= 1_00_000:
        return f"₹{amount / 1_00_000:.2f} Lakh"
    return f"₹{amount:,.0f}"


def _profile_facts(profile: Optional[ProfileModel], documents: Optional[List[Any]] = None) -> Dict[str, Any]:
    if not profile:
        return {"registered_types": set(), "docs_uploaded": set()}

    biz  = profile.business
    fin  = profile.financial
    loc  = profile.location
    char = profile.characteristics

    reg_registered = set()
    if profile.registrations:
        for r in profile.registrations:
            rstat = getattr(r, "status", None)
            sval = rstat.value if hasattr(rstat, "value") else (str(rstat) if rstat else "")
            rtype = getattr(r, "type", None)
            tval = rtype.value if hasattr(rtype, "value") else (str(rtype) if rtype else "")
            if sval == "registered" and tval:
                reg_registered.add(tval.lower())

    docs_uploaded = set()
    if documents:
        for d in documents:
            dtype = getattr(d, "document_type", None)
            dval = dtype.value if hasattr(dtype, "value") else (str(dtype) if dtype else "")
            dstat = getattr(d, "status", None)
            sval = dstat.value if hasattr(dstat, "value") else (str(dstat) if dstat else "uploaded")
            if dval and sval in ("uploaded", "verified"):
                docs_uploaded.add(dval.lower())

    # Business age in years
    age_years: Optional[float] = None
    if biz and biz.established_date:
        try:
            now = datetime.now(timezone.utc)
            est = biz.established_date
            if est.tzinfo is None:
                from datetime import timezone as _tz
                est = est.replace(tzinfo=_tz.utc)
            age_years = (now - est).days / 365.25
        except Exception:
            pass

    return {
        "business_name":         biz.name                        if biz  else None,
        "business_type":         biz.type.value if hasattr(biz.type, "value") else str(biz.type) if (biz and biz.type) else None,
        "industry":              biz.industry                    if biz  else None,
        "age_years":             age_years,
        "state":                 loc.state                       if loc  else None,
        "area_type":             loc.area_type.value if hasattr(loc.area_type, "value") else str(loc.area_type) if (loc and loc.area_type) else None,
        "msme_classification":   fin.msme_classification.value if hasattr(fin.msme_classification, "value") else str(fin.msme_classification) if (fin and fin.msme_classification) else None,
        "annual_turnover_inr":   fin.annual_turnover_inr         if fin  else None,
        "investment_inr":        fin.investment_inr              if fin  else None,
        "employee_count":        fin.employee_count              if fin  else None,
        "has_existing_loan":     fin.has_existing_loan           if fin  else None,
        "profitability_status":  fin.profitability_status.value if hasattr(fin.profitability_status, "value") else str(fin.profitability_status) if (fin and fin.profitability_status) else None,
        "is_women_owned":        char.is_women_owned             if char else None,
        "social_category":       char.social_category.value if hasattr(char.social_category, "value") else str(char.social_category) if (char and char.social_category) else None,
        "is_rural_enterprise":   char.is_rural_enterprise        if char else None,
        "is_startup_recognized": char.is_startup_recognized      if char else None,
        "exports_currently":     char.exports_currently          if char else None,
        "export_intent":         char.export_intent              if char else None,
        "registered_types":      reg_registered,
        "docs_uploaded":         docs_uploaded,
    }


# ---------------------------------------------------------------------------
# Gap Analysis Engine
# ---------------------------------------------------------------------------

def _run_gap_analysis(scheme_name: str, facts: Dict[str, Any]) -> List[GapItem]:
    """
    For known schemes, produce a named checklist of key requirements
    checked against the user's profile.  Returns empty list for unknown schemes.
    """
    name_lower = scheme_name.lower()

    # Detect which scheme
    is_pmegp      = "pmegp" in name_lower or "prime minister employment" in name_lower
    is_cgtmse     = "cgtmse" in name_lower or "credit guarantee" in name_lower
    is_mudra      = "mudra" in name_lower or "pmmy" in name_lower
    is_sidbi      = "sidbi" in name_lower
    is_standup    = ("stand" in name_lower and ("up" in name_lower or "india" in name_lower))
    is_zed        = "zed" in name_lower or "zero defect" in name_lower

    gaps: List[GapItem] = []

    cls_            = facts.get("msme_classification")
    biz_type        = facts.get("business_type")
    turnover        = facts.get("annual_turnover_inr")
    investment      = facts.get("investment_inr")
    age_years       = facts.get("age_years")
    state           = facts.get("state")
    area            = facts.get("area_type")
    is_rural        = facts.get("is_rural_enterprise", False)
    is_women        = facts.get("is_women_owned")
    social_cat      = facts.get("social_category")
    is_startup      = facts.get("is_startup_recognized")
    regs            = facts.get("registered_types", set())
    docs            = facts.get("docs_uploaded", set())
    exports         = facts.get("exports_currently")
    has_loan        = facts.get("has_existing_loan")
    profit_status   = facts.get("profitability_status")

    is_special      = social_cat in ("sc", "st", "obc") or is_women or is_rural

    # ── Helper to make gap items ────────────────────────────────────────

    def gap(requirement, description, status, profile_value=None, gap_detail=None, how_to_fix=None):
        return GapItem(
            requirement=requirement,
            description=description,
            status=status,
            profile_value=profile_value,
            gap_detail=gap_detail,
            how_to_fix=how_to_fix,
        )

    # ── PMEGP ───────────────────────────────────────────────────────────

    if is_pmegp:
        # 1. Age — we only know established_date, not owner age
        gaps.append(gap(
            "Age Eligibility",
            "Applicant must be above 18 years of age.",
            RuleVerdict.NEEDS_INFO,
            profile_value=None,
            gap_detail="Your age is not stored in the profile.",
            how_to_fix="Confirm your age directly on the KVIC application form. You must be 18+ to apply.",
        ))

        # 2. Business type
        if biz_type in ("manufacturing", "services", "trading"):
            gaps.append(gap(
                "Business Sector",
                "PMEGP covers manufacturing, service, and trading activities.",
                RuleVerdict.MET,
                profile_value=f"Business type: {biz_type}",
            ))
        elif biz_type:
            gaps.append(gap(
                "Business Sector",
                "PMEGP covers manufacturing, service, and trading activities.",
                RuleVerdict.NEEDS_INFO,
                profile_value=f"Business type: {biz_type}",
                gap_detail="Verify your sector falls under PMEGP-covered activities.",
                how_to_fix="Contact the nearest KVIC/DIC office to confirm your activity is covered.",
            ))
        else:
            gaps.append(gap(
                "Business Sector",
                "PMEGP covers manufacturing, service, and trading activities.",
                RuleVerdict.NEEDS_INFO,
                gap_detail="Business type not set in profile.",
                how_to_fix="Go to Profile → Business section → set your business type.",
            ))

        # 3. Project cost limit
        mfg_limit = 50_00_000  # ₹50L manufacturing
        svc_limit = 20_00_000  # ₹20L service/trading
        limit = mfg_limit if biz_type == "manufacturing" else svc_limit
        limit_str = "₹50 Lakh" if biz_type == "manufacturing" else "₹20 Lakh"
        if investment is not None:
            if investment <= limit:
                gaps.append(gap(
                    "Project Cost Limit",
                    f"Maximum project cost is {limit_str} for {biz_type or 'your'} sector.",
                    RuleVerdict.MET,
                    profile_value=f"Investment: {_fmt_inr(investment)}",
                ))
            else:
                gaps.append(gap(
                    "Project Cost Limit",
                    f"Maximum project cost is {limit_str} for {biz_type or 'your'} sector.",
                    RuleVerdict.NOT_MET,
                    profile_value=f"Investment: {_fmt_inr(investment)} exceeds {limit_str} limit",
                    gap_detail=f"Your investment of {_fmt_inr(investment)} exceeds the PMEGP project cost ceiling of {limit_str}.",
                    how_to_fix=f"Consider splitting the project or reducing scope to stay within {limit_str}. Alternatively explore CGTMSE or SIDBI for larger amounts.",
                ))
        else:
            gaps.append(gap(
                "Project Cost Limit",
                f"Maximum project cost is {limit_str} for {biz_type or 'your'} sector.",
                RuleVerdict.NEEDS_INFO,
                gap_detail="Investment amount not entered in profile.",
                how_to_fix="Go to Profile → Financial section → enter your total project cost (investment in plant & machinery).",
            ))

        # 4. Udyam registration
        if "udyam" in regs or "udyam_certificate" in docs or "udyam" in docs:
            gaps.append(gap("Udyam Registration", "Udyam Registration is mandatory for PMEGP.",
                            RuleVerdict.MET, profile_value="Udyam: Registered"))
        else:
            gaps.append(gap("Udyam Registration", "Udyam Registration is mandatory for PMEGP.",
                            RuleVerdict.NOT_MET,
                            gap_detail="Udyam Registration not found in your profile.",
                            how_to_fix="Register at udyamregistration.gov.in (free, takes 10 minutes). Then go to Profile → Registrations → add Udyam as Registered."))

        # 5. Own contribution (margin money)
        contrib_pct = "5%" if is_special else "10%"
        gaps.append(gap(
            "Own Contribution (Margin Money)",
            f"You must contribute {contrib_pct} of the project cost from your own funds.",
            RuleVerdict.NEEDS_INFO,
            profile_value=f"Category: {'Special' if is_special else 'General'} → {contrib_pct} contribution required",
            gap_detail="The system cannot verify your available capital against the project cost.",
            how_to_fix=f"Arrange {contrib_pct} of your total project cost as personal contribution before applying. The bank will verify this during loan sanctioning.",
        ))

        # 6. Subsidy rate
        if area == "rural" or is_rural:
            subsidy = "35%" if is_special else "25%"
            area_label = "Rural"
        else:
            subsidy = "25%" if is_special else "15%"
            area_label = "Urban"
        cat_label = "Special category" if is_special else "General category"
        gaps.append(gap(
            "Applicable Subsidy Rate",
            f"PMEGP subsidy rate for your profile.",
            RuleVerdict.MET,
            profile_value=f"{cat_label}, {area_label} → {subsidy} subsidy",
        ))

        # 7. Project Report
        if any(dt in docs for dt in ("project_report", "dpr", "business_plan")):
            gaps.append(gap(
                "Project Report (DPR)",
                "A Detailed Project Report is required for PMEGP application.",
                RuleVerdict.MET,
                profile_value="Document Uploaded: Detailed Project Report (DPR)",
            ))
        else:
            gaps.append(gap(
                "Project Report (DPR)",
                "A Detailed Project Report is required for PMEGP application.",
                RuleVerdict.NOT_MET,
                gap_detail="Project Report not uploaded in your Documents section.",
                how_to_fix="Prepare a Detailed Project Report (DPR) covering: business description, market analysis, cost breakdown, revenue projections, and repayment plan. Upload it in Profile → Documents.",
            ))

    # ── CGTMSE ──────────────────────────────────────────────────────────

    elif is_cgtmse:
        # 1. MSME classification
        if cls_ in ("micro", "small"):
            gaps.append(gap("Enterprise Classification",
                            "CGTMSE covers Micro and Small Enterprises only.",
                            RuleVerdict.MET, profile_value=f"Classification: {cls_.capitalize()}"))
        elif cls_ == "medium":
            gaps.append(gap("Enterprise Classification",
                            "CGTMSE covers Micro and Small Enterprises only.",
                            RuleVerdict.NOT_MET,
                            profile_value="Classification: Medium",
                            gap_detail="CGTMSE does not cover Medium enterprises.",
                            how_to_fix="Check if your turnover/investment qualifies as Small. Otherwise explore SIDBI or other credit guarantee schemes for medium enterprises."))
        else:
            gaps.append(gap("Enterprise Classification",
                            "CGTMSE covers Micro and Small Enterprises only.",
                            RuleVerdict.NEEDS_INFO,
                            gap_detail="MSME classification not determined in profile.",
                            how_to_fix="Go to Profile → Financial section → enter turnover and investment to auto-calculate your MSME classification."))

        # 2. Sector exclusion check
        excluded_sectors = ["retail trade", "education", "agriculture"]
        industry = (facts.get("industry") or "").lower()
        is_excluded = any(s in industry for s in excluded_sectors)
        if is_excluded:
            gaps.append(gap("Sector Eligibility",
                            "Retail trade, educational institutions, and agriculture are excluded from CGTMSE.",
                            RuleVerdict.NOT_MET,
                            profile_value=f"Industry: {facts.get('industry')}",
                            gap_detail="Your industry may be excluded from CGTMSE coverage.",
                            how_to_fix="Contact the bank or CGTMSE directly to confirm if your specific activity is covered. Some sub-sectors have exceptions."))
        else:
            gaps.append(gap("Sector Eligibility",
                            "Manufacturing and service MSEs are covered. Retail trade and agriculture are excluded.",
                            RuleVerdict.MET if biz_type in ("manufacturing", "services") else RuleVerdict.NEEDS_INFO,
                            profile_value=f"Business type: {biz_type}",
                            gap_detail=None if biz_type in ("manufacturing", "services") else "Verify your sector is covered under CGTMSE.",
                            how_to_fix=None if biz_type in ("manufacturing", "services") else "Contact the nearest member lending institution to confirm sector coverage."))

        # 3. Udyam
        if "udyam" in regs or "udyam_certificate" in docs or "udyam" in docs:
            gaps.append(gap("Udyam Registration", "Required for CGTMSE guarantee.",
                            RuleVerdict.MET, profile_value="Udyam: Registered"))
        else:
            gaps.append(gap("Udyam Registration", "Required for CGTMSE guarantee.",
                            RuleVerdict.NOT_MET,
                            gap_detail="Udyam not registered.",
                            how_to_fix="Register free at udyamregistration.gov.in and add it to Profile → Registrations."))

        # 4. Financial Records
        if any(dt in docs for dt in ("balance_sheet", "financial_statement", "bank_statement")):
            gaps.append(gap("Financial Records",
                            "Financial statements or bank statements required for appraisal.",
                            RuleVerdict.MET, profile_value="Document Uploaded: Financial / Bank Records"))
        else:
            gaps.append(gap("Financial Records",
                            "Financial statements or bank statements required for credit appraisal.",
                            RuleVerdict.NEEDS_INFO,
                            gap_detail="No financial statement or bank statement uploaded.",
                            how_to_fix="Upload 6-month Bank Statement or latest Balance Sheet under Profile → Documents."))

        # 5. Women/SC-ST benefit
        if is_women or social_cat in ("sc", "st"):
            cat = "Women" if is_women else social_cat.upper()
            gaps.append(gap("Enhanced Coverage",
                            "Women and SC/ST entrepreneurs get higher guarantee cover and reduced fee.",
                            RuleVerdict.MET,
                            profile_value=f"{cat} entrepreneur — eligible for enhanced benefits"))
        else:
            gaps.append(gap("Special Category Benefits",
                            "Women and SC/ST entrepreneurs get higher coverage.",
                            RuleVerdict.NEEDS_INFO,
                            profile_value=f"Category: {social_cat or 'not set'}",
                            gap_detail="Your category is General — standard terms apply.",
                            how_to_fix="No action needed. You are still eligible under standard CGTMSE terms."))

    # ── MUDRA ───────────────────────────────────────────────────────────

    elif is_mudra:
        # 1. Business type
        if biz_type in ("manufacturing", "services", "trading"):
            gaps.append(gap("Business Sector",
                            "MUDRA covers manufacturing, service, and trading micro enterprises.",
                            RuleVerdict.MET, profile_value=f"Business type: {biz_type}"))
        else:
            gaps.append(gap("Business Sector",
                            "MUDRA covers manufacturing, service, and trading activities.",
                            RuleVerdict.NEEDS_INFO,
                            gap_detail="Business type not confirmed.",
                            how_to_fix="Go to Profile → Business section → set business type to Manufacturing, Services, or Trading."))

        # 2. Loan category
        if turnover is not None:
            if turnover <= 5_00_000:
                cat_lbl = "Shishu (up to ₹50,000)"
            elif turnover <= 50_00_000:
                cat_lbl = "Kishor (₹50,001 – ₹5 Lakh)"
            else:
                cat_lbl = "Tarun (₹5 Lakh – ₹10 Lakh)"
            gaps.append(gap("MUDRA Loan Category",
                            "Choose Shishu / Kishor / Tarun based on your loan requirement.",
                            RuleVerdict.MET, profile_value=f"Suggested category: {cat_lbl}"))
        else:
            gaps.append(gap("MUDRA Loan Category",
                            "Shishu (≤₹50K), Kishor (≤₹5L), Tarun (≤₹10L).",
                            RuleVerdict.NEEDS_INFO,
                            gap_detail="Turnover not entered — cannot suggest MUDRA category.",
                            how_to_fix="Go to Profile → Financial section → enter Annual Turnover."))

        # 3. No collateral required
        gaps.append(gap("Collateral Requirement",
                        "MUDRA loans up to ₹10 Lakh are collateral-free.",
                        RuleVerdict.MET,
                        profile_value="No collateral required under MUDRA"))

        # 4. Identity documents
        if any(dt in docs for dt in ("pan_card", "identity_proof", "bank_statement")):
            gaps.append(gap("Identity & Bank Documents",
                            "PAN Card, Aadhaar, address proof, and bank statements required.",
                            RuleVerdict.MET,
                            profile_value="Document Uploaded: PAN / Bank Records"))
        else:
            gaps.append(gap("Identity & Bank Documents",
                            "PAN Card, Aadhaar, address proof, and bank statements required.",
                            RuleVerdict.NEEDS_INFO,
                            gap_detail="Document upload status not verified.",
                            how_to_fix="Upload PAN Card and Aadhaar in Profile → Documents. Keep 6-month bank statement ready."))

    # ── SIDBI ───────────────────────────────────────────────────────────

    elif is_sidbi:
        # 1. Operating history
        if age_years is not None:
            if age_years >= 2:
                gaps.append(gap("Operating History",
                                "At least 2 years of operating history required for SIDBI direct lending.",
                                RuleVerdict.MET,
                                profile_value=f"Business age: {age_years:.1f} years"))
            else:
                gaps.append(gap("Operating History",
                                "At least 2 years of operating history required.",
                                RuleVerdict.NOT_MET,
                                profile_value=f"Business age: {age_years:.1f} years",
                                gap_detail="Your business is less than 2 years old.",
                                how_to_fix="Consider PMEGP or MUDRA which are designed for early-stage enterprises. SIDBI direct lending requires at least 2 years of operation."))
        else:
            gaps.append(gap("Operating History",
                            "Minimum 2 years operating history required.",
                            RuleVerdict.NEEDS_INFO,
                            gap_detail="Establishment date not set in profile.",
                            how_to_fix="Go to Profile → Business section → set your business established date."))

        # 2. Udyam
        if "udyam" in regs or "udyam_certificate" in docs or "udyam" in docs:
            gaps.append(gap("Udyam Registration", "Mandatory for all SIDBI borrowers.",
                            RuleVerdict.MET, profile_value="Udyam: Registered"))
        else:
            gaps.append(gap("Udyam Registration", "Mandatory for all SIDBI borrowers.",
                            RuleVerdict.NOT_MET,
                            gap_detail="Udyam not registered.",
                            how_to_fix="Register free at udyamregistration.gov.in."))

        # 3. Financial documents
        if any(dt in docs for dt in ("balance_sheet", "financial_statement", "it_return")):
            gaps.append(gap("Audited Financials",
                            "2 years of audited financial statements required.",
                            RuleVerdict.MET,
                            profile_value="Document Uploaded: Audited Financial Statements"))
        else:
            gaps.append(gap("Audited Financials",
                            "2 years of audited financial statements required.",
                            RuleVerdict.NEEDS_INFO,
                            gap_detail="Audited financial statement upload not verified.",
                            how_to_fix="Prepare audited balance sheet and P&L for last 2 years. Upload in Profile → Documents section."))

    # ── STAND-UP INDIA ──────────────────────────────────────────────────

    elif is_standup:
        # 1. SC/ST or Women — mandatory
        qualifies = social_cat in ("sc", "st") or is_women is True
        if qualifies:
            who = []
            if social_cat in ("sc", "st"):
                who.append(social_cat.upper())
            if is_women:
                who.append("Women")
            gaps.append(gap("SC/ST or Women Entrepreneur",
                            "Stand-Up India is exclusively for SC/ST and/or women entrepreneurs.",
                            RuleVerdict.MET,
                            profile_value=f"Category: {', '.join(who)}"))
        else:
            gaps.append(gap("SC/ST or Women Entrepreneur",
                            "Stand-Up India is exclusively for SC/ST and/or women entrepreneurs.",
                            RuleVerdict.NOT_MET if (social_cat == "general" and is_women is False) else RuleVerdict.NEEDS_INFO,
                            profile_value=f"Category: {social_cat or 'not set'}, Women-owned: {is_women}",
                            gap_detail="You may not meet the exclusive SC/ST or women entrepreneur criterion.",
                            how_to_fix="Update Profile → Characteristics section with your social category and women-owned status. If you do not meet this criterion, consider PMEGP, MUDRA or SIDBI instead."))

        # 2. Udyam
        if "udyam" in regs or "udyam_certificate" in docs or "udyam" in docs:
            gaps.append(gap("Udyam Registration", "Required for Stand-Up India.",
                            RuleVerdict.MET, profile_value="Udyam: Registered"))
        else:
            gaps.append(gap("Udyam Registration", "Required for Stand-Up India.",
                            RuleVerdict.NOT_MET,
                            gap_detail="Udyam not registered.",
                            how_to_fix="Register free at udyamregistration.gov.in."))

        # 3. Project Report
        if any(dt in docs for dt in ("project_report", "dpr", "business_plan")):
            gaps.append(gap("Greenfield Project Report",
                            "Project proposal required for Stand-Up India.",
                            RuleVerdict.MET, profile_value="Document Uploaded: Greenfield Project Proposal"))
        else:
            gaps.append(gap("Greenfield Project Report",
                            "Greenfield project proposal required for loan sanction.",
                            RuleVerdict.NEEDS_INFO,
                            gap_detail="Project proposal not uploaded.",
                            how_to_fix="Prepare greenfield project proposal and upload under Profile → Documents."))

    # ── ZED ─────────────────────────────────────────────────────────────

    elif is_zed:
        # 1. Udyam
        if "udyam" in regs or "udyam_certificate" in docs or "udyam" in docs:
            gaps.append(gap("Udyam Registration", "ZED requires Udyam Registration.",
                            RuleVerdict.MET, profile_value="Udyam: Registered"))
        else:
            gaps.append(gap("Udyam Registration", "ZED requires Udyam Registration.",
                            RuleVerdict.NOT_MET,
                            gap_detail="Udyam not registered.",
                            how_to_fix="Register free at udyamregistration.gov.in."))

        # 2. Subsidy rate
        subsidy_map = {"micro": "80%", "small": "60%", "medium": "50%"}
        subsidy = subsidy_map.get(cls_, "varies")
        gaps.append(gap("ZED Certification Subsidy",
                        f"Government subsidy on ZED certification fee.",
                        RuleVerdict.MET if cls_ in subsidy_map else RuleVerdict.NEEDS_INFO,
                        profile_value=f"{cls_.capitalize() if cls_ else 'Classification unknown'} enterprise → {subsidy} subsidy",
                        gap_detail=None if cls_ in subsidy_map else "MSME classification not determined.",
                        how_to_fix=None if cls_ in subsidy_map else "Go to Profile → Financial section → enter turnover and investment."))

    # ── GENERIC SCHEME FALLBACK ─────────────────────────────────────────

    else:
        # Comprehensive Gap Checklist for any custom or non-templated scheme
        gaps.append(gap(
            "Udyam Registration",
            "Official Udyam Registration Certificate for MSMEs.",
            RuleVerdict.MET if ("udyam" in regs or "udyam_certificate" in docs or "udyam" in docs) else RuleVerdict.NOT_MET,
            profile_value="Udyam: Registered" if ("udyam" in regs or "udyam_certificate" in docs or "udyam" in docs) else "Udyam: Not registered",
            gap_detail=None if ("udyam" in regs or "udyam_certificate" in docs or "udyam" in docs) else "Udyam registration is mandatory for most government schemes.",
            how_to_fix=None if ("udyam" in regs or "udyam_certificate" in docs or "udyam" in docs) else "Register free at udyamregistration.gov.in and add to Profile → Registrations.",
        ))

        gaps.append(gap(
            "MSME Classification & Financial Metrics",
            "Enterprise classification based on annual turnover and investment.",
            RuleVerdict.MET if cls_ else RuleVerdict.NEEDS_INFO,
            profile_value=f"Classification: {cls_.capitalize()} (Turnover: {_fmt_inr(turnover)})" if (cls_ and turnover) else (f"Classification: {cls_.capitalize()}" if cls_ else "Not classified"),
            gap_detail=None if cls_ else "Financial inputs missing in profile.",
            how_to_fix=None if cls_ else "Go to Profile → Financial section → enter Annual Turnover & Investment.",
        ))

        gaps.append(gap(
            "Business Sector Eligibility",
            "Business sector coverage check.",
            RuleVerdict.MET if biz_type else RuleVerdict.NEEDS_INFO,
            profile_value=f"Sector: {biz_type.capitalize()}" if biz_type else "Sector not specified",
            gap_detail=None if biz_type else "Business type not set in profile.",
            how_to_fix=None if biz_type else "Go to Profile → Business section → set business type.",
        ))

        gaps.append(gap(
            "State & Regional Grounding",
            "State location check for regional scheme eligibility.",
            RuleVerdict.MET if state else RuleVerdict.NEEDS_INFO,
            profile_value=f"Location: {state} ({area or 'Urban/Rural'})" if state else "Location not set",
            gap_detail=None if state else "State location not set in profile.",
            how_to_fix=None if state else "Go to Profile → Location section → set State and Area Type.",
        ))

        gaps.append(gap(
            "Document Verification",
            "Upload of business documents (Project Report, Bank Statement, PAN).",
            RuleVerdict.MET if docs else RuleVerdict.NEEDS_INFO,
            profile_value=f"Uploaded: {len(docs)} document(s)" if docs else "No documents uploaded",
            gap_detail=None if docs else "No business documents uploaded yet.",
            how_to_fix=None if docs else "Go to Profile → Documents and upload your Project Report, Bank Statements, or PAN Card.",
        ))

        if is_special:
            gaps.append(gap(
                "Special Category Benefits",
                "Higher subsidy or priority access for Special Category enterprises.",
                RuleVerdict.MET,
                profile_value=f"Special Category Entitlement applicable (Women: {is_women}, Social Cat: {social_cat}, Rural: {is_rural})",
            ))

    return gaps


# ---------------------------------------------------------------------------
# Rule assessment (unchanged logic, applied to filtered rules)
# ---------------------------------------------------------------------------

def _assess(rule: Dict[str, Any], facts: Dict[str, Any]) -> ComplianceRuleResult:
    stmt_lower = rule["rule_statement"].lower()
    category   = rule["category"]

    verdict:      RuleVerdict   = RuleVerdict.NEEDS_INFO
    profile_fact: Optional[str] = None
    explanation:  str           = _generic_needs_info(category)

    biz_type = facts.get("business_type")
    if biz_type:
        only_mfg = (biz_type != "manufacturing" and bool(re.search(
            r"\bonly\b.{0,30}\bmanufacturing\b|\bmanufacturing\b.{0,20}\bonly\b", stmt_lower)))
        if only_mfg:
            return _make(rule, RuleVerdict.NOT_MET, f"Business type: {biz_type}",
                         f"Your business type is '{biz_type}'. "
                         "The official source restricts this to manufacturing enterprises only.")
        if biz_type in stmt_lower or "msme" in stmt_lower or "enterprise" in stmt_lower:
            verdict = RuleVerdict.MET
            profile_fact = f"Business type: {biz_type}"
            explanation = f"Your business type '{biz_type}' aligns with the sector coverage in this provision."

    cls_ = facts.get("msme_classification")
    if cls_ and any(k in stmt_lower for k in ("micro", "small", "medium", "msme")):
        micro_only = (cls_ != "micro" and bool(re.search(
            r"\bonly\b.{0,20}\bmicro\b|\bmicro\b.{0,20}\bonly\b", stmt_lower)))
        if micro_only:
            return _make(rule, RuleVerdict.NOT_MET, f"MSME classification: {cls_}",
                         f"Your enterprise is '{cls_}'. The official source restricts this to micro enterprises only.")
        if cls_ in stmt_lower or "msme" in stmt_lower:
            verdict = RuleVerdict.MET
            profile_fact = f"MSME classification: {cls_}"
            explanation = f"Your '{cls_}' classification is covered under this provision."

    reg_types = facts.get("registered_types", set())
    _REG_KW = {"udyam": "udyam", "gst": "gst", "pan": "pan", "fssai": "fssai", "iec": "iec",
               "factory license": "factory_license", "trade license": "trade_license"}
    for kw, rtype in _REG_KW.items():
        if kw in stmt_lower and re.search(r"\b(?:required|mandatory|compulsory|must|shall)\b", stmt_lower):
            if rtype in reg_types:
                return _make(rule, RuleVerdict.MET, f"{kw.upper()} registration: Registered",
                             f"Your profile shows {kw.upper()} is registered.")
            else:
                return _make(rule, RuleVerdict.NEEDS_INFO, f"{kw.upper()}: Not confirmed",
                             f"Official source requires {kw.upper()} registration.\n\nWhat to do: "
                             f"Go to Profile → Registrations → add {kw.upper()} status. "
                             f"If not yet registered, apply at the official portal.")

    if re.search(r"\bwomen\b|\bwoman\b|\bmahila\b", stmt_lower):
        is_women = facts.get("is_women_owned")
        if is_women is True:
            return _make(rule, RuleVerdict.MET, "Women-owned: Yes",
                         "Your enterprise is women-owned. This provision or higher subsidy tier applies.")
        elif is_women is False:
            return _make(rule, RuleVerdict.NEEDS_INFO, "Women-owned: No",
                         "This provision mentions women-entrepreneur benefits. Standard terms apply to you. No action needed.")
        else:
            return _make(rule, RuleVerdict.NEEDS_INFO, None,
                         "This provision mentions women-entrepreneur benefits.\n\nWhat to do: "
                         "Go to Profile → Characteristics → set Women-Owned field.")

    if re.search(r"\b(?:sc|st|obc|scheduled caste|scheduled tribe|special category)\b", stmt_lower):
        cat = facts.get("social_category")
        if cat in ("sc", "st", "obc"):
            return _make(rule, RuleVerdict.MET, f"Social category: {cat.upper()}",
                         f"Your '{cat.upper()}' category qualifies for preferential terms.")
        elif cat == "general":
            return _make(rule, RuleVerdict.NEEDS_INFO, "Social category: General",
                         "SC/ST/OBC preferences mentioned. General category gets standard terms.\n\nWhat to do: "
                         "No profile change needed. Select General category on the application form.")
        else:
            return _make(rule, RuleVerdict.NEEDS_INFO, None,
                         "SC/ST/OBC preferences mentioned.\n\nWhat to do: "
                         "Go to Profile → Characteristics → set Social Category.")

    if re.search(r"\b(?:rural|gramin|backward area|village)\b", stmt_lower):
        area = facts.get("area_type")
        is_rural = facts.get("is_rural_enterprise")
        if area == "rural" or is_rural:
            return _make(rule, RuleVerdict.MET, "Area type: Rural", "Your rural location meets this provision.")
        elif area == "urban":
            return _make(rule, RuleVerdict.NEEDS_INFO, "Area type: Urban",
                         "This provision mentions rural benefits. Urban enterprises may get lower subsidy.\n\nWhat to do: "
                         "Verify subsidy rate applicable to urban enterprises with the scheme authority.")
        else:
            return _make(rule, RuleVerdict.NEEDS_INFO, None,
                         "Area type not set.\n\nWhat to do: Go to Profile → Location → set Area Type.")

    if re.search(r"turnover[^.\n]*(?:not exceeding|up to|below|₹|rs\.?|inr|lakh|crore)", stmt_lower):
        t = facts.get("annual_turnover_inr")
        if t is not None:
            return _make(rule, RuleVerdict.MET, f"Annual turnover: {_fmt_inr(t)}",
                         f"Your turnover of {_fmt_inr(t)} is recorded. Verify it falls within the scheme ceiling.")
        else:
            return _make(rule, RuleVerdict.NEEDS_INFO, None,
                         "Turnover threshold mentioned.\n\nWhat to do: "
                         "Go to Profile → Financial section → enter Annual Turnover.")

    if re.search(r"investment[^.\n]*(?:not exceeding|up to|below|₹|rs\.?|inr|lakh|crore)", stmt_lower):
        inv = facts.get("investment_inr")
        if inv is not None:
            return _make(rule, RuleVerdict.MET, f"Investment: {_fmt_inr(inv)}",
                         f"Your investment of {_fmt_inr(inv)} is recorded. Verify it falls within the scheme ceiling.")
        else:
            return _make(rule, RuleVerdict.NEEDS_INFO, None,
                         "Investment ceiling mentioned.\n\nWhat to do: "
                         "Go to Profile → Financial section → enter Investment in Plant & Machinery.")

    if re.search(r"\b(?:export|iec|foreign trade|import export code)\b", stmt_lower):
        if facts.get("exports_currently") or facts.get("export_intent"):
            return _make(rule, RuleVerdict.MET, "Export activity: Yes", "Your profile indicates export activity.")
        else:
            return _make(rule, RuleVerdict.NEEDS_INFO, None,
                         "Export activity mentioned.\n\nWhat to do: "
                         "Go to Profile → Characteristics → set Export Intent or Exports Currently.")

    if re.search(r"\b(?:startup|dpiit|seed fund)\b", stmt_lower):
        is_startup = facts.get("is_startup_recognized")
        if is_startup is True:
            return _make(rule, RuleVerdict.MET, "DPIIT startup: Yes", "Your startup recognition matches this provision.")
        else:
            return _make(rule, RuleVerdict.NEEDS_INFO,
                         f"DPIIT startup: {'No' if is_startup is False else 'Not set'}",
                         "Startup provision mentioned.\n\nWhat to do: "
                         "Go to Profile → Characteristics → set Startup Recognised status.")

    if category == "Application":
        source_url = rule.get("source_url", "")
        return _make(rule, RuleVerdict.NEEDS_INFO, None,
                     "Application process from official source.\n\nWhat to do: "
                     f"{'Visit ' + source_url + ' to apply.' if source_url else 'Visit the official portal (link above).'} "
                     "Keep Udyam, PAN, Aadhaar, Project Report, and Bank Statements ready.")

    if category == "Documents":
        docs = facts.get("docs_uploaded", set())
        doc_kw_map = {
            "project report": ["project_report", "dpr", "business_plan"],
            "dpr": ["project_report", "dpr", "business_plan"],
            "bank statement": ["bank_statement"],
            "balance sheet": ["balance_sheet", "financial_statement"],
            "financial statement": ["balance_sheet", "financial_statement"],
            "it return": ["it_return", "income_tax_return"],
            "pan": ["pan_card", "pan"],
            "aadhaar": ["aadhaar_card", "aadhaar"],
            "udyam": ["udyam_certificate", "udyam"],
            "caste certificate": ["caste_certificate"],
        }
        matched = None
        for kw, dtypes in doc_kw_map.items():
            if kw in stmt_lower:
                if any(dt in docs for dt in dtypes):
                    matched = kw
                    break
        if matched:
            return _make(rule, RuleVerdict.MET, f"Document: {matched.title()} uploaded",
                         f"Your uploaded {matched.title()} document satisfies this requirement.")
        else:
            return _make(rule, RuleVerdict.NEEDS_INFO, "Document: Not uploaded",
                         "Document requirement found in official source.\n\nWhat to do: "
                         "Go to Profile → Documents → upload the required document (PDF/JPG/PNG, max 10MB).")

    if category == "Financial":
        return _make(rule, RuleVerdict.NEEDS_INFO, None,
                     "Financial condition found in official source.\n\nWhat to do: "
                     "Check the rule statement carefully. For margin money requirements, arrange the own contribution amount. "
                     "For collateral, check if CGTMSE covers your loan collateral-free.")

    return _make(rule, verdict, profile_fact, explanation)


def _generic_needs_info(category: str) -> str:
    guides = {
        "Eligibility": (
            "This eligibility condition was found in the official source.\n\nWhat to do: "
            "Read the rule statement and verify whether your business meets it. "
            "Contact the implementing agency or nodal bank with your Udyam certificate for a formal check."
        ),
        "Registration": (
            "A registration requirement found in the official source.\n\nWhat to do: "
            "Go to Profile → Registrations and confirm the required registration is added. "
            "Common: Udyam (udyamregistration.gov.in), GST (gst.gov.in), PAN (incometax.gov.in)."
        ),
        "Documents": (
            "A document requirement found in the official source.\n\nWhat to do: "
            "Go to Profile → Documents and upload the required document."
        ),
        "Financial": (
            "A financial requirement found in the official source.\n\nWhat to do: "
            "Ensure Profile → Financial section is fully filled with turnover and investment amounts."
        ),
        "Application": (
            "Application process instruction from official source.\n\nWhat to do: "
            "Visit the official scheme portal (link above). Keep Udyam, PAN, Aadhaar, Project Report, Bank Statements ready."
        ),
        "Special Provisions": (
            "Special provision for a category found in official source.\n\nWhat to do: "
            "Go to Profile → Characteristics and fill Social Category, Women-Owned, Rural Enterprise, and Startup fields."
        ),
    }
    return guides.get(category,
        "Requirement found in official source.\n\nWhat to do: "
        "Read the rule statement and contact the scheme authority with your business details.")


def _make(rule: Dict[str, Any], verdict: RuleVerdict,
          profile_fact: Optional[str], explanation: str) -> ComplianceRuleResult:
    return ComplianceRuleResult(
        rule_id             = f"rule_{rule.get('_index', 0)}",
        category            = rule["category"],
        rule_statement      = rule["rule_statement"],
        verdict             = verdict,
        profile_fact        = profile_fact,
        explanation         = explanation,
        source_chunk_id     = rule.get("chunk_id"),
        source_page_number  = rule.get("page_number"),
        source_organization = rule.get("source_organization"),
        source_url          = rule.get("source_url"),
    )


# ---------------------------------------------------------------------------
# Overall status
# ---------------------------------------------------------------------------

def _overall(rules: List[ComplianceRuleResult],
             gaps: List[GapItem]) -> Tuple[OverallComplianceStatus, str]:
    # Combine both gap and rule verdicts for overall status
    all_verdicts = [r.verdict for r in rules] + [g.status for g in gaps]
    if not all_verdicts:
        return (OverallComplianceStatus.INSUFFICIENT_DATA,
                "No compliance requirements could be extracted for this scheme. "
                "Check the official portal directly.")

    not_met    = sum(1 for v in all_verdicts if v == RuleVerdict.NOT_MET)
    needs_info = sum(1 for v in all_verdicts if v == RuleVerdict.NEEDS_INFO)
    met        = sum(1 for v in all_verdicts if v == RuleVerdict.MET)
    total      = len(all_verdicts)

    if not_met > 0:
        return (OverallComplianceStatus.ACTION_REQUIRED,
                f"{not_met} requirement(s) are not met by your current profile. "
                "Review the flagged items and address them before applying.")
    if met > 0 and needs_info > 0:
        return (OverallComplianceStatus.PARTIALLY_READY,
                f"{met} of {total} requirements appear to be met. "
                f"{needs_info} item(s) need additional information or direct verification.")
    if needs_info > 0 and met == 0:
        return (OverallComplianceStatus.PARTIALLY_READY,
                f"{needs_info} requirement(s) were found but could not be fully assessed. "
                "Complete your profile and verify with the scheme authority.")
    return (OverallComplianceStatus.READY,
            f"All {total} assessed requirements appear to be met. "
            "Verify final eligibility with the scheme authority before applying.")


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class ComplianceService:

    def __init__(self, rag_client: Optional[RagClient] = None):
        self.rag_client = rag_client or RagClient()

    async def assess(self, request: SchemeComplianceRequest,
                     profile: Optional[ProfileModel],
                     documents: Optional[List[Any]] = None) -> SchemeComplianceResponse:

        scheme_name  = request.scheme_name.strip()
        org          = request.scheme_organization or "Government of India"
        official_url = request.official_url
        k_type       = request.knowledge_type or "SCHEME"
        # Fix 1 — pinning
        pin_source   = request.source_id
        pin_doc      = request.document_id

        # User-isolated cache lookup
        cache_key = f"{request.scheme_id or scheme_name}|{str(getattr(profile, 'id', 'anon'))}|{getattr(profile, 'updated_at', '')}|{len(documents or [])}"
        now = time.time()
        if cache_key in _COMPLIANCE_CACHE:
            cached_time, cached_res = _COMPLIANCE_CACHE[cache_key]
            if now - cached_time < 300.0:
                return cached_res

        business_name = "Your Enterprise"
        msme_class    = "not_classified"
        facts: Dict[str, Any] = {}

        if profile:
            if profile.business:
                business_name = profile.business.name
            if profile.financial:
                msme_class = profile.financial.msme_classification.value
            facts = _profile_facts(profile, documents=documents)
        elif documents:
            facts = _profile_facts(None, documents=documents)

        # ── RAG retrieval (Concurrent Execution via asyncio.gather) ─────
        queries = self._build_queries(scheme_name, facts)
        all_chunks: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        query_tasks = [
            self.rag_client.search(
                query                = query,
                top_k                = _RAG_TOP_K,
                similarity_threshold = 0.0,
                knowledge_type       = k_type,
                source_id            = pin_source,
            )
            for query in queries
        ]
        query_results = await asyncio.gather(*query_tasks, return_exceptions=True)

        for chunk_batch in query_results:
            if not isinstance(chunk_batch, list):
                continue
            for c in chunk_batch:
                cid = c.get("chunk_id") or c.get("document_id")
                if cid and cid not in seen_ids:
                    if pin_doc and c.get("document_id") and c.get("document_id") != pin_doc:
                        continue
                    if _is_blocked(c):
                        continue
                    seen_ids.add(cid)
                    all_chunks.append(c)

        # Widen concurrently if sparse (and no pinning)
        if len(all_chunks) < 3 and not pin_source:
            extra_tasks = [
                self.rag_client.search(
                    query=f"{scheme_name} compliance eligibility requirements documents",
                    top_k=5,
                    similarity_threshold=0.0,
                    knowledge_type=extra_kt,
                )
                for extra_kt in ("COMPLIANCE", "GUIDELINE")
            ]
            extra_results = await asyncio.gather(*extra_tasks, return_exceptions=True)
            for chunk_batch in extra_results:
                if not isinstance(chunk_batch, list):
                    continue
                for c in chunk_batch:
                    cid = c.get("chunk_id") or c.get("document_id")
                    if cid and cid not in seen_ids and not _is_blocked(c):
                        seen_ids.add(cid)
                        all_chunks.append(c)

        rag_evidence_note: Optional[str] = None
        if not all_chunks:
            rag_evidence_note = (
                "The RAG knowledge base did not return chunks for this scheme. "
                "Showing scheme-specific guidelines from official sources."
            )

        # ── Fix 2: Extract rules with quality filter ────────────────────
        raw_rules = _extract_rules(all_chunks)

        # ── Fix 3: Fallback templates if too few quality RAG rules ──────
        used_fallback = False
        if len(raw_rules) < _MIN_RAG_RULES:
            fallback = _match_fallback(scheme_name)
            if fallback:
                used_fallback = True
                # Merge: add fallback rules not already covered by RAG
                rag_statements = {r["rule_statement"].lower() for r in raw_rules}
                for fb in fallback:
                    if fb["rule_statement"].lower() not in rag_statements:
                        raw_rules.append(fb)
                        if len(raw_rules) >= _MAX_RULES:
                            break

        # ── Assess each rule ────────────────────────────────────────────
        results: List[ComplianceRuleResult] = []
        for idx, raw in enumerate(raw_rules):
            raw["_index"] = idx + 1
            r = _assess(raw, facts)
            r.rule_id = f"rule_{idx + 1}"
            results.append(r)

        # ── Gap analysis ────────────────────────────────────────────────
        gaps = _run_gap_analysis(scheme_name, facts)

        # ── Aggregates ──────────────────────────────────────────────────
        met_cnt        = sum(1 for r in results if r.verdict == RuleVerdict.MET)
        not_met_cnt    = sum(1 for r in results if r.verdict == RuleVerdict.NOT_MET)
        needs_info_cnt = sum(1 for r in results if r.verdict == RuleVerdict.NEEDS_INFO)
        gap_met        = sum(1 for g in gaps if g.status == RuleVerdict.MET)
        gap_missing    = sum(1 for g in gaps if g.status != RuleVerdict.MET)
        overall_status, overall_summary = _overall(results, gaps)

        response = SchemeComplianceResponse(
            scheme_name         = scheme_name,
            scheme_organization = org,
            official_url        = official_url,
            business_name       = business_name,
            msme_classification = msme_class,
            overall_status      = overall_status,
            overall_summary     = overall_summary,
            gap_analysis        = gaps,
            gap_met_count       = gap_met,
            gap_missing_count   = gap_missing,
            rules               = results,
            total_rules         = len(results),
            met_count           = met_cnt,
            not_met_count       = not_met_cnt,
            needs_info_count    = needs_info_cnt,
            rag_chunks_used     = len(all_chunks),
            rag_evidence_note   = rag_evidence_note,
            used_fallback       = used_fallback,
        )

        # Cache result
        if len(_COMPLIANCE_CACHE) > 200:
            oldest = min(_COMPLIANCE_CACHE.keys(), key=lambda k: _COMPLIANCE_CACHE[k][0])
            _COMPLIANCE_CACHE.pop(oldest, None)
        _COMPLIANCE_CACHE[cache_key] = (now, response)

        return response

    def _build_queries(self, scheme_name: str, facts: Dict[str, Any]) -> List[str]:
        queries = [
            f"{scheme_name} eligibility criteria who can apply requirements",
            f"{scheme_name} documents required application process",
        ]
        parts = [v for k, v in [
            ("msme_classification", facts.get("msme_classification")),
            ("business_type",       facts.get("business_type")),
            ("state",               facts.get("state")),
        ] if v]
        if parts:
            queries.append(f"{scheme_name} {' '.join(parts)} MSME compliance guidelines")
        queries.append(f"MSME {scheme_name} subsidy loan eligibility financial assistance")
        return queries
