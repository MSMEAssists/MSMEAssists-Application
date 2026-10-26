"""
VectorStore abstraction.

The application never talks to FAISS/Qdrant/pgvector directly -- everything
goes through this interface, so the backend can be swapped later without
touching retrieval/ingestion code. Every stored vector retains chunk_id,
document_id, source_id and knowledge_type as required metadata.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class VectorRecord:
    chunk_id: str
    document_id: str
    source_id: str
    knowledge_type: str
    vector: List[float]


@dataclass
class VectorSearchHit:
    chunk_id: str
    document_id: str
    source_id: str
    knowledge_type: str
    score: float


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, records: List[VectorRecord]) -> None:
        ...

    @abstractmethod
    def delete(self, chunk_ids: List[str]) -> None:
        ...

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[VectorSearchHit]:
        ...

    @abstractmethod
    def count(self) -> int:
        ...

    @abstractmethod
    def persist(self) -> None:
        ...

    @abstractmethod
    def load(self) -> None:
        ...
