"""PDF file parser implementation."""
from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.parsers.contracts import (
    CorruptPdfError,
    DocumentParser,
    DocumentTooLargeError,
    EmptyDocumentError,
    EncryptedPdfError,
    ParsedDocument,
    ParsedPage,
    PdfTextNotFoundError,
)


class PdfParser(DocumentParser):
    """Parser for PDF files.

    Extracts text from text-based PDFs.
    Does not support OCR for scanned documents.
    """

    def __init__(
        self,
        max_size_bytes: int = 50 * 1024 * 1024,
        max_pages: int = 1000,
    ):
        """Initialize PDF parser.

        Args:
            max_size_bytes: Maximum file size in bytes (default: 50MB).
            max_pages: Maximum number of pages (default: 1000).
        """
        self._max_size = max_size_bytes
        self._max_pages = max_pages

    def parse(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        """Parse PDF file.

        Args:
            content: Raw file bytes.
            filename: Original filename.
            mime_type: Optional MIME type.

        Returns:
            ParsedDocument with pages in order.

        Raises:
            EmptyDocumentError: File is empty.
            DocumentTooLargeError: File or page count exceeds limits.
            CorruptPdfError: PDF is malformed.
            EncryptedPdfError: PDF is encrypted.
            PdfTextNotFoundError: PDF has no text layer (possibly scanned).
        """
        if not content:
            raise EmptyDocumentError("File is empty")

        if len(content) > self._max_size:
            raise DocumentTooLargeError(
                f"File size {len(content)} bytes exceeds limit {self._max_size} bytes"
            )

        # Basic PDF signature check
        if not content.startswith(b'%PDF-'):
            raise CorruptPdfError("Invalid PDF signature")

        # Parse PDF from bytes
        try:
            pdf_stream = io.BytesIO(content)
            reader = PdfReader(pdf_stream)
        except PdfReadError as e:
            raise CorruptPdfError(f"Failed to read PDF: {str(e)}")
        except Exception as e:
            raise CorruptPdfError(f"Unexpected error reading PDF: {type(e).__name__}")

        # Check encryption
        if reader.is_encrypted:
            # Try empty password
            try:
                if not reader.decrypt(""):
                    raise EncryptedPdfError("PDF is encrypted and requires a password")
            except Exception:
                raise EncryptedPdfError("PDF is encrypted and cannot be read")

        # Get page count
        page_count = len(reader.pages)

        if page_count == 0:
            raise EmptyDocumentError("PDF has no pages")

        if page_count > self._max_pages:
            raise DocumentTooLargeError(
                f"PDF has {page_count} pages, exceeds limit {self._max_pages}"
            )

        # Extract text from each page
        pages: list[ParsedPage] = []
        total_text_parts: list[str] = []
        has_any_text = False

        for page_num in range(page_count):
            try:
                page = reader.pages[page_num]
                page_text = page.extract_text() or ""
            except Exception as e:
                # Single page extraction failure should fail the entire document
                # to avoid silently indexing incomplete content
                raise CorruptPdfError(
                    f"Failed to extract text from page {page_num + 1}: {type(e).__name__}"
                ) from e

            # Normalize line endings and clean up
            page_text = page_text.replace('\r\n', '\n').replace('\r', '\n')
            page_text = page_text.strip()

            # Check if this page has meaningful text
            if page_text and page_text.strip():
                has_any_text = True

            # Create page object (even if empty, to preserve page numbers)
            parsed_page = ParsedPage(
                page_number=page_num + 1,  # 1-based
                text=page_text,
                metadata={},
            )
            pages.append(parsed_page)

            # Add to full text with page separator
            if page_text:
                total_text_parts.append(page_text)

        # Check if any text was found
        if not has_any_text:
            raise PdfTextNotFoundError(
                "PDF has no extractable text layer. "
                "This may be a scanned document that requires OCR."
            )

        # Merge all pages with double newline separator
        full_text = '\n\n'.join(total_text_parts)

        metadata = {
            'filename': filename,
            'parser': 'PdfParser',
            'mime_type': mime_type or 'application/pdf',
            'page_count': page_count,
            'character_count': len(full_text),
            'possibly_scanned': not has_any_text,
            'encrypted': reader.is_encrypted,
        }

        return ParsedDocument(
            text=full_text,
            pages=tuple(pages),
            metadata=metadata,
        )
