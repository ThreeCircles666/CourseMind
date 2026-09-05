"""Document retrieval service for RAG pipeline.

Provides semantic search over document chunks using vector similarity.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embedding_contracts import EmbeddingProvider
from app.models import Document, DocumentChunk, EMBEDDING_DIMENSION
from app.services.dtos import RetrievalHit

logger = logging.getLogger(__name__)


class RetrievalError(Exception):
    """Base exception for retrieval errors."""
    pass


class InvalidQueryError(RetrievalError):
    """Query validation failed."""
    pass


async def search(
    *,
    session: Session,
    embedding_provider: EmbeddingProvider,
    question: str,
    top_k: int = 5,
    min_similarity: float | None = None,
    document_ids: list[UUID] | None = None,
    current_user_id: int,
) -> list[RetrievalHit]:
    """Search for relevant document chunks using semantic similarity.

    Args:
        session: Database session
        embedding_provider: Embedding provider
        question: Search query
        top_k: Number of results to return (1-20)
        min_similarity: Minimum similarity threshold (0-1)
        document_ids: Optional whitelist of document IDs (None = no filter, [] = return empty)
        current_user_id: Current authenticated user ID (for access control)

    Returns:
        List of retrieval hits sorted by similarity (highest first)

    Raises:
        InvalidQueryError: Invalid query parameters
        RetrievalError: Other retrieval errors

    Note:
        Defense in depth: joins Document table and filters by user_id
        even if document_ids was pre-validated in the route layer.
    """
    # Validate inputs
    if not question or not question.strip():
        raise InvalidQueryError("Question cannot be empty")

    if len(question) > 10000:
        raise InvalidQueryError("Question too long (max 10000 characters)")

    if not (1 <= top_k <= 20):
        raise InvalidQueryError("top_k must be between 1 and 20")

    if min_similarity is not None and not (0 <= min_similarity <= 1):
        raise InvalidQueryError("min_similarity must be between 0 and 1")

    # Handle empty document_ids
    if document_ids is not None and len(document_ids) == 0:
        logger.info("Empty document_ids whitelist, returning no results")
        return []

    # Remove duplicates
    if document_ids is not None:
        document_ids = list(set(document_ids))

    # Generate query embedding
    try:
        embedding_result = await embedding_provider.embed([question])
    except Exception as e:
        raise RetrievalError(f"Failed to embed question: {e}") from e

    if len(embedding_result.vectors) != 1:
        raise RetrievalError(
            f"Expected 1 embedding, got {len(embedding_result.vectors)}"
        )

    query_vector = embedding_result.vectors[0]

    if len(query_vector) != EMBEDDING_DIMENSION:
        raise RetrievalError(
            f"Query embedding has wrong dimension: {len(query_vector)}"
        )

    if embedding_result.dimension != EMBEDDING_DIMENSION:
        raise RetrievalError(
            f"Provider reported wrong dimension: {embedding_result.dimension}"
        )

    # Query database
    # Join chunks with documents and filter by user_id (defense in depth)
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            Document.original_name,
            DocumentChunk.chunk_index,
            DocumentChunk.content,
            DocumentChunk.page_number,
            DocumentChunk.title_path,
            DocumentChunk.embedding.cosine_distance(query_vector).label('distance'),
        )
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(
            Document.status == 'succeeded',
            Document.user_id == current_user_id,  # Only user's own documents
            DocumentChunk.embedding_model == embedding_result.model,
        )
    )

    # Filter by document IDs if provided
    if document_ids is not None:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

    # Apply similarity threshold (as distance threshold)
    if min_similarity is not None:
        max_distance = 1.0 - min_similarity
        stmt = stmt.where(
            DocumentChunk.embedding.cosine_distance(query_vector) <= max_distance
        )

    # Order by distance (ascending = most similar first)
    stmt = stmt.order_by('distance').limit(top_k)

    # Execute query
    results = session.execute(stmt).all()

    # Convert to hits
    hits = []
    for row in results:
        chunk_id, doc_id, file_name, chunk_idx, content, page_num, title_path, distance = row

        # Convert distance to similarity
        similarity = 1.0 - distance

        hits.append(RetrievalHit(
            chunk_id=chunk_id,
            document_id=doc_id,
            file_name=file_name,
            chunk_index=chunk_idx,
            content=content,
            page_number=page_num,
            title_path=tuple(title_path),
            distance=float(distance),
            similarity=float(similarity),
        ))

    logger.info(
        f"Retrieved {len(hits)} chunks for query (top_k={top_k})",
        extra={
            "question_length": len(question),
            "top_k": top_k,
            "hits": len(hits),
        }
    )

    return hits
