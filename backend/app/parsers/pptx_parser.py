"""PPTX text/table extraction for indexing; original visuals use LibreOffice/PDFium."""
from __future__ import annotations

import io
import zipfile

from pptx import Presentation

from app.parsers.contracts import DocumentParser, ParsedDocument, ParsedPage, DocumentParseError, DocumentTooLargeError


class PptxParser(DocumentParser):
    def __init__(self, max_size_bytes: int = 50 * 1024 * 1024, max_pages: int = 1000):
        self.max_size_bytes, self.max_pages = max_size_bytes, max_pages

    def parse(self, content: bytes, filename: str, mime_type: str | None = None) -> ParsedDocument:
        if len(content) > self.max_size_bytes:
            raise DocumentTooLargeError("PPTX exceeds file size limit")
        try:
            # Bound expanded archives before letting the XML reader allocate memory.
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if sum(i.file_size for i in archive.infolist()) > 200 * 1024 * 1024:
                    raise DocumentTooLargeError("Expanded PPTX exceeds 200 MB")
            slides = Presentation(io.BytesIO(content)).slides
            if not 0 < len(slides) <= self.max_pages:
                raise DocumentTooLargeError("PPTX exceeds slide count limit or is empty")
            pages = []
            for i, slide in enumerate(slides):
                parts: list[str] = []
                def read_shapes(shapes):
                    for shape in shapes:
                        if shape.has_text_frame:
                            parts.append(shape.text)
                        if shape.has_table:
                            parts.extend(" | ".join(cell.text for cell in row.cells) for row in shape.table.rows)
                        if hasattr(shape, "shapes"):
                            read_shapes(shape.shapes)
                read_shapes(slide.shapes)
                pages.append(ParsedPage(i + 1, "\n".join(parts), {}))
            if not any(p.text.strip() for p in pages):
                raise DocumentParseError("PPTX has no extractable text; use visual reading in Courseware Review")
            return ParsedDocument("\n\n".join(p.text for p in pages), tuple(pages),
                                  {"filename": filename, "page_count": len(pages), "parser": "PptxParser"})
        except DocumentParseError:
            raise
        except Exception as error:
            raise DocumentParseError("PPTX could not be parsed") from error
