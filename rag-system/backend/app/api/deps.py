"""
Shared singletons / dependency-injection helpers for the FastAPI layer.
"""
from functools import lru_cache
from typing import List

from fastapi import Header, HTTPException
from app.core.config import settings
from app.core.source_registry import ApprovedSource, DEFAULT_APPROVED_SOURCES
from app.db.repository import SQLiteRepository, get_repository
from app.embeddings.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.query_service import QueryService
from app.vectorstore.base import VectorStore
from app.vectorstore.factory import build_vector_store


@lru_cache
def get_settings():
    return settings


def get_repo() -> SQLiteRepository:
    return get_repository()


@lru_cache
def _vector_store_singleton() -> VectorStore:
    return build_vector_store()


def get_vector_store_dep() -> VectorStore:
    return _vector_store_singleton()


@lru_cache
def _embedding_service_singleton() -> EmbeddingService:
    service = EmbeddingService()
    # If the provider is already fitted (e.g. loaded from tfidf_svd_model.pkl), avoid expensive DB read
    if getattr(service._provider, "_fitted", False):
        return service
    try:
        repo = get_repo()
        chunks = repo._list("chunks") if hasattr(repo, "_list") else []
        texts = [c["text"] for c in chunks if isinstance(c, dict) and "text" in c]
        if texts:
            service.fit(texts)
    except Exception:
        pass
    return service


def get_embedding_service_dep() -> EmbeddingService:
    return _embedding_service_singleton()


def get_approved_sources() -> List[ApprovedSource]:
    """Approved sources = registry defaults, overlaid with any admin
    enable/disable/add changes persisted to the repository."""
    repo = get_repo()
    stored = {s["source_id"]: s for s in repo.list_sources()}
    if not stored:
        for s in DEFAULT_APPROVED_SOURCES:
            repo.upsert_source(s)
        return list(DEFAULT_APPROVED_SOURCES)

    sources = []
    for default in DEFAULT_APPROVED_SOURCES:
        row = stored.get(default.source_id)
        if row:
            sources.append(ApprovedSource(**{**default.__dict__, **{k: v for k, v in row.items() if k in default.__dict__}}))
        else:
            sources.append(default)
    for source_id, row in stored.items():
        if source_id not in {d.source_id for d in DEFAULT_APPROVED_SOURCES}:
            sources.append(ApprovedSource(**row))
    return sources


def get_ingestion_service() -> IngestionService:
    return IngestionService(
        repository=get_repo(),
        vector_store=get_vector_store_dep(),
        embedding_service=get_embedding_service_dep(),
        approved_sources=get_approved_sources(),
    )


@lru_cache
def _query_service_singleton() -> QueryService:
    qs = QueryService(
        repository=get_repo(),
        vector_store=get_vector_store_dep(),
        embedding_service=get_embedding_service_dep(),
        llm_client=None,
    )
    try:
        qs.retriever._ensure_lexical_index()
    except Exception:
        pass
    return qs


def get_query_service() -> QueryService:
    return _query_service_singleton()


def require_admin_auth(x_admin_api_key: str = Header(default="")):
    if not settings.admin_auth_enabled:
        return
    if not settings.admin_api_key or x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")
