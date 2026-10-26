"""
Pydantic schemas for Module 5: Agent Orchestration & Decision Intelligence.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DecisionObjective(str, Enum):
    COMPREHENSIVE = "comprehensive"
    LOAN_FINANCE = "loan_finance"
    EXPORT_EXPANSION = "export_expansion"
    SCHEME_SUBSIDY = "scheme_subsidy"
    COMPLIANCE_AUDIT = "compliance_audit"


class DecisionRequest(BaseModel):
    objective: DecisionObjective = Field(
        default=DecisionObjective.COMPREHENSIVE,
        description="Core decision objective guiding the multi-agent orchestration pipeline.",
    )
    target_loan_amount_inr: Optional[float] = Field(
        default=None,
        description="Optional custom loan requirement amount in INR to evaluate against DSCR and schemes.",
    )
    target_loan_purpose: Optional[str] = Field(
        default=None,
        description="Optional loan purpose: working_capital, machinery_purchase, business_expansion, etc.",
    )
    target_state: Optional[str] = Field(
        default=None,
        description="Optional target state to narrow regional government scheme applicability.",
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Optional specific query or domain keywords for the RAG search layer.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Maximum number of top recommendations to return.",
    )


class AgentExecutionStatus(BaseModel):
    agent_name: str
    status: str = Field(description="'success' | 'partial' | 'failed' | 'skipped'")
    latency_ms: float
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class SchemeRecommendationItem(BaseModel):
    rank: int
    id: str
    title: str
    organization: str
    knowledge_type: str
    official_url: str
    eligibility_status: str
    btl_theta_score: float
    win_probability: float
    similarity_score: float
    key_benefits: List[str] = Field(default_factory=list)
    eligibility_criteria: List[str] = Field(default_factory=list)
    why_recommended: str
    driving_profile_factors: List[str] = Field(default_factory=list)
    provenance_citation: Optional[str] = None
    page_number: Optional[int] = None


class PairwiseExplainability(BaseModel):
    matrix: List[List[float]] = Field(default_factory=list)
    scheme_labels: List[str] = Field(default_factory=list)
    feature_importance: Dict[str, float] = Field(default_factory=dict)
    btl_iterations: int = 0
    btl_converged: bool = True
    traceable_path: List[str] = Field(default_factory=list)


class LoanAdvisorySummary(BaseModel):
    annual_revenue: str
    net_cash_flow: str
    estimated_dscr: float
    dscr_rating: str
    repayment_capacity: str
    funding_requirement: str
    loan_category: str
    recommended_options: List[Dict[str, Any]] = Field(default_factory=list)
    financial_risks: List[str] = Field(default_factory=list)
    improvement_areas: List[str] = Field(default_factory=list)


class ComplianceAdvisorySummary(BaseModel):
    compliance_score: int
    overall_risk: str
    rules_evaluated: int
    rules_met: int
    rules_needing_info: int
    rules_not_met: int
    key_action_items: List[str] = Field(default_factory=list)


class PermissionLicenseSummary(BaseModel):
    licenses_held: int
    licenses_required: int
    mandatory_licenses: List[Dict[str, Any]] = Field(default_factory=list)
    status_overview: str


class ExportAdvisorySummary(BaseModel):
    readiness_score: int
    export_status: str
    priority_schemes: List[Dict[str, Any]] = Field(default_factory=list)
    document_checklist: List[Dict[str, Any]] = Field(default_factory=list)


class ActionItem(BaseModel):
    priority: str = Field(description="'CRITICAL' | 'HIGH' | 'MEDIUM'")
    title: str
    description: str
    target_agency: str
    official_portal_url: Optional[str] = None
    deadline_days: int


class PrioritizedActionPlan(BaseModel):
    phase1_immediate: List[ActionItem] = Field(default_factory=list)
    phase2_application: List[ActionItem] = Field(default_factory=list)
    phase3_expansion: List[ActionItem] = Field(default_factory=list)


class RiskWarning(BaseModel):
    severity: str = Field(description="'HIGH' | 'MEDIUM' | 'LOW'")
    category: str
    headline: str
    details: str
    mitigation: str


class DecisionIntelligenceResponse(BaseModel):
    business_overview: Dict[str, Any]
    decision_summary: Dict[str, Any]
    orchestration_status: Dict[str, AgentExecutionStatus]
    top_scheme_recommendations: List[SchemeRecommendationItem]
    pairwise_explainability: PairwiseExplainability
    loan_advisory: LoanAdvisorySummary
    compliance_advisory: ComplianceAdvisorySummary
    permission_license_advisory: PermissionLicenseSummary
    export_advisory: ExportAdvisorySummary
    business_gaps: List[str] = Field(default_factory=list)
    risks_and_warnings: List[RiskWarning] = Field(default_factory=list)
    prioritized_action_plan: PrioritizedActionPlan
    orchestrated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
