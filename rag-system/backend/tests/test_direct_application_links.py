"""
Tests for verified official direct application URLs in MSMEAssist RAG backend.
Validates:
1. Genuine online application portals are accepted.
2. Generic homepages, information listings, and PDFs are rejected.
3. SSRF and unapproved domains are rejected.
4. Retriever correctly attaches verified application URLs to RetrievedResult.
5. Missing links for offline/bank-routed schemes evaluate to None.
"""
import pytest
from app.core.url_validator import verify_direct_application_url
from app.core.local_documents import LOCAL_PDF_REGISTRY
from app.retrieval.retriever import RetrievedResult, Retriever
from app.db.repository import SQLiteRepository
from app.models.entities import Document, KnowledgeItem, KnowledgeType, ContentFormat


def test_verify_direct_application_url_valid_portals():
    # PMEGP online e-portal
    assert verify_direct_application_url(
        "https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp"
    ) == "https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp"

    # ZED registration portal
    assert verify_direct_application_url(
        "https://zed.msme.gov.in/account/register"
    ) == "https://zed.msme.gov.in/account/register"

    # Stand-Up India registration portal
    assert verify_direct_application_url(
        "https://www.standupmitra.in/Login/Register"
    ) == "https://www.standupmitra.in/Login/Register"

    # Samadhaan ODR portal
    assert verify_direct_application_url(
        "https://samadhaan.msme.gov.in/MyMsme/MSEFC/MSEFC_Welcome.aspx"
    ) == "https://samadhaan.msme.gov.in/MyMsme/MSEFC/MSEFC_Welcome.aspx"

    # Dedicated subdomain portals
    assert verify_direct_application_url("https://cluster.dcmsme.gov.in/") == "https://cluster.dcmsme.gov.in/"
    assert verify_direct_application_url("https://seedfund.startupindia.gov.in/") == "https://seedfund.startupindia.gov.in/"
    assert verify_direct_application_url("https://ipass.telangana.gov.in/") == "https://ipass.telangana.gov.in/"


def test_verify_direct_application_url_rejects_homepages_and_info_pages():
    # Rule: Do not use a general information page or government homepage as Apply Now URL
    assert verify_direct_application_url("https://msme.gov.in/") is None
    assert verify_direct_application_url("https://www.msme.gov.in") is None
    assert verify_direct_application_url("https://www.msme.gov.in/offerings/schemes-and-services") is None
    assert verify_direct_application_url("https://msme.gov.in/pmegp") is None
    assert verify_direct_application_url("https://www.cgtmse.in/") is None
    assert verify_direct_application_url("https://www.cgtmse.in") is None
    assert verify_direct_application_url("https://www.mudra.org.in/") is None
    assert verify_direct_application_url("https://www.sidbi.in/en/") is None
    assert verify_direct_application_url("https://doe.gov.in/") is None
    assert verify_direct_application_url("https://mca.gov.in/") is None


def test_verify_direct_application_url_rejects_documents_and_pdfs():
    assert verify_direct_application_url("https://msme.gov.in/documents/pmegp_guidelines.pdf") is None
    assert verify_direct_application_url("https://www.cgtmse.in/circular_2024.pdf") is None
    assert verify_direct_application_url("https://dcmsme.gov.in/guidelines.docx") is None


def test_verify_direct_application_url_rejects_invalid_and_unapproved_targets():
    # None and empty
    assert verify_direct_application_url(None) is None
    assert verify_direct_application_url("") is None
    assert verify_direct_application_url("   ") is None

    # External / arbitrary domains
    assert verify_direct_application_url("https://example.com/apply") is None
    assert verify_direct_application_url("https://malicious-site.com/pmegp/apply") is None

    # SSRF targets
    assert verify_direct_application_url("http://localhost:8080/apply") is None
    assert verify_direct_application_url("http://127.0.0.1:8000/apply") is None
    assert verify_direct_application_url("http://169.254.169.254/latest/meta-data") is None


def test_local_registry_scheme_mapping():
    # PMEGP must carry verified direct application URL
    pmegp_meta = LOCAL_PDF_REGISTRY.get("Prime Minister Employment Generation Programme, PMEGP.pdf")
    assert pmegp_meta is not None
    assert pmegp_meta.official_application_url == "https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp"

    # CGTMSE is an offline/bank-guarantee scheme -- direct online application URL must be None
    cgtmse_meta = LOCAL_PDF_REGISTRY.get("CGTMSE_Credit_Guarantee_Fund_Trust_Scheme.pdf")
    assert cgtmse_meta is not None
    assert cgtmse_meta.official_application_url is None

    # MUDRA is applied via commercial banks/RRBs -- direct application URL must be None
    mudra_meta = LOCAL_PDF_REGISTRY.get("Pradhan_Mantri_MUDRA_Yojana_PMMY_Guidelines.pdf")
    assert mudra_meta is not None
    assert mudra_meta.official_application_url is None

    # ZED certification carries direct registration URL
    zed_meta = LOCAL_PDF_REGISTRY.get("Technology Upgradation and Quality Certification.pdf")
    assert zed_meta is not None
    assert zed_meta.official_application_url == "https://zed.msme.gov.in/account/register"


