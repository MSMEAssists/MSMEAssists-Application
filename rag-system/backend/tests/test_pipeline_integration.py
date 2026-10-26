"""
End-to-end pipeline test.

This exercises the REAL pipeline -- real HTML/PDF extraction, real
cleaning, real classification, real chunking, real TF-IDF/SVD embeddings,
real numpy vector search, real provenance construction, real RAG answer
assembly -- with NO hard-coded scheme/loan data and NO fabricated
retrieval results (see project rule: "no mock RAG").

The one thing it does NOT do is fetch over the live network: `RawFetchResult`
objects are constructed directly from local fixture bytes instead of going
through app.utils.http.fetch()/app.collectors.html_collector's crawler,
because this test environment has no internet access. Everything
downstream of "bytes have been fetched" is the real, unmodified pipeline.
"""
import os
import shutil
import tempfile
import unittest

from app.core.source_registry import DEFAULT_APPROVED_SOURCES
from app.db.repository import SQLiteRepository
from app.embeddings.embedding_service import EmbeddingService
from app.models.entities import ContentFormat, KnowledgeType, RawFetchResult, now_ts
from app.rag.answer_generator import NO_RESULTS_MESSAGE, generate_answer
from app.retrieval.retriever import Retriever
from app.services.ingestion_service import IngestionService
from app.vectorstore.numpy_store import NumpyVectorStore

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
MSME_SOURCE = next(s for s in DEFAULT_APPROVED_SOURCES if s.source_id == "msme")
SIDBI_SOURCE = next(s for s in DEFAULT_APPROVED_SOURCES if s.source_id == "sidbi")
EPROCURE_SOURCE = next(s for s in DEFAULT_APPROVED_SOURCES if s.source_id == "eprocure")


def _raw_from_fixture(filename, url, content_format):
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, "rb") as f:
        raw_bytes = f.read()
    return RawFetchResult(
        url=url, final_url=url, status_code=200,
        content_format=content_format, raw_bytes=raw_bytes, fetched_at=now_ts(),
    )


