"""
Export Agent Router

Exposes endpoints for export readiness scoring, DGFT/RoDTEP scheme eligibility,
license audit, and customs document checklist.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_document_service, get_profile_service
from app.models.user_model import UserModel
from app.schemas.export_schema import ExportAdvisoryResponse, ExportRequest
from app.services.document_service import DocumentService
from app.services.export_service import assess_export_advisory
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export & Global Trade Agent"])


@router.post(
    "/advisory",
    response_model=ExportAdvisoryResponse,
    summary="Get personalized export & global trade advisory",
    description="Evaluates business profile facts, uploaded documents, and DGFT guidelines to provide export readiness score, RoDTEP/DGFT scheme recommendations, and customs document checklist.",
)
async def get_export_advisory(
    payload: Optional[ExportRequest] = None,
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
    document_service: DocumentService = Depends(get_document_service),
):
    profile = await profile_service.get_profile_model(current_user.id)
    documents = []
    try:
        documents = await document_service.list_documents(current_user.id)
    except Exception as doc_exc:
        logger.warning("Could not fetch user documents for export assessment: %s", doc_exc)

    request_data = payload or ExportRequest()
    return assess_export_advisory(request_data, profile, documents)
