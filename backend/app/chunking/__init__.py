"""Text chunking module.

Provides text chunking for RAG applications:
- Character-based chunking with natural boundaries
- Markdown heading hierarchy tracking
- PDF page boundary preservation
- Configurable chunk size and overlap

Usage:
    from app.chunking import RecursiveCharacterChunker
    from app.parsers import parse_document

    doc = parse_document(content, "file.md")
    chunker = RecursiveCharacterChunker(chunk_size=800, chunk_overlap=100)
    chunks = chunker.chunk(doc)
"""
from app.chunking.contracts import (
    Chunk,
    DocumentChunker,
    InvalidChunkConfigurationError,
)
from app.chunking.recursive_chunker import RecursiveCharacterChunker

__all__ = [
    "Chunk",
    "DocumentChunker",
    "RecursiveCharacterChunker",
    "InvalidChunkConfigurationError",
]
