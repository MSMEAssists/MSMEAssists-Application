from app.core.config import settings
from app.vectorstore.base import VectorStore
from app.vectorstore.numpy_store import NumpyVectorStore


def build_vector_store(dimensions: int = None) -> VectorStore:
    dimensions = dimensions or settings.embedding_dimensions
    backend = settings.vector_store_backend

    if backend == "faiss":
        from app.vectorstore.faiss_store import FaissVectorStore
        store = FaissVectorStore(settings.vector_store_path, dimensions)
    elif backend == "numpy":
        store = NumpyVectorStore(settings.vector_store_path)
    elif backend in ("qdrant", "pgvector"):
        raise NotImplementedError(
            f"'{backend}' backend is not yet implemented in this prototype. "
            "Implement app/vectorstore/{backend}_store.py against the "
            "VectorStore interface in app/vectorstore/base.py -- no other "
            "code needs to change."
        )
    else:
        raise ValueError(f"Unknown VECTOR_STORE_BACKEND: {backend}")

    store.load()
    return store
