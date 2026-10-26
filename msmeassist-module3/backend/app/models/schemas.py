"""
Data models and Pydantic schemas for Module 3 Explainable AI Recommendation Engine.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CandidateScheme(BaseModel):
    id: str
    title: str
    organization: str = "Government of India"
    official_url: str = ""
    official_application_url: Optional[str] = None
    knowledge_type: str = "SCHEME"
    snippet: str = ""
    benefits: List[str] = Field(default_factory=list)
    eligibility_criteria: List[str] = Field(default_factory=list)
    page_number: Optional[int] = None
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    retrieval_score: float = 0.0
    scheme_scope: str = "CENTRAL"
    state_jurisdiction: str = "All India"


class PairwiseComparison(BaseModel):
    scheme_a_id: str
    scheme_a_title: str
    scheme_b_id: str
    scheme_b_title: str
    winner_id: Optional[str] = None
    preference_probability: float = Field(
        ...,
        description="Probability that Scheme A is preferred over Scheme B (0.0 to 1.0; 0.5 = tie)",
    )
    comparative_rationale: str
    driving_attributes: List[str] = Field(default_factory=list)
    benefit_differential: str = ""


class BtlRankingItem(BaseModel):
    rank: int
    scheme_id: str
    title: str
    organization: str
    official_url: str
    official_application_url: Optional[str] = None
    knowledge_type: str
    theta_score: float = Field(..., description="Latent utility parameter θ_i estimated via MLE")
    win_probability: float = Field(..., description="Normalized BTL probability π_i = exp(θ_i) / Σ exp(θ_k)")
    wins: float = 0.0
    losses: float = 0.0
    head_to_head_win_rate: float = 0.0
    key_comparative_advantage: str
    feature_attributions: Dict[str, float] = Field(
        default_factory=dict,
        description="Percentage contribution of profile attributes (e.g. women_owned, micro, mfg)",
    )
    snippet: str = ""
    page_number: Optional[int] = None
    official_citations: List[Dict[str, Any]] = Field(default_factory=list)
    scheme_scope: str = Field(default="CENTRAL", description="Scope of the scheme: 'STATE' or 'CENTRAL'")
    state_jurisdiction: str = Field(default="All India", description="State jurisdiction (e.g. 'Telangana' or 'All India')")


class RecommendationRequest(BaseModel):
    profile: Optional[Dict[str, Any]] = None
    top_k: Optional[int] = 5
    custom_query: Optional[str] = None
    state: Optional[str] = Field(default=None, description="Strict location filter by State (e.g. 'Telangana', 'Karnataka')")
    scope: Optional[str] = Field(default="all", description="Scope filter: 'all', 'state', or 'central'")


class RecommendationResponse(BaseModel):
    business_name: str
    msme_classification: str
    detected_location: str
    filter_applied: Dict[str, Any] = Field(default_factory=dict)
    total_candidates: int
    disqualified_other_states_count: int = 0
    pairwise_comparisons_count: int
    btl_iterations: int
    btl_log_likelihood: float
    rankings: List[BtlRankingItem]
    state_schemes: List[BtlRankingItem] = Field(default_factory=list, description="Strictly filtered State-specific schemes")
    central_schemes: List[BtlRankingItem] = Field(default_factory=list, description="Central Government / All-India schemes")
    pairwise_matrix: List[List[float]]
    scheme_ids_order: List[str]
    pairwise_details: List[PairwiseComparison]
    feature_importance_summary: Dict[str, float]
    generated_at: str


class BtlSolveRequest(BaseModel):
    items: List[str]
    win_matrix: List[List[float]]  # W[i][j] = wins of i over j
    max_iterations: Optional[int] = 100
    tolerance: Optional[float] = 1e-6


class BtlSolveResponse(BaseModel):
    items: List[str]
    thetas: Dict[str, float]
    probabilities: Dict[str, float]
    ranks: List[str]
    iterations: int
    converged: bool
    log_likelihood: float
