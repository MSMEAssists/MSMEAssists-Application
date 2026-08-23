"""
Password hashing and JWT issuance/verification.

Kept isolated from services so the hashing scheme or token library can be
swapped without touching business logic.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=[settings.password_hash_scheme], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str, extra_claims: Optional[dict[str, Any]] = None) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expire_minutes = settings.jwt_access_token_expire_minutes
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    # python-jose expects a naive-UTC-equivalent timestamp; passing an aware
    # datetime is fine, jose converts via timegm internally.
    payload: dict[str, Any] = {"sub": subject, "exp": expire_at}
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expire_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jose.JWTError on invalid/expired token — caller maps to 401."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


__all__ = ["hash_password", "verify_password", "create_access_token", "decode_access_token", "JWTError"]
