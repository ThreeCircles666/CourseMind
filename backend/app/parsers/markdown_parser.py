"""Markdown file parser implementation."""
from __future__ import annotations

import re

from app.parsers.contracts import (
    DocumentParser,
    EmptyDocumentError,
    ParsedDocument,
    ParsedPage,
    TextDecodingError,
)


class MarkdownParser(DocumentParser):
    """Parser for Markdown files (.md, .markdown).

    Preserves structure and extracts heading metadata.
    Does not render HTML or execute scripts.
    """

    def __init__(self, max_size_bytes: int = 10 * 1024 * 1024):
        """Initialize markdown parser.

        Args:
            max_size_bytes: Maximum file size in bytes (default: 10MB).
        """
        self._max_size = max_size_bytes
        # ATX heading pattern: # Heading
        self._heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    def parse(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> ParsedDocument:
        """Parse Markdown file.

        Args:
            content: Raw file bytes.
            filename: Original filename.
            mime_type: Optional MIME type.

        Returns:
            ParsedDocument with single logical page and heading metadata.

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

        # Decode as UTF-8
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as e:
            raise TextDecodingError(
                f"Failed to decode as UTF-8: {e.reason} at position {e.start}"
            )

        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Remove trailing whitespace
        text = text.rstrip()

        # Check for empty content
        if not text or not text.strip():
            raise EmptyDocumentError("File contains only whitespace")

        # Extract headings (avoid extracting from code blocks)
        headings = self._extract_headings(text)

        # Create single logical page
        page = ParsedPage(
            page_number=1,
            text=text,
            metadata={'headings': headings},
        )

        metadata = {
            'filename': filename,
            'parser': 'MarkdownParser',
            'encoding': 'utf-8',
            'page_count': 1,
            'character_count': len(text),
            'mime_type': mime_type or 'text/markdown',
            'headings': headings,
            'heading_count': len(headings),
        }

        return ParsedDocument(
            text=text,
            pages=(page,),
            metadata=metadata,
        )

    def _extract_headings(self, text: str) -> list[dict[str, Any]]:
        """Extract ATX-style headings from markdown text.

        Avoids extracting from code blocks.

        Args:
            text: Markdown text.

        Returns:
            List of heading dicts with 'level' and 'text'.
        """
        from typing import Any

        headings: list[dict[str, Any]] = []

        # Simple heuristic: skip lines inside fenced code blocks
        in_code_block = False
        lines = text.split('\n')

        for line in lines:
            # Toggle code block state
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue

            # Skip lines inside code blocks
            if in_code_block:
                continue

            # Try to match heading
            match = self._heading_pattern.match(line)
            if match:
                level = len(match.group(1))  # Count #
                heading_text = match.group(2).strip()
                headings.append({
                    'level': level,
                    'text': heading_text,
                })

        return headings
