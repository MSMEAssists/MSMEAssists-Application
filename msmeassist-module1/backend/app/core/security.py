"""
Password hashing and JWT issuance/verification.

Kept isolated from services so the hashing scheme or token library can be
swapped without touching business logic.

NOTE: passlib 1.7.4 + bcrypt >= 4.0 produces a benign __about__ warning.
      Passwords are truncated to 72 bytes before hashing (bcrypt hard limit).
"""
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# Suppress the passlib/bcrypt __about__ version-detection warning
warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt hard limit is 72 bytes. Truncate to avoid ValueError on long passwords.
_BCRYPT_MAX_BYTES = 72


def _prepare_password(plain_password: str) -> bytes:
    """Encode to UTF-8 and truncate to bcrypt's 72-byte hard limit."""
    return plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain_password: str) -> str:
    pwd_bytes = _prepare_password(plain_password)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        pwd_bytes = _prepare_password(plain_password)
        return bcrypt.checkpw(pwd_bytes, password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject: str, extra_claims: Optional[dict[str, Any]] = None) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expire_minutes = settings.jwt_access_token_expire_minutes
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire_at}
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expire_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jose.JWTError on invalid/expired token — caller maps to 401."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


__all__ = ["hash_password", "verify_password", "create_access_token", "decode_access_token", "JWTError"]
