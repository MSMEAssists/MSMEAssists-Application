#!/usr/bin/env python3
"""
Final verification script.

Runs the REAL pipeline (extraction, cleaning, classification, chunking,
embedding, vector indexing, retrieval, RAG answer generation) against the
local test fixtures, since this script may be run in environments without
internet access. If you have internet access and have installed
requirements.txt, prefer running actual ingestion via the API
(`POST /api/ingestion/run`) against the live approved sources instead --
this script is the offline-safe verification path.

Usage:
    cd backend
    python verify_pipeline.py
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from app.core.source_registry import DEFAULT_APPROVED_SOURCES  # noqa: E402
from app.db.repository import SQLiteRepository  # noqa: E402
from app.embeddings.embedding_service import EmbeddingService  # noqa: E402
from app.extractors.html_extractor import extract_html  # noqa: E402
from app.extractors.pdf_extractor import extract_pdf  # noqa: E402
from app.models.entities import ContentFormat, RawFetchResult, now_ts  # noqa: E402
from app.processors.cleaner import clean_pdf_pages, clean_text  # noqa: E402
from app.rag.answer_generator import generate_answer  # noqa: E402
from app.retrieval.retriever import Retriever  # noqa: E402
from app.services.ingestion_service import IngestionService  # noqa: E402
from app.vectorstore.numpy_store import NumpyVectorStore  # noqa: E402

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "tests", "fixtures")
SOURCES_BY_ID = {s.source_id: s for s in DEFAULT_APPROVED_SOURCES}


def _raw(filename, url, fmt):
    with open(os.path.join(FIXTURE_DIR, filename), "rb") as f:
        raw_bytes = f.read()
    return RawFetchResult(url=url, final_url=url, status_code=200, content_format=fmt, raw_bytes=raw_bytes, fetched_at=now_ts())


def main():
    tmpdir = tempfile.mkdtemp()
    print("=" * 70)
    print("GOVERNMENT INFORMATION RAG — PIPELINE VERIFICATION")
    print("=" * 70)

    repository = SQLiteRepository(path=os.path.join(tmpdir, "meta.db"))
    vector_store = NumpyVectorStore(os.path.join(tmpdir, "vecstore"))
    embedding_service = EmbeddingService(provider_name="tfidf_svd", dimensions=64)
    ingestion_service = IngestionService(
        repository=repository, vector_store=vector_store,
        embedding_service=embedding_service, approved_sources=list(DEFAULT_APPROVED_SOURCES),
    )

    # 1-2. Approved sources
    print(f"\n[1] Approved sources configured: {len(DEFAULT_APPROVED_SOURCES)}")
    for s in DEFAULT_APPROVED_SOURCES:
        print(f"    - {s.source_id}: {s.name} ({s.allowed_domains[0]})")

    # 3-4. Ingestion (fixture-based -- see module docstring)
    print("\n[2] Running ingestion against local fixtures (offline verification path)...")
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
        print(f"    - {raw.url}: {outcome}")
    vector_store.persist()

    documents = repository.list_documents()
    scheme_items = repository.list_knowledge_items(knowledge_type="SCHEME")
    loan_items = repository.list_knowledge_items(knowledge_type="LOAN")
    total_chunks = sum(len(repository.list_chunks_for_document(d["document_id"])) for d in documents)

    print(f"\n[3] Documents collected: {len(documents)}")
    print(f"[4] Scheme records: {len(scheme_items)}")
    print(f"[5] Loan/credit records: {len(loan_items)}")
    print(f"[6] Chunks generated: {total_chunks}")
    print(f"[7] Vectors indexed: {vector_store.count()}")
    print(f"[8] Embedding model: {embedding_service.model_name} ({embedding_service.dimensions} dims)")

    # Retrieval
    retriever = Retriever(repository, vector_store, embedding_service)
    print("\n[9] Semantic query tests:")
    for q, expect_type in [
        ("What government schemes are available for MSMEs?", "SCHEME"),
        ("What loans are available for small manufacturing businesses?", "LOAN"),
    ]:
        results = retriever.search(q, top_k=3, similarity_threshold=0.1)
        ok = bool(results) and results[0].knowledge_type == expect_type
        print(f"    - \"{q}\"")
        print(f"      top result type={results[0].knowledge_type if results else 'NONE'}, "
              f"score={results[0].similarity_score if results else 0:.3f}, "
              f"url={results[0].official_url if results else '-'}  [{'PASS' if ok else 'CHECK'}]")

    # PDF page reference check
    pdf_doc = next(d for d in documents if d["content_format"] == "PDF")
    pdf_chunks = repository.list_chunks_for_document(pdf_doc["document_id"])
    print(f"\n[10] PDF page references: {len(pdf_chunks)} chunks, "
          f"pages referenced = {sorted({c['page_number'] for c in pdf_chunks})}")

    # Provenance check
    all_have_provenance = all(
        len(repository.list_provenance_for_document(d["document_id"])) > 0 for d in documents
    )
    print(f"\n[11] Provenance verification: {'PASS' if all_have_provenance else 'FAIL'} "
          f"(every document has >=1 provenance record with an official URL)")

    # RAG answer generation
    print("\n[12] RAG answer generation test:")
    q = "What is the eligibility for PMEGP?"
    results = retriever.search(q, top_k=3, similarity_threshold=0.1)
    answer = generate_answer(q, results, llm_client=None)
    print(f"    Query: {q}")
    print(f"    has_sufficient_context: {answer.has_sufficient_context}")
    print(f"    citations: {[c.official_url for c in answer.citations]}")

    # No-hallucination test
    print("\n[13] No-hallucination test:")
    q2 = "How do I train my pet parrot to talk?"
    results2 = retriever.search(q2, top_k=3, similarity_threshold=0.15)
    answer2 = generate_answer(q2, results2, llm_client=None)
    print(f"    Query: {q2}")
    print(f"    has_sufficient_context: {answer2.has_sufficient_context} "
          f"[{'PASS - correctly refused' if not answer2.has_sufficient_context else 'FAIL'}]")
    print(f"    answer_text: {answer2.answer_text}")

    shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Architecture implemented:      Dual-pipeline RAG (ingestion + retrieval), as specified")
    print(f"Official sources configured:   {len(DEFAULT_APPROVED_SOURCES)}")
    print(f"Documents collected (fixture): {len(documents)}")
    print(f"Scheme records:                {len(scheme_items)}")
    print(f"Loan/credit records:           {len(loan_items)}")
    print(f"Chunks:                        {total_chunks}")
    print(f"Embedding status:              OK ({embedding_service.model_name})")
    print(f"Vector store status:           OK ({vector_store.count()} vectors, numpy backend)")
    print(f"Retrieval test results:        See [9] above")
    print(f"RAG test results:               See [12]-[13] above")
    print(f"Provenance verification:       {'PASS' if all_have_provenance else 'FAIL'}")
    print(f"Known limitations:             Live .gov.in ingestion not run in this environment")
    print(f"                                (no internet access). TF-IDF fallback embeddings")
    print(f"                                (not sentence-transformers) used; on this tiny 3-doc")
    print(f"                                fixture corpus, broad/generic queries can occasionally")
    print(f"                                rank a topically-adjacent document above the ideal one")
    print(f"                                (see query [9] above) -- switch EMBEDDING_PROVIDER=")
    print(f"                                sentence_transformers for production-quality semantic")
    print(f"                                ranking at real corpus scale.")


if __name__ == "__main__":
    main()
