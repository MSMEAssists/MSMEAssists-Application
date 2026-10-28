"""
Request/response schemas for the HTTP API. Requires pydantic (see
requirements.txt) -- not needed for the core pipeline logic itself, only
for the FastAPI layer in app/api.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class SourceOut(BaseModel):
    source_id: str
    name: str
    organization: str
    base_url: str
    allowed_domains: List[str]
    enabled: bool


class AddSourceIn(BaseModel):
    source_id: str
    name: str
    organization: str
    base_url: str
    allowed_domains: List[str]
    allowed_path_prefixes: List[str] = Field(default_factory=lambda: [""])


class DocumentOut(BaseModel):
    document_id: str
    source_id: str
    organization: str
    url: str
    content_format: str
    title: Optional[str]
    content_hash: str
    version: int
    retrieved_at: float
    publication_date: Optional[str]
    last_updated_date: Optional[str]
    knowledge_type: str


class KnowledgeItemOut(BaseModel):
    knowledge_id: str
    document_id: str
    source_id: str
    knowledge_type: str
    title: Optional[str]
    original_source_url: str
    source_organization: str
    official_application_url: Optional[str] = None
    application_portal_url: Optional[str] = None
    scheme_details_url: Optional[str] = None
    verification_status: Optional[str] = None
    publication_date: Optional[str] = None
    last_updated_date: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    eligibility: Optional[str] = None
    benefits: Optional[str] = None
    financial_assistance: Optional[str] = None
    subsidy_details: Optional[str] = None
    application_process: Optional[str] = None
    required_documents: Optional[str] = None
    implementing_organization: Optional[str] = None
    provider: Optional[str] = None
    purpose: Optional[str] = None
    eligible_applicants: Optional[str] = None
    loan_amount: Optional[str] = None
    interest_information: Optional[str] = None
    repayment_information: Optional[str] = None
    collateral_information: Optional[str] = None
    guarantee_information: Optional[str] = None


class IngestionRunIn(BaseModel):
    source_id: Optional[str] = None
    max_pages: Optional[int] = None


class IngestionLocalIn(BaseModel):
    documents_dir: Optional[str] = None
    source_id: Optional[str] = None


class ProcessingJobOut(BaseModel):
    job_id: str
    source_id: Optional[str]
    status: str
    started_at: float
    finished_at: Optional[float]
    documents_discovered: int
    documents_ingested: int
    documents_unchanged: int
    errors: List[str]


class RetrievalSearchIn(BaseModel):
    query: str
    top_k: Optional[int] = None
    similarity_threshold: Optional[float] = None
    knowledge_type: Optional[str] = None
    source_id: Optional[str] = None


class RetrievedResultOut(BaseModel):
    chunk_id: str
    document_id: str
    knowledge_id: Optional[str]
    text: str
    similarity_score: float
    title: Optional[str]
    knowledge_type: str
    source_organization: str
    official_url: str
    page_number: Optional[int]
    publication_date: Optional[str]
    last_updated_date: Optional[str]
    official_application_url: Optional[str] = None
    application_portal_url: Optional[str] = None
    scheme_details_url: Optional[str] = None
    verification_status: Optional[str] = None


class RagQueryIn(BaseModel):
    query: str
    top_k: Optional[int] = None
    similarity_threshold: Optional[float] = None
    knowledge_type: Optional[str] = None
    source_id: Optional[str] = None


class CitationOut(BaseModel):
    title: Optional[str]
    organization: str
    official_url: str
    page_number: Optional[int]
    document_id: str
    chunk_id: str
    official_application_url: Optional[str] = None
    application_portal_url: Optional[str] = None
    scheme_details_url: Optional[str] = None
    verification_status: Optional[str] = None


class RagAnswerOut(BaseModel):
    query: str
    answer_text: str
    has_sufficient_context: bool
    citations: List[CitationOut]
    retrieved_result_count: int


class ProvenanceOut(BaseModel):
    chunk_id: str
    document_id: str
    knowledge_id: Optional[str]
    source_id: str
    source_name: str
    organization: str
    official_url: str
    page_number: Optional[int]
    publication_date: Optional[str]
    last_updated_date: Optional[str]
    retrieval_timestamp: float


class HealthOut(BaseModel):
    status: str
    documents_indexed: int
    vectors_indexed: int
    approved_sources: int


class DiscoveryRunIn(BaseModel):
    seed_urls: Optional[List[str]] = None
    max_sources: int = 10
    max_urls_per_source: int = 50
    ingest_discovered: bool = True


class DiscoveryResultOut(BaseModel):
    status: str
    sources_registered_total: int
    new_sources_discovered: int = 0
    urls_discovered: int
    documents_ingested: int = 0
    documents_unchanged: int = 0
    errors: List[str] = Field(default_factory=list)


class SchedulerConfigIn(BaseModel):
    enabled: Optional[bool] = None
    interval_hours: Optional[int] = None
    run_on_startup: Optional[bool] = None


class SchedulerStatusOut(BaseModel):
    enabled: bool
    interval_hours: int
    run_on_startup: bool
    is_active: bool
    is_currently_running_job: bool
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_job_id: Optional[str] = None
    last_job_summary: Optional[dict] = None


