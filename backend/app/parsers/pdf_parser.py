"""PDF file parser implementation."""
from __future__ import annotations

import io
import unicodedata

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
        
        # Check for CID font encoding issues
        _check_cid_encoding(full_text, filename)
        _check_pdf_text_quality(full_text, filename)

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


def _check_cid_encoding(text: str, filename: str) -> None:
    """Check if extracted text contains excessive CID references.
    
    CID (Character ID) references like "(cid:123)" indicate font encoding issues
    where the PDF uses custom fonts that prevent text extraction.
    
    Args:
        text: Extracted text to check
        filename: Filename for error message
        
    Raises:
        PdfTextNotFoundError: If text quality is too poor due to CID encoding
    """
    # Count CID occurrences
    cid_count = text.count("(cid:")

    if len(text) < 200 and cid_count < 5:
        # Text too short to reliably detect unless CID noise dominates.
        return
    
    # Rule 1: Absolute count threshold
    if cid_count >= 20:
        raise PdfTextNotFoundError(
            f"PDF text extraction failed: the file may use custom font encoding or scanned pages. "
            f"Found {cid_count} font encoding errors. Please use a text-selectable PDF."
        )
    
    # Rule 2: Ratio threshold for shorter documents
    if cid_count > 0:
        # Calculate ratio of CID characters to total text
        # Each "(cid:123)" is roughly 10 chars, estimate total CID content
        cid_chars = cid_count * 10
        ratio = cid_chars / len(text)
        
        # If CID content is >15% of document, consider it unusable
        if ratio > 0.15:
            raise PdfTextNotFoundError(
                f"PDF text extraction failed: the file may use custom font encoding or scanned pages. "
                f"Text quality too poor for indexing. Please use a text-selectable PDF."
            )


def _check_pdf_text_quality(text: str, filename: str) -> None:
    """Reject text that was technically extracted but is mostly font-encoding noise."""
    visible_chars = [char for char in text if not char.isspace()]
    if len(visible_chars) < 500:
        return

    suspicious_count = 0
    for char in visible_chars:
        category = unicodedata.category(char)
        is_private_or_unknown = category in {"Co", "Cn"}
        is_cjk_extension = "\u3400" <= char <= "\u4dbf" or "\U00020000" <= char <= "\U0002EBEF"
        is_symbol_noise = category == "So"
        if is_private_or_unknown or is_cjk_extension or is_symbol_noise:
            suspicious_count += 1

    suspicious_ratio = suspicious_count / len(visible_chars)
    if suspicious_ratio > 0.2:
        raise PdfTextNotFoundError(
            "PDF text extraction failed: the extracted text appears unreadable due to "
            "custom font encoding or scanned pages. Please use a text-selectable PDF."
        )
