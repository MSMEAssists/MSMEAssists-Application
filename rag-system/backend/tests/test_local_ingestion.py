import os
import tempfile
import pytest

from app.core.local_documents import LOCAL_PDF_REGISTRY, get_local_document_metadata
from app.core.source_registry import DEFAULT_APPROVED_SOURCES
from app.core.url_validator import validate_url
from app.db.repository import SQLiteRepository
from app.embeddings.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.vectorstore.numpy_store import NumpyVectorStore


def test_local_pdf_registry_validity():
    assert len(LOCAL_PDF_REGISTRY) >= 12
    for fname, meta in LOCAL_PDF_REGISTRY.items():
        assert meta.filename == fname
        assert meta.official_url.startswith("https://")
        assert meta.source_id in [s.source_id for s in DEFAULT_APPROVED_SOURCES]
        
        # Verify every registered URL passes strict domain validation
        val = validate_url(meta.official_url, list(DEFAULT_APPROVED_SOURCES), resolve_dns=False)
        assert val.is_valid is True, f"Failed URL validation for {fname}: {val.reason}"


def test_get_local_document_metadata():
    meta = get_local_document_metadata("Consortia & Tender Marketing Scheme.pdf")
    assert meta is not None
    assert meta.source_id == "msme"

    # Case insensitive
    meta_lower = get_local_document_metadata("consortia & tender marketing scheme.pdf")
    assert meta_lower is not None
    assert meta_lower.filename == "Consortia & Tender Marketing Scheme.pdf"

    # Unknown
    assert get_local_document_metadata("non_existent_file.pdf") is None


def test_ingest_local_documents_mock():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    vec_path = os.path.join(tmpdir, "test_vec")
    docs_dir = os.path.join(tmpdir, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    # Copy fixture PDF to docs directory under a registered name
    fixture_pdf = os.path.join(os.path.dirname(__file__), "fixtures", "notification.pdf")
    test_pdf_name = "mse_cdp_faq.pdf"
    with open(fixture_pdf, "rb") as f_in, open(os.path.join(docs_dir, test_pdf_name), "wb") as f_out:
        f_out.write(f_in.read())

    repo = SQLiteRepository(path=db_path)
    for s in DEFAULT_APPROVED_SOURCES:
        repo.upsert_source(s)

    vec_store = NumpyVectorStore(path=vec_path)
    embed_svc = EmbeddingService(provider_name="tfidf_svd", dimensions=32)

    service = IngestionService(
        repository=repo,
        vector_store=vec_store,
        embedding_service=embed_svc,
        approved_sources=list(DEFAULT_APPROVED_SOURCES),
    )

    job = service.ingest_local_documents(documents_dir=docs_dir)

    assert job.status == "completed"
    assert job.documents_discovered == 1
    assert job.documents_ingested == 1
    assert len(job.errors) == 0

    docs = repo.list_documents()
    assert len(docs) == 1
    assert docs[0]["url"] == LOCAL_PDF_REGISTRY[test_pdf_name].official_url
    assert docs[0]["source_id"] == LOCAL_PDF_REGISTRY[test_pdf_name].source_id

    provenance = repo.list_provenance_for_document(docs[0]["document_id"])
    assert len(provenance) > 0
    assert provenance[0]["official_url"] == LOCAL_PDF_REGISTRY[test_pdf_name].official_url

    assert vec_store.count() > 0
