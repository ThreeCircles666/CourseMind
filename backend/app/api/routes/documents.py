"""Document management routes and background ingestion orchestration."""
from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.embedding_contracts import EmbeddingProvider
from app.ai.adapters.dashscope_embedding import DashScopeEmbeddingProvider
from app.api.dependencies import get_current_user
from app.chunking import RecursiveCharacterChunker
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.document import Document, ProcessingJob
from app.models.user import User
from app.parsers.registry import ParserRegistry
from app.schemas.documents import DocumentListResponse, DocumentResponse
from app.services.ingestion import ingest_document
from app.services.upload import (
    EmptyFileError,
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
    save_upload_file,
)

router = APIRouter(tags=["documents"])
logger = logging.getLogger(__name__)
SessionFactory = Callable[[], Session]
EmbeddingProviderFactory = Callable[[], EmbeddingProvider]


def get_upload_root() -> Path:
    return settings.get_upload_root_path()


def get_background_session_factory() -> SessionFactory:
    return SessionLocal


def get_embedding_provider() -> EmbeddingProvider:
    settings.validate_dashscope_key()
    return DashScopeEmbeddingProvider(
        api_key=settings.get_dashscope_key(),
        model=settings.embedding_model,
    )


def get_embedding_provider_factory() -> EmbeddingProviderFactory:
    """Return a lazy provider factory so authorization runs before setup."""
    return get_embedding_provider


def get_background_processor() -> Callable[..., object]:
    return process_document_background


def claim_document_reprocessing(
    db: Session, document_id: UUID, user_id: int
) -> Document | None:
    """Atomically move an owned failed document to pending."""
    updated_id = db.scalar(
        update(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == user_id)
        .where(Document.status == "failed")
        .values(status="pending", error_message=None)
        .returning(Document.id)
    )
    if updated_id is None:
        db.rollback()
        return None
    db.commit()
    return db.get(Document, updated_id)


def _cleanup_owned_upload(upload_root: Path, document_id: UUID) -> None:
    """Remove only the UUID directory created by the current request."""
    document_dir = upload_root / str(document_id)
    if document_dir.exists():
        shutil.rmtree(document_dir)


def _is_sha_unique_violation(error: IntegrityError) -> bool:
    """Recognize only the documents.sha256 uniqueness conflict."""
    original = getattr(error, "orig", None)
    constraint_name = getattr(getattr(original, "diag", None), "constraint_name", "")
    detail = str(original or error).lower()
    return (
        constraint_name in {"uq_documents_sha256", "uq_documents_user_sha256"}
        or ("sha256" in detail and ("unique" in detail or "duplicate" in detail))
    )


