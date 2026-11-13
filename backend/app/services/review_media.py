"""Local original-page rendering. No generated replicas of source slides."""
from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
import threading
import zipfile
from pathlib import Path

import pypdfium2 as pdfium
from pypdf import PdfReader

PDFIUM_LOCK = threading.Lock()  # PDFium is not thread-safe.


def document_pdf(path: Path, destination: Path) -> Path:
    if path.suffix.lower() == ".pdf":
        return path
    if path.suffix.lower() != ".pptx":
        raise ValueError("Original-page images require PDF or PPTX")
    with zipfile.ZipFile(path) as archive:
        if sum(entry.file_size for entry in archive.infolist()) > 200 * 1024 * 1024:
            raise ValueError("Expanded PPTX exceeds 200 MB")
    output = destination / "source.pdf"
    if output.exists():
        return output
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if not executable:
        raise ValueError("PPTX page rendering requires LibreOffice. Export the slides to PDF or install LibreOffice.")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        # Use a fresh filename and profile; simultaneous conversions cannot share state.
        shutil.copyfile(path, root / "slides.pptx")
        result = subprocess.run(
            [executable, f"-env:UserInstallation={(root / 'profile').as_uri()}",
             "--headless", "--convert-to", "pdf", "--outdir", str(root), str(root / "slides.pptx")],
            capture_output=True, timeout=120, check=False,
        )
        if result.returncode or not (root / "slides.pdf").is_file():
            raise ValueError("PPTX conversion failed; export the source slides to PDF and retry")
        shutil.copyfile(root / "slides.pdf", output)
    return output


def extract_pages(path: Path, destination: Path, max_pages: int) -> list[dict]:
    destination.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() not in {".pdf", ".pptx"}:
        from app.parsers.registry import ParserRegistry
        parser = ParserRegistry().get_parser(path.name)
        parsed = parser.parse(path.read_bytes(), path.name)
        return [{"number": page.page_number, "text": page.text, "has_image": False}
                for page in parsed.pages]
    pdf_path = document_pdf(path, destination)
    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs must be unlocked before review")
    if not 0 < len(reader.pages) <= max_pages:
        raise ValueError(f"Review supports 1–{max_pages} pages per request")
    return [{"number": i + 1, "text": page.extract_text() or "", "has_image": True}
            for i, page in enumerate(reader.pages)]


def render_page(path: Path, destination: Path, page_number: int) -> bytes:
    image_path = destination / f"page-{page_number}.jpg"
    if image_path.exists():
        return image_path.read_bytes()
    pdf_path = document_pdf(path, destination)
    with PDFIUM_LOCK:
        with pdfium.PdfDocument(pdf_path) as pdf:
            if not 1 <= page_number <= len(pdf):
                raise ValueError("Page not found")
            page = pdf[page_number - 1]
            width, height = page.get_size()
            if min(width, height) <= 0:
                raise ValueError("Invalid PDF page dimensions")
            bitmap = page.render(scale=min(1.8, 1600 / max(width, height)))
            image = bitmap.to_pil()
            stream = io.BytesIO()
            image.convert("RGB").save(stream, "JPEG", quality=85)
            image.close()
            bitmap.close()
            page.close()
    image_path.write_bytes(stream.getvalue())
    return stream.getvalue()
