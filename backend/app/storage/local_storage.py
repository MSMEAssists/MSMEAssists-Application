"""Local-disk storage driver — used when STORAGE_BACKEND=local (dev default)."""
import os

import aiofiles

from app.storage.base_storage import BaseStorage


class LocalStorage(BaseStorage):
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def _full_path(self, key: str) -> str:
        return os.path.join(self.base_path, key)

    async def save(self, key: str, content: bytes) -> str:
        full_path = self._full_path(key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)
        return key

    async def delete(self, key: str) -> None:
        full_path = self._full_path(key)
        if os.path.exists(full_path):
            os.remove(full_path)

    async def get_url(self, key: str) -> str:
        # Dev-only convenience path; production S3 driver returns a real URL.
        return f"/local-storage/{key}"