async def process_document_background(
    document_id: UUID,
    user_id: int,
    safe_name: str,
    session_factory: SessionFactory | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    upload_root: Path | None = None,
) -> None:
    """Process a committed document using a fresh session and saved bytes.

    Args:
        document_id: Document UUID to process
        user_id: Expected owner user ID (for verification)
        safe_name: Safe filename
        session_factory: Session factory
        embedding_provider: Embedding provider
        upload_root: Upload directory root
    """
    factory = session_factory or get_background_session_factory()
    session = factory()
    root = upload_root or get_upload_root()

    try:
        document = session.get(Document, document_id)
        if document is None:
            logger.error("Document %s not found in background task", document_id)
            return

        # Verify document belongs to expected user
        if document.user_id != user_id:
            logger.error(
                f"Document {document_id} owner mismatch: expected user {user_id}, "
                f"got {document.user_id}. Rejecting background processing."
            )
            return

        file_path = root / str(document_id) / safe_name
        try:
            file_path.resolve().relative_to(root.resolve())
        except ValueError:
            raise InvalidFileError("Invalid document storage path")

        if not file_path.is_file():
            document.status = "failed"
            document.error_message = "Stored document file is missing"
            session.commit()
            return

        content = file_path.read_bytes()
        provider = embedding_provider or get_embedding_provider()
        registry = ParserRegistry(
            max_text_size=settings.upload_text_max_bytes,
            max_pdf_size=settings.upload_pdf_max_bytes,
        )
        chunker = RecursiveCharacterChunker(chunk_size=800, chunk_overlap=100)

        await ingest_document(
            session=session,
            document_id=document_id,
            content=content,
            filename=document.original_name,
            mime_type=document.mime_type,
            parser_registry=registry,
            chunker=chunker,
            embedding_provider=provider,
        )
    except Exception as error:
        session.rollback()
        document = session.get(Document, document_id)
        if document is not None:
            document.status = "failed"
            document.error_message = f"{type(error).__name__}: {str(error)[:200]}"
            job = session.execute(
                select(ProcessingJob)
                .where(ProcessingJob.document_id == document_id)
                .order_by(ProcessingJob.created_at.desc())
            ).scalars().first()
            if job is not None and job.status not in {"succeeded", "failed"}:
                job.status = "failed"
            session.commit()
        logger.exception("Background processing failed for %s", document_id)
    finally:
        session.close()


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    upload_root: Path = Depends(get_upload_root),
    session_factory: SessionFactory = Depends(get_background_session_factory),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    background_processor: Callable[..., object] = Depends(get_background_processor),
) -> DocumentResponse:
    """Store an upload, deduplicate it, commit metadata, then enqueue ingestion."""
    document_id = uuid4()
    committed = False
    stored = False

    try:
        original_name, safe_name, size_bytes, sha256 = await save_upload_file(
            file,
            document_id,
            upload_root=upload_root,
        )
        stored = True

        existing = db.execute(
            select(Document)
            .where(Document.user_id == current_user.id)
            .where(Document.sha256 == sha256)
        ).scalar_one_or_none()
        if existing is not None:
            _cleanup_owned_upload(upload_root, document_id)
            response = DocumentResponse.model_validate(existing)
            response.duplicate = True
            return response

        mime_type = "application/pdf" if safe_name.lower().endswith(".pdf") else (
            "text/markdown" if safe_name.lower().endswith((".md", ".markdown")) else "text/plain"
        )
        document = Document(
            id=document_id,
            user_id=current_user.id,
            original_name=original_name,
            safe_name=safe_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            status="pending",
        )
        db.add(document)
        try:
            db.commit()
            db.refresh(document)
            committed = True
        except IntegrityError as error:
            db.rollback()
            if not _is_sha_unique_violation(error):
                raise
            winner = db.execute(
                select(Document)
                .where(Document.user_id == current_user.id)
                .where(Document.sha256 == sha256)
            ).scalar_one_or_none()
            if winner is None:
                raise
            _cleanup_owned_upload(upload_root, document_id)
            response = DocumentResponse.model_validate(winner)
            response.duplicate = True
            return response

        background_tasks.add_task(
            background_processor,
            document.id,
            current_user.id,
            safe_name,
            session_factory,
            embedding_provider,
            upload_root,
        )
        return DocumentResponse.model_validate(document)
    except EmptyFileError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except FileTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except UnsupportedFileTypeError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except InvalidFileError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        db.rollback()
        logger.exception("Document upload failed")
        raise HTTPException(status_code=500, detail="Upload failed") from error
    finally:
        if stored and not committed:
            _cleanup_owned_upload(upload_root, document_id)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    # Only show documents owned by current user
    total = db.scalar(
        select(func.count())
        .select_from(Document)
        .where(Document.user_id == current_user.id)
    ) or 0
    documents = db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(document) for document in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    document = db.execute(
        select(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == current_user.id)
    ).scalar_one_or_none()

    if document is None:
        # Return same 404 whether document doesn't exist or belongs to another user
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse.model_validate(document)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    upload_root: Path = Depends(get_upload_root),
) -> None:
    """Delete a document and its associated data.

    Only the document owner can delete it. Documents being processed cannot be deleted.
    Database cascades handle ProcessingJob and DocumentChunk cleanup.
    Disk files are removed after successful database commit.
    """
    # Query document with ownership check
    document = db.execute(
        select(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == current_user.id)
    ).scalar_one_or_none()

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if document is being processed
    if document.status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Document is currently being processed and cannot be deleted"
        )

    # Delete from database (cascades to processing_jobs and document_chunks)
    db.delete(document)
    try:
        db.commit()
    except Exception as error:
        db.rollback()
        logger.exception(
            "Failed to delete document metadata",
            extra={"document_id": str(document_id), "user_id": current_user.id},
        )
        raise HTTPException(status_code=500, detail="Document deletion failed") from error

    # After successful commit, clean up disk files
    document_dir = upload_root / str(document_id)

    # Validate path is within upload_root
    try:
        document_dir.resolve().relative_to(upload_root.resolve())
    except ValueError:
        logger.error(
            f"Document directory {document_id} outside upload root",
            extra={"document_id": str(document_id), "user_id": current_user.id}
        )
        return  # Database already deleted, just log and return

    # Remove directory if it exists
    if document_dir.exists() and document_dir.is_dir():
        try:
            shutil.rmtree(document_dir)
            logger.info(
                f"Deleted document {document_id} and files",
                extra={"document_id": str(document_id), "user_id": current_user.id}
            )
        except Exception as e:
            # Database is already committed, log error but don't fail request
            logger.error(
                f"Failed to delete files for document {document_id}: {type(e).__name__}",
                extra={"document_id": str(document_id), "user_id": current_user.id},
                exc_info=True
            )
    else:
        # File doesn't exist - not an error, just log
        logger.info(
            f"Deleted document {document_id} (files already absent)",
            extra={"document_id": str(document_id), "user_id": current_user.id}
        )


