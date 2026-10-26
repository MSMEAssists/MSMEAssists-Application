"""
Module 5: Agent Orchestration & Decision Intelligence API Router.

Exposes REST endpoints to orchestrate all upstream MSMEAssist modules
(Modules 1-4) into a unified executive decision intelligence result.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.v1.deps import get_current_user, get_document_service, get_profile_service
from app.models.user_model import UserModel
from app.schemas.decision_intelligence_schema import (
    DecisionObjective,
    DecisionRequest,
    DecisionIntelligenceResponse,
)
from app.services.decision_intelligence_service import DecisionIntelligenceService
from app.services.document_service import DocumentService
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/decision-intelligence", tags=["Module 5: Agent Orchestration & Decision Intelligence"])

# Shared service instance
_orchestrator = DecisionIntelligenceService()


@router.post(
    "/orchestrate",
    response_model=DecisionIntelligenceResponse,
    summary="Execute Unified Agent Orchestration & Decision Intelligence Pipeline",
    description=(
        "Executes the full multi-agent decision intelligence flow: "
        "resolves business profile, evaluates Udyam eligibility, queries official RAG knowledge, "
        "runs pairwise tournament and BTL MLE recommendation ranking, executes Module 4 loan advisory, "
        "audits scheme compliance, checks statutory permissions/licenses, analyzes export readiness, "
        "and synthesizes a prioritized action plan with complete traceable explainability."
    ),
)
async def orchestrate_decision_intelligence(
    payload: Optional[DecisionRequest] = None,
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
    document_service: DocumentService = Depends(get_document_service),
    authorization: Optional[str] = Header(None),
) -> DecisionIntelligenceResponse:
    request_data = payload or DecisionRequest()
    profile = await profile_service.get_profile_model(current_user.id)
    documents = []
    try:
        documents = await document_service.list_documents(current_user.id)
    except Exception as doc_exc:
        logger.warning("Could not fetch user documents for orchestration: %s", doc_exc)

    try:
        return await _orchestrator.orchestrate(
            profile=profile,
            documents=documents,
            request=request_data,
            auth_token=authorization,
        )
    except Exception as exc:
        logger.exception("Agent orchestration failed for user '%s': %s", str(current_user.id), exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent orchestration failed: {str(exc)}",
        ) from exc


@router.get(
    "/objectives",
    summary="List Supported Decision Objectives",
)
def get_supported_objectives():
    """Returns available strategic decision objectives with human-readable descriptions."""
    return [
        {
            "id": DecisionObjective.COMPREHENSIVE.value,
            "title": "Comprehensive Growth & Readiness",
            "description": "Holistic evaluation across loans, subsidies, compliance, licensing, and export opportunities.",
            "badge": "Recommended",
        },
        {
            "id": DecisionObjective.LOAN_FINANCE.value,
            "title": "Working Capital & Debt Financing",
            "description": "Focuses on DSCR coverage, collateral-free credit (CGTMSE), MUDRA, and institutional debt.",
            "badge": "Finance",
        },
        {
            "id": DecisionObjective.SCHEME_SUBSIDY.value,
            "title": "Government Subsidies & Grants",
            "description": "Prioritizes capital subsidies, PMEGP margin money, ZED certification support, and technology grants.",
            "badge": "Subsidies",
        },
        {
            "id": DecisionObjective.COMPLIANCE_AUDIT.value,
            "title": "Statutory Compliance & Licensing Audit",
            "description": "Audits factory permits, pollution consents (SPCB), FSSAI, GST, and mandatory regulatory filings.",
            "badge": "Compliance",
        },
        {
            "id": DecisionObjective.EXPORT_EXPANSION.value,
            "title": "Export Readiness & Global Trade",
            "description": "Evaluates DGFT foreign trade schemes, RoDTEP remissions, customs documentation, and international markets.",
            "badge": "Global",
        },
    ]
