"""
Integration tests for FinanceLoanAgentOrchestrator and Module 4 API endpoints.
"""
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    BusinessProfilePayload,
    FinancialInputs,
    LoanInputs,
    LoanRecommendationRequest,
)
from app.services.agent_orchestrator import FinanceLoanAgentOrchestrator

client = TestClient(app)


# ---------------------------------------------------------------------------
# Async orchestrator test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_orchestrator_workflow():
    orchestrator = FinanceLoanAgentOrchestrator()
    request = LoanRecommendationRequest(
        financial_inputs=FinancialInputs(
            annual_turnover_inr=3_000_000.0,
            investment_requirement_inr=500_000.0,   # correct field name
        ),
        loan_inputs=LoanInputs(
            requested_amount_inr=1_000_000.0,
            purpose="Working Capital & Equipment",
        ),
        business_profile=BusinessProfilePayload(
            name="Green Valley Foods",
            business_type="manufacturing",
            msme_classification="micro",
        ),
    )

    response = await orchestrator.generate_loan_advisory(request)

    assert response.business_name == "Green Valley Foods"
    assert response.msme_classification == "Micro"
    assert response.financial_summary.annual_revenue == "₹30.00 Lakh"
    assert len(response.recommended_options) > 0
    assert response.explanation != ""
    assert "disclaimer" in response.model_dump()


# ---------------------------------------------------------------------------
# Synchronous API endpoint tests (use TestClient — no event loop needed)
# ---------------------------------------------------------------------------

def test_api_analyze_endpoint():
    payload = {
        "financial_inputs": {"annual_turnover_inr": 4_000_000.0},
        "business_profile": {"name": "Test Enterprise"},
    }
    res = client.post("/api/finance/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "financial_summary" in data
    assert data["financial_summary"]["annual_revenue"] == "₹40.00 Lakh"
    assert "financial_risks" in data
    assert "missing_information" in data


def test_api_analyze_missing_all_financials():
    """All financial fields omitted — must not crash; must flag missing info."""
    payload = {
        "financial_inputs": {},
        "business_profile": {"name": "Empty Data MSME"},
    }
    res = client.post("/api/finance/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["missing_information"]) > 0


def test_api_loan_recommendation_endpoint():
    payload = {
        "financial_inputs": {"annual_turnover_inr": 5_000_000.0},
        "loan_inputs": {"requested_amount_inr": 1_500_000.0, "purpose": "Expansion"},
        "business_profile": {"name": "Expansion Traders", "msme_classification": "small"},
    }
    res = client.post("/api/finance/loan-recommendation", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["business_name"] == "Expansion Traders"
    assert len(data["recommended_options"]) > 0
    assert "disclaimer" in data
    assert data["disclaimer"] != ""


def test_api_loan_recommendation_no_auth():
    """No Authorization header — must still work (auth is optional)."""
    payload = {
        "financial_inputs": {"annual_turnover_inr": 2_400_000.0},
        "business_profile": {"name": "Solo Trader"},
    }
    res = client.post("/api/finance/loan-recommendation", json=payload)
    assert res.status_code == 200


def test_api_options_endpoint():
    res = client.get("/api/finance/options")
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert len(data["categories"]) >= 5


def test_api_health_endpoint():
    res = client.get("/api/finance/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "module" in data
    assert data["supported_categories"] >= 5


def test_api_root():
    res = client.get("/")
    assert res.status_code == 200
    assert "Module 4" in res.json()["message"]
