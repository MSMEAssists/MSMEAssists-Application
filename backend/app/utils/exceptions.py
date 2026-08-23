"""
Domain-level exceptions raised by the service layer.

Routers never raise HTTPException directly for business errors — they let
these bubble up to the global exception handler registered in main.py,
which maps them to the error envelope documented in docs/module-1-api.md:

    { "error": { "code": "...", "message": "...", "field": "..." } }
"""
from typing import Optional


class AppError(Exception):
    status_code: int = 400
    code: str = "APP_ERROR"

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


# --- Auth ---
class EmailAlreadyExistsError(AppError):
    status_code = 409
    code = "EMAIL_ALREADY_EXISTS"


class MobileAlreadyExistsError(AppError):
    status_code = 409
    code = "MOBILE_ALREADY_EXISTS"


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"


class AccountInactiveError(AppError):
    status_code = 403
    code = "ACCOUNT_INACTIVE"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


# --- Profile ---
class ProfileNotFoundError(AppError):
    status_code = 404
    code = "PROFILE_NOT_FOUND"


class ProfileAlreadyExistsError(AppError):
    status_code = 409
    code = "PROFILE_ALREADY_EXISTS"


class ReadOnlyFieldError(AppError):
    status_code = 422
    code = "READ_ONLY_FIELD"


# --- Documents ---
class DocumentNotFoundError(AppError):
    status_code = 404
    code = "DOCUMENT_NOT_FOUND"


class FileTooLargeError(AppError):
    status_code = 413
    code = "FILE_TOO_LARGE"


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = "UNSUPPORTED_MEDIA_TYPE"


# --- Generic validation ---
class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
