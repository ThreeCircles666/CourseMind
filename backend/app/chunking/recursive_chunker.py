"""Recursive character-based chunking implementation."""
from __future__ import annotations

import re
from typing import Callable

from app.chunking.contracts import (
    Chunk,
    DocumentChunker,
    InvalidChunkConfigurationError,
)
from app.parsers.contracts import ParsedDocument


# Type alias for length functions
LengthFunction = Callable[[str], int]


class RecursiveCharacterChunker(DocumentChunker):
    """Recursive character-based chunking with natural boundaries.

    Splits text hierarchically using separators in priority order:
    1. Page boundaries (for PDFs)
    2. Markdown headings (for Markdown)
    3. Double newlines (paragraphs)
    4. Single newlines
    5. Chinese sentence endings
    6. English sentence endings
    7. Spaces
    8. Character-level hard split

    Uses character count as length unit (not tokens).
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 80,
        separators: tuple[str, ...] | None = None,
        length_function: LengthFunction | None = None,
        respect_page_boundaries: bool = True,
    ):
        """Initialize recursive character chunker.

        Args:
            chunk_size: Target maximum characters per chunk.
            chunk_overlap: Characters to overlap between chunks.
            separators: Ordered list of split boundaries (None for default).
            length_function: Custom length function (None for len()).
            respect_page_boundaries: Don't split across pages for PDFs.

        Raises:
            InvalidChunkConfigurationError: Invalid configuration.
        """
        # Validate configuration
        if chunk_size <= 0:
            raise InvalidChunkConfigurationError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise InvalidChunkConfigurationError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise InvalidChunkConfigurationError("chunk_overlap must be less than chunk_size")

        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._length_function = length_function or len
        self._respect_pages = respect_page_boundaries

        # Default separators in priority order
        if separators is None:
            separators = (
                "\n\n",  # Paragraphs
                "\n",    # Lines
                "。",    # Chinese period
                "！",    # Chinese exclamation
                "？",    # Chinese question
                ". ",    # English sentence (with space)
                "! ",    # English exclamation
                "? ",    # English question
                " ",     # Spaces
                "",      # Character-level
            )

        if not separators:
            raise InvalidChunkConfigurationError("separators cannot be empty")

        self._separators = separators

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """Split document into chunks.

        Args:
            document: Parsed document.

        Returns:
            List of chunks with sequential indices.
        """
        if not document.text or not document.text.strip():
            return []

        chunks: list[Chunk] = []

        # Extract Markdown headings if available
        headings = document.metadata.get('headings', [])

        if self._respect_pages and len(document.pages) > 1:
            # Process each page separately for PDFs
            chunks = self._chunk_by_pages(document, headings)
        else:
            # Process entire document
            chunks = self._chunk_text(
                text=document.text,
                start_offset=0,
                page_number=document.pages[0].page_number if document.pages else 1,
                headings=headings,
                start_index=0,
            )

        return chunks

    def _chunk_by_pages(
        self,
        document: ParsedDocument,
        headings: list[dict],
    ) -> list[Chunk]:
        """Chunk document page by page.

        Args:
            document: Parsed document.
            headings: Markdown headings metadata.

        Returns:
            List of chunks.
        """
        all_chunks: list[Chunk] = []
        current_offset = 0
        chunk_index = 0

        for page in document.pages:
            if not page.text or not page.text.strip():
                # Skip empty pages
                current_offset += len(page.text)
                continue

            # Chunk this page
            page_chunks = self._chunk_text(
                text=page.text,
                start_offset=current_offset,
                page_number=page.page_number,
                headings=headings,
                start_index=chunk_index,
            )

            all_chunks.extend(page_chunks)
            chunk_index += len(page_chunks)
            current_offset += len(page.text)

            # Account for page separator if using document.text
            # (pages are joined with '\n\n')
            if page != document.pages[-1]:
                current_offset += 2  # '\n\n'

        # Re-index to ensure continuity
        return [
            Chunk(
                index=i,
                text=chunk.text,
                page_number=chunk.page_number,
                title_path=chunk.title_path,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                metadata=chunk.metadata,
            )
            for i, chunk in enumerate(all_chunks)
        ]

    def _chunk_text(
        self,
        text: str,
        start_offset: int,
        page_number: int,
        headings: list[dict],
        start_index: int,
    ) -> list[Chunk]:
        """Recursively chunk text using separators.

        Args:
            text: Text to chunk.
            start_offset: Global character offset in document.
            page_number: Page number for these chunks.
            headings: Markdown headings with positions.
            start_index: Starting chunk index.

        Returns:
            List of chunks.
        """
        chunks: list[Chunk] = []

        # Build heading position map for this text scope
        heading_map = self._build_heading_map(text, headings, start_offset)

        # Split with overlap
        splits = self._split_text_with_overlap(text)

        for i, (chunk_text, local_start, local_end) in enumerate(splits):
            global_start = start_offset + local_start

            # Determine title path for this chunk position
            title_path = self._get_title_path_at_position(global_start, heading_map)

            chunk = Chunk(
                index=start_index + i,
                text=chunk_text,
                page_number=page_number,
                title_path=title_path,
                start_char=global_start,
                end_char=start_offset + local_end,
                metadata={
                    'length': self._length_function(chunk_text),
                },
            )
            chunks.append(chunk)

        return chunks

    def _build_heading_map(
        self,
        text: str,
        headings: list[dict],
        start_offset: int,
    ) -> list[tuple[int, int, str]]:
        """Build map of heading positions in text.

        Args:
            text: Text to scan.
            headings: Heading metadata from parser.
            start_offset: Global offset of this text.

        Returns:
            List of (position, level, title) sorted by position.
        """
        heading_positions: list[tuple[int, int, str]] = []

        # Scan text for headings, avoiding code blocks
        in_code_block = False
        lines = text.split('\n')
        current_pos = 0

        for line in lines:
            # Track code block state
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                current_pos += len(line) + 1
                continue

            # Skip lines in code blocks
            if in_code_block:
                current_pos += len(line) + 1
                continue

            # Check for ATX heading
            stripped = line.strip()
            if stripped.startswith('#'):
                # Count heading level
                level = 0
                for char in stripped:
                    if char == '#':
                        level += 1
                    else:
                        break

                if level <= 6 and level < len(stripped) and stripped[level] == ' ':
                    # Valid heading
                    title = stripped[level + 1:].strip()
                    global_pos = start_offset + current_pos
                    heading_positions.append((global_pos, level, title))

            current_pos += len(line) + 1

        return sorted(heading_positions, key=lambda x: x[0])

    def _get_title_path_at_position(
        self,
        position: int,
        heading_map: list[tuple[int, int, str]],
    ) -> tuple[str, ...]:
        """Get active heading path at a given position.

        Args:
            position: Character position to check.
            heading_map: List of (position, level, title).

        Returns:
            Tuple of heading titles from top to current level.
        """
        if not heading_map:
            return ()

        # Find all headings before this position
        active_headings: list[tuple[int, str]] = []

        for head_pos, level, title in heading_map:
            if head_pos > position:
                break

            # Maintain heading stack
            # Remove deeper or same-level headings
            active_headings = [
                (l, t) for l, t in active_headings if l < level
            ]
            active_headings.append((level, title))

        # Return titles in order
        return tuple(t for _, t in active_headings)

    def _split_text_with_overlap(
        self,
        text: str,
    ) -> list[tuple[str, int, int]]:
        """Split text into chunks with overlap.

        Args:
            text: Text to split.

        Returns:
            List of (chunk_text, start_pos, end_pos) tuples.
        """
        if not text:
            return []

        text_length = self._length_function(text)

        if text_length <= self._chunk_size:
            # Text fits in one chunk
            return [(text, 0, len(text))]

        # Try splitting with separators
        return self._split_recursive(text, 0)

    def _split_recursive(
        self,
        text: str,
        depth: int,
    ) -> list[tuple[str, int, int]]:
        """Recursively split text using separators.

        Args:
            text: Text to split.
            depth: Current separator depth.

        Returns:
            List of (chunk_text, start_pos, end_pos) tuples.
        """
        if depth >= len(self._separators):
            # No more separators, force character split
            return self._hard_split(text)

        separator = self._separators[depth]

        if separator == "":
            # Character-level split
            return self._hard_split(text)

        # Split by current separator
        if separator not in text:
            # Try next separator
            return self._split_recursive(text, depth + 1)

        # Split and reassemble with separator preserved
        parts = text.split(separator)

        # Reconstruct with separator
        reconstructed_parts: list[str] = []
        for i, part in enumerate(parts):
            if i < len(parts) - 1:
                reconstructed_parts.append(part + separator)
            else:
                reconstructed_parts.append(part)

        # Merge parts into chunks
        return self._merge_parts(reconstructed_parts, depth)

    def _merge_parts(
        self,
        parts: list[str],
        depth: int,
    ) -> list[tuple[str, int, int]]:
        """Merge parts into chunks with overlap.

        Args:
            parts: Text parts to merge.
            depth: Current separator depth.

        Returns:
            List of (chunk_text, start_pos, end_pos) tuples.
        """
        chunks: list[tuple[str, int, int]] = []
        current_parts: list[str] = []
        current_start = 0
        current_pos = 0

        for part in parts:
            part_len = self._length_function(part)

            # Calculate what length would be if we add this part
            would_be = sum(self._length_function(p) for p in current_parts) + part_len

            if would_be <= self._chunk_size or not current_parts:
                # Add to current chunk
                current_parts.append(part)
            else:
                # Finalize current chunk
                chunk_text = "".join(current_parts)
                chunk_end = current_pos
                chunks.append((chunk_text, current_start, chunk_end))

                # Start new chunk with overlap
                # Find where the new chunk should actually start in the text
                overlap_chars = min(len(chunk_text), self._chunk_overlap)
                new_start = chunk_end - overlap_chars

                # If part itself is too large, split recursively
                if part_len > self._chunk_size:
                    sub_chunks = self._split_recursive(part, depth + 1)
                    for sub_text, sub_start, sub_end in sub_chunks:
                        chunks.append((sub_text, current_pos + sub_start, current_pos + sub_end))
                    current_pos += len(part)
                    current_parts = []
                    current_start = current_pos
                    continue

                # Start fresh with this part
                current_parts = [part]
                current_start = current_pos

            current_pos += len(part)

        # Add final chunk
        if current_parts:
            chunk_text = "".join(current_parts)
            chunks.append((chunk_text, current_start, current_pos))

        return chunks

    def _hard_split(self, text: str) -> list[tuple[str, int, int]]:
        """Hard split by character count.

        Args:
            text: Text to split.

        Returns:
            List of (chunk_text, start_pos, end_pos) tuples.
        """
        chunks: list[tuple[str, int, int]] = []
        start = 0

        while start < len(text):
            end = min(start + self._chunk_size, len(text))
            chunk_text = text[start:end]
            chunks.append((chunk_text, start, end))

            # Move forward, accounting for overlap
            start = max(start + 1, end - self._chunk_overlap)

            # Prevent infinite loop
            if start >= end:
                start = end

        return chunks
