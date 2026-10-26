"""
Financial Analyzer Service for Module 4.

Performs robust financial analysis, cash flow estimation, DSCR calculations,
funding gap analysis, risk detection, missing data detection, and health scoring.
"""
from typing import Dict, List, Tuple
from app.core.config import get_finance_settings
from app.models.schemas import (
    BusinessProfilePayload,
    FinancialAnalysisResponse,
    FinancialInputs,
    FinancialSummary,
)


def format_inr(amount: float) -> str:
    """Format currency values cleanly in INR format (Lakhs / Crores or standard thousands)."""
    if amount is None or amount < 0:
        return "N/A"
    if amount >= 10_000_000:
        return f"₹{amount / 10_000_000:.2f} Cr"
    elif amount >= 100_000:
        return f"₹{amount / 100_000:.2f} Lakh"
    else:
        return f"₹{amount:,.0f}"


class FinancialAnalyzer:
    def __init__(self):
        self.settings = get_finance_settings()

    def analyze(
        self,
        inputs: FinancialInputs,
        profile: BusinessProfilePayload,
    ) -> FinancialAnalysisResponse:
        missing_info: List[str] = []
        risks: List[str] = []
        improvement_areas: List[str] = []

        # 1. Annual Turnover & Monthly Revenue
        annual_turnover = inputs.annual_turnover_inr
        if annual_turnover is None or annual_turnover <= 0:
            annual_turnover = 1_200_000.0  # Conservative base threshold for calculation
            missing_info.append("Annual turnover was not provided; assumed baseline value of ₹12.00 Lakh for analysis.")

        monthly_revenue = inputs.monthly_revenue_inr
        if monthly_revenue is None or monthly_revenue <= 0:
            monthly_revenue = annual_turnover / 12.0
            missing_info.append(f"Monthly revenue not explicitly specified; derived from annual turnover ({format_inr(monthly_revenue)}/mo).")

        # 2. Monthly Expenses
        monthly_expenses = inputs.monthly_expenses_inr
        if monthly_expenses is None or monthly_expenses <= 0:
            expense_ratio = self.settings.default_monthly_expense_ratio
            monthly_expenses = monthly_revenue * expense_ratio
            missing_info.append(
                f"Monthly expenses not explicitly provided; estimated at {int(expense_ratio*100)}% of revenue ({format_inr(monthly_expenses)}/mo)."
            )

        # 3. Profit & Margin
        monthly_profit = monthly_revenue - monthly_expenses
        gross_margin_pct = (monthly_profit / monthly_revenue * 100) if monthly_revenue > 0 else 0.0

        if monthly_profit <= 0:
            risks.append("Operating margin is zero or negative; business is operating near break-even or loss.")
            improvement_areas.append("Review operating overheads and raw material sourcing to improve net margins above 15%.")

        # 4. Existing Debt & EMI
        existing_liabilities = inputs.existing_liabilities_inr or 0.0
        if inputs.existing_liabilities_inr is None and inputs.has_existing_loan:
            existing_liabilities = annual_turnover * 0.20
            missing_info.append("Existing loan balance was not specified; estimated at 20% of annual turnover.")

        monthly_emi = inputs.existing_monthly_emi_inr
        if monthly_emi is None:
            if existing_liabilities > 0:
                # Estimate 36-month EMI at 11% interest
                monthly_emi = (existing_liabilities * 0.032)
                missing_info.append(f"Monthly loan EMI not specified; estimated at {format_inr(monthly_emi)}/mo.")
            else:
                monthly_emi = 0.0

        # Debt to Turnover ratio
        debt_ratio = (existing_liabilities / annual_turnover) if annual_turnover > 0 else 0.0
        if debt_ratio > 0.40:
            risks.append(f"High debt-to-turnover ratio ({debt_ratio*100:.1f}%); existing liabilities represent a large portion of turnover.")
            improvement_areas.append("Prioritize debt consolidation or high-interest liability repayment before taking on major new debt.")

        # 5. Debt Service Coverage Ratio (DSCR)
        net_operating_income = max(monthly_profit, 0.0)
        if monthly_emi > 0:
            dscr = net_operating_income / monthly_emi
        else:
            dscr = 3.0  # High DSCR when no existing debt service

        dscr = round(min(dscr, 5.0), 2)

        if dscr < self.settings.min_dscr_acceptable and monthly_emi > 0:
            risks.append(f"Low Debt Service Coverage Ratio (DSCR: {dscr}); monthly cash flows may be strained by debt obligations.")

        # 6. Repayment Capacity Rating
        if dscr >= 2.0 and debt_ratio < 0.30 and monthly_profit > 0:
            repayment_rating = "HIGH"
        elif dscr >= 1.25 and monthly_profit > 0:
            repayment_rating = "MODERATE"
        elif dscr >= 1.0:
            repayment_rating = "CONSTRAINED"
        else:
            repayment_rating = "LOW"

        # 7. Funding Requirements
        wc_req = inputs.working_capital_requirement_inr
        if wc_req is None:
            wc_req = monthly_expenses * 2.0  # 2 months operating expenses as default working capital gap
            missing_info.append(f"Working capital requirement not specified; calculated at 2 months of operating expenses ({format_inr(wc_req)}).")

        inv_req = inputs.investment_requirement_inr or 0.0
        available_cap = inputs.available_capital_inr or 0.0
        if inputs.available_capital_inr is None:
            missing_info.append("Available liquid capital was not specified; assumed ₹0 available liquid reserve.")

        total_needed = wc_req + inv_req
        funding_gap = max(total_needed - available_cap, 0.0)

        # 8. Net Cash Flow
        net_cash_flow = monthly_profit - monthly_emi

        if net_cash_flow < 0:
            risks.append("Net monthly cash flow after debt servicing is negative.")

        # 9. Business Age Risk
        biz_age = profile.business_age_years or 3.0
        if biz_age < 2.0:
            risks.append("Business operating history is under 2 years; traditional commercial banks may require extra collateral or government guarantee cover.")
            improvement_areas.append("Apply for government-backed schemes like PMEGP or MUDRA designed for early-stage enterprises.")

        # 10. Financial Health Score (0-100)
        score = 50
        if monthly_profit > 0:
            score += 15
        if dscr >= 1.5:
            score += 15
        if debt_ratio < 0.25:
            score += 10
        if biz_age >= 3.0:
            score += 10
        if available_cap >= monthly_expenses:
            score += 10
        if len(risks) >= 3:
            score -= 15
        health_score = max(min(score, 100), 20)

        # General Improvement Areas
        if available_cap < (monthly_expenses * 2.0):
            improvement_areas.append("Build a liquid operating cash reserve equivalent to 2-3 months of operating expenses.")

        improvement_areas.append("Maintain clear Udyam and GST filing records to qualify for interest subvention and CGTMSE collateral-free guarantee cover.")

        # Summary Object
        summary = FinancialSummary(
            annual_revenue=format_inr(annual_turnover),
            monthly_revenue=format_inr(monthly_revenue),
            monthly_expenses=format_inr(monthly_expenses),
            monthly_profit=format_inr(monthly_profit),
            net_cash_flow=format_inr(net_cash_flow),
            existing_liabilities=format_inr(existing_liabilities),
            working_capital_requirement=format_inr(wc_req),
            investment_requirement=format_inr(inv_req),
            available_capital=format_inr(available_cap),
            funding_requirement=format_inr(funding_gap),
            gross_margin_pct=round(gross_margin_pct, 1),
            estimated_dscr=dscr,
            repayment_capacity_rating=repayment_rating,
            financial_health_score=health_score,
        )

        # Explanation Text
        explanation = (
            f"The business generates an estimated annual turnover of {format_inr(annual_turnover)} "
            f"with monthly revenue of {format_inr(monthly_revenue)} and operating expenses of {format_inr(monthly_expenses)}. "
            f"The estimated monthly net profit margin is {gross_margin_pct:.1f}% ({format_inr(monthly_profit)}/mo). "
            f"Debt Service Coverage Ratio (DSCR) is {dscr:.2f}, indicating a '{repayment_rating}' repayment capacity rating. "
            f"Total funding requirement is calculated at {format_inr(funding_gap)} "
            f"(Working Capital: {format_inr(wc_req)}, Capital Investment: {format_inr(inv_req)}). "
            f"Overall Financial Health Score is {health_score}/100."
        )

        return FinancialAnalysisResponse(
            financial_summary=summary,
            financial_risks=risks,
            missing_information=missing_info,
            improvement_areas=improvement_areas,
            analysis_explanation=explanation,
        )
