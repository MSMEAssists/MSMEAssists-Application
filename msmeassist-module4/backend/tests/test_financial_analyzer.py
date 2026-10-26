"""
Unit tests for FinancialAnalyzer service in Module 4.
Tests financial calculations, DSCR, margin, risk detection, and missing data detection.
"""
import pytest
from app.models.schemas import BusinessProfilePayload, FinancialInputs
from app.services.financial_analyzer import FinancialAnalyzer


def test_financial_analysis_with_complete_inputs():
    analyzer = FinancialAnalyzer()
    inputs = FinancialInputs(
        annual_turnover_inr=5_000_000.0,
        monthly_revenue_inr=416_666.0,
        monthly_expenses_inr=300_000.0,
        existing_liabilities_inr=500_000.0,
        existing_monthly_emi_inr=20_000.0,
        working_capital_requirement_inr=600_000.0,
        investment_requirement_inr=1_000_000.0,
        available_capital_inr=300_000.0,
    )
    profile = BusinessProfilePayload(
        name="Apex Precision Engineering",
        business_type="manufacturing",
        business_age_years=4.5,
    )

    res = analyzer.analyze(inputs, profile)

    assert res.financial_summary.gross_margin_pct > 0
    assert res.financial_summary.repayment_capacity_rating in ("HIGH", "MODERATE")
    assert res.financial_summary.estimated_dscr >= 1.0
    assert res.financial_summary.financial_health_score > 50
    assert isinstance(res.financial_risks, list)
    assert isinstance(res.missing_information, list)


def test_financial_analysis_missing_data_handling():
    analyzer = FinancialAnalyzer()
    inputs = FinancialInputs(
        annual_turnover_inr=2_400_000.0,
        # monthly_revenue, expenses, emi, capital intentionally omitted
    )
    profile = BusinessProfilePayload(name="Fresh Startup")

    res = analyzer.analyze(inputs, profile)

    # Missing information should be explicitly identified
    assert len(res.missing_information) > 0
    missing_str = " ".join(res.missing_information).lower()
    assert "monthly revenue" in missing_str or "monthly expenses" in missing_str
    # Financial values should not crash or produce invalid shapes
    assert res.financial_summary.annual_revenue == "₹24.00 Lakh"
    assert res.financial_summary.financial_health_score >= 0


def test_financial_analysis_risk_detection():
    analyzer = FinancialAnalyzer()
    # High debt burden and low margin
    inputs = FinancialInputs(
        annual_turnover_inr=1_000_000.0,
        monthly_revenue_inr=80_000.0,
        monthly_expenses_inr=85_000.0,  # Negative margin
        existing_liabilities_inr=600_000.0,  # 60% of annual turnover
        existing_monthly_emi_inr=30_000.0,
    )
    profile = BusinessProfilePayload(business_age_years=1.0)

    res = analyzer.analyze(inputs, profile)

    assert len(res.financial_risks) > 0
    assert res.financial_summary.repayment_capacity_rating in ("CONSTRAINED", "LOW")
