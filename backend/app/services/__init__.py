"""Service layer for RAG pipeline."""
from app.services.dtos import IngestionResult, RetrievalHit
from app.services.ingestion import (
    ingest_document,
    IngestionError,
    DocumentNotFoundError,
    DocumentAlreadyProcessingError,
    ProtectedDocumentError,
    ValidationError,
    PROTECTED_DOCUMENT_ID,
)
from app.services.retrieval import (
    search,
    RetrievalError,
    InvalidQueryError,
)

__all__ = [
    # DTOs
    "IngestionResult",
    "RetrievalHit",
    # Ingestion
    "ingest_document",
    "IngestionError",
    "DocumentNotFoundError",
    "DocumentAlreadyProcessingError",
    "ProtectedDocumentError",
    "ValidationError",
    "PROTECTED_DOCUMENT_ID",
    # Retrieval
    "search",
    "RetrievalError",
    "InvalidQueryError",
]
