#!/usr/bin/env python3
"""
Seed script: populates the default database (./data/gov_rag.db) and vector store
(./data/vector_store) with official government documents from fixtures.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings
from app.core.source_registry import DEFAULT_APPROVED_SOURCES
from app.db.repository import get_repository
from app.embeddings.embedding_service import EmbeddingService
from app.extractors.html_extractor import extract_html
from app.extractors.pdf_extractor import extract_pdf
from app.models.entities import ContentFormat, RawFetchResult, now_ts
from app.processors.cleaner import clean_pdf_pages, clean_text
from app.services.ingestion_service import IngestionService
from app.vectorstore.factory import build_vector_store

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "tests", "fixtures")
SOURCES_BY_ID = {s.source_id: s for s in DEFAULT_APPROVED_SOURCES}


def _raw(filename, url, fmt):
    with open(os.path.join(FIXTURE_DIR, filename), "rb") as f:
        raw_bytes = f.read()
    return RawFetchResult(url=url, final_url=url, status_code=200, content_format=fmt, raw_bytes=raw_bytes, fetched_at=now_ts())


def seed():
    os.makedirs(os.path.dirname(settings.sqlite_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(settings.vector_store_path) or ".", exist_ok=True)

    repository = get_repository()
    vector_store = build_vector_store()
    embedding_service = EmbeddingService()
    approved_sources = list(DEFAULT_APPROVED_SOURCES)

    for s in approved_sources:
        repository.upsert_source(s)

    ingestion_service = IngestionService(
        repository=repository,
        vector_store=vector_store,
        embedding_service=embedding_service,
        approved_sources=approved_sources,
    )

    batch = [
        ("scheme_page.html", "https://www.msme.gov.in/schemes/pmegp", ContentFormat.HTML, SOURCES_BY_ID["msme"]),
        ("loan_page.html", "https://www.sidbi.in/en/loans/wctl", ContentFormat.HTML, SOURCES_BY_ID["sidbi"]),
        ("notification.pdf", "https://etenders.gov.in/eprocure/app", ContentFormat.PDF, SOURCES_BY_ID["eprocure"]),
    ]

    corpus = []
    raws = []
    for filename, url, fmt, source in batch:
        raw = _raw(filename, url, fmt)
        raws.append((raw, source))
        if fmt == ContentFormat.HTML:
            corpus.append(clean_text(extract_html(raw.raw_bytes.decode(), url).text))
        else:
            corpus.append(clean_text("\n".join(clean_pdf_pages(extract_pdf(raw.raw_bytes).page_texts))))
    
    embedding_service.fit(corpus)

    for raw, source in raws:
        outcome = ingestion_service._ingest_one(raw, source)
        print(f"Seeded: {raw.url} -> {outcome}")

    vector_store.persist()
    print(f"Successfully seeded {len(repository.list_documents())} documents with {vector_store.count()} vectors.")


if __name__ == "__main__":
    seed()
