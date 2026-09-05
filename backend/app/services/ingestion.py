"""Document ingestion service for RAG pipeline.

Coordinates parsing, chunking, embedding, and storage of document content.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.chunking import DocumentChunker, Chunk
from app.ai.embedding_contracts import EmbeddingProvider, EmbeddingResult
from app.models import Document, ProcessingJob, DocumentChunk, EMBEDDING_DIMENSION
from app.parsers import ParserRegistry, ParsedDocument
from app.services.dtos import IngestionResult

logger = logging.getLogger(__name__)

# Protected document that must not be modified
PROTECTED_DOCUMENT_ID = UUID("d42818a8-089c-404f-a3a0-aca970098f11")


class IngestionError(Exception):
    """Base exception for ingestion errors."""
    pass


class DocumentNotFoundError(IngestionError):
    """Document does not exist."""
    pass


class DocumentAlreadyProcessingError(IngestionError):
    """Document is already being processed."""
    pass


class ProtectedDocumentError(IngestionError):
    """Attempted to modify protected document."""
    pass


class ValidationError(IngestionError):
    """Data validation failed."""
    pass


async def ingest_document(
    *,
    session: Session,
    document_id: UUID,
    content: bytes,
    filename: str,
    mime_type: str,
    parser_registry: ParserRegistry,
    chunker: DocumentChunker,
    embedding_provider: EmbeddingProvider,
) -> IngestionResult:
    """Ingest a document: parse, chunk, embed, and store.

    Args:
        session: Database session
        document_id: Existing document UUID
        content: Raw file content
        filename: Original filename
        mime_type: MIME type
        parser_registry: Parser registry
        chunker: Text chunker
        embedding_provider: Embedding provider

    Returns:
        IngestionResult with processing details

    Raises:
        DocumentNotFoundError: Document doesn't exist
        DocumentAlreadyProcessingError: Document is being processed
        ProtectedDocumentError: Attempted to modify protected document
        ValidationError: Data validation failed
        IngestionError: Other ingestion errors
    """
    # Check protected document
    if document_id == PROTECTED_DOCUMENT_ID:
        raise ProtectedDocumentError(
            f"Document {document_id} is protected and cannot be modified"
        )

    # Phase A: Short transaction - atomically claim processing rights
    # Use UPDATE with condition to prevent race conditions
    from sqlalchemy import update

    # Atomic conditional update
    stmt = (
        update(Document)
        .where(
            Document.id == document_id,
            Document.status != "processing"
        )
        .values(status="processing", error_message=None)
        .returning(Document.id)
    )

    result = session.execute(stmt)
    updated_id = result.scalar()

    if not updated_id:
        # Either document doesn't exist or is already processing
        doc = session.get(Document, document_id)
        if not doc:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        else:
            raise DocumentAlreadyProcessingError(
                f"Document {document_id} is already being processed"
            )

    # Create processing job
    job = ProcessingJob(
        document_id=document_id,
        status="processing",
        started_at=datetime.now(timezone.utc),
    )
    session.add(job)

    session.commit()
    session.refresh(job)
    job_id = job.id

    logger.info(
        f"Started ingestion job {job_id} for document {document_id}",
        extra={"document_id": str(document_id), "job_id": str(job_id)}
    )

    try:
        # Phase B: Parse, chunk, and embed (outside transaction)
        parsed_doc, chunks, embedding_result = await _process_content(
            content=content,
            filename=filename,
            mime_type=mime_type,
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=embedding_provider,
        )

        # Phase C: Write chunks in transaction
        chunk_count = _write_chunks(
            session=session,
            document_id=document_id,
            chunks=chunks,
            embeddings=embedding_result.vectors,
            embedding_model=embedding_result.model,
        )

        # Mark success
        doc = session.get(Document, document_id)
        doc.status = "succeeded"
        doc.error_message = None

        job = session.get(ProcessingJob, job_id)
        job.status = "succeeded"
        job.finished_at = datetime.now(timezone.utc)

        session.commit()

        logger.info(
            f"Completed ingestion job {job_id}: {chunk_count} chunks",
            extra={
                "document_id": str(document_id),
                "job_id": str(job_id),
                "chunk_count": chunk_count,
            }
        )

        return IngestionResult(
            document_id=document_id,
            job_id=job_id,
            chunk_count=chunk_count,
            embedding_model=embedding_result.model,
            embedding_dimension=embedding_result.dimension,
        )

    except Exception as e:
        # Phase D: Update failure status in new transaction
        session.rollback()

        try:
            doc = session.get(Document, document_id)
            doc.status = "failed"
            # Safe error summary - no sensitive data
            error_type = type(e).__name__
            error_msg = str(e)[:200]  # Truncate
            doc.error_message = f"{error_type}: {error_msg}"

            job = session.get(ProcessingJob, job_id)
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)

            session.commit()

            logger.error(
                f"Failed ingestion job {job_id}: {error_type}",
                extra={
                    "document_id": str(document_id),
                    "job_id": str(job_id),
                    "error": error_type,
                },
                exc_info=True
            )
        except Exception as update_error:
            logger.error(
                f"Failed to update failure status: {update_error}",
                extra={"document_id": str(document_id), "job_id": str(job_id)},
            )

        # Re-raise original error
        raise IngestionError(f"Ingestion failed: {type(e).__name__}") from e


async def _process_content(
    *,
    content: bytes,
    filename: str,
    mime_type: str,
    parser_registry: ParserRegistry,
    chunker: DocumentChunker,
    embedding_provider: EmbeddingProvider,
) -> tuple[ParsedDocument, list[Chunk], EmbeddingResult]:
    """Process content: parse, chunk, and embed.

    This phase runs outside database transaction to avoid holding locks
    during remote API calls.
    """
    # Parse
    parser = parser_registry.get_parser(filename, mime_type, content)
    parsed_doc = parser.parse(content, filename, mime_type)

    if not parsed_doc.text:
        raise ValidationError("Parsed document is empty")

    # Chunk
    chunks = chunker.chunk(parsed_doc)

    if not chunks:
        raise ValidationError("No chunks generated")

    # Validate chunks
    _validate_chunks(chunks, parsed_doc)

    # Embed
    texts = [chunk.text for chunk in chunks]
    embedding_result = await embedding_provider.embed(texts)

    # Validate embeddings
    _validate_embeddings(
        embeddings=embedding_result.vectors,
        expected_count=len(chunks),
        expected_model=embedding_provider.model_name,
        provider_model=embedding_result.model,
        provider_dimension=embedding_result.dimension,
    )

    return parsed_doc, chunks, embedding_result


def _validate_chunks(chunks: list[Chunk], parsed_doc: ParsedDocument) -> None:
    """Validate chunk data before database write."""
    # Check continuity
    for i, chunk in enumerate(chunks):
        if chunk.index != i:
            raise ValidationError(
                f"Chunk indices not continuous: expected {i}, got {chunk.index}"
            )

        if not chunk.text or not chunk.text.strip():
            raise ValidationError(f"Chunk {i} has empty text")

        if chunk.start_char < 0:
            raise ValidationError(f"Chunk {i} has negative start_char")

        if chunk.end_char <= chunk.start_char:
            raise ValidationError(
                f"Chunk {i} has invalid range: {chunk.start_char}:{chunk.end_char}"
            )

        # Verify offset matches document
        expected = parsed_doc.text[chunk.start_char:chunk.end_char]
        if chunk.text != expected:
            raise ValidationError(
                f"Chunk {i} text doesn't match document offset"
            )


def _validate_embeddings(
    *,
    embeddings: list[list[float]],
    expected_count: int,
    expected_model: str,
    provider_model: str,
    provider_dimension: int,
) -> None:
    """Validate embeddings before database write."""
    if len(embeddings) != expected_count:
        raise ValidationError(
            f"Embedding count mismatch: expected {expected_count}, got {len(embeddings)}"
        )

    if provider_model != expected_model:
        raise ValidationError(
            f"Model mismatch: expected {expected_model}, got {provider_model}"
        )

    if provider_dimension != EMBEDDING_DIMENSION:
        raise ValidationError(
            f"Dimension mismatch: expected {EMBEDDING_DIMENSION}, got {provider_dimension}"
        )

    for i, embedding in enumerate(embeddings):
        if len(embedding) != EMBEDDING_DIMENSION:
            raise ValidationError(
                f"Embedding {i} has wrong dimension: {len(embedding)}"
            )

        # Check for invalid values
        for j, val in enumerate(embedding):
            if not isinstance(val, (int, float)):
                raise ValidationError(f"Embedding {i}[{j}] is not numeric")

            import math
            if math.isnan(val):
                raise ValidationError(f"Embedding {i}[{j}] is NaN")

            if math.isinf(val):
                raise ValidationError(f"Embedding {i}[{j}] is infinite")

        # Check for zero vector
        if all(v == 0.0 for v in embedding):
            raise ValidationError(f"Embedding {i} is zero vector")


def _write_chunks(
    *,
    session: Session,
    document_id: UUID,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    embedding_model: str,
) -> int:
    """Write chunks to database in a transaction.

    Uses atomic replace strategy:
    1. Delete old chunks for this document+model
    2. Insert new chunks

    If insert fails, transaction rolls back and old chunks remain.
    """
    # Delete old chunks for this document and model
    delete_stmt = delete(DocumentChunk).where(
        DocumentChunk.document_id == document_id,
        DocumentChunk.embedding_model == embedding_model,
    )
    session.execute(delete_stmt)

    # Prepare new chunks
    new_chunks = []
    for chunk, embedding in zip(chunks, embeddings):
        db_chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk.index,
            content=chunk.text,
            page_number=chunk.page_number,
            title_path=list(chunk.title_path),
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            embedding_model=embedding_model,
            embedding_dimension=EMBEDDING_DIMENSION,
            embedding=embedding,
            chunk_metadata=chunk.metadata or {},
        )
        new_chunks.append(db_chunk)

    # Batch insert
    session.add_all(new_chunks)
    session.flush()  # Force write to check constraints

    return len(new_chunks)
