"""Chat request and response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for chat stream endpoint."""

    message: str = Field(..., min_length=1, description="User message to send to the model")


class ChatStreamEvent(BaseModel):
    """Single event in the chat stream."""

    type: str = Field(..., description="Event type: 'content', 'done', or 'error'")
    content: str = Field(default="", description="Text content for 'content' type events")
    error: str = Field(default="", description="Error message for 'error' type events")
