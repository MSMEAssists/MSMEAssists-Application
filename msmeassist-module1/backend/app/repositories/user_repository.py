from datetime import datetime, timezone
from typing import Optional

from app.models.user_model import UserModel
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    collection_name = "users"
    model_cls = UserModel

    async def find_by_email(self, email: str) -> Optional[UserModel]:
        return await self.find_one({"email": email.lower()})

    async def find_by_mobile(self, mobile_number: str) -> Optional[UserModel]:
        return await self.find_one({"mobile_number": mobile_number})

    async def touch_last_login(self, user_id) -> None:
        await self._collection.update_one(
            {"_id": user_id}, {"$set": {"last_login_at": datetime.now(timezone.utc)}}
        )
