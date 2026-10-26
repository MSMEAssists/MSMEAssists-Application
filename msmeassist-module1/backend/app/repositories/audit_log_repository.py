from typing import List

from app.models.audit_log_model import ProfileAuditLogModel
from app.repositories.base_repository import BaseRepository


class AuditLogRepository(BaseRepository[ProfileAuditLogModel]):
    collection_name = "profile_audit_logs"
    model_cls = ProfileAuditLogModel

    async def find_by_profile_id(self, profile_id, limit: int = 50) -> List[ProfileAuditLogModel]:
        cursor = self._collection.find({"profile_id": profile_id}).sort("created_at", -1).limit(limit)
        return [ProfileAuditLogModel(**doc) async for doc in cursor]
