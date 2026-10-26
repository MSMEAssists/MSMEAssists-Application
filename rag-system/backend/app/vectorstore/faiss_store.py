"""
FAISS-backed VectorStore implementation, per the spec's initial-prototype
recommendation. Imports faiss lazily so the rest of the app still works in
environments where faiss isn't installed (see numpy_store.py, the default
backend used when faiss is unavailable).
"""
import json
import os
from typing import Dict, List, Optional

import numpy as np

from app.vectorstore.base import VectorRecord, VectorSearchHit, VectorStore


class FaissVectorStore(VectorStore):
    def __init__(self, path: str, dimensions: int):
        try:
            import faiss  # noqa
        except ImportError as e:
            raise ImportError(
                "faiss is not installed. Install faiss-cpu, or set "
                "VECTOR_STORE_BACKEND=numpy to use the built-in fallback."
            ) from e
        import faiss
        self._faiss = faiss
        self.path = path
        self.dimensions = dimensions
        # IndexFlatIP over L2-normalized vectors == cosine similarity.
        self._index = faiss.IndexIDMap2(faiss.IndexFlatIP(dimensions))
        self._id_to_meta: Dict[int, dict] = {}
        self._next_int_id = 0
        self._chunk_id_to_int: Dict[str, int] = {}
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def upsert(self, records: List[VectorRecord]) -> None:
        if not records:
            return
        self.delete([r.chunk_id for r in records])
        vectors = np.array([r.vector for r in records], dtype=np.float32)
        ids = []
        for r in records:
            int_id = self._next_int_id
            self._next_int_id += 1
            self._chunk_id_to_int[r.chunk_id] = int_id
            self._id_to_meta[int_id] = {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "source_id": r.source_id,
                "knowledge_type": r.knowledge_type,
            }
            ids.append(int_id)
        self._index.add_with_ids(vectors, np.array(ids, dtype=np.int64))

    def delete(self, chunk_ids: List[str]) -> None:
        int_ids = [self._chunk_id_to_int[c] for c in chunk_ids if c in self._chunk_id_to_int]
        if int_ids:
            self._index.remove_ids(np.array(int_ids, dtype=np.int64))
            for i in int_ids:
                self._id_to_meta.pop(i, None)
            for c in chunk_ids:
                self._chunk_id_to_int.pop(c, None)

    def search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[VectorSearchHit]:
        if self._index.ntotal == 0:
            return []
        q = np.array([query_vector], dtype=np.float32)
        # Over-fetch when filtering, since FAISS itself is filter-agnostic.
        fetch_k = top_k * 10 if filters else top_k
        fetch_k = min(fetch_k, self._index.ntotal)
        scores, ids = self._index.search(q, fetch_k)

        hits = []
        for score, int_id in zip(scores[0], ids[0]):
            if int_id == -1:
                continue
            meta = self._id_to_meta.get(int(int_id))
            if not meta:
                continue
            if filters:
                if "source_id" in filters and meta["source_id"] != filters["source_id"]:
                    continue
                if "knowledge_type" in filters and meta["knowledge_type"] != filters["knowledge_type"]:
                    continue
            hits.append(VectorSearchHit(score=float(score), **meta))
            if len(hits) >= top_k:
                break
        return hits

    def count(self) -> int:
        return self._index.ntotal

    def persist(self) -> None:
        self._faiss.write_index(self._index, self.path + ".faiss")
        with open(self.path + ".meta.json", "w") as f:
            json.dump(
                {"id_to_meta": self._id_to_meta, "next_int_id": self._next_int_id},
                f,
            )

    def load(self) -> None:
        index_path = self.path + ".faiss"
        meta_path = self.path + ".meta.json"
        if not (os.path.exists(index_path) and os.path.exists(meta_path)):
            return
        self._index = self._faiss.read_index(index_path)
        with open(meta_path) as f:
            data = json.load(f)
        self._id_to_meta = {int(k): v for k, v in data["id_to_meta"].items()}
        self._next_int_id = data["next_int_id"]
        self._chunk_id_to_int = {v["chunk_id"]: int(k) for k, v in self._id_to_meta.items()}


def get_vector_store(backend: str, path: str, dimensions: int) -> VectorStore:
    """Factory used by app.vectorstore.factory -- kept here to avoid a
    circular import between the faiss and numpy modules."""
    if backend == "faiss":
        return FaissVectorStore(path, dimensions)
    from app.vectorstore.numpy_store import NumpyVectorStore
    return NumpyVectorStore(path)
