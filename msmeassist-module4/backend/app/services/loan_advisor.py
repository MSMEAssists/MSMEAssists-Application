"""
Loan Advisor Service for Module 4.

Determines loan categories, evaluates eligibility against business profile and financial limits,
and generates structured financing recommendations with tailored explanations.
"""
from typing import Any, Dict, List, Optional
from app.models.schemas import (
    BusinessProfilePayload,
    FinancialInputs,
    FinancialSummary,
    LoanInputs,
    LoanRequirement,
    RecommendedLoanOption,
)
from app.services.financial_analyzer import format_inr


SUPPORTED_LOAN_CATEGORIES = [
    {
        "id": "working_capital",
        "name": "Working Capital Loan",
        "description": "Short-term credit for daily operations, raw material procurement, and cash flow management.",
        "typical_tenure": "12 to 36 months",
        "typical_interest": "8.5% - 12.5% p.a.",
    },
    {
        "id": "term_loan",
        "name": "Term Loan",
        "description": "Medium to long-term capital financing for business infrastructure, expansion, or asset creation.",
        "typical_tenure": "3 to 7 years",
        "typical_interest": "9.0% - 13.0% p.a.",
    },
    {
        "id": "machinery_loan",
        "name": "Machinery/Equipment Loan",
        "description": "Financing specifically for purchasing plant equipment, machinery, technology upgrades, or tools.",
        "typical_tenure": "3 to 5 years",
        "typical_interest": "8.0% - 11.5% p.a.",
    },
    {
        "id": "expansion_loan",
        "name": "Business Expansion Loan",
        "description": "Capital loans for opening new branches, expanding operational capacity, or entering export markets.",
        "typical_tenure": "3 to 7 years",
        "typical_interest": "9.5% - 14.0% p.a.",
    },
    {
        "id": "msme_gov_supported",
        "name": "MSME Government-Supported Loan",
        "description": "Government schemes with interest subvention, capital subsidies, or special concessions for MSMEs.",
        "typical_tenure": "3 to 7 years",
        "typical_interest": "7.0% - 10.5% p.a. (Post Subsidy)",
    },
    {
        "id": "credit_guarantee",
        "name": "Credit Guarantee-linked Financing",
        "description": "Collateral-free credit covered under CGTMSE or government guarantee funds up to ₹2-5 Crore.",
        "typical_tenure": "3 to 7 years",
        "typical_interest": "8.5% - 11.5% p.a.",
    },
]


