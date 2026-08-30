"""Application configuration via Pydantic Settings.

All environment-driven configuration is centralized here so that values like
CORS origins and the database URL are not scattered across business code.
"""
from __future__ import annotations

import os

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

    # DashScope API Key for Qwen model access.
    # MUST be set via environment variable, never hardcode.
    dashscope_api_key: str = Field(default="")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_dashscope_key(self) -> None:
        """Validate that DashScope API key is configured.
        
        Raises:
            ValueError: If API key is not set.
        """
        key = self.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY", "")
        if not key:
            raise ValueError(
                "DashScope API key not configured. "
                "Please set DASHSCOPE_API_KEY environment variable."
            )

    def get_dashscope_key(self) -> str:
        """Get DashScope API key from settings or environment.
        
        Returns:
            str: The API key.
            
        Raises:
            ValueError: If API key is not set.
        """
        key = self.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY", "")
        if not key:
            raise ValueError(
                "DashScope API key not configured. "
                "Please set DASHSCOPE_API_KEY environment variable."
            )
        return key

    def is_dashscope_configured(self) -> bool:
        """Check if DashScope API key is configured without exposing the value."""
        key = self.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY", "")
        return bool(key)


settings = Settings()
