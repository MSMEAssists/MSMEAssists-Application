"""
Application settings for Module 3 Explainable AI Recommendation Engine.
"""
from functools import lru_cache
from typing import List, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "MSMEAssist Module 3"
    api_prefix: str = "/api"
    module_port: int = 8002

    # Upstream integration endpoints
    module1_base_url: str = "http://localhost:8000"
    rag_base_url: str = "http://localhost:8000"

    # CORS
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    # Recommendation settings
    top_k_candidates: int = 5
    btl_max_iterations: int = 100
    btl_tolerance: float = 1e-6
    btl_smoothing: float = 0.01  # Laplace regularization weight for undefeated/unwon items

    # LLM Settings
    llm_provider: Literal["offline_analytical", "gemini", "anthropic", "openai"] = "offline_analytical"
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Logging
    log_level: str = "INFO"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
