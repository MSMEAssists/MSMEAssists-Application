"""
Schemas for Government Schemes Discovery and Grounded RAG Intelligence (Module 2).
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    CONDITIONALLY_ELIGIBLE = "conditionally_eligible"
    POTENTIALLY_ELIGIBLE = "potentially_eligible"
    NOT_ELIGIBLE = "not_eligible"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ProvenanceItem(BaseModel):
    statement: str
    chunk_id: Optional[str] = None
    page_number: Optional[int] = None
    source_url: str
    source_organization: Optional[str] = None


class SchemeCitationOut(BaseModel):
    title: Optional[str] = None
    organization: str
    official_url: str
    page_number: Optional[int] = None
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None


class DiscoveredSchemeOut(BaseModel):
    id: str
    title: str
    knowledge_type: str = "SCHEME"
    organization: str
    official_url: str
    official_application_url: Optional[str] = None
    page_number: Optional[int] = None
    description: Optional[str] = None
    snippet: Optional[str] = None
    similarity_score: float = 0.0
    aligned_attributes: List[str] = Field(default_factory=list)
    # Fix 1 — document pinning fields so compliance agent can restrict RAG search
    document_id: Optional[str] = None
    source_id:   Optional[str] = None

    # Module 2 Explainable Intelligence
    eligibility_status: EligibilityStatus = EligibilityStatus.POTENTIALLY_ELIGIBLE
    recommendation_score: float = 0.0
    retrieval_score: float = 0.0
    eligibility_evidence_score: float = 0.0
    profile_alignment_score: float = 0.0

    why_it_matches: List[str] = Field(default_factory=list)
    key_eligibility_criteria: List[ProvenanceItem] = Field(default_factory=list)
    benefits_available: List[ProvenanceItem] = Field(default_factory=list)
    required_documents: List[ProvenanceItem] = Field(default_factory=list)
    application_process: Optional[ProvenanceItem] = None
    unmet_or_conflicting_conditions: List[ProvenanceItem] = Field(default_factory=list)
    insufficient_evidence_notes: List[str] = Field(default_factory=list)


class SchemeDiscoveryResponse(BaseModel):
    business_name: str
    msme_classification: str
    attributes: List[str]
    total_discovered: int
    schemes: List[DiscoveredSchemeOut]


class SchemeQueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    knowledge_type: Optional[str] = None
    conversation_history: Optional[List[dict]] = None
    current_scheme_id: Optional[str] = None


class SchemeQueryResponse(BaseModel):
    query: str
    answer_text: str
    has_sufficient_context: bool
    citations: List[SchemeCitationOut]
    retrieved_result_count: int
    intent: Optional[str] = None
    recommended_schemes: Optional[List[dict]] = None
    eligibility_gaps: Optional[List[dict]] = None
    next_steps: Optional[List[str]] = None
    requires_clarification: Optional[bool] = False


class WorkflowDecisionRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    knowledge_type: Optional[str] = None


class WorkflowDecisionResponse(BaseModel):
    workflow: dict
    business_name: str
    profile_status: str
    eligibility: dict
    ranked_recommendations: List[DiscoveredSchemeOut]
    grounded_answer: SchemeQueryResponse

