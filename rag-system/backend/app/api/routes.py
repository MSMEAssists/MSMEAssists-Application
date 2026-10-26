from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    get_approved_sources, get_ingestion_service, get_query_service,
    get_repo, get_vector_store_dep, require_admin_auth,
)
from app.core.source_registry import ApprovedSource
from app.core.url_validator import validate_url
from app.db.repository import SQLiteRepository
from app.models.entities import new_id
from app.retrieval.retriever import Retriever
from app.schemas.api_schemas import (
    AddSourceIn, DiscoveryResultOut, DiscoveryRunIn, DocumentOut, HealthOut,
    IngestionLocalIn, IngestionRunIn, KnowledgeItemOut, ProcessingJobOut,
    ProvenanceOut, RagAnswerOut, RagQueryIn, RetrievalSearchIn,
    RetrievedResultOut, SchedulerConfigIn, SchedulerStatusOut, SourceOut,
)
from app.services.ingestion_service import IngestionService
from app.services.query_service import QueryService
from app.vectorstore.base import VectorStore

router = APIRouter()


# --- Sources ---------------------------------------------------------------

@router.get("/api/sources", response_model=list[SourceOut])
def list_sources(sources: list[ApprovedSource] = Depends(get_approved_sources)):
    return [
        SourceOut(
            source_id=s.source_id, name=s.name, organization=s.organization,
            base_url=s.base_url, allowed_domains=s.allowed_domains, enabled=s.enabled,
        )
        for s in sources
    ]


@router.post("/api/sources", response_model=SourceOut, dependencies=[Depends(require_admin_auth)])
def add_source(payload: AddSourceIn, repo: SQLiteRepository = Depends(get_repo)):
    """Add a new approved source. The URL/domain still has to pass
    app.core.url_validator at ingestion time -- adding it here only makes it
    eligible, it doesn't bypass validation."""
    source = ApprovedSource(
        source_id=payload.source_id, name=payload.name, organization=payload.organization,
        base_url=payload.base_url, allowed_domains=payload.allowed_domains,
        allowed_path_prefixes=payload.allowed_path_prefixes, enabled=True,
    )
    validation = validate_url(source.base_url, [source], resolve_dns=False)
    if not validation.is_valid:
        raise HTTPException(400, f"base_url failed validation: {validation.reason}")
    repo.upsert_source(source)
    return SourceOut(
        source_id=source.source_id, name=source.name, organization=source.organization,
        base_url=source.base_url, allowed_domains=source.allowed_domains, enabled=source.enabled,
    )


@router.post("/api/sources/{source_id}/enable", dependencies=[Depends(require_admin_auth)])
def enable_source(
    source_id: str,
    enabled: bool = True,
    repo: SQLiteRepository = Depends(get_repo),
    sources_list: list[ApprovedSource] = Depends(get_approved_sources),
):
    sources = {s.source_id: s for s in sources_list}
    if source_id not in sources:
        raise HTTPException(404, "Unknown source_id")
    source = sources[source_id]
    source.enabled = enabled
    repo.upsert_source(source)
    return {"source_id": source_id, "enabled": enabled}


# --- Documents ---------------------------------------------------------------

@router.get("/api/documents", response_model=list[DocumentOut])
def list_documents(source_id: Optional[str] = None, repo: SQLiteRepository = Depends(get_repo)):
    docs = repo.list_documents(source_id=source_id)
    return docs


