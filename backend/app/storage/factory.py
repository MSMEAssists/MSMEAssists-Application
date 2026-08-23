from functools import lru_cache

from app.core.config import get_settings
from app.storage.base_storage import BaseStorage
from app.storage.local_storage import LocalStorage


@lru_cache
def get_storage() -> BaseStorage:
    settings = get_settings()
    if settings.storage_backend == "s3":
        from app.storage.s3_storage import S3Storage

        return S3Storage()
    return LocalStorage(base_path=settings.storage_local_path)
