"""Parser registry for selecting appropriate document parser."""
from __future__ import annotations

from pathlib import Path

from app.parsers.contracts import (
    DocumentParser,
    UnsupportedDocumentTypeError,
)
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.pdf_parser import PdfParser
from app.parsers.text_parser import TextParser


class ParserRegistry:
    """Registry for selecting document parsers based on file type.

    Supports:
    - .txt (text/plain)
    - .md, .markdown (text/markdown, text/plain)
    - .pdf (application/pdf)
    """

    def __init__(
        self,
        max_text_size: int = 10 * 1024 * 1024,
        max_pdf_size: int = 50 * 1024 * 1024,
        max_pdf_pages: int = 1000,
    ):
        """Initialize parser registry.

        Args:
            max_text_size: Max size for text/markdown files (default: 10MB).
            max_pdf_size: Max size for PDF files (default: 50MB).
            max_pdf_pages: Max pages for PDF files (default: 1000).
        """
        self._text_parser = TextParser(max_size_bytes=max_text_size)
        self._markdown_parser = MarkdownParser(max_size_bytes=max_text_size)
        self._pdf_parser = PdfParser(
            max_size_bytes=max_pdf_size,
            max_pages=max_pdf_pages,
        )

        # Extension to parser mapping
        self._extension_map = {
            '.txt': self._text_parser,
            '.md': self._markdown_parser,
            '.markdown': self._markdown_parser,
            '.pdf': self._pdf_parser,
        }

        # MIME type hints
        self._mime_to_extensions = {
            'text/plain': {'.txt', '.md', '.markdown'},
            'text/markdown': {'.md', '.markdown'},
            'application/pdf': {'.pdf'},
        }

    def get_parser(
        self,
        filename: str,
        mime_type: str | None = None,
        content: bytes | None = None,
    ) -> DocumentParser:
        """Select appropriate parser for the file.

        Args:
            filename: Original filename.
            mime_type: Optional MIME type hint.
            content: Optional file content for signature verification.

        Returns:
            DocumentParser instance.

        Raises:
            UnsupportedDocumentTypeError: File type not supported or conflict detected.
        """
        # Extract and normalize extension
        path = Path(filename)
        extension = path.suffix.lower()

        if not extension:
            raise UnsupportedDocumentTypeError(
                f"File '{filename}' has no extension"
            )

        # Check if extension is supported
        if extension not in self._extension_map:
            raise UnsupportedDocumentTypeError(
                f"File extension '{extension}' is not supported. "
                f"Supported: {', '.join(self._extension_map.keys())}"
            )

        # Validate MIME type if provided
        if mime_type:
            mime_type = mime_type.lower().split(';')[0].strip()

            # Check for obvious conflicts
            if mime_type in self._mime_to_extensions:
                expected_extensions = self._mime_to_extensions[mime_type]
                if extension not in expected_extensions:
                    # Allow text/plain for markdown (browser behavior)
                    if not (mime_type == 'text/plain' and extension in {'.md', '.markdown'}):
                        raise UnsupportedDocumentTypeError(
                            f"MIME type '{mime_type}' conflicts with extension '{extension}'"
                        )

        # For PDF, verify signature if content is provided
        if extension == '.pdf' and content:
            if not content.startswith(b'%PDF-'):
                raise UnsupportedDocumentTypeError(
                    f"File has .pdf extension but invalid PDF signature"
                )

        return self._extension_map[extension]


# Default registry instance
default_registry = ParserRegistry()


def parse_document(
    content: bytes,
    filename: str,
    mime_type: str | None = None,
) -> "ParsedDocument":  # noqa: F821
    """Convenience function to parse document using default registry.

    Args:
        content: File content as bytes.
        filename: Original filename.
        mime_type: Optional MIME type.

    Returns:
        ParsedDocument.

    Raises:
        UnsupportedDocumentTypeError: File type not supported.
        DocumentParseError: Parsing failed.
    """
    parser = default_registry.get_parser(filename, mime_type, content)
    return parser.parse(content, filename, mime_type)
