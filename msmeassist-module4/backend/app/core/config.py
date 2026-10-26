"""
Core settings for Module 4: Finance & Loan Agent.
Values are loaded from .env; all fields have safe defaults so the module
runs out-of-the-box without a populated .env file.
"""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FinanceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MSMEAssist Finance & Loan Agent"
    environment: str = "development"
    debug: bool = True

    # Server
    module_port: int = 8004

    # Financial analysis thresholds
    default_monthly_expense_ratio: float = 0.75   # 75 % of revenue when expenses not provided
    min_dscr_acceptable: float = 1.25
    target_dscr_healthy: float = 2.0

    # Upstream service URLs
    rag_service_url: str = "http://localhost:8001"
    rag_top_k: int = 6
    module3_service_url: str = "http://localhost:8002"
    module1_service_url: str = "http://localhost:8000"


@lru_cache()
def get_finance_settings() -> FinanceSettings:
    return FinanceSettings()
