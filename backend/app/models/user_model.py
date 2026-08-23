"""
Mongo document shape for the `users` collection.

This is the internal representation only — API responses are built from
app/schemas/auth_schema.py, never from this model directly, so the
password hash can never accidentally leak.
"""
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import UserRole
from app.utils.object_id import PyObjectId


class UserModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    full_name: str
    email: str
    mobile_number: str
    password_hash: str
    role: UserRole = UserRole.MSME_OWNER
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: Optional[datetime] = None
