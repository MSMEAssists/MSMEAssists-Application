"""
Routers for Government Scheme Discovery and Grounded RAG Assistant.
"""
from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_profile_service, get_schemes_service
from app.models.user_model import UserModel
from app.schemas.schemes_schema import (
    SchemeDiscoveryResponse,
    SchemeQueryRequest,
    SchemeQueryResponse,
    WorkflowDecisionRequest,
    WorkflowDecisionResponse,
)
from app.services import eligibility_service
from app.services.profile_service import ProfileService
from app.services.schemes_service import SchemesService

router = APIRouter(prefix="/schemes", tags=["Government Schemes & Intelligence"])
workflow_router = APIRouter(prefix="/workflow", tags=["Workflow"])


@router.get("/discovery", response_model=SchemeDiscoveryResponse)
async def discover_schemes(
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
    schemes_service: SchemesService = Depends(get_schemes_service),
):
    """
    Retrieves tailored government schemes and programs from the RAG service,
    aligned to the authenticated user's business profile and eligibility attributes.
    """
    profile = await profile_service.get_profile_model(current_user.id)
    return await schemes_service.discover_schemes_for_profile(profile)


@router.post("/query", response_model=SchemeQueryResponse)
async def query_schemes_assistant(
    payload: SchemeQueryRequest,
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
    schemes_service: SchemesService = Depends(get_schemes_service),
):
    """
    Queries the official Government Information RAG System with natural language questions.
    Returns answers strictly grounded in official sources with mandatory provenance and citations.
    """
    profile = await profile_service.get_profile_model(current_user.id)
    return await schemes_service.query_rag_assistant(payload, profile)


@workflow_router.post("/decision", response_model=WorkflowDecisionResponse)
async def workflow_decision(
    payload: WorkflowDecisionRequest,
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
    schemes_service: SchemesService = Depends(get_schemes_service),
):
    """
    Unified workflow that matches the diagrammed decision-support sequence:
    1) load profile,
    2) compute eligibility,
    3) discover ranked schemes,
    4) query the grounded evidence layer,
    5) return a single workflow response.
    """
    profile = await profile_service.get_profile_model(current_user.id)
    if profile is None:
        raise ValueError("No profile found for this user. Please complete the profile onboarding first.")

    eligibility = eligibility_service.compute_eligibility(profile)
    ranked = await schemes_service.discover_schemes_for_profile(profile)
    grounded = await schemes_service.query_rag_assistant(
        SchemeQueryRequest(query=payload.query, top_k=payload.top_k, knowledge_type=payload.knowledge_type),
        profile,
    )

    return WorkflowDecisionResponse(
        workflow={
            "status": "completed",
            "steps": [
                "profile_loaded",
                "eligibility_evaluated",
                "scheme_discovery_completed",
                "grounded_answer_generated",
            ],
        },
        business_name=profile.business.name if profile.business else "Your Business",
        profile_status=profile.status.value,
        eligibility={
            "msme_classification": eligibility.msme_classification.value,
            "attributes": eligibility.attributes,
            "computed_at": eligibility.computed_at.isoformat(),
        },
        ranked_recommendations=ranked.schemes,
        grounded_answer=grounded,
    )
