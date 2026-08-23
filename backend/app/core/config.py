"""
Application settings.

All configuration is read from environment variables (see /.env.example).
Nothing here should be hardcoded — this is the single seam that makes the
app deployable across dev / staging / production without code changes.
"""
from functools import lru_cache
from typing import List, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "MSMEAssist Module 1"
    api_prefix: str = "/api"

    # --- Database ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "msmeassist_dev"

    # --- Auth / JWT ---
    jwt_secret_key: str = Field(..., description="Signing key for JWT access tokens")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    password_hash_scheme: Literal["bcrypt", "argon2"] = "bcrypt"

    # --- CORS ---
    allowed_origins: str = "http://localhost:5173"

    # --- Document storage ---
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_path: str = "./storage/documents"
    max_upload_size_mb: int = 10

    # --- S3-compatible storage ---
    s3_bucket_name: str = ""
    s3_region: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_endpoint_url: str = ""

    # --- Module 2 integration ---
    module_2_allowed: bool = True

    # --- Logging ---
    log_level: str = "INFO"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> "Settings":
    """Cached settings accessor — read once per process."""
    return Settings()