class TestPipelineIntegration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repository = SQLiteRepository(path=os.path.join(self.tmpdir, "meta.db"))
        self.vector_store = NumpyVectorStore(os.path.join(self.tmpdir, "vecstore"))
        self.embedding_service = EmbeddingService(provider_name="tfidf_svd", dimensions=64)
        self.approved_sources = list(DEFAULT_APPROVED_SOURCES)
        self.ingestion_service = IngestionService(
            repository=self.repository,
            vector_store=self.vector_store,
            embedding_service=self.embedding_service,
            approved_sources=self.approved_sources,
        )

        scheme_raw = _raw_from_fixture(
            "scheme_page.html", "https://www.msme.gov.in/schemes/pmegp", ContentFormat.HTML
        )
        loan_raw = _raw_from_fixture(
            "loan_page.html", "https://www.sidbi.in/en/loans/wctl", ContentFormat.HTML
        )
        notification_raw = _raw_from_fixture(
            "notification.pdf", "https://etenders.gov.in/eprocure/app",
            ContentFormat.PDF,
        )

        # Fit the embedding service once across the whole batch, mirroring
        # what IngestionService.run_ingestion() does for a real crawl.
        from app.extractors.html_extractor import extract_html
        from app.extractors.pdf_extractor import extract_pdf
        from app.processors.cleaner import clean_text, clean_pdf_pages

        corpus = [
            clean_text(extract_html(scheme_raw.raw_bytes.decode(), scheme_raw.final_url).text),
            clean_text(extract_html(loan_raw.raw_bytes.decode(), loan_raw.final_url).text),
            clean_text("\n".join(clean_pdf_pages(extract_pdf(notification_raw.raw_bytes).page_texts))),
        ]
        self.embedding_service.fit(corpus)

        self.ingestion_service._ingest_one(scheme_raw, MSME_SOURCE)
        self.ingestion_service._ingest_one(loan_raw, SIDBI_SOURCE)
        self.ingestion_service._ingest_one(notification_raw, EPROCURE_SOURCE)

        self.retriever = Retriever(self.repository, self.vector_store, self.embedding_service)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- ingestion outcomes ---

    def test_documents_stored(self):
        docs = self.repository.list_documents()
        self.assertEqual(len(docs), 3)

    def test_scheme_and_loan_knowledge_items_created(self):
        scheme_items = self.repository.list_knowledge_items(knowledge_type="SCHEME")
        loan_items = self.repository.list_knowledge_items(knowledge_type="LOAN")
        self.assertEqual(len(scheme_items), 1)
        self.assertEqual(len(loan_items), 1)
        self.assertIn("18 years", scheme_items[0]["eligibility"])

    def test_chunks_generated_and_indexed(self):
        docs = self.repository.list_documents()
        total_chunks = sum(len(self.repository.list_chunks_for_document(d["document_id"])) for d in docs)
        self.assertGreater(total_chunks, 0)
        self.assertEqual(self.vector_store.count(), total_chunks)

    def test_pdf_chunk_retains_page_number(self):
        pdf_doc = next(d for d in self.repository.list_documents() if d["content_format"] == "PDF")
        chunks = self.repository.list_chunks_for_document(pdf_doc["document_id"])
        self.assertTrue(all(c["page_number"] is not None for c in chunks))

    def test_provenance_records_created_with_official_url(self):
        docs = self.repository.list_documents()
        for d in docs:
            prov = self.repository.list_provenance_for_document(d["document_id"])
            self.assertGreater(len(prov), 0)
            for p in prov:
                self.assertEqual(p["official_url"], d["url"])

    def test_unchanged_refetch_does_not_duplicate(self):
        scheme_raw = _raw_from_fixture(
            "scheme_page.html", "https://www.msme.gov.in/schemes/pmegp", ContentFormat.HTML
        )
        before = len(self.repository.list_documents())
        outcome = self.ingestion_service._ingest_one(scheme_raw, MSME_SOURCE)
        after = len(self.repository.list_documents())
        self.assertEqual(outcome, "unchanged")
        self.assertEqual(before, after)

    # --- retrieval ---

    def test_scheme_query_retrieves_scheme_content(self):
        results = self.retriever.search(
            "What government schemes are available for setting up micro enterprises?",
            top_k=3, similarity_threshold=0.0,
        )
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].knowledge_type, "SCHEME")
        self.assertEqual(results[0].official_url, "https://www.msme.gov.in/schemes/pmegp")

    def test_loan_query_retrieves_loan_content(self):
        results = self.retriever.search(
            "What working capital loans are available for MSMEs?",
            top_k=3, similarity_threshold=0.0,
        )
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].knowledge_type, "LOAN")

    def test_knowledge_type_filter_restricts_results(self):
        results = self.retriever.search(
            "government financial assistance", top_k=5, similarity_threshold=0.0,
            knowledge_type="LOAN",
        )
        self.assertTrue(all(r.knowledge_type == "LOAN" for r in results))

    def test_every_result_has_provenance_fields(self):
        results = self.retriever.search("scheme eligibility", top_k=5, similarity_threshold=0.0)
        for r in results:
            self.assertTrue(r.official_url.startswith("https://"))
            self.assertIsNotNone(r.source_organization)

    # --- RAG answer generation ---

    def test_rag_answer_includes_citation_and_official_url(self):
        results = self.retriever.search(
            "What is the eligibility for PMEGP?", top_k=3, similarity_threshold=0.0,
        )
        answer = generate_answer("What is the eligibility for PMEGP?", results, llm_client=None)
        self.assertTrue(answer.has_sufficient_context)
        self.assertGreater(len(answer.citations), 0)
        self.assertIn("msme.gov.in", answer.citations[0].official_url)

    def test_no_hallucination_on_irrelevant_query(self):
        # A query with essentially no vocabulary overlap with the ingested
        # corpus -- distinct from testing a merely "different topic but
        # shares a common word" query, which is a separate (documented)
        # precision limitation of the offline TF-IDF fallback on tiny
        # corpora, not a hallucination-guard failure. See docs/rag.md.
        query = "How do I train my pet parrot to talk?"
        results = self.retriever.search(query, top_k=3, similarity_threshold=0.15)
        answer = generate_answer(query, results, llm_client=None)
        self.assertFalse(answer.has_sufficient_context)
        self.assertEqual(answer.answer_text, NO_RESULTS_MESSAGE)
        self.assertEqual(len(answer.citations), 0)


if __name__ == "__main__":
    unittest.main()