class LoanAdvisor:
    def identify_loan_requirement(
        self,
        loan_inputs: LoanInputs,
        financial_summary: FinancialSummary,
        financial_inputs: FinancialInputs,
    ) -> LoanRequirement:
        # Determine raw required amount
        if loan_inputs.requested_amount_inr and loan_inputs.requested_amount_inr > 0:
            raw_amount = loan_inputs.requested_amount_inr
        else:
            # Parse funding requirement from summary or estimate
            wc = financial_inputs.working_capital_requirement_inr or 0.0
            inv = financial_inputs.investment_requirement_inr or 0.0
            available = financial_inputs.available_capital_inr or 0.0
            raw_amount = max((wc + inv) - available, 500_000.0)

        # Determine purpose & type
        purpose = loan_inputs.purpose or "Business Expansion & Working Capital"
        loan_type = loan_inputs.preferred_loan_type or "MSME Government-Supported Loan"

        urgency = "HIGH" if financial_summary.repayment_capacity_rating in ("CONSTRAINED", "LOW") else "MODERATE"

        return LoanRequirement(
            required_amount=format_inr(raw_amount),
            raw_amount_inr=raw_amount,
            purpose=purpose,
            loan_type=loan_type,
            urgency=urgency,
        )

    def evaluate_and_rank_loan_options(
        self,
        rag_schemes: List[Dict[str, Any]],
        module3_rankings: List[Dict[str, Any]],
        financial_summary: FinancialSummary,
        loan_requirement: LoanRequirement,
        profile: BusinessProfilePayload,
    ) -> List[RecommendedLoanOption]:
        recommended: List[RecommendedLoanOption] = []
        seen_names = set()

        # Build map from module3 rankings if available
        btl_map = {}
        for idx, item in enumerate(module3_rankings, 1):
            s_name = item.get("scheme_name") or item.get("id")
            if s_name:
                btl_map[s_name.lower()] = (idx, item.get("final_score", 0.8))

        # 1. Process retrieved RAG scheme candidates
        for idx, scheme in enumerate(rag_schemes):
            name = scheme.get("title") or scheme.get("name") or f"Government Scheme {idx+1}"
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

            k_type = scheme.get("knowledge_type") or "SCHEME"
            text_lower = (scheme.get("text") or "").lower()

            # Categorize
            if "cgtmse" in text_lower or "guarantee" in text_lower:
                category = "Credit Guarantee-linked financing"
                type_name = "Credit Guarantee-linked Financing"
            elif "machinery" in text_lower or "equipment" in text_lower:
                category = "Machinery/Equipment Loan"
                type_name = "Machinery/Equipment Loan"
            elif "working capital" in text_lower or "credit line" in text_lower:
                category = "Working Capital Loan"
                type_name = "Working Capital Loan"
            elif "subsidy" in text_lower or "pmegp" in text_lower or "mudra" in text_lower:
                category = "MSME Government-Supported Loan"
                type_name = "MSME Government-Supported Loan"
            else:
                category = "MSME Government-Supported Loan"
                type_name = "Term Loan"

            # Match BTL rank if present
            btl_match = btl_map.get(name.lower())
            btl_rank = btl_match[0] if btl_match else (idx + 1)
            base_score = btl_match[1] if btl_match else max(0.95 - (idx * 0.05), 0.60)

            # Adjust financial suitability score based on repayment capacity
            fin_score = base_score
            if financial_summary.repayment_capacity_rating == "HIGH":
                fin_score = min(fin_score + 0.05, 0.99)
            elif financial_summary.repayment_capacity_rating == "LOW":
                fin_score = max(fin_score - 0.15, 0.45)

            # Generate tailored explanation
            reason = (
                f"Option recommended for {profile.name} because the business reported an annual turnover of "
                f"{financial_summary.annual_revenue} with a '{financial_summary.repayment_capacity_rating}' repayment capacity, "
                f"matching the eligibility terms retrieved from official records for {loan_requirement.purpose}."
            )

            # Extract amount / tenure / interest if available in text or use standards
            amt_str = f"Up to ₹2.00 Crore (Coverage based on {profile.msme_classification.capitalize()} Enterprise eligibility)"
            if "200 lakh" in text_lower or "2 crore" in text_lower:
                amt_str = "Up to ₹2.00 Crore"
            elif "50 lakh" in text_lower:
                amt_str = "Up to ₹50.00 Lakh"
            elif "10 lakh" in text_lower or "mudra" in text_lower:
                amt_str = "Up to ₹10.00 Lakh"

            int_str = "8.5% - 11.5% p.a. (Bank & Scheme dependent)"
            if "subsidy" in text_lower or "interest subvention" in text_lower:
                int_str = "6.5% - 9.5% p.a. (Subsidized rate)"

            tenure_str = "3 to 7 Years"

            docs = [
                "Udyam Registration Certificate",
                "PAN Card & Aadhaar of Business Owner",
                "Bank Statements (Last 12 Months)",
                "GST Returns / Financial Statements",
                "Project Report / Quotation for Investment",
            ]

            recommended.append(
                RecommendedLoanOption(
                    id=f"rag_loan_{idx+1}",
                    name=name,
                    type=type_name,
                    category=category,
                    reason=reason,
                    eligibility=f"Registered {profile.msme_classification.capitalize()} Enterprise operating in {profile.state}.",
                    amount=amt_str,
                    interest_rate=int_str,
                    tenure=tenure_str,
                    documents=docs,
                    financial_suitability_score=round(fin_score, 2),
                    btl_rank=btl_rank,
                    source_organization=scheme.get("source_organization", "Ministry of MSME / SIDBI"),
                    official_url=scheme.get("official_url", "https://msme.gov.in"),
                )
            )

        # 2. Guarantee baseline standard loan categories exist if RAG candidates are few
        if len(recommended) < 3:
            standard_defaults = [
                {
                    "id": "std_cgtmse",
                    "name": "CGTMSE Collateral-Free Credit Guarantee Scheme",
                    "type": "Credit Guarantee-linked Financing",
                    "category": "Credit Guarantee-linked financing",
                    "reason": f"Recommended for {profile.name} to secure loan capital up to ₹2 Crore without pledging physical collateral assets.",
                    "eligibility": "Micro & Small Enterprises with Udyam Registration",
                    "amount": "Up to ₹2.00 Crore",
                    "interest_rate": "8.5% - 11.0% p.a.",
                    "tenure": "5 Years",
                    "docs": ["Udyam Certificate", "GST Returns", "12 Months Bank Statement", "Business Plan"],
                    "url": "https://www.cgtmse.in",
                },
                {
                    "id": "std_mudra",
                    "name": "PMMY MUDRA Business Loan (Tarun Category)",
                    "type": "MSME Government-Supported Loan",
                    "category": "MSME Government-Supported Loan",
                    "reason": "Provides working capital and equipment financing up to ₹10 Lakhs with minimal processing friction.",
                    "eligibility": "Non-Corporate Micro & Small Business Units",
                    "amount": "Up to ₹10.00 Lakh",
                    "interest_rate": "8.5% - 10.0% p.a.",
                    "tenure": "3 to 5 Years",
                    "docs": ["Udyam / Trade License", "PAN & Aadhaar", "Bank Account Details"],
                    "url": "https://www.mudra.org.in",
                },
                {
                    "id": "std_machinery",
                    "name": "SIDBI Equipment & Machinery Purchase Term Loan",
                    "type": "Machinery/Equipment Loan",
                    "category": "Machinery/Equipment Loan",
                    "reason": "Tailored for acquiring new machinery, plant equipment, or technology modernisations for manufacturing & service units.",
                    "eligibility": "Operating MSME units with > 2 years track record",
                    "amount": "Up to ₹1.00 Crore",
                    "interest_rate": "8.0% - 10.5% p.a.",
                    "tenure": "3 to 7 Years",
                    "docs": ["Machinery Quotation", "Audited Financials", "GST Returns", "Udyam Certificate"],
                    "url": "https://www.sidbi.in",
                },
            ]

            for s in standard_defaults:
                if s["name"].lower() not in seen_names:
                    seen_names.add(s["name"].lower())
                    recommended.append(
                        RecommendedLoanOption(
                            id=s["id"],
                            name=s["name"],
                            type=s["type"],
                            category=s["category"],
                            reason=s["reason"],
                            eligibility=s["eligibility"],
                            amount=s["amount"],
                            interest_rate=s["interest_rate"],
                            tenure=s["tenure"],
                            documents=s["docs"],
                            financial_suitability_score=0.85,
                            btl_rank=len(recommended) + 1,
                            source_organization="Ministry of MSME / Bank",
                            official_url=s["url"],
                        )
                    )

        # Sort options by financial_suitability_score descending
        recommended.sort(key=lambda x: -x.financial_suitability_score)

        return recommended
