"""Application settings, loaded from the environment with `REVYN_` prefixed keys."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REVYN_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Persistence
    database_url: str = "sqlite+aiosqlite:///./revyn.db"
    db_echo: bool = False
    redis_url: str | None = None

    # LLM. Revyn degrades to a deterministic reasoning provider when unavailable.
    llm_enabled: bool = True
    llm_model: str = "claude-opus-5"
    llm_effort: Literal["low", "medium", "high", "xhigh", "max"] = "low"
    llm_max_tokens: int = 4096
    llm_timeout_seconds: float = 45.0
    # Server-side rescue if a request is declined by a safety classifier.
    llm_fallback_model: str = "claude-opus-4-8"
    # Cap narrative refinement per scan cycle: the top opportunities get it, the rest
    # fall back to the deterministic path.
    llm_max_events_per_scan: int = 5
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Payment gateway
    gateway: Literal["simulator", "razorpay"] = "simulator"
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None
    razorpay_base_url: str = "https://api.razorpay.com/v1"
    gateway_timeout_seconds: float = 15.0

    # Orchestrator
    scheduler_enabled: bool = True
    scheduler_interval_seconds: float = 10.0
    # Demo dial: compresses journey wait times so a 6-hour follow-up lands in seconds.
    clock_speedup: float = 120.0
    max_actions_per_tick: int = 25

    # Synthetic data
    seed: int = 20260901
    synthetic_transactions: int = 10_000
    synthetic_customers: int = 1_400

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def llm_available(self) -> bool:
        return self.llm_enabled and bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
