from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import DocumentStatus, DocumentType, StorageBackend
from app.utils.object_id import PyObjectId


class DocumentModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    profile_id: PyObjectId
    document_type: DocumentType
    file_name: str
    mime_type: str
    size_bytes: int
    storage_backend: StorageBackend
    storage_key: str
    status: DocumentStatus = DocumentStatus.UPLOADED
    rejection_reason: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