def test_retriever_build_retrieved_result_preserves_application_url(tmp_path):
    repo = SQLiteRepository(path=str(tmp_path / "test.db"))

    # Document 1: PMEGP (has verified application URL)
    doc_pmegp = Document(
        document_id="doc_pmegp_1",
        source_id="msme",
        organization="Ministry of MSME",
        url="https://www.msme.gov.in/offerings/schemes-and-services",
        content_format=ContentFormat.PDF,
        title="Prime Minister's Employment Generation Programme (PMEGP)",
        content_hash="hash1",
        version=1,
        retrieved_at=1000.0,
    )
    repo.upsert_document(doc_pmegp)

    know_pmegp = KnowledgeItem(
        knowledge_id="know_pmegp_1",
        document_id="doc_pmegp_1",
        source_id="msme",
        knowledge_type=KnowledgeType.SCHEME,
        title="Prime Minister's Employment Generation Programme (PMEGP)",
        original_source_url="https://www.msme.gov.in/offerings/schemes-and-services",
        source_organization="Ministry of MSME",
        official_application_url="https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp",
    )
    repo.upsert_knowledge_item(know_pmegp)

    from app.models.entities import Chunk
    chunk_pmegp = Chunk(
        chunk_id="chk_pmegp_1",
        document_id="doc_pmegp_1",
        source_id="msme",
        knowledge_id="know_pmegp_1",
        knowledge_type=KnowledgeType.SCHEME,
        title="Prime Minister's Employment Generation Programme (PMEGP)",
        section="Overview",
        page_number=1,
        chunk_index=0,
        text="PMEGP provides margin money subsidy up to 35% on manufacturing units up to 50 lakhs.",
    )
    repo.upsert_chunks([chunk_pmegp])

    # Document 2: CGTMSE (offline bank application, official_application_url=None)
    doc_cgtmse = Document(
        document_id="doc_cgtmse_1",
        source_id="sidbi",
        organization="SIDBI & CGTMSE",
        url="https://www.cgtmse.in/",
        content_format=ContentFormat.PDF,
        title="Credit Guarantee Fund Trust for Micro and Small Enterprises",
        content_hash="hash2",
        version=1,
        retrieved_at=1000.0,
    )
    repo.upsert_document(doc_cgtmse)

    know_cgtmse = KnowledgeItem(
        knowledge_id="know_cgtmse_1",
        document_id="doc_cgtmse_1",
        source_id="sidbi",
        knowledge_type=KnowledgeType.LOAN,
        title="Credit Guarantee Fund Trust for Micro and Small Enterprises",
        original_source_url="https://www.cgtmse.in/",
        source_organization="SIDBI & CGTMSE",
        official_application_url=None,
    )
    repo.upsert_knowledge_item(know_cgtmse)

    chunk_cgtmse = Chunk(
        chunk_id="chk_cgtmse_1",
        document_id="doc_cgtmse_1",
        source_id="sidbi",
        knowledge_id="know_cgtmse_1",
        knowledge_type=KnowledgeType.LOAN,
        title="Credit Guarantee Fund Trust for Micro and Small Enterprises",
        section="Eligibility",
        page_number=1,
        chunk_index=0,
        text="CGTMSE provides credit guarantee up to 5 Crore through Member Lending Institutions.",
    )
    repo.upsert_chunks([chunk_cgtmse])

    retriever = Retriever(repository=repo, vector_store=None, embedding_service=None)

    # 1. PMEGP should carry its direct online application URL
    res_pmegp = retriever._build_retrieved_result("chk_pmegp_1", 0.95)
    assert res_pmegp is not None
    assert res_pmegp.official_application_url == "https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp"
    assert res_pmegp.official_url == "https://www.msme.gov.in/offerings/schemes-and-services"

    # 2. CGTMSE should clearly carry None for official_application_url
    res_cgtmse = retriever._build_retrieved_result("chk_cgtmse_1", 0.90)
    assert res_cgtmse is not None
    assert res_cgtmse.official_application_url is None
    assert res_cgtmse.official_url == "https://www.cgtmse.in/"
