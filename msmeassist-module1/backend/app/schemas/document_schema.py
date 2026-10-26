from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.core.constants import DocumentStatus, DocumentType


class DocumentResponse(BaseModel):
    id: str
    document_type: DocumentType
    file_name: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    rejection_reason: Optional[str] = None
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
