"""Document chunk model for text embeddings and vector search."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import VECTOR

from app.db.base import Base

# Fixed embedding dimension from DashScope text-embedding-v3
EMBEDDING_DIMENSION = 1024


class DocumentChunk(Base):
    """Represents a text chunk with its embedding vector.

    Each chunk is a slice of a document's text content with:
    - Sequential index within the document
    - Original text content
    - Page number (if applicable)
    - Markdown heading hierarchy (title path)
    - Character offsets in the source document
    - Embedding vector for semantic search
    - Model metadata for version tracking
    """

    __tablename__ = "document_chunks"

    # Primary key: UUID
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )

    # Foreign key to document with CASCADE delete
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Chunk sequence and content
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Document structure
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    title_path: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="'{}'",
    )

    # Character offsets (half-open interval [start_char, end_char))
    start_char: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    end_char: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Embedding metadata
    embedding_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    embedding_dimension: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Vector embedding (1024 dimensions for text-embedding-v3)
    embedding: Mapped[list[float]] = mapped_column(
        VECTOR(EMBEDDING_DIMENSION),
        nullable=False,
    )

    # Additional metadata (JSONB for flexible storage)
    chunk_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default="'{}'::jsonb",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="document_chunks",
    )

    # Constraints and indexes
    __table_args__ = (
        # Check constraints
        CheckConstraint(
            "chunk_index >= 0",
            name="ck_document_chunks_chunk_index_nonnegative",
        ),
        CheckConstraint(
            "length(btrim(content)) > 0",
            name="ck_document_chunks_content_nonempty",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_document_chunks_page_number_positive",
        ),
        CheckConstraint(
            "start_char >= 0",
            name="ck_document_chunks_start_char_nonnegative",
        ),
        CheckConstraint(
            "end_char > start_char",
            name="ck_document_chunks_char_range_valid",
        ),
        CheckConstraint(
            f"embedding_dimension = {EMBEDDING_DIMENSION}",
            name="ck_document_chunks_embedding_dimension",
        ),
        # Unique constraint: one chunk per (document, index, model)
        Index(
            "uq_document_chunks_document_index_model",
            "document_id",
            "chunk_index",
            "embedding_model",
            unique=True,
        ),
        # Query index for lookups
        Index(
            "ix_document_chunks_document_model",
            "document_id",
            "embedding_model",
        ),
    )
