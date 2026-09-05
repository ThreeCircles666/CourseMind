"""Text file parser implementation."""
from __future__ import annotations

from app.parsers.contracts import (
    DocumentParser,
    EmptyDocumentError,
    ParsedDocument,
    ParsedPage,
    TextDecodingError,
)


class TextParser(DocumentParser):
    """Parser for plain text files (.txt).

    Supports UTF-8 encoding with optional BOM.
    """

    def __init__(self, max_size_bytes: int = 10 * 1024 * 1024):
        """Initialize text parser.

        Args:
            max_size_bytes: Maximum file size in bytes (default: 10MB).
        """
        self._max_size = max_size_bytes

    def parse(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        """Parse plain text file.

        Args:
            content: Raw file bytes.
            filename: Original filename.
            mime_type: Optional MIME type.

        Returns:
            ParsedDocument with single logical page.

        Raises:
            EmptyDocumentError: File is empty or whitespace-only.
            TextDecodingError: Invalid UTF-8 encoding.
        """
        if not content:
            raise EmptyDocumentError("File is empty")

        if len(content) > self._max_size:
            from app.parsers.contracts import DocumentTooLargeError
            raise DocumentTooLargeError(
                f"File size {len(content)} bytes exceeds limit {self._max_size} bytes"
            )

        # Try UTF-8 decoding (strict)
        try:
            text = content.decode('utf-8-sig')  # Handles BOM automatically
        except UnicodeDecodeError as e:
            raise TextDecodingError(
                f"Failed to decode as UTF-8: {e.reason} at position {e.start}"
            )

        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Remove trailing whitespace but preserve internal structure
        text = text.rstrip()

        # Check for empty or whitespace-only content
        if not text or not text.strip():
            raise EmptyDocumentError("File contains only whitespace")

        # Create single logical page
        page = ParsedPage(
            page_number=1,
            text=text,
            metadata={},
        )

        metadata = {
            'filename': filename,
            'parser': 'TextParser',
            'encoding': 'utf-8',
            'page_count': 1,
            'character_count': len(text),
            'mime_type': mime_type or 'text/plain',
        }

        return ParsedDocument(
            text=text,
            pages=(page,),
            metadata=metadata,
        )
