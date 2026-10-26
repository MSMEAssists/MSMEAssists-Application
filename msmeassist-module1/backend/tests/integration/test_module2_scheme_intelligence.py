"""
Unit and Integration Tests for Module 2 - Government Scheme Intelligence.
"""
from datetime import date
from unittest.mock import AsyncMock, patch
from bson import ObjectId
import pytest

from app.core.constants import AreaType, BusinessType, MSMEClassification, SocialCategory
from app.models.profile_model import (
    BusinessSection,
    CharacteristicsSection,
    FinancialSection,
    LocationSection,
    ProfileModel,
)
from app.schemas.schemes_schema import EligibilityStatus
from app.services.scheme_evaluator import SchemeEvaluator
from app.services.scheme_query_builder import SchemeQueryBuilder
from app.services.schemes_service import SchemesService


@pytest.fixture
def sample_micro_manufacturing_profile():
    return ProfileModel(
        user_id=ObjectId("507f1f77bcf86cd799439011"),
        business=BusinessSection(
            name="Apex Precision Engineering",
            type=BusinessType.MANUFACTURING,
            industry="Automotive Components",
            sub_sector="Machined Parts",
            established_date=date(2021, 5, 10),
            description="Precision CNC milling and components",
        ),
        location=LocationSection(
            state="Telangana",
            district="Medchal-Malkajgiri",
            city="Hyderabad",
            pin_code="500037",
            area_type=AreaType.URBAN,
        ),
        financial=FinancialSection(
            annual_turnover_inr=15000000,
            investment_inr=4000000,
            employee_count=18,
            msme_classification=MSMEClassification.MICRO,
        ),
        characteristics=CharacteristicsSection(
            is_women_owned=True,
            social_category=SocialCategory.GENERAL,
            is_sustainable=True,
        ),
    )


@pytest.fixture
def sample_tech_startup_profile():
    return ProfileModel(
        user_id=ObjectId("507f1f77bcf86cd799439012"),
        business=BusinessSection(
            name="NeuralLogix AI",
            type=BusinessType.SERVICES,
            industry="Software & AI",
            established_date=date(2023, 1, 1),
        ),
        location=LocationSection(
            state="Karnataka",
            district="Bengaluru Urban",
            city="Bengaluru",
            pin_code="560001",
            area_type=AreaType.URBAN,
        ),
        financial=FinancialSection(
            annual_turnover_inr=5000000,
            investment_inr=2000000,
            employee_count=8,
            msme_classification=MSMEClassification.MICRO,
        ),
        characteristics=CharacteristicsSection(
            is_startup_recognized=True,
            is_tech_oriented=True,
        ),
    )


@pytest.fixture
def sample_trading_profile():
    return ProfileModel(
        user_id=ObjectId("507f1f77bcf86cd799439013"),
        business=BusinessSection(
            name="Sri Venkateshwara Traders",
            type=BusinessType.TRADING,
            industry="Hardware Wholesale",
            established_date=date(2018, 4, 1),
        ),
        financial=FinancialSection(
            annual_turnover_inr=80000000,
            investment_inr=15000000,
            employee_count=12,
            msme_classification=MSMEClassification.SMALL,
        ),
    )


def test_query_builder_facets(sample_micro_manufacturing_profile, sample_tech_startup_profile):
    builder = SchemeQueryBuilder()
    
    # Micro Manufacturing
    q1 = builder.build_queries(sample_micro_manufacturing_profile)
    assert any("manufacturing" in q.lower() for q in q1)
    assert any("micro" in q.lower() for q in q1)
    assert any("women" in q.lower() for q in q1)
    assert any("sustainable" in q.lower() or "zed" in q.lower() for q in q1)

    # Tech Startup
    q2 = builder.build_queries(sample_tech_startup_profile)
    assert any("services" in q.lower() for q in q2)
    assert any("startup" in q.lower() for q in q2)


def test_evaluator_positive_and_provenance(sample_micro_manufacturing_profile):
    evaluator = SchemeEvaluator()
    chunks = [
        {
            "chunk_id": "chunk_pmegp_p1",
            "page_number": 1,
            "official_url": "https://www.msme.gov.in/schemes/pmegp",
            "source_organization": "Ministry of MSME",
            "text": "PMEGP is applicable to micro manufacturing enterprises. Any individual above 18 years is eligible. Maximum cost of project is Rs. 50 lakhs for manufacturing sector. Subsidy rate of 25% to 35% is provided. Enclosures include Aadhaar, PAN, and project report.",
            "similarity_score": 0.85,
        }
    ]
    doc_meta = {"title": "PMEGP Guidelines", "official_url": "https://www.msme.gov.in/schemes/pmegp"}

    res = evaluator.evaluate_scheme(sample_micro_manufacturing_profile, chunks, doc_meta)
    
    assert res["eligibility_status"] in (EligibilityStatus.ELIGIBLE, EligibilityStatus.CONDITIONALLY_ELIGIBLE)
    assert len(res["key_eligibility_criteria"]) > 0
    assert len(res["benefits_available"]) > 0
    assert len(res["required_documents"]) > 0
    
    # Check provenance
    top_crit = res["key_eligibility_criteria"][0]
    assert top_crit.chunk_id == "chunk_pmegp_p1"
    assert top_crit.page_number == 1
    assert top_crit.source_url == "https://www.msme.gov.in/schemes/pmegp"

    # Check score decoupling
    assert res["retrieval_score"] == 0.85
    assert res["eligibility_evidence_score"] >= 0.8
    assert res["recommendation_score"] > 0.6


