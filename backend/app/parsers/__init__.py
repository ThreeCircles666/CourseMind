"""Document parsing module.

Provides unified interface for parsing various document formats:
- Plain text (.txt)
- Markdown (.md, .markdown)
- PDF (.pdf)

Usage:
    from app.parsers import parse_document

    content = b"Hello world"
    result = parse_document(content, "file.txt")
    print(result.text)
    print(result.pages[0].text)
"""
from app.parsers.contracts import (
    CorruptPdfError,
    DocumentParseError,
    DocumentParser,
    DocumentTooLargeError,
    EmptyDocumentError,
    EncryptedPdfError,
    ParsedDocument,
    ParsedPage,
    PdfTextNotFoundError,
    TextDecodingError,
    UnsupportedDocumentTypeError,
)
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.pdf_parser import PdfParser
from app.parsers.registry import ParserRegistry, default_registry, parse_document
from app.parsers.text_parser import TextParser

__all__ = [
    # Main function
    "parse_document",
    # Data structures
    "ParsedDocument",
    "ParsedPage",
    # Parsers
    "DocumentParser",
    "TextParser",
    "MarkdownParser",
    "PdfParser",
    # Registry
    "ParserRegistry",
    "default_registry",
    # Exceptions
    "DocumentParseError",
    "UnsupportedDocumentTypeError",
    "EmptyDocumentError",
    "TextDecodingError",
    "CorruptPdfError",
    "EncryptedPdfError",
    "PdfTextNotFoundError",
    "DocumentTooLargeError",
]
