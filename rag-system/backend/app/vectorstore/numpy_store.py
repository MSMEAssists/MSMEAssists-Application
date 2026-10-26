"""
Pure numpy VectorStore implementation. This is the default backend because
it requires no extra install (faiss is not always available in restricted
environments) while implementing the exact same VectorStore interface as
the FAISS-backed store -- so switching backends is a one-line config change,
never a code change in retrieval/ingestion.

Suitable for small-to-medium corpora (a few hundred thousand chunks); for
larger corpora, configure VECTOR_STORE_BACKEND=faiss or qdrant/pgvector.
"""
import json
import os
from typing import Dict, List, Optional

import numpy as np

from app.vectorstore.base import VectorRecord, VectorSearchHit, VectorStore


class NumpyVectorStore(VectorStore):
    def __init__(self, path: str):
        self.path = path
        self._chunk_ids: List[str] = []
        self._document_ids: List[str] = []
        self._source_ids: List[str] = []
        self._knowledge_types: List[str] = []
        self._matrix: Optional[np.ndarray] = None
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def upsert(self, records: List[VectorRecord]) -> None:
        if not records:
            return
        # Remove any existing rows with the same chunk_id (true upsert).
        incoming_ids = {r.chunk_id for r in records}
        if self._matrix is not None:
            keep_mask = [cid not in incoming_ids for cid in self._chunk_ids]
            self._chunk_ids = [c for c, k in zip(self._chunk_ids, keep_mask) if k]
            self._document_ids = [c for c, k in zip(self._document_ids, keep_mask) if k]
            self._source_ids = [c for c, k in zip(self._source_ids, keep_mask) if k]
            self._knowledge_types = [c for c, k in zip(self._knowledge_types, keep_mask) if k]
            self._matrix = self._matrix[keep_mask] if any(keep_mask) else None

        new_vectors = np.array([r.vector for r in records], dtype=np.float32)
        if self._matrix is None:
            self._matrix = new_vectors
        else:
            self._matrix = np.vstack([self._matrix, new_vectors])

        for r in records:
            self._chunk_ids.append(r.chunk_id)
            self._document_ids.append(r.document_id)
            self._source_ids.append(r.source_id)
            self._knowledge_types.append(r.knowledge_type)

    def delete(self, chunk_ids: List[str]) -> None:
        if self._matrix is None:
            return
        remove = set(chunk_ids)
        keep_mask = [cid not in remove for cid in self._chunk_ids]
        self._chunk_ids = [c for c, k in zip(self._chunk_ids, keep_mask) if k]
        self._document_ids = [c for c, k in zip(self._document_ids, keep_mask) if k]
        self._source_ids = [c for c, k in zip(self._source_ids, keep_mask) if k]
        self._knowledge_types = [c for c, k in zip(self._knowledge_types, keep_mask) if k]
        self._matrix = self._matrix[keep_mask] if any(keep_mask) else None

    def search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[VectorSearchHit]:
        if self._matrix is None or len(self._chunk_ids) == 0:
            return []

        candidate_idx = list(range(len(self._chunk_ids)))
        if filters:
            def keep(i):
                if "source_id" in filters and self._source_ids[i] != filters["source_id"]:
                    return False
                if "knowledge_type" in filters and self._knowledge_types[i] != filters["knowledge_type"]:
                    return False
                return True
            candidate_idx = [i for i in candidate_idx if keep(i)]

        if not candidate_idx:
            return []

        q = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm

        sub_matrix = self._matrix[candidate_idx]
        row_norms = np.linalg.norm(sub_matrix, axis=1)
        row_norms[row_norms == 0] = 1.0
        sims = (sub_matrix @ q) / row_norms

        order = np.argsort(-sims)[:top_k]
        hits = []
        for rank in order:
            i = candidate_idx[rank]
            hits.append(
                VectorSearchHit(
                    chunk_id=self._chunk_ids[i],
                    document_id=self._document_ids[i],
                    source_id=self._source_ids[i],
                    knowledge_type=self._knowledge_types[i],
                    score=float(sims[rank]),
                )
            )
        return hits

    def count(self) -> int:
        return len(self._chunk_ids)

    def persist(self) -> None:
        np.save(self.path + ".vectors.npy", self._matrix if self._matrix is not None else np.zeros((0, 0)))
        meta = {
            "chunk_ids": self._chunk_ids,
            "document_ids": self._document_ids,
            "source_ids": self._source_ids,
            "knowledge_types": self._knowledge_types,
        }
        with open(self.path + ".meta.json", "w") as f:
            json.dump(meta, f)

    def load(self) -> None:
        vec_path = self.path + ".vectors.npy"
        meta_path = self.path + ".meta.json"
        if not (os.path.exists(vec_path) and os.path.exists(meta_path)):
            return
        matrix = np.load(vec_path)
        self._matrix = matrix if matrix.size > 0 else None
        with open(meta_path) as f:
            meta = json.load(f)
        self._chunk_ids = meta["chunk_ids"]
        self._document_ids = meta["document_ids"]
        self._source_ids = meta["source_ids"]
        self._knowledge_types = meta["knowledge_types"]
