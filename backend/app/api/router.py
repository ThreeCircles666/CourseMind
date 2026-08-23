"""Aggregate API router. Individual route modules are included here."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