def test_evaluator_explicit_conflict_not_eligible(sample_trading_profile):
    evaluator = SchemeEvaluator()
    chunks = [
        {
            "chunk_id": "chunk_zed_p3",
            "page_number": 3,
            "official_url": "https://www.msme.gov.in/schemes/zed",
            "source_organization": "Ministry of MSME",
            "text": "Applicable only to manufacturing enterprises. Trading and service units are not covered under this certification.",
            "similarity_score": 0.70,
        }
    ]
    doc_meta = {"title": "ZED Guidelines", "official_url": "https://www.msme.gov.in/schemes/zed"}

    res = evaluator.evaluate_scheme(sample_trading_profile, chunks, doc_meta)
    assert res["eligibility_status"] == EligibilityStatus.NOT_ELIGIBLE
    assert len(res["unmet_or_conflicting_conditions"]) > 0
    assert "manufacturing" in res["unmet_or_conflicting_conditions"][0].statement.lower()
    assert res["recommendation_score"] < 0.2


def test_evaluator_silent_evidence_never_not_eligible():
    evaluator = SchemeEvaluator()
    minimal_profile = ProfileModel(
        user_id=ObjectId("507f1f77bcf86cd799439099"),
        business=BusinessSection(name="New Co", type=BusinessType.SERVICES, industry="General Services", established_date=date(2024, 1, 1)),
    )
    chunks = [
        {
            "chunk_id": "chunk_generic_1",
            "page_number": 10,
            "official_url": "https://dcmsme.gov.in/",
            "source_organization": "DC-MSME",
            "text": "General overview of international trade fairs and bilateral institutional cooperation.",
            "similarity_score": 0.45,
        }
    ]
    doc_meta = {"title": "Trade Fair Overview", "official_url": "https://dcmsme.gov.in/"}

    res = evaluator.evaluate_scheme(minimal_profile, chunks, doc_meta)
    # Must NOT falsely mark NOT_ELIGIBLE when evidence is merely silent
    assert res["eligibility_status"] in (EligibilityStatus.INSUFFICIENT_EVIDENCE, EligibilityStatus.POTENTIALLY_ELIGIBLE)
    assert res["eligibility_status"] != EligibilityStatus.NOT_ELIGIBLE


@pytest.mark.asyncio
async def test_module2_end_to_end_orchestration(sample_micro_manufacturing_profile):
    mock_search_results = [
        {
            "chunk_id": "chunk_pmegp_1",
            "document_id": "doc_pmegp",
            "title": "Prime Minister Employment Generation Programme (PMEGP)",
            "knowledge_type": "SCHEME",
            "source_organization": "Ministry of MSME, Govt. of India",
            "official_url": "https://www.msme.gov.in/schemes/pmegp",
            "page_number": 1,
            "text": "PMEGP is a credit-linked subsidy scheme for micro manufacturing enterprises. Beneficiaries must be above 18 years. Subsidy rate up to 35% for women and special category in rural areas. Application is online through kviconline.gov.in portal. Documents required include Udyam, Aadhaar, and DPR.",
            "similarity_score": 0.88,
        },
        {
            "chunk_id": "chunk_zed_1",
            "document_id": "doc_zed",
            "title": "MSME Sustainable (ZED) Certification Scheme",
            "knowledge_type": "SCHEME",
            "source_organization": "Ministry of MSME, Govt. of India",
            "official_url": "https://www.msme.gov.in/schemes/zed",
            "page_number": 2,
            "text": "MSME Sustainable ZED certification provides financial assistance for quality and sustainable practices. Micro units get 80% subsidy, with additional 10% for women-owned enterprises.",
            "similarity_score": 0.82,
        },
    ]

    with patch("app.services.rag_client.RagClient.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_search_results

        service = SchemesService()
        response = await service.discover_schemes_for_profile(sample_micro_manufacturing_profile)

        assert response.business_name == "Apex Precision Engineering"
        assert response.msme_classification == "micro"
        assert len(response.schemes) >= 2
        
        # Validate first scheme
        s1 = response.schemes[0]
        assert s1.official_url.startswith("https://")
        assert s1.eligibility_status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.CONDITIONALLY_ELIGIBLE)
        assert len(s1.why_it_matches) > 0
        assert s1.recommendation_score > 0.5
        assert s1.retrieval_score > 0.0
        assert len(s1.key_eligibility_criteria) > 0
        assert len(s1.benefits_available) > 0
