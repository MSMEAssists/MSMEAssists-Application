"""
Shared FastAPI dependencies.

get_current_user() is the single place that turns a JWT into a trusted
UserModel — every profile/document endpoint depends on this rather than
accepting any user/profile id from the request body or query string.
This is what "use the authenticated JWT identity rather than trusting
user IDs from the frontend" means in practice: nowhere in profile.py or
documents.py does a user_id ever come from anywhere except this dependency.
"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.mongo_client import get_database
from app.models.user_model import UserModel
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService
from app.services.profile_service import ProfileService
from app.storage.factory import get_storage
from app.utils.exceptions import UnauthorizedError

_bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> AsyncIOMotorDatabase:
    return get_database()


def get_user_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_profile_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> ProfileRepository:
    return ProfileRepository(db)


def get_document_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


def get_audit_log_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> AuditLogRepository:
    return AuditLogRepository(db)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
) -> AuthService:
    return AuthService(user_repo, profile_repo)


def get_profile_service(
    profile_repo: ProfileRepository = Depends(get_profile_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> ProfileService:
    return ProfileService(profile_repo, document_repo, audit_repo)


def get_document_service(
    document_repo: DocumentRepository = Depends(get_document_repository),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
    settings: Settings = Depends(get_settings),
) -> DocumentService:
    return DocumentService(
        document_repo=document_repo,
        profile_repo=profile_repo,
        audit_repo=audit_repo,
        storage=get_storage(),
        storage_backend=settings.storage_backend,
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserModel:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    user = await user_repo.find_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated")

    return user
