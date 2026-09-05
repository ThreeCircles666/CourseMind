"""Data transfer objects for RAG pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class IngestionResult:
    """Result of document ingestion process."""

    document_id: UUID
    job_id: UUID
    chunk_count: int
    embedding_model: str
    embedding_dimension: int


@dataclass(frozen=True)
class RetrievalHit:
    """A single search result from vector retrieval."""

    chunk_id: UUID
    document_id: UUID
    file_name: str
    chunk_index: int
    content: str
    page_number: int | None
    title_path: tuple[str, ...]
    distance: float
    similarity: float
