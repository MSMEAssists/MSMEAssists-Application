"""
Unit tests for LoanAdvisor service in Module 4.
Tests loan requirement calculation, categorization, and option ranking.
"""
from app.models.schemas import (
    BusinessProfilePayload,
    FinancialInputs,
    FinancialSummary,
    LoanInputs,
)
from app.services.loan_advisor import LoanAdvisor


def test_identify_loan_requirement():
    advisor = LoanAdvisor()
    summary = FinancialSummary(
        annual_revenue="₹50.00 Lakh",
        monthly_revenue="₹4.17 Lakh",
        monthly_expenses="₹3.00 Lakh",
        monthly_profit="₹1.17 Lakh",
        net_cash_flow="₹1.00 Lakh",
        existing_liabilities="₹5.00 Lakh",
        working_capital_requirement="₹6.00 Lakh",
        investment_requirement="₹10.00 Lakh",
        available_capital="₹3.00 Lakh",
        funding_requirement="₹13.00 Lakh",
        gross_margin_pct=28.0,
        estimated_dscr=2.1,
        repayment_capacity_rating="HIGH",
        financial_health_score=80,
    )
    loan_in = LoanInputs(
        requested_amount_inr=1_500_000.0,
        purpose="Machinery Acquisition",
        preferred_loan_type="Machinery/Equipment Loan",
    )
    fin_in = FinancialInputs()

    req = advisor.identify_loan_requirement(loan_in, summary, fin_in)

    assert req.raw_amount_inr == 1_500_000.0
    assert req.purpose == "Machinery Acquisition"
    assert req.loan_type == "Machinery/Equipment Loan"
    assert req.urgency in ("HIGH", "MODERATE")


def test_evaluate_and_rank_loan_options():
    advisor = LoanAdvisor()
    summary = FinancialSummary(
        annual_revenue="₹50.00 Lakh",
        monthly_revenue="₹4.17 Lakh",
        monthly_expenses="₹3.00 Lakh",
        monthly_profit="₹1.17 Lakh",
        net_cash_flow="₹1.00 Lakh",
        existing_liabilities="₹5.00 Lakh",
        working_capital_requirement="₹6.00 Lakh",
        investment_requirement="₹10.00 Lakh",
        available_capital="₹3.00 Lakh",
        funding_requirement="₹13.00 Lakh",
        gross_margin_pct=28.0,
        estimated_dscr=2.1,
        repayment_capacity_rating="HIGH",
        financial_health_score=80,
    )
    loan_req = advisor.identify_loan_requirement(LoanInputs(), summary, FinancialInputs())
    profile = BusinessProfilePayload(name="Tech MSME", msme_classification="small")

    rag_schemes = [
        {
            "title": "CGTMSE Collateral Free Loan Guarantee",
            "knowledge_type": "LOAN",
            "text": "Collateral free credit guarantee scheme up to Rs 2 Crore.",
            "source_organization": "SIDBI & MSME",
            "official_url": "https://cgtmse.in",
        }
    ]
    module3_rankings = [{"scheme_name": "CGTMSE Collateral Free Loan Guarantee", "final_score": 0.92}]

    options = advisor.evaluate_and_rank_loan_options(
        rag_schemes=rag_schemes,
        module3_rankings=module3_rankings,
        financial_summary=summary,
        loan_requirement=loan_req,
        profile=profile,
    )

    assert len(options) > 0
    top = options[0]
    assert "CGTMSE" in top.name or "Credit" in top.name
    assert top.financial_suitability_score > 0.5
    assert len(top.documents) > 0
    assert top.official_url.startswith("http")
