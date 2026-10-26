"""
Knowledge classification: decide which KnowledgeType a document represents,
and (for SCHEME / LOAN, the prioritized types for this prototype) extract
structured fields -- WITHOUT inventing anything not present in the text.

This is a transparent, rule-based classifier (keyword + structural signals).
It is intentionally conservative: if signals are weak/absent, the document
is classified OTHER rather than guessed into SCHEME/LOAN. A future
iteration can swap in an LLM-based or ML classifier behind this same
function signature.
"""
import re
from typing import Optional

from app.models.entities import KnowledgeType

_TYPE_KEYWORDS = {
    KnowledgeType.LOAN: [
        "loan", "credit facility", "credit scheme", "interest rate",
        "collateral", "repayment", "line of credit", "working capital loan",
        "term loan", "refinance",
    ],
    KnowledgeType.SUBSIDY: ["subsidy", "subsidised", "subsidized", "reimbursement of"],
    KnowledgeType.GRANT: ["grant-in-aid", "grant of ", "financial grant", "seed grant"],
    KnowledgeType.SCHEME: ["scheme", "yojana", "programme", "program for", "mission"],
    KnowledgeType.POLICY: ["policy", "national policy", "draft policy"],
    KnowledgeType.NOTIFICATION: ["notification no", "gazette", "office memorandum", "circular"],
    KnowledgeType.GUIDELINE: ["guidelines", "standard operating procedure", "sop for"],
    KnowledgeType.COMPLIANCE: ["compliance", "mandatory filing", "statutory requirement"],
    KnowledgeType.EXPORT: ["export obligation", "export promotion", "foreign trade policy", "shipping bill"],
    KnowledgeType.PERMISSION: ["license", "licence", "permit", "registration certificate", "approval required"],
    KnowledgeType.PROCUREMENT: ["tender", "e-procurement", "bid document", "request for proposal", "rfp"],
}

# LOAN is checked before SCHEME because loan/credit pages very often also
# contain the word "scheme" (e.g. "Credit Guarantee Scheme"), but the
# financial-instrument signals should win.
_PRIORITY_ORDER = [
    KnowledgeType.LOAN,
    KnowledgeType.PROCUREMENT,
    KnowledgeType.NOTIFICATION,
    KnowledgeType.PERMISSION,
    KnowledgeType.EXPORT,
    KnowledgeType.COMPLIANCE,
    KnowledgeType.GUIDELINE,
    KnowledgeType.SUBSIDY,
    KnowledgeType.GRANT,
    KnowledgeType.POLICY,
    KnowledgeType.SCHEME,
]

_MIN_HITS_TO_CLASSIFY = 1


def classify(title: Optional[str], text: str) -> KnowledgeType:
    haystack = f"{title or ''}\n{text}".lower()

    scores = {}
    for ktype, keywords in _TYPE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in haystack)
        scores[ktype] = hits

    # LOAN gets a scoring boost: financial-instrument terms (interest rate,
    # collateral, repayment...) are a strong, fairly unambiguous signal even
    # when a loan/credit page also happens to say "scheme" (e.g. "Credit
    # Guarantee Scheme"), so a single LOAN hit should usually outrank a
    # single generic SCHEME/SUBSIDY hit rather than losing a tied vote.
    if scores.get(KnowledgeType.LOAN, 0) > 0:
        scores[KnowledgeType.LOAN] += 1

    best_score = max(scores.values(), default=0)
    if best_score < _MIN_HITS_TO_CLASSIFY:
        return KnowledgeType.OTHER

    for ktype in _PRIORITY_ORDER:
        if scores.get(ktype, 0) == best_score:
            return ktype

    return KnowledgeType.OTHER


# --- Field extraction helpers (SCHEME / LOAN) -----------------------------
#
# These use section-heading matching against the cleaned text/headings to
# pull out a field's content. If no matching section exists, the field is
# left as None (unavailable) rather than guessed.

_FIELD_HEADING_PATTERNS = {
    "objective": [r"objective[s]?", r"aim[s]?"],
    "eligibility": [r"eligibilit(y|ies)", r"who can apply", r"eligible applicants?"],
    "benefits": [r"benefits?", r"key features?"],
    "financial_assistance": [r"financial assistance", r"assistance provided", r"funding pattern"],
    "subsidy_details": [r"subsidy", r"subsidy details"],
    "application_process": [r"how to apply", r"application process", r"procedure for application"],
    "required_documents": [r"documents? required", r"required documents?", r"list of documents"],
    "implementing_organization": [r"implementing agency", r"nodal agency", r"implementing organi[sz]ation"],
    "provider": [r"lending institution", r"provided by", r"scheme (is )?offered by"],
    "purpose": [r"purpose", r"objective[s]?"],
    "loan_amount": [r"loan amount", r"quantum of (loan|assistance)", r"amount of (loan|assistance)"],
    "interest_information": [r"interest rate", r"rate of interest"],
    "repayment_information": [r"repayment", r"tenure"],
    "collateral_information": [r"collateral", r"security requirement"],
    "guarantee_information": [r"guarantee", r"credit guarantee"],
    "description": [r"about (the )?scheme", r"overview", r"introduction"],
}


def _find_section(text: str, headings: list, patterns: list) -> Optional[str]:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        norm = line.strip().lower()
        for pattern in patterns:
            if re.fullmatch(pattern + r"\s*:?", norm) or re.match(r"^" + pattern + r"\s*[:\-]", norm):
                # Collect following lines until the next heading-like line
                # or a blank gap, as the section body.
                body_lines = []
                for j in range(i + 1, min(i + 15, len(lines))):
                    nxt = lines[j].strip()
                    if not nxt:
                        if body_lines:
                            break
                        continue
                    if nxt.lower() in [h.lower() for h in headings] and body_lines:
                        break
                    body_lines.append(nxt)
                if body_lines:
                    return " ".join(body_lines).strip()
    return None


def extract_fields(knowledge_type: KnowledgeType, title: Optional[str], text: str, headings: list) -> dict:
    fields = {}
    if knowledge_type == KnowledgeType.SCHEME:
        keys = [
            "description", "objective", "eligibility", "benefits",
            "financial_assistance", "subsidy_details", "application_process",
            "required_documents", "implementing_organization",
        ]
    elif knowledge_type == KnowledgeType.LOAN:
        keys = [
            "provider", "purpose", "eligibility", "loan_amount",
            "interest_information", "repayment_information",
            "collateral_information", "guarantee_information",
            "application_process", "required_documents",
        ]
    else:
        keys = []

    for key in keys:
        patterns = _FIELD_HEADING_PATTERNS.get(key, [])
        fields[key] = _find_section(text, headings, patterns) if patterns else None

    return fields
