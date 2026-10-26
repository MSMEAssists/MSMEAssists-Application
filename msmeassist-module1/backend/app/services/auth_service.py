"""
Auth service — the only layer allowed to reason about credentials, tokens,
and account state. Routers (api/v1/routers/auth.py) just call these.
"""
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user_model import UserModel
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginRequest, MeResponse, RegisterRequest, UserPublic
from app.utils.exceptions import (
    AccountInactiveError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    MobileAlreadyExistsError,
)


class AuthService:
    def __init__(self, user_repo: UserRepository, profile_repo: ProfileRepository):
        self.user_repo = user_repo
        self.profile_repo = profile_repo

    async def register(self, payload: RegisterRequest) -> tuple[UserModel, str, int]:
        email = payload.email.lower()

        if await self.user_repo.find_by_email(email):
            raise EmailAlreadyExistsError("An account with this email already exists", field="email")
        if await self.user_repo.find_by_mobile(payload.mobile_number):
            raise MobileAlreadyExistsError("An account with this mobile number already exists", field="mobile_number")

        user = UserModel(
            full_name=payload.full_name,
            email=email,
            mobile_number=payload.mobile_number,
            password_hash=hash_password(payload.password),
        )
        user = await self.user_repo.insert(user)
        token, expires_in = create_access_token(subject=str(user.id))
        return user, token, expires_in

    async def login(self, payload: LoginRequest) -> tuple[UserModel, str, int]:
        user = await self.user_repo.find_by_email(payload.email.lower())
        if user is None or not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsError("Incorrect email or password")
        if not user.is_active:
            raise AccountInactiveError("This account has been deactivated")

        await self.user_repo.touch_last_login(user.id)
        token, expires_in = create_access_token(subject=str(user.id))
        return user, token, expires_in

    async def get_me(self, user: UserModel) -> MeResponse:
        profile = await self.profile_repo.find_by_user_id(user.id)
        return MeResponse(
            id=str(user.id),
            full_name=user.full_name,
            email=user.email,
            mobile_number=user.mobile_number,
            role=user.role,
            is_verified=user.is_verified,
            has_profile=profile is not None,
            created_at=user.created_at,
        )

    @staticmethod
    def to_public(user: UserModel) -> UserPublic:
        return UserPublic(
            id=str(user.id),
            full_name=user.full_name,
            email=user.email,
            mobile_number=user.mobile_number,
            role=user.role,
            is_verified=user.is_verified,
            created_at=user.created_at,
        )
