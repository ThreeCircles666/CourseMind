"""Chat request and response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for chat stream endpoint."""

    message: str = Field(..., min_length=1, description="User message to send to the model")
    session_id: int | None = Field(default=None, description="Optional session ID to continue existing conversation")


class ChatStreamEvent(BaseModel):
    """Single event in the chat stream."""

    type: str = Field(..., description="Event type: 'session', 'content', 'done', or 'error'")
    session_id: int | None = Field(default=None, description="Session ID (only in 'session' type events)")
    content: str = Field(default="", description="Text content for 'content' type events")
    error: str = Field(default="", description="Error message for 'error' type events")


class MessageResponse(BaseModel):
    """Individual message in a session."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Message creation timestamp")

    model_config = {"from_attributes": True}


class SessionSummary(BaseModel):
    """Summary of a chat session for list view."""

    id: int = Field(..., description="Session ID")
    title: str = Field(..., description="Session title")
    message_count: int = Field(..., description="Number of messages in session")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class SessionDetail(BaseModel):
    """Detailed view of a chat session with messages."""

    id: int = Field(..., description="Session ID")
    title: str = Field(..., description="Session title")
    model: str = Field(..., description="AI model used")
    messages: list[MessageResponse] = Field(default_factory=list, description="Messages in session")

    model_config = {"from_attributes": True}


class SessionRenameRequest(BaseModel):
    """Request to rename a session."""

    title: str = Field(..., min_length=1, max_length=200, description="New session title")
