"""RAG (Retrieval-Augmented Generation) service schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RagAskRequest(BaseModel):
    """Request schema for RAG question answering."""

    question: str = Field(..., description="User question to answer")
    document_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="List of document UUIDs to search within (must provide at least one)"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top chunks to retrieve"
    )
    min_similarity: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Minimum cosine similarity threshold (optional). Server enforces a minimum of RAG_MIN_SIMILARITY."
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate question is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        if len(v) > 2000:
            raise ValueError("Question too long (max 2000 characters)")
        return v

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, v: list[UUID]) -> list[UUID]:
        """Deduplicate document IDs while preserving order."""
        seen = set()
        result = []
        for doc_id in v:
            if doc_id not in seen:
                seen.add(doc_id)
                result.append(doc_id)
        return result


class RagSource(BaseModel):
    """Source reference for a RAG answer."""

    source_id: str = Field(..., description="Source reference ID (e.g., S1, S2)")
    chunk_id: UUID = Field(..., description="Document chunk UUID")
    document_id: UUID = Field(..., description="Document UUID")
    file_name: str = Field(..., description="Original filename")
    chunk_index: int = Field(..., description="Chunk index within document")
    page_number: int | None = Field(None, description="Page number if available")
    title_path: list[str] = Field(default_factory=list, description="Heading hierarchy")
    similarity: float = Field(..., description="Cosine similarity score")
    excerpt: str = Field(..., description="Content excerpt from chunk")


class RagAskResponse(BaseModel):
    """Response schema for RAG question answering."""

    answer: str = Field(..., description="Generated answer based on documents")
    sources: list[RagSource] = Field(
        default_factory=list,
        description="Source references used in the answer"
    )
    model: str | None = Field(None, description="Chat model used (null if insufficient context)")
    insufficient_context: bool = Field(
        default=False,
        description="Whether documents were insufficient to answer"
    )