@router.get("/api/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, repo: SQLiteRepository = Depends(get_repo)):
    doc = repo.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.delete("/api/documents/{document_id}")
def delete_document(
    document_id: str,
    repo: SQLiteRepository = Depends(get_repo),
    vs: VectorStore = Depends(get_vector_store_dep),
):
    doc = repo.get_document(document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    
    # 1. Delete associated chunks from vector store
    chunks = repo.list_chunks_for_document(document_id)
    chunk_ids = [c["chunk_id"] for c in chunks if isinstance(c, dict) and "chunk_id" in c]
    if chunk_ids:
        try:
            vs.delete(chunk_ids)
            vs.persist()
        except Exception:
            pass

    # 2. Delete from database
    repo.delete_document(document_id)
    return {"status": "deleted", "document_id": document_id, "chunks_removed": len(chunk_ids)}


# --- Knowledge ---------------------------------------------------------------

@router.get("/api/knowledge", response_model=list[KnowledgeItemOut])
def list_knowledge(knowledge_type: Optional[str] = None, repo: SQLiteRepository = Depends(get_repo)):
    return repo.list_knowledge_items(knowledge_type=knowledge_type)


@router.get("/api/knowledge/{knowledge_id}", response_model=KnowledgeItemOut)
def get_knowledge(knowledge_id: str, repo: SQLiteRepository = Depends(get_repo)):
    item = repo.get_knowledge_item(knowledge_id)
    if not item:
        raise HTTPException(404, "Knowledge item not found")
    return item


# --- Ingestion ---------------------------------------------------------------

@router.post("/api/ingestion/run", response_model=ProcessingJobOut, dependencies=[Depends(require_admin_auth)])
def run_ingestion(
    payload: IngestionRunIn,
    service: IngestionService = Depends(get_ingestion_service),
):
    from app.services.ingestion_service import is_ingestion_running
    from app.services.scheduler import scheduler
    if scheduler.is_running or is_ingestion_running():
        raise HTTPException(status_code=409, detail="An ingestion job is already running.")
    job = service.run_ingestion(source_id=payload.source_id, max_pages=payload.max_pages)
    return job


@router.post("/api/ingestion/local", response_model=ProcessingJobOut, dependencies=[Depends(require_admin_auth)])
def run_local_ingestion(
    payload: IngestionLocalIn = IngestionLocalIn(),
    service: IngestionService = Depends(get_ingestion_service),
):
    from app.services.ingestion_service import is_ingestion_running
    from app.services.scheduler import scheduler
    if scheduler.is_running or is_ingestion_running():
        raise HTTPException(status_code=409, detail="An ingestion job is already running.")
    job = service.ingest_local_documents(documents_dir=payload.documents_dir, source_id=payload.source_id)
    return job


@router.get("/api/ingestion/jobs", response_model=list[ProcessingJobOut])
def list_ingestion_jobs(repo: SQLiteRepository = Depends(get_repo)):
    return repo.list_jobs()


# --- Discovery ----------------------------------------------------------------

@router.post("/api/discovery/run", response_model=DiscoveryResultOut, dependencies=[Depends(require_admin_auth)])
def run_discovery(
    payload: DiscoveryRunIn = DiscoveryRunIn(),
    service: IngestionService = Depends(get_ingestion_service),
):
    from app.services.ingestion_service import is_ingestion_running
    from app.services.scheduler import scheduler
    if payload.ingest_discovered and (scheduler.is_running or is_ingestion_running()):
        raise HTTPException(status_code=409, detail="An ingestion job is already running.")
    return service.discover_sources(
        seed_urls=payload.seed_urls,
        max_sources=payload.max_sources,
        max_urls_per_source=payload.max_urls_per_source,
        ingest_discovered=payload.ingest_discovered,
    )


# --- Retrieval / RAG ---------------------------------------------------------------

@router.post("/api/retrieval/search", response_model=list[RetrievedResultOut])
def retrieval_search(
    payload: RetrievalSearchIn,
    service: QueryService = Depends(get_query_service),
):
    results = service.retriever.search(
        payload.query, top_k=payload.top_k, similarity_threshold=payload.similarity_threshold,
        knowledge_type=payload.knowledge_type, source_id=payload.source_id,
    )
    return [r.__dict__ for r in results]


@router.post("/api/rag/query", response_model=RagAnswerOut)
def rag_query(
    payload: RagQueryIn,
    service: QueryService = Depends(get_query_service),
):
    answer = service.rag_query(
        payload.query, top_k=payload.top_k, similarity_threshold=payload.similarity_threshold,
        knowledge_type=payload.knowledge_type, source_id=payload.source_id,
    )
    return {
        "query": answer.query,
        "answer_text": answer.answer_text,
        "has_sufficient_context": answer.has_sufficient_context,
        "citations": [c.__dict__ for c in answer.citations],
        "retrieved_result_count": answer.retrieved_result_count,
    }


# --- Provenance ---------------------------------------------------------------

@router.get("/api/provenance/{document_id}", response_model=list[ProvenanceOut])
def get_provenance(document_id: str, repo: SQLiteRepository = Depends(get_repo)):
    records = repo.list_provenance_for_document(document_id)
    if not records:
        raise HTTPException(404, "No provenance records found for this document")
    return records


# --- Health ---------------------------------------------------------------

@router.get("/api/health", response_model=HealthOut)
def health(
    repo: SQLiteRepository = Depends(get_repo),
    vector_store: VectorStore = Depends(get_vector_store_dep),
    sources: list[ApprovedSource] = Depends(get_approved_sources),
):
    return HealthOut(
        status="ok",
        documents_indexed=len(repo.list_documents()),
        vectors_indexed=vector_store.count(),
        approved_sources=len(sources),
    )


# --- Scheduler -------------------------------------------------------------

@router.get("/api/scheduler/status", response_model=SchedulerStatusOut)
def get_scheduler_status():
    from app.services.scheduler import scheduler
    return scheduler.get_status()


@router.post("/api/scheduler/trigger", dependencies=[Depends(require_admin_auth)])
async def trigger_scheduler_run():
    from app.services.scheduler import scheduler
    return await scheduler.run_now()


@router.post("/api/scheduler/configure", response_model=SchedulerStatusOut, dependencies=[Depends(require_admin_auth)])
def configure_scheduler(payload: SchedulerConfigIn = SchedulerConfigIn()):
    from app.services.scheduler import scheduler
    return scheduler.configure(
        enabled=payload.enabled,
        interval_hours=payload.interval_hours,
        run_on_startup=payload.run_on_startup,
    )
