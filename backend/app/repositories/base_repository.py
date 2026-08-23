"""
Generic Mongo repository. Concrete repositories (user/profile/document/
audit_log) extend this for collection-specific queries. No business rules
live here — only data access.
"""
from typing import Any, Generic, Optional, Type, TypeVar

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(Generic[ModelT]):
    collection_name: str
    model_cls: Type[ModelT]

    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection: AsyncIOMotorCollection = db[self.collection_name]

    async def find_by_id(self, doc_id: str | ObjectId) -> Optional[ModelT]:
        if not ObjectId.is_valid(doc_id):
            return None
        doc = await self._collection.find_one({"_id": ObjectId(doc_id)})
        return self.model_cls(**doc) if doc else None

    async def find_one(self, query: dict[str, Any]) -> Optional[ModelT]:
        doc = await self._collection.find_one(query)
        return self.model_cls(**doc) if doc else None

    async def insert(self, model: ModelT) -> ModelT:
        payload = model.model_dump(by_alias=True)
        await self._collection.insert_one(payload)
        return model

    async def update_by_id(self, doc_id: str | ObjectId, update: dict[str, Any]) -> Optional[ModelT]:
        if not ObjectId.is_valid(doc_id):
            return None
        await self._collection.update_one({"_id": ObjectId(doc_id)}, {"$set": update})
        return await self.find_by_id(doc_id)

    async def delete_by_id(self, doc_id: str | ObjectId) -> bool:
        if not ObjectId.is_valid(doc_id):
            return False
        result = await self._collection.delete_one({"_id": ObjectId(doc_id)})
        return result.deleted_count > 0
