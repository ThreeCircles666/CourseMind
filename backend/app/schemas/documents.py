"""Document management schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Response schema for document."""

    id: UUID
    original_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    status: Literal["pending", "processing", "succeeded", "failed"]
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    duplicate: bool = False

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Response schema for document list."""

    documents: list[DocumentResponse]
    total: int
    limit: int
    offset: int
