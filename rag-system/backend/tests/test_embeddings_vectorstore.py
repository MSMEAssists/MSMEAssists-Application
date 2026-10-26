import shutil
import tempfile
import unittest

from app.embeddings.embedding_service import EmbeddingService
from app.vectorstore.base import VectorRecord
from app.vectorstore.numpy_store import NumpyVectorStore

CORPUS = [
    "PMEGP is a credit-linked subsidy scheme for setting up micro enterprises and generating employment.",
    "Eligibility for PMEGP requires the applicant to be above 18 years of age.",
    "SIDBI working capital term loan helps MSMEs meet operational funding requirements.",
    "The loan repayment tenure is up to 5 years including a moratorium period.",
    "Government e-procurement tenders require registration on the official portal.",
]


class TestEmbeddingService(unittest.TestCase):
    def test_embed_returns_correct_dimensions(self):
        service = EmbeddingService(provider_name="tfidf_svd", dimensions=64)
        service.fit(CORPUS)
        result = service.embed(["credit scheme for MSMEs"])
        self.assertEqual(len(result.vectors[0]), 64)

    def test_similar_texts_score_higher_than_dissimilar(self):
        service = EmbeddingService(provider_name="tfidf_svd", dimensions=64)
        service.fit(CORPUS)
        query_vec = service.embed(["What subsidy scheme is available for micro enterprises?"]).vectors[0]
        scheme_vec = service.embed([CORPUS[0]]).vectors[0]
        loan_vec = service.embed([CORPUS[2]]).vectors[0]

        import numpy as np
        sim_scheme = float(np.dot(query_vec, scheme_vec))
        sim_loan = float(np.dot(query_vec, loan_vec))
        self.assertGreater(sim_scheme, sim_loan)


class TestNumpyVectorStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = NumpyVectorStore(self.tmpdir + "/store")
        self.service = EmbeddingService(provider_name="tfidf_svd", dimensions=32)
        self.service.fit(CORPUS)
        vectors = self.service.embed(CORPUS).vectors
        self.records = [
            VectorRecord(
                chunk_id=f"chunk_{i}",
                document_id=f"doc_{i % 2}",
                source_id="msme" if i < 2 else "sidbi",
                knowledge_type="SCHEME" if i < 2 else ("LOAN" if i < 4 else "PROCUREMENT"),
                vector=vec,
            )
            for i, vec in enumerate(vectors)
        ]
        self.store.upsert(self.records)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_count(self):
        self.assertEqual(self.store.count(), 5)

    def test_search_returns_relevant_top_result(self):
        query_vec = self.service.embed(["credit-linked subsidy scheme for micro enterprises"]).vectors[0]
        hits = self.store.search(query_vec, top_k=3)
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].chunk_id, "chunk_0")

    def test_metadata_filter_by_knowledge_type(self):
        query_vec = self.service.embed(["loan"]).vectors[0]
        hits = self.store.search(query_vec, top_k=5, filters={"knowledge_type": "LOAN"})
        self.assertTrue(all(h.knowledge_type == "LOAN" for h in hits))

    def test_persist_and_load_roundtrip(self):
        self.store.persist()
        reloaded = NumpyVectorStore(self.tmpdir + "/store")
        reloaded.load()
        self.assertEqual(reloaded.count(), 5)

    def test_upsert_replaces_existing_chunk(self):
        new_vec = self.service.embed(["updated content for chunk zero"]).vectors[0]
        self.store.upsert([VectorRecord(chunk_id="chunk_0", document_id="doc_0", source_id="msme", knowledge_type="SCHEME", vector=new_vec)])
        self.assertEqual(self.store.count(), 5)  # no duplicate row


if __name__ == "__main__":
    unittest.main()
