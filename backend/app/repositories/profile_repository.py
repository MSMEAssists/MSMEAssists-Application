from typing import Optional

from app.models.profile_model import ProfileModel
from app.repositories.base_repository import BaseRepository


class ProfileRepository(BaseRepository[ProfileModel]):
    collection_name = "business_profiles"
    model_cls = ProfileModel

    async def find_by_user_id(self, user_id) -> Optional[ProfileModel]:
        return await self.find_one({"user_id": user_id})
