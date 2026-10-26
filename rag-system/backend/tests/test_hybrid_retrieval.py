import pytest
from app.db.repository import get_repository
from app.vectorstore.factory import build_vector_store
from app.embeddings.embedding_service import EmbeddingService
from app.retrieval.retriever import Retriever, extract_exact_query_terms


@pytest.fixture(scope='module')
def retriever_instance():
    repo = get_repository()
    vec_store = build_vector_store()
    embed_svc = EmbeddingService()
    chunks = repo._list('chunks') if hasattr(repo, '_list') else []
    texts = [c['text'] for c in chunks if isinstance(c, dict) and 'text' in c]
    if texts:
        embed_svc.fit(texts)
    return Retriever(repository=repo, vector_store=vec_store, embedding_service=embed_svc)


def test_extract_exact_query_terms():
    terms = extract_exact_query_terms('What is PMEGP and MSE-CDP scheme under MSME?')
    assert 'pmegp' in terms
    assert 'mse-cdp' in terms
    assert 'msme' in terms


def test_retrieve_pmegp(retriever_instance):
    results = retriever_instance.search('What is PMEGP and who is eligible for it?', top_k=3, similarity_threshold=0.0)
    assert len(results) > 0
    top = results[0]
    assert 'PMEGP' in (top.title or '') or 'Employment Generation' in (top.title or '') or 'PMEGP' in top.text
    assert top.official_url.startswith('https://')


def test_retrieve_pmegp_subsidy(retriever_instance):
    results = retriever_instance.search('What subsidy is available under PMEGP?', top_k=3, similarity_threshold=0.0)
    assert len(results) > 0
    top = results[0]
    assert 'PMEGP' in (top.title or '') or 'PMEGP' in top.text


def test_retrieve_mse_cdp(retriever_instance):
    results = retriever_instance.search('What is the MSE-CDP scheme?', top_k=3, similarity_threshold=0.0)
    assert len(results) > 0
    top = results[0]
    assert 'Cluster Development' in (top.title or '') or 'MSE-CDP' in (top.title or '') or 'MSE-CDP' in top.text


def test_retrieve_zed(retriever_instance):
    results = retriever_instance.search('What is the ZED certification scheme?', top_k=3, similarity_threshold=0.0)
    assert len(results) > 0
    top = results[0]
    assert 'ZED' in (top.title or '') or 'Zero Defect' in top.text


def test_retrieve_delayed_payments_odr(retriever_instance):
    results = retriever_instance.search('How can an MSME address delayed payments?', top_k=3, similarity_threshold=0.0)
    assert len(results) > 0
    top = results[0]
    assert 'Delayed Payments' in (top.title or '') or 'ODR' in (top.title or '') or 'MSEFC' in top.text


def test_retrieve_cgss_startups(retriever_instance):
    results = retriever_instance.search('What is the Credit Guarantee Scheme for Startups CGSS?', top_k=3, similarity_threshold=0.0)
    assert len(results) > 0
    top = results[0]
    assert 'Startups' in (top.title or '') or 'CGSS' in (top.title or '') or 'Credit Guarantee' in top.text


def test_retrieve_pms_procurement(retriever_instance):
    results = retriever_instance.search('What support is available for government procurement and marketing PMS?', top_k=3, similarity_threshold=0.0)
    assert len(results) > 0
    top = results[0]
    assert 'Procurement' in (top.title or '') or 'PMS' in (top.title or '') or 'Marketing' in top.text


def test_retrieve_esdp(retriever_instance):
    results = retriever_instance.search('What entrepreneurship and skill development programs are available ESDP?', top_k=3, similarity_threshold=0.0)
    assert len(results) > 0
    top = results[0]
    assert 'Skill Development' in (top.title or '') or 'ESDP' in (top.title or '') or 'Entrepreneurship' in top.text


def test_provenance_fields_intact(retriever_instance):
    results = retriever_instance.search('MSME loan schemes', top_k=2, similarity_threshold=0.0)
    assert len(results) > 0
    r = results[0]
    assert r.chunk_id is not None
    assert r.document_id is not None
    assert r.title is not None
    assert r.official_url.startswith('https://')
    assert r.source_organization is not None
    assert isinstance(r.similarity_score, float)
    assert len(r.text) > 0
