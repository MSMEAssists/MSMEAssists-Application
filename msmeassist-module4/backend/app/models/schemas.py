"""
Pydantic Request and Response Schemas for Module 4: Finance & Loan Agent.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =====================================================================
# Financial Analysis Input & Output Schemas
# =====================================================================

class FinancialInputs(BaseModel):
    annual_turnover_inr: Optional[float] = Field(default=None, description="Annual revenue / turnover in INR", ge=0)
    monthly_revenue_inr: Optional[float] = Field(default=None, description="Monthly revenue in INR", ge=0)
    monthly_expenses_inr: Optional[float] = Field(default=None, description="Monthly operational expenses in INR", ge=0)
    existing_liabilities_inr: Optional[float] = Field(default=None, description="Total outstanding loans/liabilities in INR", ge=0)
    existing_monthly_emi_inr: Optional[float] = Field(default=None, description="Current monthly loan EMI payments in INR", ge=0)
    working_capital_requirement_inr: Optional[float] = Field(default=None, description="Working capital needed in INR", ge=0)
    investment_requirement_inr: Optional[float] = Field(default=None, description="Machinery / capital expansion needed in INR", ge=0)
    available_capital_inr: Optional[float] = Field(default=None, description="Current liquid savings / capital available in INR", ge=0)
    credit_score: Optional[int] = Field(default=None, description="Credit score if available", ge=300, le=900)
    has_existing_loan: Optional[bool] = Field(default=None, description="Whether business has existing loan")
    has_bank_finance: Optional[bool] = Field(default=None, description="Whether business has existing bank banking relationship")
    profitability_status: Optional[str] = Field(default=None, description="profitable, break_even, loss")


class LoanInputs(BaseModel):
    requested_amount_inr: Optional[float] = Field(default=None, description="Desired loan amount in INR", ge=0)
    purpose: Optional[str] = Field(default=None, description="Purpose: Working Capital, Machinery, Expansion, etc.")
    preferred_loan_type: Optional[str] = Field(default=None, description="Preferred category")
    max_acceptable_interest_rate: Optional[float] = Field(default=None, description="Max acceptable interest rate %")
    preferred_tenure_months: Optional[int] = Field(default=None, description="Preferred tenure in months")


class BusinessProfilePayload(BaseModel):
    name: Optional[str] = "MSME Enterprise"
    business_type: Optional[str] = "manufacturing"
    industry: Optional[str] = "General Industry"
    sub_sector: Optional[str] = None
    business_age_years: Optional[float] = 3.0
    msme_classification: Optional[str] = "micro"
    state: Optional[str] = "India"
    district: Optional[str] = None
    is_women_owned: Optional[bool] = False
    social_category: Optional[str] = "general"
    is_rural_enterprise: Optional[bool] = False
    is_startup_recognized: Optional[bool] = False


class FinancialAnalysisRequest(BaseModel):
    financial_inputs: Optional[FinancialInputs] = Field(default_factory=FinancialInputs)
    business_profile: Optional[BusinessProfilePayload] = Field(default_factory=BusinessProfilePayload)


class FinancialSummary(BaseModel):
    annual_revenue: str
    monthly_revenue: str
    monthly_expenses: str
    monthly_profit: str
    net_cash_flow: str
    existing_liabilities: str
    working_capital_requirement: str
    investment_requirement: str
    available_capital: str
    funding_requirement: str
    gross_margin_pct: float
    estimated_dscr: float
    repayment_capacity_rating: str  # HIGH, MODERATE, CONSTRAINED, LOW
    financial_health_score: int  # 0 to 100


class FinancialAnalysisResponse(BaseModel):
    financial_summary: FinancialSummary
    financial_risks: List[str]
    missing_information: List[str]
    improvement_areas: List[str]
    analysis_explanation: str


# =====================================================================
# Loan Advisory & Recommendation Schemas
# =====================================================================

class LoanRequirement(BaseModel):
    required_amount: str
    raw_amount_inr: float
    purpose: str
    loan_type: str
    urgency: str


class RecommendedLoanOption(BaseModel):
    id: str
    name: str
    type: str  # e.g., MSME Government-Supported Loan, Working Capital Loan, Term Loan
    category: str  # e.g., Credit Guarantee-linked financing, Machinery/Equipment Loan
    reason: str
    eligibility: str
    amount: str
    interest_rate: str
    tenure: str
    documents: List[str]
    financial_suitability_score: float
    btl_rank: Optional[int] = None
    source_organization: Optional[str] = None
    official_url: Optional[str] = None


class LoanRecommendationRequest(BaseModel):
    financial_inputs: Optional[FinancialInputs] = Field(default_factory=FinancialInputs)
    loan_inputs: Optional[LoanInputs] = Field(default_factory=LoanInputs)
    business_profile: Optional[BusinessProfilePayload] = Field(default_factory=BusinessProfilePayload)
    use_module3_rankings: bool = True
    top_k: int = 5


class LoanAdvisoryResponse(BaseModel):
    business_name: str
    msme_classification: str
    financial_summary: FinancialSummary
    loan_requirement: LoanRequirement
    recommended_options: List[RecommendedLoanOption]
    financial_risks: List[str]
    missing_information: List[str]
    improvement_areas: List[str]
    explanation: str
    disclaimer: str = Field(
        default="Final loan approval, interest rate, sanctioned amount, and eligibility are determined solely by the respective bank, financial institution, or government authority."
    )


class FinancingCategoriesResponse(BaseModel):
    categories: List[Dict[str, Any]]
