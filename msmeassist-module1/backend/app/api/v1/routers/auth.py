from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_auth_service, get_current_user
from app.models.user_model import UserModel
from app.schemas.auth_schema import AuthTokenResponse, LoginRequest, MeResponse, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    user, token, expires_in = await auth_service.register(payload)
    return AuthTokenResponse(
        user=AuthService.to_public(user),
        access_token=token,
        expires_in=expires_in,
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    user, token, expires_in = await auth_service.login(payload)
    return AuthTokenResponse(
        user=AuthService.to_public(user),
        access_token=token,
        expires_in=expires_in,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.get_me(current_user)
