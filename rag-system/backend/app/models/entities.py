"""
Core domain entities. Plain dataclasses (no pydantic dependency required
at the domain layer) so the pipeline logic is testable without the web
framework installed. The API layer (app/schemas) maps these to
request/response schemas.
"""
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def now_ts() -> float:
    return time.time()


class KnowledgeType(str, Enum):
    SCHEME = "SCHEME"
    LOAN = "LOAN"
    SUBSIDY = "SUBSIDY"
    GRANT = "GRANT"
    POLICY = "POLICY"
    NOTIFICATION = "NOTIFICATION"
    GUIDELINE = "GUIDELINE"
    COMPLIANCE = "COMPLIANCE"
    EXPORT = "EXPORT"
    PERMISSION = "PERMISSION"
    PROCUREMENT = "PROCUREMENT"
    OTHER = "OTHER"


class ContentFormat(str, Enum):
    HTML = "HTML"
    PDF = "PDF"


UNAVAILABLE = None  # explicit marker: field not present in official source


@dataclass
class RawFetchResult:
    url: str
    final_url: str
    status_code: int
    content_format: ContentFormat
    raw_bytes: bytes
    fetched_at: float = field(default_factory=now_ts)
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExtractedContent:
    title: Optional[str]
    text: str
    headings: List[str] = field(default_factory=list)
    lists: List[List[str]] = field(default_factory=list)
    tables: List[List[List[str]]] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    page_texts: Optional[List[str]] = None  # PDF only: text per page (1-indexed via list order)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Document:
    document_id: str
    source_id: str
    organization: str
    url: str
    content_format: ContentFormat
    title: Optional[str]
    content_hash: str
    version: int
    retrieved_at: float
    publication_date: Optional[str] = None
    last_updated_date: Optional[str] = None
    knowledge_type: KnowledgeType = KnowledgeType.OTHER


@dataclass
class DocumentVersion:
    document_id: str
    version: int
    content_hash: str
    retrieved_date: float
    publication_date: Optional[str]
    last_updated_date: Optional[str]


@dataclass
class KnowledgeItem:
    """A structured knowledge record extracted from a Document.

    Fields intentionally use `None` (never a fabricated default) when the
    official source does not provide that information -- see
    docs/ingestion.md "no invented fields" rule.
    """
    knowledge_id: str
    document_id: str
    source_id: str
    knowledge_type: KnowledgeType
    title: Optional[str]
    original_source_url: str
    source_organization: str
    official_application_url: Optional[str] = None
    publication_date: Optional[str] = None
    last_updated_date: Optional[str] = None

    # SCHEME fields
    description: Optional[str] = None
    objective: Optional[str] = None
    eligibility: Optional[str] = None
    benefits: Optional[str] = None
    financial_assistance: Optional[str] = None
    subsidy_details: Optional[str] = None
    application_process: Optional[str] = None
    required_documents: Optional[str] = None
    implementing_organization: Optional[str] = None

    # LOAN fields
    provider: Optional[str] = None
    purpose: Optional[str] = None
    eligible_applicants: Optional[str] = None
    loan_amount: Optional[str] = None
    interest_information: Optional[str] = None
    repayment_information: Optional[str] = None
    collateral_information: Optional[str] = None
    guarantee_information: Optional[str] = None


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    source_id: str
    knowledge_id: Optional[str]
    knowledge_type: KnowledgeType
    title: Optional[str]
    section: Optional[str]
    page_number: Optional[int]
    chunk_index: int
    text: str


@dataclass
class EmbeddingRecord:
    chunk_id: str
    vector: List[float]
    embedding_model: str
    embedding_version: str
    dimensions: int
    generated_at: float = field(default_factory=now_ts)


@dataclass
class ProvenanceRecord:
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
    retrieval_timestamp: float = field(default_factory=now_ts)


@dataclass
class ProcessingJob:
    job_id: str
    source_id: Optional[str]
    status: str  # "pending" | "running" | "completed" | "failed"
    started_at: float
    finished_at: Optional[float] = None
    documents_discovered: int = 0
    documents_ingested: int = 0
    documents_unchanged: int = 0
    errors: List[str] = field(default_factory=list)


def content_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
