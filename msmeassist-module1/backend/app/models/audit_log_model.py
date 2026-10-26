from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import AuditAction
from app.utils.object_id import PyObjectId


class ProfileAuditLogModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    profile_id: PyObjectId
    action: AuditAction
    changed_fields: List[str] = Field(default_factory=list)
    previous_values: dict = Field(default_factory=dict)
    actor: str = "self"
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
