"""Health check route.

Returns a static status payload. This endpoint MUST NOT depend on the
database so it works even when PostgreSQL is not running.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
    )
