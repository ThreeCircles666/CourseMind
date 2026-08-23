"""Application configuration via Pydantic Settings.

All environment-driven configuration is centralized here so that values like
CORS origins and the database URL are not scattered across business code.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "courseguard-api"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    # Comma-separated list of allowed CORS origins.
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    # Database URL is configured for future use. It is intentionally NOT
    # connected on startup, so the API works without PostgreSQL running.
    database_url: str = Field(
        default="postgresql+psycopg://courseguard:courseguard_dev@localhost:5432/courseguard"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
