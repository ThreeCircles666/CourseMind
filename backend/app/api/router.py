"""Aggregate API router. Individual route modules are included here."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, chat, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
