"""
Storage adapter interface.

document_service.py only ever talks to this interface — never to a
concrete driver directly — so STORAGE_BACKEND can switch between `local`
and `s3` purely via configuration (see docs/architecture.md §1).
"""
from abc import ABC, abstractmethod


class BaseStorage(ABC):
    @abstractmethod
    async def save(self, key: str, content: bytes) -> str:
        """Persist bytes under `key`. Returns the storage_key actually used."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove the object at `key`. Must be a no-op (not an error) if absent."""
        raise NotImplementedError

    @abstractmethod
    async def get_url(self, key: str) -> str:
        """Return a URL/path the object can be retrieved from."""
        raise NotImplementedError
