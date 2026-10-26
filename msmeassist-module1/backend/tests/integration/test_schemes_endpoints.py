"""
Integration tests for Government Schemes Discovery and RAG Assistant endpoints.
"""
from unittest.mock import AsyncMock, patch
import pytest


@pytest.mark.asyncio
async def test_schemes_discovery_requires_auth(client):
    resp = client.get("/api/schemes/discovery")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_schemes_query_requires_auth(client):
    resp = client.post("/api/schemes/query", json={"query": "What is PMEGP?"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_schemes_discovery_flow_with_profile(client, auth_headers):
    # 1. Create a business profile first
    profile_payload = {
        "business": {
            "name": "Meridian Fabrication Works",
            "type": "manufacturing",
            "industry": "Metal & Engineering",
            "established_date": "2020-01-15",
            "description": "Precision sheet metal fabrication",
        },
        "financial": {
            "annual_turnover_inr": 35000000,
            "investment_inr": 8000000,
            "employee_count": 25,
            "has_existing_loan": False,
        },
    }
    create_resp = client.post("/api/profile/me", json=profile_payload, headers=auth_headers)
    assert create_resp.status_code == 201

    # 2. Mock RAG search responses
    mock_search_results = [
        {
            "chunk_id": "chunk_pmegp_1",
            "document_id": "doc_pmegp",
            "title": "Prime Minister's Employment Generation Programme (PMEGP)",
            "knowledge_type": "SCHEME",
            "source_organization": "Ministry of MSME",
            "official_url": "https://www.msme.gov.in/schemes/pmegp",
            "page_number": None,
            "text": "PMEGP is a major credit-linked subsidy scheme for setting up micro enterprises.",
            "similarity_score": 0.88,
        },
        {
            "chunk_id": "chunk_sidbi_1",
            "document_id": "doc_sidbi",
            "title": "Working Capital Term Loan for MSMEs",
            "knowledge_type": "LOAN",
            "source_organization": "SIDBI",
            "official_url": "https://www.sidbi.in/en/loans/wctl",
            "page_number": None,
            "text": "SIDBI provides working capital term loans to manufacturing units.",
            "similarity_score": 0.82,
        },
    ]

    with patch("app.services.rag_client.RagClient.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_search_results

        resp = client.get("/api/schemes/discovery", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["business_name"] == "Meridian Fabrication Works"
        assert data["msme_classification"] == "micro"
        assert len(data["schemes"]) >= 2
        assert data["schemes"][0]["official_url"].startswith("https://")
        assert data["schemes"][0]["organization"] in ("Ministry of MSME", "SIDBI")


@pytest.mark.asyncio
async def test_schemes_query_returns_grounded_answer(client, auth_headers):
    mock_rag_response = {
        "query": "What is the eligibility for PMEGP?",
        "answer_text": "Based on official information from Ministry of MSME, any individual above 18 years of age is eligible.",
        "has_sufficient_context": True,
        "citations": [
            {
                "title": "Prime Minister's Employment Generation Programme (PMEGP)",
                "organization": "Ministry of MSME",
                "official_url": "https://www.msme.gov.in/schemes/pmegp",
                "page_number": None,
                "document_id": "doc_pmegp",
                "chunk_id": "chunk_pmegp_1",
            }
        ],
        "retrieved_result_count": 1,
    }

    with patch("app.services.rag_client.RagClient.query_rag", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_rag_response

        resp = client.post(
            "/api/schemes/query",
            json={"query": "What is the eligibility for PMEGP?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_sufficient_context"] is True
        assert len(data["citations"]) == 1
        assert data["citations"][0]["official_url"] == "https://www.msme.gov.in/schemes/pmegp"
        assert "18 years" in data["answer_text"]


@pytest.mark.asyncio
async def test_workflow_decision_flow(client, auth_headers):
    profile_payload = {
        "business": {
            "name": "Meridian Fabrication Works",
            "type": "manufacturing",
            "industry": "Metal & Engineering",
            "established_date": "2020-01-15",
            "description": "Precision sheet metal fabrication",
        },
        "financial": {
            "annual_turnover_inr": 35000000,
            "investment_inr": 8000000,
            "employee_count": 25,
            "has_existing_loan": False,
        },
        "characteristics": {
            "is_women_owned": True,
            "social_category": "general",
            "is_sustainable": True,
        },
    }
    create_resp = client.post("/api/profile/me", json=profile_payload, headers=auth_headers)
    assert create_resp.status_code == 201

    mock_search_results = [
        {
            "chunk_id": "chunk_pmegp_1",
            "document_id": "doc_pmegp",
            "title": "Prime Minister's Employment Generation Programme (PMEGP)",
            "knowledge_type": "SCHEME",
            "source_organization": "Ministry of MSME",
            "official_url": "https://www.msme.gov.in/schemes/pmegp",
            "page_number": 1,
            "text": "PMEGP supports women-owned micro manufacturing enterprises with credit-linked subsidy.",
            "similarity_score": 0.89,
        },
        {
            "chunk_id": "chunk_sidbi_1",
            "document_id": "doc_sidbi",
            "title": "Working Capital Term Loan for MSMEs",
            "knowledge_type": "LOAN",
            "source_organization": "SIDBI",
            "official_url": "https://www.sidbi.in/en/loans/wctl",
            "page_number": 1,
            "text": "SIDBI finances eligible MSMEs and women-owned enterprises with working capital support.",
            "similarity_score": 0.81,
        },
    ]

    mock_rag_response = {
        "query": "What is the best scheme for this profile?",
        "answer_text": "PMEGP is the strongest fit because the enterprise is a women-owned micro manufacturing business.",
        "has_sufficient_context": True,
        "citations": [
            {
                "title": "Prime Minister's Employment Generation Programme (PMEGP)",
                "organization": "Ministry of MSME",
                "official_url": "https://www.msme.gov.in/schemes/pmegp",
                "page_number": 1,
                "document_id": "doc_pmegp",
                "chunk_id": "chunk_pmegp_1",
            }
        ],
        "retrieved_result_count": 1,
    }

    with patch("app.services.rag_client.RagClient.search", new_callable=AsyncMock) as mock_search, patch(
        "app.services.rag_client.RagClient.query_rag", new_callable=AsyncMock
    ) as mock_query:
        mock_search.return_value = mock_search_results
        mock_query.return_value = mock_rag_response

        resp = client.post(
            "/api/workflow/decision",
            json={"query": "Recommend the best scheme for this MSME profile"},
            headers=auth_headers,
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["profile_status"] == "draft"
        assert data["eligibility"]["msme_classification"] == "micro"
        assert data["ranked_recommendations"][0]["title"] == "Prime Minister's Employment Generation Programme (PMEGP)"
        assert data["grounded_answer"]["has_sufficient_context"] is True
        assert data["workflow"]["status"] == "completed"
