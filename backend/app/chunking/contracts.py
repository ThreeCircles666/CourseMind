"""Text chunking contracts and data structures.

This module defines provider-agnostic interfaces for text chunking.
Chunks are used for embedding-based retrieval.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.parsers.contracts import ParsedDocument


@dataclass(frozen=True)
class Chunk:
    """A single text chunk for embedding and retrieval.

    Attributes:
        index: Sequential index in document (0-based).
        text: Chunk content for embedding.
        page_number: Source page number (1-based for PDFs, 1 for text files).
        title_path: Markdown heading hierarchy (empty for non-markdown).
        start_char: Start position in ParsedDocument.text (inclusive).
        end_char: End position in ParsedDocument.text (exclusive).
        metadata: Optional chunk-specific metadata.
    """
    index: int
    text: str
    page_number: int | None
    title_path: tuple[str, ...]
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)


class InvalidChunkConfigurationError(ValueError):
    """Invalid chunking configuration."""
    pass


class DocumentChunker(ABC):
    """Abstract interface for document chunking.

    Implementations must:
    - Not access database, network, or embedding services
    - Produce non-empty chunks
    - Not exceed configured size limits
    - Maintain correct offsets relative to ParsedDocument.text
    - Preserve content (no silent loss)
    """

    @abstractmethod
    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """Split document into chunks.

        Args:
            document: Parsed document with text and pages.

        Returns:
            List of chunks with sequential indices.

        Raises:
            InvalidChunkConfigurationError: Invalid configuration.
            ValueError: Invalid input document.
        """
        raise NotImplementedError
