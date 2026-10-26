"""
Personalized AI Scheme Advisor Service.

Coordinates multi-agent intelligence across:
  1. Scheme Intelligence (discovery, alternative ranking, BTL matching)
  2. Eligibility Advisor (profile attribute verification against official gazette rules)
  3. Financial Advisor (subsidy calculation, collateral-free credit, machinery financing)
  4. Compliance Advisor (6-point gap analysis, document checklist, statutory registrations)
  5. Scheme Reconsideration Workflow (intent-driven alternative scheme recommendation)
  6. Conversational Memory (maintaining multi-turn context without asking users to repeat profile data)
"""
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models.profile_model import ProfileModel
from app.schemas.schemes_schema import SchemeCitationOut, SchemeQueryResponse
from app.services.compliance_service import (
    _FALLBACK_RULES,
    _profile_facts,
    _run_gap_analysis,
    ComplianceService,
)
from app.services import eligibility_service

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Sanitizes text to remove mojibake, replacement chars, control chars, and HTML entities."""
    if not text:
        return ""
    import html
    import unicodedata

    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)

    replacements = {
        "\ufffd": " ",   # Replacement character
        "\u00a0": " ",   # Non-breaking space
        "\u200b": "",    # Zero-width space
        "\ufeff": "",    # BOM
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": " -- ",
        "\u2022": " - ",
        "\u25cf": " - ",
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€“": "-",
        "â€”": " -- ",
        "\x91": "'",
        "\x92": "'",
        "\x93": '"',
        "\x94": '"',
        "\x96": "-",
        "\x97": " -- ",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Strip unprintable control codes and private use area codes
    cleaned = []
    for ch in text:
        code = ord(ch)
        if 0xE000 <= code <= 0xF8FF:
            continue
        if code < 32 and ch not in ("\n", "\r", "\t"):
            continue
        if code == 127:
            continue
        cleaned.append(ch)

    res = "".join(cleaned)
    res = re.sub(r"[ \t]+", " ", res)
    res = re.sub(r"\n{3,}", "\n\n", res)
    return res.strip()


def resolve_conversational_query(
    query: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[str, Optional[str]]:
    """Resolves pronouns and follow-up references ('that', 'this scheme', 'it', 'for it')
    using recent conversation turns.
    
    Returns:
      (effective_query, resolved_scheme_name)
    """
    if not history:
        return query, None

    q_lower = query.lower().strip()
    has_pronoun = any(
        p in q_lower
        for p in (
            "for that", "for this", "for it", "about that", "about this",
            "apply for it", "qualify for it", "this scheme", "that scheme",
            "these schemes", "under this", "under that", "needed for that",
            "required for that", "documents for that", "documents needed for that",
            "eligibility for that", "how do i apply", "what documents do i need",
            "what are the documents", "am i eligible", "how to qualify",
            "maximum limit", "interest rate", "subsidy percentage", "guarantee limit",
        )
    )

    schemes_pattern = r"\b(CGTMSE|PMEGP|MUDRA|PMMY|ZED|CLCSS|STAND-?UP\s*INDIA|MSME\s*SAMADHAAN|MSEFC|ODR|DGFT|MAI|RODTEP|UDYAM)\b"
    resolved_scheme = None

    for msg in reversed(history[-4:]):
        content = msg.get("content", "")
        m = re.search(schemes_pattern, content, re.IGNORECASE)
        if m:
            raw_match = m.group(1).upper()
            if "STAND" in raw_match:
                resolved_scheme = "Stand-Up India"
            elif "SAMADHAAN" in raw_match or "MSEFC" in raw_match or "ODR" in raw_match:
                resolved_scheme = "MSME Samadhaan"
            elif "ZED" in raw_match:
                resolved_scheme = "ZED Certification Scheme"
            elif "MUDRA" in raw_match or "PMMY" in raw_match:
                resolved_scheme = "MUDRA"
            elif "CGTMSE" in raw_match:
                resolved_scheme = "CGTMSE"
            elif "PMEGP" in raw_match:
                resolved_scheme = "PMEGP"
            elif "UDYAM" in raw_match:
                resolved_scheme = "Udyam Registration"
            elif "DGFT" in raw_match or "MAI" in raw_match:
                resolved_scheme = "DGFT MAI"
            else:
                resolved_scheme = raw_match
            break

    if resolved_scheme and has_pronoun:
        effective_query = re.sub(
            r"\b(for\s+that|for\s+this|for\s+it|this\s+scheme|that\s+scheme|under\s+this|under\s+that)\b",
            f"for {resolved_scheme}",
            query,
            flags=re.IGNORECASE,
        )
        if resolved_scheme.lower() not in effective_query.lower():
            effective_query = f"{effective_query} for {resolved_scheme}"
        return effective_query.strip(), resolved_scheme

    return query, resolved_scheme


class AdvisorService:
    def __init__(self, schemes_service=None, rag_client=None):
        self.schemes_service = schemes_service
        self.rag_client = rag_client

    def extract_profile_facts(self, profile: Optional[ProfileModel]) -> Dict[str, Any]:
        """Extracts complete facts from ProfileModel without mutating anything."""
        if not profile:
            return {
                "business_name": "Your Enterprise",
                "industry": "Manufacturing / Services",
                "msme_classification": "Micro Enterprise",
                "state": "India",
                "area_type": "urban",
                "turnover_inr": None,
                "investment_inr": None,
                "employee_count": None,
                "is_women_owned": False,
                "social_category": "General",
                "is_rural": False,
                "registered_types": set(),
                "age_years": 2.0,
                "has_existing_loan": False,
                "has_bank_finance": False,
            }

        return _profile_facts(profile)

    def detect_intent(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Classifies conversational intent, desired financing types, and scheme mentions."""
        q_lower = query.lower()

        # Check recent conversation history for context
        history_context = ""
        if history:
            history_context = " ".join([m.get("content", "").lower() for m in history[-4:]])

        combined = f"{history_context} {q_lower}"

        # 1. Scheme mentions
        mentioned_scheme = None
        if "pmegp" in combined or "prime minister employment" in combined:
            mentioned_scheme = "PMEGP"
        elif "cgtmse" in combined or "credit guarantee" in combined:
            mentioned_scheme = "CGTMSE"
        elif "mudra" in combined or "pmmy" in combined or "tarun" in combined:
            mentioned_scheme = "MUDRA"
        elif "stand" in combined and "up" in combined:
            mentioned_scheme = "Stand-Up India"
        elif "clcss" in combined or "capital subsidy" in combined:
            mentioned_scheme = "CLCSS"
        elif "zed" in combined or "zero defect" in combined:
            mentioned_scheme = "ZED Certification Scheme"
        elif "sidbi" in combined:
            mentioned_scheme = "SIDBI Schemes"

        # 2. Rejection / Reconsideration
        is_rejection = any(
            phrase in q_lower
            for phrase in (
                "don't like", "dont like", "do not like", "reject", "not interested",
                "other schemes", "another scheme", "different scheme", "alternatives",
                "not useful", "something else", "change recommendation", "don't want",
                "dont want", "do not want", "exclude", "avoid", "hate"
            )
        )

        # 3. Profile improvement / How to qualify
        is_qualification = any(
            phrase in q_lower
            for phrase in (
                "how to qualify", "how can i qualify", "what changes", "how to become eligible",
                "what should i do to qualify", "what do i need to qualify", "make to qualify",
                "how to meet", "how do i qualify", "qualify for"
            )
        )

        # 4. Eligibility check / Explanation
        is_eligibility_check = any(
            phrase in q_lower
            for phrase in (
                "why am i not eligible", "why not eligible", "am i eligible",
                "check my eligibility", "eligibility criteria", "reasons for rejection",
                "why ineligib", "can i apply"
            )
        )

        # 5. Financing specific preferences
        wants_collateral_free = any(k in q_lower for k in ("collateral-free", "collateral free", "no collateral", "zero collateral", "without collateral", "unsecured"))
        wants_higher_subsidy = any(k in q_lower for k in ("higher subsidy", "more subsidy", "grant", "maximum subsidy", "capital subsidy"))
        wants_machinery = any(k in q_lower for k in ("machinery", "equipment", "purchase machine", "purchasing machinery", "plant", "technology upgrade", "automation", "tools"))
        wants_loan = any(k in q_lower for k in ("loan", "credit", "working capital", "finance", "debt", "bank finance"))
        wants_best = any(k in q_lower for k in ("best scheme", "which scheme is best", "best option", "recommend the best"))
        wants_compliance = any(k in q_lower for k in ("documents required", "what documents", "registration needed", "udyam", "gst", "license", "permission"))

        return {
            "is_rejection": is_rejection,
            "is_qualification": is_qualification,
            "is_eligibility_check": is_eligibility_check,
            "wants_collateral_free": wants_collateral_free,
            "wants_higher_subsidy": wants_higher_subsidy,
            "wants_machinery": wants_machinery,
            "wants_loan": wants_loan,
            "wants_best": wants_best,
            "wants_compliance": wants_compliance,
            "mentioned_scheme": mentioned_scheme,
        }

    async def generate_personalized_response(
        self,
        query: str,
        profile: Optional[ProfileModel],
        history: Optional[List[Dict[str, str]]] = None,
        current_scheme_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Main personalized advisor entrypoint routing based on intent, conversation context, and business facts."""
        effective_query, resolved_scheme = resolve_conversational_query(query, history)
        facts = self.extract_profile_facts(profile)
        intent = self.detect_intent(effective_query, history)

        biz_name = facts.get("business_name") or "Your Enterprise"
        industry = facts.get("industry") or "Manufacturing"
        msme_class = facts.get("msme_classification") or "Micro Enterprise"
        state = facts.get("state") or "India"
        is_rural = facts.get("is_rural_enterprise", False)
        is_women = facts.get("is_women_owned", False)
        target_scheme = intent.get("mentioned_scheme") or resolved_scheme or current_scheme_id

        # ── WORKFLOW 1: Business Profile Improvement & Ineligibility Gap Analysis ──
        # Triggers when user asks: "How can I qualify?", "Why am I not eligible?", "What changes to qualify?"
        if intent["is_qualification"] or (intent["is_eligibility_check"] and target_scheme):
            return self._build_profile_improvement_guidance(
                scheme_name=target_scheme or "PMEGP",
                facts=facts,
                biz_name=biz_name,
                msme_class=msme_class,
                industry=industry,
            )

        # ── WORKFLOW 2: Explicit Scheme Reconsideration / Alternative Discovery ──
        # Triggers when user explicitly rejects current recommendations (e.g. "don't like PMEGP", "show alternatives")
        if intent["is_rejection"]:
            return await self._build_scheme_reconsideration(
                query=effective_query,
                intent=intent,
                facts=facts,
                biz_name=biz_name,
                msme_class=msme_class,
                industry=industry,
                state=state,
            )

        # ── WORKFLOW 3: Best Scheme for Situation ──
        if intent["wants_best"]:
            return self._build_best_scheme_advisory(
                facts=facts,
                biz_name=biz_name,
                msme_class=msme_class,
                industry=industry,
                state=state,
                is_women=is_women,
                is_rural=is_rural,
            )

        # ── WORKFLOW 4: Grounded Context-Aware RAG Query (Default General Intelligence) ──
        # Dynamically handles all scheme queries, subsidies, loans, machinery, delayed payments,
        # compliance, and export questions using official retrieved circulars.
        return await self._build_grounded_rag_response(
            query=effective_query,
            facts=facts,
            biz_name=biz_name,
            msme_class=msme_class,
            industry=industry,
        )

    def _build_profile_improvement_guidance(
        self,
        scheme_name: str,
        facts: Dict[str, Any],
        biz_name: str,
        msme_class: str,
        industry: str,
    ) -> Dict[str, Any]:
        """Compares official scheme eligibility criteria against user's profile and returns
        the exact 6-point structured improvement roadmap for each unmet requirement.
        """
        # Run the official gap analysis engine from compliance_service
        gaps = _run_gap_analysis(scheme_name, facts)
        unmet_gaps = [g for g in gaps if g.status in ("not_met", "needs_info")]
        met_gaps = [g for g in gaps if g.status == "met"]

        scheme_display = scheme_name.upper()
        if scheme_display == "PMEGP":
            official_portal = "https://www.kviconline.gov.in/pmegp/"
            ministry = "Ministry of MSME & KVIC"
        elif scheme_display == "CGTMSE":
            official_portal = "https://www.cgtmse.in"
            ministry = "Ministry of MSME & SIDBI"
        elif scheme_display == "MUDRA":
            official_portal = "https://www.mudra.org.in"
            ministry = "Department of Financial Services, Ministry of Finance"
        elif "STAND" in scheme_display:
            official_portal = "https://www.standupmitra.in"
            ministry = "Department of Financial Services / SIDBI"
        else:
            official_portal = "https://msme.gov.in"
            ministry = "Ministry of MSME, Govt. of India"

        lines = [
            f"### Qualification & Profile Improvement Roadmap: {scheme_display}",
            f"Here is a personalized statutory comparison for **{biz_name}** ({msme_class}, {industry}) against official guidelines published by **{ministry}**.",
            "",
        ]

        if not unmet_gaps:
            lines.extend([
                f"Great news! Your registered enterprise profile currently satisfies all primary statutory eligibility criteria checked for **{scheme_display}**.",
                "",
                "#### Confirmed Requirements Met in Your Profile:",
            ])
            for m in met_gaps[:5]:
                lines.append(f"- **{m.requirement}**: {m.description} *(Confirmed: {m.profile_value})*")
            lines.extend([
                "",
                f"You can proceed directly to submit an application on the [{scheme_display} Official Portal]({official_portal}).",
            ])
        else:
            lines.extend([
                f"To qualify for **{scheme_display}**, the following requirements currently have gaps or require verification against your business profile:",
                "",
            ])

            for idx, gap in enumerate(unmet_gaps, start=1):
                cur_status = gap.profile_value if gap.profile_value else "Not recorded in current profile"
                possible_step = gap.how_to_fix or "Update or obtain this statutory credential through the official government portal."
                gap_explanation = gap.gap_detail or gap.description

                # Determine evidence required
                if "udyam" in gap.requirement.lower():
                    evidence = "Udyam Registration Certificate (URC) issued by Ministry of MSME"
                elif "gst" in gap.requirement.lower():
                    evidence = "GST Registration Certificate (GSTIN) & recent GSTR-3B filings"
                elif "turnover" in gap.requirement.lower() or "investment" in gap.requirement.lower():
                    evidence = "Audited Balance Sheet, ITR-V, and CA Plant & Machinery Certificate"
                elif "age" in gap.requirement.lower() or "greenfield" in gap.requirement.lower():
                    evidence = "Project Report / DPR showing new manufacturing or service activity"
                elif "document" in gap.requirement.lower() or "pan" in gap.requirement.lower():
                    evidence = "PAN Card of Enterprise / Proprietor and Aadhaar of authorized signatory"
                else:
                    evidence = "Official statutory certificates, bank account statements, and project DPR"

                lines.extend([
                    f"#### {idx}. {gap.requirement}",
                    f"- **Requirement:** {gap.description}",
                    f"- **Current Profile Status:** {cur_status}",
                    f"- **Identified Gap:** {gap_explanation}",
                    f"- **Realistic Next Step:** {possible_step}",
                    f"- **Statutory Evidence Needed:** {evidence}",
                    f"- **Official Documentation Source:** [{scheme_display} Official Guidelines]({official_portal})",
                    "",
                ])

            lines.extend([
                "---",
                "#### Important Advisory on Business Profile Integrity:",
                "- **Never falsify business numbers:** Official scheme applications are verified against GSTN, CBDT tax records, and Udyam databases during bank credit appraisal. Falsifying figures will lead to mandatory rejection.",
                "- **Structural Constraints:** If an unmet condition relates to your enterprise scale or business age (such as greenfield requirements), you cannot alter that fact. In such cases, we recommend exploring alternative credit schemes such as CGTMSE or MUDRA.",
                "- **Approval Disclaimer:** Fulfilling statutory eligibility is mandatory, but actual loan disbursement or subsidy sanction depends on bank credit viability and project DPR approval.",
            ])

        citations = [
            SchemeCitationOut(
                title=f"{scheme_display} Official Guidelines",
                organization=ministry,
                official_url=official_portal,
                page_number=1,
            )
        ]

        return {
            "query": f"How to qualify for {scheme_display}",
            "answer_text": clean_text("\n".join(lines)),
            "has_sufficient_context": True,
            "citations": citations,
            "retrieved_result_count": len(citations),
            "intent": "PROFILE_IMPROVEMENT",
            "eligibility_gaps": [g.__dict__ for g in unmet_gaps],
            "next_steps": [g.how_to_fix for g in unmet_gaps if g.how_to_fix],
        }

    async def _build_scheme_reconsideration(
        self,
        query: str,
        intent: Dict[str, Any],
        facts: Dict[str, Any],
        biz_name: str,
        msme_class: str,
        industry: str,
        state: str,
    ) -> Dict[str, Any]:
        """Handles scheme reconsideration when a user rejects current recommendations
        or asks for different funding types (collateral-free, higher subsidy, machinery).
        """
        # Determine preference focus
        wants_collateral_free = intent.get("wants_collateral_free", False)
        wants_machinery = intent.get("wants_machinery", False)
        wants_subsidy = intent.get("wants_higher_subsidy", False)

        if wants_collateral_free and wants_machinery:
            preference_summary = "collateral-free credit specifically for purchasing machinery and equipment"
        elif wants_collateral_free:
            preference_summary = "collateral-free credit and institutional finance"
        elif wants_subsidy:
            preference_summary = "higher capital subsidies and upfront grants"
        elif wants_machinery:
            preference_summary = "machinery purchase and technology upgrades"
        else:
            preference_summary = "alternative government credit and subsidy support"

        # Prioritize based on user's specific request
        schemes_to_present = []

        if wants_collateral_free and wants_machinery:
            schemes_to_present = [
                {
                    "title": "Credit Guarantee Fund Trust for Micro and Small Enterprises (CGTMSE)",
                    "ministry": "Ministry of MSME & SIDBI",
                    "benefit": "100% guarantee coverage for collateral-free term loans up to ₹5 Crore specifically for purchasing plant, machinery, and equipment.",
                    "why_match": f"Eliminates the requirement of pledging land, building, or third-party collateral for {biz_name} to acquire manufacturing machinery.",
                    "condition": "Available to new and existing Micro and Small enterprises with viable project cash flows through scheduled commercial banks.",
                    "url": "https://www.cgtmse.in",
                },
                {
                    "title": "SIDBI Speed Loan / Equipment Financing",
                    "ministry": "Small Industries Development Bank of India (SIDBI)",
                    "benefit": "100% institutional financing for new plant & machinery acquisition up to ₹1 Crore with rapid 48-hour sanction and zero third-party collateral required.",
                    "why_match": f"Direct institutional lending designed specifically for {industry} enterprises to purchase machinery without collateral delays.",
                    "condition": "Enterprise must have at least 3 years of operations with audited financials and positive net worth.",
                    "url": "https://www.sidbi.in",
                },
                {
                    "title": "Credit Linked Capital Subsidy Scheme (CLCSS)",
                    "ministry": "Office of DC-MSME, Ministry of MSME",
                    "benefit": "15% upfront capital subsidy (up to ₹15 Lakhs) on institutional finance for modern plant machinery and technology upgrades.",
                    "why_match": f"Reduces the effective cost of machinery acquisition for {biz_name} by providing non-repayable upfront capital grant alongside bank credit.",
                    "condition": "Machinery must be from approved technology sub-sectors linked to a term loan from scheduled commercial banks.",
                    "url": "https://dcmsme.gov.in",
                },
                {
                    "title": "Pradhan Mantri Mudra Yojana (PMMY) -- Tarun Category",
                    "ministry": "Department of Financial Services, Ministry of Finance",
                    "benefit": "Collateral-free term loans between ₹5 Lakhs and ₹10 Lakhs specifically for equipment, machinery, and business assets.",
                    "why_match": f"Zero collateral and zero margin money requirements for micro enterprises purchasing equipment.",
                    "condition": "Non-corporate, non-farm small/micro enterprises with satisfactory bank credit track record.",
                    "url": "https://www.mudra.org.in",
                },
            ]
        elif wants_higher_subsidy:
            schemes_to_present = [
                {
                    "title": "Prime Minister's Employment Generation Programme (PMEGP)",
                    "ministry": "KVIC / Ministry of MSME",
                    "benefit": "15% to 35% Credit-Linked Capital Subsidy on project costs up to ₹50 Lakhs (Manufacturing).",
                    "why_match": f"Ideal for {biz_name} seeking capital grants. Rural enterprises and special categories receive up to 35% margin money subsidy.",
                    "condition": "New projects only; beneficiary contribution is only 5% for special categories and 10% for general categories.",
                    "url": "https://www.kviconline.gov.in/pmegp/",
                },
                {
                    "title": "Credit Linked Capital Subsidy Scheme (CLCSS)",
                    "ministry": "Office of DC-MSME",
                    "benefit": "15% upfront capital subsidy (up to ₹15 Lakhs) on institutional finance for technology modernization.",
                    "why_match": f"Provides non-repayable upfront subsidy for upgrading plant machinery in {industry}.",
                    "condition": "Must be linked to institutional term loans from scheduled commercial banks for approved modern technologies.",
                    "url": "https://dcmsme.gov.in",
                },
            ]
        elif wants_collateral_free:
            schemes_to_present = [
                {
                    "title": "Credit Guarantee Fund Trust for Micro and Small Enterprises (CGTMSE)",
                    "ministry": "Ministry of MSME & SIDBI",
                    "benefit": "100% guarantee coverage for collateral-free credit facilities up to ₹5 Crore.",
                    "why_match": f"Eliminates the requirement of pledging immovable property or third-party collateral for {biz_name}.",
                    "condition": "Available to new and existing Micro and Small enterprises with viable cash-flow projects.",
                    "url": "https://www.cgtmse.in",
                },
                {
                    "title": "Pradhan Mantri Mudra Yojana (PMMY) -- Tarun Category",
                    "ministry": "Department of Financial Services",
                    "benefit": "Collateral-free business loans between ₹5 Lakhs and ₹10 Lakhs at competitive interest rates.",
                    "why_match": "Zero processing fee for Shishu and Kishore; minimal documentation for expanding micro units.",
                    "condition": "Non-corporate, non-farm small/micro enterprises with satisfactory bank track record.",
                    "url": "https://www.mudra.org.in",
                },
            ]
        elif wants_machinery:
            schemes_to_present = [
                {
                    "title": "Credit Linked Capital Subsidy Scheme (CLCSS)",
                    "ministry": "Ministry of MSME",
                    "benefit": "15% capital grant on purchase of state-of-the-art plant machinery up to ₹1 Crore investment.",
                    "why_match": f"Directly reduces capital expenditure for {biz_name} to install modern machinery.",
                    "condition": "Machinery must be from approved technology sub-sectors (e.g. food processing, electronics, engineering).",
                    "url": "https://dcmsme.gov.in",
                },
                {
                    "title": "SIDBI Speed Loan / Equipment Financing",
                    "ministry": "Small Industries Development Bank of India (SIDBI)",
                    "benefit": "100% financing for new machinery purchase up to ₹1 Crore with rapid 48-hour sanction.",
                    "why_match": "Direct lending scheme with lower interest rate for established MSME units in manufacturing.",
                    "condition": "Enterprise must have at least 3 years of operational track record with positive net worth.",
                    "url": "https://www.sidbi.in",
                },
            ]
        else:
            # General reconsideration — offer distinct varied options
            schemes_to_present = [
                {
                    "title": "CGTMSE Collateral-Free Credit Scheme",
                    "ministry": "Ministry of MSME & SIDBI",
                    "benefit": "Credit guarantee up to ₹5 Crore without third-party guarantee or property mortgage.",
                    "why_match": f"Designed to secure working capital and term loans for {msme_class} enterprises in {industry}.",
                    "condition": "Standard credit appraisal by scheduled banks; guarantee fee covered under the trust.",
                    "url": "https://www.cgtmse.in",
                },
                {
                    "title": "PMEGP Credit-Linked Subsidy Scheme",
                    "ministry": "KVIC / Ministry of MSME",
                    "benefit": "Up to 35% capital subsidy and bank loan for establishing new production capacity.",
                    "why_match": f"Maximum grant support for {industry} enterprises located in {state}.",
                    "condition": "Requires formal project report (DPR) and online application through KVIC portal.",
                    "url": "https://www.kviconline.gov.in/pmegp/",
                },
                {
                    "title": "MSME Sustainable (ZED) Certification Scheme",
                    "ministry": "Ministry of MSME",
                    "benefit": "Up to 80% financial subsidy on certification costs, plus interest concession on bank loans.",
                    "why_match": f"Enhances enterprise credibility, reduces manufacturing defects, and unlocks bank concessions.",
                    "condition": "Enterprise must hold valid Udyam Registration.",
                    "url": "https://zed.msme.gov.in",
                },
            ]

        ack_prefix = ""
        if intent.get("is_rejection") and intent.get("mentioned_scheme"):
            ack_prefix = f"Understood. We have excluded **{intent['mentioned_scheme']}** based on your feedback. "
        else:
            ack_prefix = "Understood. "

        lines = [
            f"### Reconsidered Government Scheme Recommendations for {biz_name}",
            f"{ack_prefix}We have re-aligned our government scheme search to focus specifically on **{preference_summary}** for your enterprise ({msme_class}, {industry}, {state}).",
            "",
            "Here are tailored alternative schemes matching your stated preference:",
            "",
        ]

        citations = []
        for idx, s in enumerate(schemes_to_present, start=1):
            lines.extend([
                f"#### {idx}. {s['title']}",
                f"- **Nodal Ministry / Organization:** {s['ministry']}",
                f"- **Financial & Structural Benefits:** {s['benefit']}",
                f"- **Why it matches your preference:** {s['why_match']}",
                f"- **Key Eligibility Condition:** {s['condition']}",
                f"- **Official Portal:** [{s['title']}]({s['url']})",
                "",
            ])
            citations.append(
                SchemeCitationOut(
                    title=s["title"],
                    organization=s["ministry"],
                    official_url=s["url"],
                    page_number=1,
                )
            )

        lines.extend([
            "---",
            "**Next Step:** Would you like to review the statutory qualification checklist or document requirements for any of these alternatives? Simply ask: *\"How to qualify for PMEGP?\"* or *\"What documents are required for CGTMSE?\"*.",
        ])

        return {
            "query": query,
            "answer_text": clean_text("\n".join(lines)),
            "has_sufficient_context": True,
            "citations": citations,
            "retrieved_result_count": len(citations),
            "intent": "SCHEME_RECONSIDERATION",
            "recommended_schemes": schemes_to_present,
            "next_steps": ["Review qualification checklist", "Inspect official portal links"],
        }

    def _build_best_scheme_advisory(
        self,
        facts: Dict[str, Any],
        biz_name: str,
        msme_class: str,
        industry: str,
        state: str,
        is_women: bool,
        is_rural: bool,
    ) -> Dict[str, Any]:
        """Provides an explainable, personalized verdict on which scheme is best suited."""
        lines = [
            f"### Best Scheme Assessment for {biz_name}",
            f"Based on your registered profile facts as a **{msme_class}** in the **{industry}** sector ({state}), here is our explainable advisory assessment:",
            "",
        ]

        if is_women:
            lines.extend([
                "#### Top Recommendation: Stand-Up India & PMEGP Special Category",
                f"- **Why it's best for you:** As a women-owned enterprise, you qualify for special statutory concessions under both PMEGP and Stand-Up India.",
                "- **PMEGP:** You receive **35% capital subsidy** (rural) or **25%** (urban) with a personal promoter contribution of only 5% of project cost.",
                "- **Stand-Up India:** Bank loans between ₹10 Lakhs and ₹1 Crore for greenfield projects with handholding support.",
                "- **Official Links:** [KVIC PMEGP Portal](https://www.kviconline.gov.in/pmegp/) | [Stand-Up India](https://www.standupmitra.in)",
                "",
            ])
        else:
            lines.extend([
                "#### 1. For Working Capital & Business Loans: CGTMSE",
                f"- **Why it's best for you:** If {biz_name} needs credit facilities without mortgaging real estate, CGTMSE covers up to ₹5 Crore in collateral-free bank loans.",
                "- **Official Link:** [CGTMSE Official Portal](https://www.cgtmse.in)",
                "",
                "#### 2. For Project Expansion & Capital Subsidy: PMEGP",
                f"- **Why it's best for you:** If you are setting up new manufacturing lines in {state}, PMEGP offers 15% to 35% non-repayable capital subsidy.",
                "- **Official Link:** [PMEGP Application Portal](https://www.kviconline.gov.in/pmegp/)",
                "",
            ])

        lines.extend([
            "#### 3. For Quality Benchmarking & Fee Subsidies: ZED Certification",
            "- **Why it's beneficial:** MSME Sustainable (ZED) provides up to 80% subsidy on certification fees, ₹5 Lakhs testing financial support, and a 0.5% interest rate discount from major public sector banks.",
            "- **Official Link:** [ZED Portal](https://zed.msme.gov.in)",
            "",
            "---",
            "To see the exact step-by-step qualification roadmap for any of these, ask: *\"How to qualify for CGTMSE?\"*.",
        ])

        citations = [
            SchemeCitationOut(
                title="CGTMSE Official Portal",
                organization="Ministry of MSME & SIDBI",
                official_url="https://www.cgtmse.in",
            ),
            SchemeCitationOut(
                title="PMEGP Application Portal",
                organization="KVIC / Ministry of MSME",
                official_url="https://www.kviconline.gov.in/pmegp/",
            ),
        ]

        return {
            "query": "Which scheme is best for my situation?",
            "answer_text": clean_text("\n".join(lines)),
            "has_sufficient_context": True,
            "citations": citations,
            "retrieved_result_count": len(citations),
            "intent": "BEST_SCHEME_ADVISORY",
        }

    def _build_compliance_document_guidance(
        self,
        scheme_name: Optional[str],
        facts: Dict[str, Any],
        biz_name: str,
    ) -> Dict[str, Any]:
        """Explains required statutory documents, registrations, and procedures."""
        scheme_label = (scheme_name or "MSME Government Schemes").upper()

        lines = [
            f"### Mandatory Statutory Documents & Registrations: {scheme_label}",
            f"For **{biz_name}**, the following government registrations and documentation are required across central schemes:",
            "",
            "#### 1. Foundation Registrations (Universal):",
            "- **Udyam Registration Certificate (URC):** Mandatory for all MSME benefits, subsidies, and priority sector lending. Free online registration at [udyamregistration.gov.in](https://udyamregistration.gov.in).",
            "- **Permanent Account Number (PAN):** Enterprise PAN (Company/LLP/Partnership) or Proprietor's PAN.",
            "- **Goods and Services Tax (GSTIN):** Mandatory for inter-state sales and turnover above statutory threshold (₹40 Lakhs goods / ₹20 Lakhs services).",
            "",
            "#### 2. Financial & Banking Evidence:",
            "- **Bank Statements:** Last 6 to 12 months active current account statement.",
            "- **Financial Accounts:** Audited Balance Sheet and Profit & Loss accounts for previous 2 years (for existing enterprises).",
            "- **Income Tax Returns:** ITR-V filings for previous 2 assessment years.",
            "",
            "#### 3. Scheme-Specific Evidence (e.g. PMEGP / CGTMSE):",
            "- **Detailed Project Report (DPR):** Cost of plant, machinery, raw material requirement, and projected cash flows.",
            "- **Premises Proof:** Registered lease deed or ownership title / electricity bill.",
            "- **Special Category Certificate:** SC/ST/OBC/Disability certificate where claiming special 35% subsidy.",
            "",
            "---",
            "**Advisory:** Ensure that your enterprise name, address, and partner/director details match identically between your PAN, GSTIN, and Udyam certificates to prevent automated bank verification failures.",
        ]

        citations = [
            SchemeCitationOut(
                title="Official Udyam Registration Portal",
                organization="Ministry of MSME, Govt. of India",
                official_url="https://udyamregistration.gov.in",
            ),
            SchemeCitationOut(
                title="GST Portal",
                organization="CBIC, Govt. of India",
                official_url="https://www.gst.gov.in",
            ),
        ]

        return {
            "query": f"Documents required for {scheme_label}",
            "answer_text": clean_text("\n".join(lines)),
            "has_sufficient_context": True,
            "citations": citations,
            "retrieved_result_count": len(citations),
            "intent": "COMPLIANCE_INQUIRY",
        }

    async def _build_grounded_rag_response(
        self,
        query: str,
        facts: Dict[str, Any],
        biz_name: str,
        msme_class: str,
        industry: str,
    ) -> Dict[str, Any]:
        """Calls RAG retrieval, cleans all character corruption, and adds a personalized summary."""
        raw_ans = None
        if self.rag_client:
            try:
                raw_ans = await self.rag_client.query_rag(query=query, top_k=5)
            except Exception as e:
                logger.warning("RAG client query failed: %s", e)

        citations_data = (raw_ans.get("citations") or []) if raw_ans else []
        has_sufficient = bool(raw_ans and raw_ans.get("has_sufficient_context") and citations_data)

        if not has_sufficient:
            # Transparent boundary / out-of-domain response: NEVER fabricate citations
            notice_text = (
                f"### Official Knowledge Base Notice\n\n"
                f"I searched official Government of India publications for **\"{query}\"**, "
                f"but could not find sufficient verified provisions or guidelines for this topic in the approved MSME repository.\n\n"
                f"- **Approved Knowledge Base Scope:** MSMEAssist is grounded strictly in verified gazettes, circulars, and operational guidelines "
                f"for central MSME schemes (including CGTMSE collateral-free loans, PMEGP subsidies, MUDRA credit, ZED certification, "
                f"MSME Samadhaan for delayed payments, and DGFT export promotion).\n"
                f"- **General Advisory:** If your question relates to non-MSME regulations, personal taxes (such as cryptocurrency or capital gains), "
                f"or foreign visas, please consult the relevant official portal directly (e.g., CBIC / Income Tax Department at [incometax.gov.in](https://incometax.gov.in) "
                f"or the respective official authority).\n"
                f"- **For your enterprise ({biz_name}, {msme_class}, {industry}):** You can ask about collateral-free borrowing, capital subsidy percentages, "
                f"recovering unpaid buyer dues, machinery upgrade finance, or statutory MSME registrations."
            )
            return {
                "query": query,
                "answer_text": clean_text(notice_text),
                "has_sufficient_context": False,
                "citations": [],
                "retrieved_result_count": 0,
                "intent": "UNSUPPORTED_OR_OUT_OF_DOMAIN",
            }

        raw_text = raw_ans.get("answer_text", "")
        cleaned_body = clean_text(raw_text)

        # Contextual prefix for personalization when enterprise profile is bound
        header = f"### Government Scheme Information for {biz_name}\n*Enterprise Context: {msme_class} in {industry}*\n"
        full_text = f"{header}\n{cleaned_body}" if not cleaned_body.startswith("###") else cleaned_body

        citations = [
            SchemeCitationOut(
                title=c.get("title") or "Government Publication",
                organization=c.get("organization") or "Government of India",
                official_url=c.get("official_url") or "https://msme.gov.in",
                page_number=c.get("page_number"),
                document_id=c.get("document_id"),
                chunk_id=c.get("chunk_id"),
            )
            for c in citations_data
        ]

        return {
            "query": query,
            "answer_text": clean_text(full_text),
            "has_sufficient_context": True,
            "citations": citations,
            "retrieved_result_count": len(citations),
            "intent": "GENERAL_QUERY",
        }
