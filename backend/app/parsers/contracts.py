"""Document parsing contracts and data structures.

This module defines provider-agnostic interfaces and data structures
for document parsing. Business logic should depend only on these abstractions.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedPage:
    """A single page or logical unit from a parsed document.

    Attributes:
        page_number: Page number (1-based for PDFs, 1 for single-page text files).
        text: Extracted text content from this page.
        metadata: Optional page-specific metadata.
    """
    page_number: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedDocument:
    """Result of parsing a document.

    Attributes:
        text: Complete document text (all pages merged in order).
        pages: Tuple of individual pages in original order.
        metadata: Document-level metadata (filename, parser, encoding, etc.).
    """
    text: str
    pages: tuple[ParsedPage, ...]
    metadata: dict[str, Any]


class DocumentParseError(Exception):
    """Base exception for document parsing errors."""
    pass


class UnsupportedDocumentTypeError(DocumentParseError):
    """Document type is not supported."""
    pass


class EmptyDocumentError(DocumentParseError):
    """Document is empty or contains only whitespace."""
    pass


class TextDecodingError(DocumentParseError):
    """Text decoding failed (invalid encoding)."""
    pass


class CorruptPdfError(DocumentParseError):
    """PDF file is corrupted or malformed."""
    pass


class EncryptedPdfError(DocumentParseError):
    """PDF file is encrypted and cannot be read."""
    pass


class PdfTextNotFoundError(DocumentParseError):
    """PDF has no extractable text layer (possibly scanned image)."""
    pass


class DocumentTooLargeError(DocumentParseError):
    """Document exceeds maximum size limit."""
    pass


class DocumentParser(ABC):
    """Abstract interface for document parsers.

    Implementations must:
    - Parse from bytes (not file paths)
    - Return ParsedDocument with ordered pages
    - Raise specific exceptions for different error cases
    - Not access database, network, or filesystem
    - Not call embedding services
    """

    @abstractmethod
    def parse(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        """Parse document from bytes.

        Args:
            content: Raw file content as bytes.
            filename: Original filename (for type detection and metadata only).
            mime_type: Optional MIME type hint.

        Returns:
            ParsedDocument with text, pages, and metadata.

        Raises:
            EmptyDocumentError: Document is empty or whitespace-only.
            DocumentTooLargeError: Content exceeds size limit.
            TextDecodingError: Text encoding is invalid.
            CorruptPdfError: PDF is malformed.
            EncryptedPdfError: PDF is encrypted.
            PdfTextNotFoundError: PDF has no text layer.
            DocumentParseError: Other parsing errors.
        """
        raise NotImplementedError
