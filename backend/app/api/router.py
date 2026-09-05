"""Aggregate API router. Individual route modules are included here."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, chat, documents, health, rag

api_router = APIRouter()
api_router.include_router(health.router, prefix="")
api_router.include_router(auth.router, prefix="")
api_router.include_router(chat.router, prefix="")
api_router.include_router(rag.router, prefix="")
api_router.include_router(documents.router, prefix="")
