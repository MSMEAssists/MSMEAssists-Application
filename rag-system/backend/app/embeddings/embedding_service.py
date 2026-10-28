"""
Embedding service abstraction.

The rest of the pipeline only ever calls `EmbeddingService.embed(texts)`.
The concrete provider is fully configurable (app.core.config.settings) and
never hard-coded elsewhere.

Two providers are implemented:

  - "tfidf_svd": TF-IDF + truncated SVD (LSI). Pure scikit-learn/numpy,
     no model download, works fully offline. This is the default so the
     system is runnable out-of-the-box in network-restricted environments.

  - "sentence_transformers": wraps a sentence-transformers model when that
     package and model weights are available in the deployment
     environment. Recommended for production semantic quality.

Adding a new provider means adding one class here and registering it in
`_PROVIDERS` -- nothing else in the codebase changes.
"""
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

import numpy as np

from app.core.config import settings


@dataclass
class EmbeddingResult:
    vectors: List[List[float]]
    model_name: str
    model_version: str
    dimensions: int


class BaseEmbeddingProvider(ABC):
    name: str = "base"

    @abstractmethod
    def fit(self, corpus: List[str]) -> None:
        """Fit/calibrate the provider on a representative corpus (only
        meaningful for corpus-fitted providers like tfidf_svd; a no-op for
        pretrained providers)."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        ...


class TfidfSvdEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, offline embedding provider: TF-IDF vectors reduced
    with truncated SVD to a fixed dimensionality. Must be `fit()` on a
    corpus (typically all chunks in the current ingestion batch, or an
    existing corpus loaded from the vector store) before `embed()` is
    meaningful for semantic similarity."""

    name = "tfidf_svd"

    def __init__(self, dimensions: int = 256):
        import pickle
        from pathlib import Path
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD

        self._dimensions = dimensions
        self._vectorizer = TfidfVectorizer(
            max_features=20000, ngram_range=(1, 2), stop_words="english"
        )
        self._svd = TruncatedSVD(n_components=min(dimensions, 256), random_state=42)
        self._fitted = False
        self._model_path = Path(settings.sqlite_path).parent / "tfidf_svd_model.pkl"

        if self._model_path.exists():
            try:
                with open(self._model_path, "rb") as f:
                    saved = pickle.load(f)
                    if saved.get("svd") and saved["svd"].n_components == min(dimensions, 256):
                        self._vectorizer = saved["vectorizer"]
                        self._svd = saved["svd"]
                        self._fitted = True
            except Exception:
                pass

    def fit(self, corpus: List[str]) -> None:
        if not corpus:
            return
        if self._fitted and self._model_path.exists():
            return
        import pickle
        tfidf = self._vectorizer.fit_transform(corpus)
        n_components = min(self._svd.n_components, max(1, min(tfidf.shape) - 1))
        if n_components != self._svd.n_components:
            from sklearn.decomposition import TruncatedSVD
            self._svd = TruncatedSVD(n_components=n_components, random_state=42)
        self._svd.fit(tfidf)
        self._fitted = True
        try:
            with open(self._model_path, "wb") as f:
                pickle.dump(
                    {"vectorizer": self._vectorizer, "svd": self._svd},
                    f,
                    protocol=pickle.HIGHEST_PROTOCOL,
                )
        except Exception:
            pass

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not self._fitted:
            # Fall back to fitting on this batch so embed() never hard-fails.
            self.fit(texts)
        tfidf = self._vectorizer.transform(texts)
        reduced = self._svd.transform(tfidf)
        # L2-normalize so cosine similarity == dot product. Texts with (near)
        # zero vocabulary overlap with the fitted corpus produce a (near)
        # zero vector pre-normalization -- normalizing THAT would blow tiny
        # numerical noise up into an arbitrary unit-length direction that
        # can spuriously look similar to real content. Guard with an
        # epsilon: below it, leave the vector at zero (correctly scores ~0
        # similarity against everything) rather than fabricating a direction.
        norms = np.linalg.norm(reduced, axis=1, keepdims=True)
        significant = norms > 1e-6
        safe_norms = np.where(significant, norms, 1.0)
        reduced = np.where(significant, reduced / safe_norms, 0.0)
        # Pad to configured dimensions if SVD produced fewer components.
        if reduced.shape[1] < self._dimensions:
            pad = np.zeros((reduced.shape[0], self._dimensions - reduced.shape[1]))
            reduced = np.hstack([reduced, pad])
        return reduced.tolist()

    @property
    def dimensions(self) -> int:
        return self._dimensions


class SentenceTransformersEmbeddingProvider(BaseEmbeddingProvider):
    """Wraps sentence-transformers when available in the deployment env."""

    name = "sentence_transformers"

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # optional dep
        self._model = SentenceTransformer(model_name)
        self._dimensions = self._model.get_sentence_embedding_dimension()

    def fit(self, corpus: List[str]) -> None:
        pass  # pretrained model; no fitting needed

    def embed(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    @property
    def dimensions(self) -> int:
        return self._dimensions


_PROVIDERS = {
    "tfidf_svd": TfidfSvdEmbeddingProvider,
    "sentence_transformers": SentenceTransformersEmbeddingProvider,
}


class EmbeddingService:
    def __init__(self, provider_name: str = None, model_name: str = None, dimensions: int = None):
        provider_name = provider_name or settings.embedding_provider
        dimensions = dimensions or settings.embedding_dimensions
        model_name = model_name or settings.embedding_model_name

        if provider_name not in _PROVIDERS:
            raise ValueError(f"Unknown embedding provider: {provider_name}")

        if provider_name == "sentence_transformers":
            self._provider = SentenceTransformersEmbeddingProvider(model_name)
        else:
            self._provider = TfidfSvdEmbeddingProvider(dimensions)

        self.model_name = model_name
        self.model_version = hashlib.md5(provider_name.encode()).hexdigest()[:8]

    def fit(self, corpus: List[str]) -> None:
        self._provider.fit(corpus)

    def embed(self, texts: List[str]) -> EmbeddingResult:
        vectors = self._provider.embed(texts)
        return EmbeddingResult(
            vectors=vectors,
            model_name=self.model_name,
            model_version=self.model_version,
            dimensions=self._provider.dimensions,
        )

    @property
    def dimensions(self) -> int:
        return self._provider.dimensions
