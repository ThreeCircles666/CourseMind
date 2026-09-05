"""Application configuration via Pydantic Settings.

All environment-driven configuration is centralized here so that values like
CORS origins and the database URL are not scattered across business code.
"""
from __future__ import annotations

import os
from pathlib import Path

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
        default="postgresql+psycopg://coursemind:coursemind_dev@127.0.0.1:5432/coursemind"
    )

    jwt_secret_key: str = Field(default="")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)
    refresh_cookie_name: str = "coursemind_refresh"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # DashScope API Key for Qwen model access.
    # MUST be set via environment variable, never hardcode.
    dashscope_api_key: str = Field(default="")

    # Embedding configuration
    embedding_provider: str = Field(default="dashscope")
    embedding_model: str = Field(default="text-embedding-v3")
    embedding_timeout_seconds: float = Field(default=60.0, ge=1.0, le=300.0)
    embedding_max_retries: int = Field(default=3, ge=1, le=10)
    embedding_trust_env: bool = Field(default=True)

    # RAG configuration
    rag_min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)
    rag_chat_model: str = Field(default="qwen3.8-flash")
    rag_max_context_chars: int = Field(default=12000, ge=1000, le=50000)
    rag_max_excerpt_chars: int = Field(default=300, ge=50, le=1000)

    # File upload configuration
    upload_root: str = Field(default="data/uploads")
    upload_text_max_bytes: int = Field(default=10 * 1024 * 1024)
    upload_pdf_max_bytes: int = Field(default=50 * 1024 * 1024)
    upload_max_bytes: int = Field(default=50 * 1024 * 1024)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def get_upload_root_path(self) -> Path:
        """Return the upload root, resolving relative paths from ``backend``."""
        backend_dir = Path(__file__).resolve().parents[2]
        return (backend_dir / self.upload_root).resolve()

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

    def validate_auth_config(self) -> None:
        if not self.jwt_secret_key:
            raise RuntimeError("JWT_SECRET_KEY is required. Set it in backend/.env.")
        if len(self.jwt_secret_key) < 32:
            raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters.")
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise RuntimeError("COOKIE_SAMESITE must be lax, strict, or none.")


settings = Settings()
