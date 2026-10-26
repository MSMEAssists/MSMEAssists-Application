"""
Central configuration, loaded from environment variables.
No hard-coded model names / DB paths anywhere else in the codebase --
everything routes through Settings.
"""
import os
from dataclasses import dataclass, field


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    # --- Storage ---
    # Metadata DB. Default: local sqlite file (zero-install, works anywhere).
    # In production this can be swapped for MongoDB by implementing the same
    # Repository interface in app/db/mongo_repository.py.
    db_backend: str = os.getenv("DB_BACKEND", "sqlite")  # "sqlite" | "mongodb"
    sqlite_path: str = os.getenv("SQLITE_PATH", "./data/gov_rag.db")
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db_name: str = os.getenv("MONGODB_DB_NAME", "gov_rag")
    source_documents_path: str = os.getenv("SOURCE_DOCUMENTS_PATH", "./data/source_documents")

    # --- Vector store ---
    vector_store_backend: str = os.getenv("VECTOR_STORE_BACKEND", "numpy")  # "numpy" | "faiss" | "qdrant" | "pgvector"
    vector_store_path: str = os.getenv("VECTOR_STORE_PATH", "./data/vector_store")

    # --- Embeddings ---
    # "tfidf_svd" works fully offline with no model download (sklearn only).
    # "sentence_transformers" is supported when that package + model weights
    # are available in the deployment environment.
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "tfidf_svd")
    embedding_model_name: str = os.getenv("EMBEDDING_MODEL_NAME", "tfidf-svd-256")
    embedding_dimensions: int = _env_int("EMBEDDING_DIMENSIONS", 256)

    # --- Chunking ---
    chunk_size: int = _env_int("CHUNK_SIZE", 900)          # characters
    chunk_overlap: int = _env_int("CHUNK_OVERLAP", 150)    # characters

    # --- Retrieval ---
    default_top_k: int = _env_int("DEFAULT_TOP_K", 5)
    similarity_threshold: float = _env_float("SIMILARITY_THRESHOLD", 0.15)
    hybrid_retrieval_enabled: bool = _env_bool("HYBRID_RETRIEVAL_ENABLED", True)
    hybrid_dense_weight: float = _env_float("HYBRID_DENSE_WEIGHT", 0.35)
    hybrid_lexical_weight: float = _env_float("HYBRID_LEXICAL_WEIGHT", 0.65)
    hybrid_exact_boost_weight: float = _env_float("HYBRID_EXACT_BOOST_WEIGHT", 0.25)

    # --- HTTP / collection ---
    request_timeout_seconds: int = _env_int("REQUEST_TIMEOUT_SECONDS", 20)
    user_agent: str = os.getenv(
        "USER_AGENT", "GovInfoRAGBot/1.0 (+standalone-government-knowledge-rag)"
    )
    max_pages_per_source_per_run: int = _env_int("MAX_PAGES_PER_SOURCE_PER_RUN", 50)

    # --- LLM (answer generation) ---
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
    llm_api_key_env_var: str = os.getenv("LLM_API_KEY_ENV_VAR", "ANTHROPIC_API_KEY")

    # --- Admin auth (only for the RAG admin endpoints) ---
    admin_auth_enabled: bool = _env_bool("ADMIN_AUTH_ENABLED", False)
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "")

    # --- Automated Periodic Scheduler ---
    auto_ingestion_enabled: bool = _env_bool("AUTO_INGESTION_ENABLED", True)
    auto_ingestion_interval_hours: int = _env_int("AUTO_INGESTION_INTERVAL_HOURS", 24)
    auto_ingestion_max_pages: int = _env_int("AUTO_INGESTION_MAX_PAGES", 50)
    auto_ingestion_run_on_startup: bool = _env_bool("AUTO_INGESTION_RUN_ON_STARTUP", False)
    auto_ingestion_startup_grace_seconds: int = _env_int("AUTO_INGESTION_STARTUP_GRACE_SECONDS", 10)

    # --- Government Source Discovery ---
    discovery_enabled: bool = _env_bool("DISCOVERY_ENABLED", True)
    allowed_gov_suffixes: str = os.getenv("ALLOWED_GOV_SUFFIXES", ".gov.in,.nic.in")
    allowed_gov_domains: str = os.getenv(
        "ALLOWED_GOV_DOMAINS",
        "sidbi.in,cgtmse.in,mudra.org.in,standupmitra.in,udyamregistration.gov.in",
    )
    discovery_max_urls_per_source: int = _env_int("DISCOVERY_MAX_URLS_PER_SOURCE", 100)
    discovery_max_sources_per_run: int = _env_int("DISCOVERY_MAX_SOURCES_PER_RUN", 10)
    discovery_crawl_delay_seconds: float = _env_float("DISCOVERY_CRAWL_DELAY_SECONDS", 0.5)
    discovery_max_sitemap_depth: int = _env_int("DISCOVERY_MAX_SITEMAP_DEPTH", 2)
    discovery_respect_robots_txt: bool = _env_bool("DISCOVERY_RESPECT_ROBOTS_TXT", True)

    # --- Server & CORS ---
    api_port: int = _env_int("API_PORT", 8001)
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8000")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def allowed_gov_suffixes_list(self) -> list[str]:
        return [s.strip().lower() for s in self.allowed_gov_suffixes.split(",") if s.strip()]

    @property
    def allowed_gov_domains_list(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_gov_domains.split(",") if d.strip()]


settings = Settings()
