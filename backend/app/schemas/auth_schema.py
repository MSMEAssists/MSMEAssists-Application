from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from app.core.constants import UserRole
from app.utils.validators import is_valid_mobile, password_strength_ok


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    mobile_number: str
    password: str
    confirm_password: str

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        if not is_valid_mobile(v):
            raise ValueError("mobile_number must be a valid +91XXXXXXXXXX number")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not password_strength_ok(v):
            raise ValueError("password must be at least 8 characters and include a letter and a digit")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    """Never includes password_hash — this is the only user shape the API ever returns."""

    id: str
    full_name: str
    email: str
    mobile_number: Optional[str] = None
    role: Optional[UserRole] = None
    is_verified: Optional[bool] = None
    created_at: Optional[datetime] = None


class AuthTokenResponse(BaseModel):
    user: UserPublic
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    id: str
    full_name: str
    email: str
    mobile_number: str
    role: UserRole
    is_verified: bool
    has_profile: bool
    created_at: datetime
