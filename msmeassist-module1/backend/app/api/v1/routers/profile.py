from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_current_user, get_profile_service
from app.models.user_model import UserModel
from app.schemas.profile_schema import (
    CompletenessResponse,
    EligibilityResponse,
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services import completeness_service, eligibility_service
from app.services.profile_service import ProfileService
from app.utils.exceptions import ProfileNotFoundError

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
):
    return await profile_service.get_profile(current_user.id)


@router.post("/me", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    payload: ProfileCreateRequest,
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
):
    return await profile_service.create_profile(current_user.id, payload)


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
):
    return await profile_service.update_profile(current_user.id, payload)


@router.get("/completeness", response_model=CompletenessResponse)
async def get_my_completeness(
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
):
    profile = await profile_service.get_profile_model(current_user.id)
    if profile is None:
        raise ProfileNotFoundError("No business profile found for this user")
    documents = await profile_service.document_repo.find_by_profile_id(profile.id)
    completeness, missing = completeness_service.compute_completeness_with_missing(profile, documents)
    return CompletenessResponse(percentage=completeness.percentage, sections=completeness.sections, missing=missing)


@router.get("/eligibility", response_model=EligibilityResponse)
async def get_my_eligibility(
    current_user: UserModel = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
):
    profile = await profile_service.get_profile_model(current_user.id)
    if profile is None:
        raise ProfileNotFoundError("No business profile found for this user")
    return eligibility_service.compute_eligibility(profile)
