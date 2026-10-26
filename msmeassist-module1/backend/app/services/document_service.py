"""
Document service.

Orchestrates: mime/size validation -> storage adapter write -> metadata
persisted in `documents` -> audit log -> completeness recompute on the
owning profile. Module 1 only tracks upload + status metadata here — no
document content verification is implemented (see docs/architecture.md
scope boundary).
"""
import uuid
from datetime import datetime, timezone
from typing import List

from app.core.constants import ALLOWED_DOCUMENT_MIME_TYPES, AuditAction, DocumentStatus, DocumentType, StorageBackend
from app.models.audit_log_model import ProfileAuditLogModel
from app.models.document_model import DocumentModel
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.profile_repository import ProfileRepository
from app.services import completeness_service
from app.storage.base_storage import BaseStorage
from app.utils.exceptions import (
    DocumentNotFoundError,
    FileTooLargeError,
    ForbiddenError,
    ProfileNotFoundError,
    UnsupportedMediaTypeError,
)


class DocumentService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        profile_repo: ProfileRepository,
        audit_repo: AuditLogRepository,
        storage: BaseStorage,
        storage_backend: StorageBackend,
        max_upload_size_bytes: int,
    ):
        self.document_repo = document_repo
        self.profile_repo = profile_repo
        self.audit_repo = audit_repo
        self.storage = storage
        self.storage_backend = storage_backend
        self.max_upload_size_bytes = max_upload_size_bytes

    async def upload_document(
        self,
        user_id,
        document_type: DocumentType,
        file_name: str,
        mime_type: str,
        content: bytes,
    ) -> DocumentModel:
        if mime_type not in ALLOWED_DOCUMENT_MIME_TYPES:
            raise UnsupportedMediaTypeError(
                "Only PDF, JPG, JPEG or PNG files are accepted", field="file"
            )
        if len(content) > self.max_upload_size_bytes:
            raise FileTooLargeError(
                f"File exceeds the {self.max_upload_size_bytes // (1024 * 1024)}MB upload limit", field="file"
            )

        profile = await self.profile_repo.find_by_user_id(user_id)
        if profile is None:
            raise ProfileNotFoundError("Create a business profile before uploading documents")

        storage_key = f"{user_id}/{document_type.value}/{uuid.uuid4().hex}_{file_name}"
        await self.storage.save(storage_key, content)

        document = DocumentModel(
            user_id=user_id,
            profile_id=profile.id,
            document_type=document_type,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=len(content),
            storage_backend=self.storage_backend,
            storage_key=storage_key,
            status=DocumentStatus.UPLOADED,
        )
        document = await self.document_repo.insert(document)

        await self.audit_repo.insert(
            ProfileAuditLogModel(
                user_id=user_id,
                profile_id=profile.id,
                action=AuditAction.DOCUMENT_UPLOADED,
                changed_fields=[f"document:{document.id}"],
                actor="self",
            )
        )

        await self._recompute_profile_completeness(profile.id)
        return document

    async def list_documents(self, user_id) -> List[DocumentModel]:
        return await self.document_repo.find_by_user_id(user_id)

    async def delete_document(self, user_id, document_id: str) -> None:
        document = await self.document_repo.find_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError("Document not found")
        if str(document.user_id) != str(user_id):
            raise ForbiddenError("You do not have access to this document")

        await self.storage.delete(document.storage_key)
        await self.document_repo.delete_by_id(document_id)

        await self.audit_repo.insert(
            ProfileAuditLogModel(
                user_id=user_id,
                profile_id=document.profile_id,
                action=AuditAction.DOCUMENT_DELETED,
                changed_fields=[f"document:{document.id}"],
                actor="self",
            )
        )
        await self._recompute_profile_completeness(document.profile_id)

    async def _recompute_profile_completeness(self, profile_id) -> None:
        profile = await self.profile_repo.find_by_id(profile_id)
        if profile is None:
            return
        documents = await self.document_repo.find_by_profile_id(profile.id)
        completeness = completeness_service.compute_completeness(profile, documents)
        await self.profile_repo.update_by_id(
            profile.id,
            {
                "completeness": completeness.model_dump(),
                "updated_at": datetime.now(timezone.utc),
            },
        )