@router.post("/documents/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    upload_root: Path = Depends(get_upload_root),
    session_factory: SessionFactory = Depends(get_background_session_factory),
    embedding_provider_factory: EmbeddingProviderFactory = Depends(get_embedding_provider_factory),
    background_processor: Callable[..., object] = Depends(get_background_processor),
) -> DocumentResponse:
    """Reprocess a failed document.

    Only the document owner can reprocess. Only failed documents can be reprocessed.
    Successfully processed documents return 409 to prevent accidental expensive re-embedding.
    """
    # Authorization and cheap local validation intentionally precede provider setup.
    document = db.execute(
        select(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == current_user.id)
    ).scalar_one_or_none()

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Only allow reprocessing of failed documents
    if document.status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Document is already being processed"
        )

    if document.status == "succeeded":
        raise HTTPException(
            status_code=409,
            detail="Document has already been successfully processed"
        )

    if document.status == "pending":
        raise HTTPException(
            status_code=409,
            detail="Document is already queued for processing"
        )

    if document.status != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reprocess document with status: {document.status}"
        )

    # Check file exists
    document_dir = upload_root / str(document_id)
    file_path = document_dir / document.safe_name

    try:
        file_path.resolve().relative_to(upload_root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document storage path")

    if not file_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="Document file not found: cannot reprocess"
        )

    # Provider creation is deliberately lazy: unauthorized and invalid requests
    # never reach it, while a setup failure still leaves the document as failed.
    embedding_provider = embedding_provider_factory()

    updated_document = claim_document_reprocessing(db, document_id, current_user.id)

    if updated_document is None:
        # Another request already claimed this document
        raise HTTPException(
            status_code=409,
            detail="Document is already being processed"
        )

    # Schedule background processing
    background_tasks.add_task(
        background_processor,
        updated_document.id,
        current_user.id,
        updated_document.safe_name,
        session_factory,
        embedding_provider,
        upload_root,
    )

    return DocumentResponse.model_validate(updated_document)
