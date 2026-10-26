"""
Scheme Compliance Agent router.

Single POST endpoint that accepts a scheme identifier and returns a
rule-by-rule compliance assessment grounded in official RAG evidence
matched against the authenticated user's business profile.

Path  : POST /api/compliance/scheme-check
Auth  : Bearer JWT — get_current_user dependency (same as every other router)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.deps import get_current_user, get_document_service, get_profile_service
from app.models.user_model import UserModel
from app.schemas.compliance_schema import SchemeComplianceRequest, SchemeComplianceResponse
from app.services.compliance_service import ComplianceService
from app.services.document_service import DocumentService
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["Scheme Compliance Agent"])

# Single shared instance — ComplianceService is stateless
_service = ComplianceService()


@router.post(
    "/scheme-check",
    response_model=SchemeComplianceResponse,
    summary="Assess scheme compliance for the authenticated user",
    description=(
        "Retrieves official eligibility rules and requirements for a scheme from the "
        "government knowledge base, then assesses each rule against the authenticated "
        "user's business profile. "
        "Every result includes a verdict (met / not_met / needs_info), the profile fact "
        "used, a plain-language explanation, and full source provenance. "
        "Results are guidance only — final eligibility is decided by the scheme authority."
    ),
)
async def check_scheme_compliance(
    payload: SchemeComplianceRequest,
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
    document_service: DocumentService = Depends(get_document_service),
) -> SchemeComplianceResponse:
    """
    Fetch the user's profile and uploaded documents, then run the compliance assessment.
    profile may be None if the user has not completed onboarding — the
    service handles that gracefully (all rules will be NEEDS_INFO).
    """
    profile = await profile_service.get_profile_model(current_user.id)
    documents = []
    try:
        documents = await document_service.list_documents(current_user.id)
    except Exception as doc_exc:
        logger.warning("Could not fetch user documents for compliance assessment: %s", doc_exc)

    try:
        return await _service.assess(payload, profile, documents=documents)
    except Exception as exc:
        logger.exception(
            "Compliance assessment failed for scheme '%s', user '%s': %s",
            payload.scheme_name,
            str(current_user.id),
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Compliance assessment failed. Please try again.",
        ) from exc
