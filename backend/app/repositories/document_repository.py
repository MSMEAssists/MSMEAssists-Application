from typing import List

from app.models.document_model import DocumentModel
from app.repositories.base_repository import BaseRepository


class DocumentRepository(BaseRepository[DocumentModel]):
    collection_name = "documents"
    model_cls = DocumentModel

    async def find_by_user_id(self, user_id) -> List[DocumentModel]:
        cursor = self._collection.find({"user_id": user_id}).sort("uploaded_at", -1)
        return [DocumentModel(**doc) async for doc in cursor]

    async def find_by_profile_id(self, profile_id) -> List[DocumentModel]:
        cursor = self._collection.find({"profile_id": profile_id}).sort("uploaded_at", -1)
        return [DocumentModel(**doc) async for doc in cursor]

    async def count_verified_or_pending_for_profile(self, profile_id) -> int:
        return await self._collection.count_documents(
            {"profile_id": profile_id, "status": {"$in": ["uploaded", "pending_review", "verified"]}}
        )
