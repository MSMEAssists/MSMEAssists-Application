"""
FastAPI Router for Module 4: Finance & Loan Agent.
Exposes clean REST endpoints for financial analysis, loan advisory, financing categories, and health checks.
"""
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, status

from app.models.schemas import (
    FinancialAnalysisRequest,
    FinancialAnalysisResponse,
    FinancingCategoriesResponse,
    LoanAdvisoryResponse,
    LoanRecommendationRequest,
)
from app.services.agent_orchestrator import FinanceLoanAgentOrchestrator
from app.services.financial_analyzer import FinancialAnalyzer
from app.services.loan_advisor import SUPPORTED_LOAN_CATEGORIES

router = APIRouter(tags=["Finance & Loan Agent"])

agent_orchestrator = FinanceLoanAgentOrchestrator()
financial_analyzer = FinancialAnalyzer()


@router.post(
    "/api/finance/analyze",
    response_model=FinancialAnalysisResponse,
    summary="Analyze Financial Situation",
)
async def analyze_financial_position(request: FinancialAnalysisRequest):
    """
    Analyzes an MSME's financial situation:
      - Computes revenue, profit margin, net cash flow, working capital gap, DSCR, and financial health score.
      - Identifies financial risks, improvement areas, and clearly flags missing information.
    """
    try:
        inputs = request.financial_inputs
        profile = request.business_profile
        return financial_analyzer.analyze(inputs, profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Financial analysis failed: {str(e)}",
        )


@router.post(
    "/api/finance/loan-recommendation",
    response_model=LoanAdvisoryResponse,
    summary="Generate Loan Recommendations",
)
async def generate_loan_recommendation(
    request: LoanRecommendationRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Generates personalized loan and financing recommendations for an MSME:
      1. Resolves business & financial profile (Module 1 integration)
      2. Performs financial situation & cash flow analysis
      3. Identifies loan requirement category and funding gap
      4. Retrieves relevant schemes from RAG knowledge base
      5. Evaluates Module 3 BTL-ranked scheme suitability
      6. Ranks eligible loan options and provides transparent explainable reasoning
    """
    try:
        return await agent_orchestrator.generate_loan_advisory(request, auth_token=authorization)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Loan advisory recommendation failed: {str(e)}",
        )


@router.get(
    "/api/finance/options",
    response_model=FinancingCategoriesResponse,
    summary="Get Financing Options & Loan Categories",
)
def get_financing_options():
    """
    Returns supported MSME loan categories (Working Capital, Term Loan, Machinery Loan, CGTMSE, etc.).
    """
    return FinancingCategoriesResponse(categories=SUPPORTED_LOAN_CATEGORIES)


@router.get("/api/finance/health", summary="Finance & Loan Agent Health Check")
def health_check():
    """
    Health check for Module 4 Finance & Loan Agent.
    """
    return {
        "status": "ok",
        "module": "Module 4: Finance & Loan Agent",
        "supported_categories": len(SUPPORTED_LOAN_CATEGORIES),
    }
