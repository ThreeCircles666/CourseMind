"""File upload service for document management."""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

# Supported file types
SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf"}
SUPPORTED_MIMES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/octet-stream",  # Only with valid extension
}

# PDF signature
PDF_SIGNATURE = b"%PDF-"

# Chunk size for streaming
CHUNK_SIZE = 1024 * 1024  # 1MB


class UploadError(Exception):
    """Base upload error."""
    pass


class UnsupportedFileTypeError(UploadError):
    """File type not supported."""
    pass


class FileTooLargeError(UploadError):
    """File exceeds size limit."""
    pass


class EmptyFileError(UploadError):
    """File is empty."""
    pass


class InvalidFileError(UploadError):
    """File validation failed."""
    pass


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal.

    Args:
        filename: Original filename

    Returns:
        Safe filename with only allowed characters
    """
    # Remove directory components from both POSIX and Windows names.
    name = re.split(r"[/\\\\]", filename)[-1]
    name = name.replace("..", "")

    # Remove dangerous characters
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_")
    safe_name = "".join(c if c in safe_chars else "_" for c in name)

    # Limit length
    if len(safe_name) > 200:
        stem = safe_name[:190]
        ext = Path(safe_name).suffix
        safe_name = stem + ext

    # Ensure not empty
    if not safe_name or safe_name in (".", ".."):
        safe_name = "unnamed_file"

    return safe_name


def validate_file_type(filename: str, content_type: str, first_bytes: bytes) -> tuple[str, str]:
    """Validate file type by extension, MIME, and content.

    Args:
        filename: Original filename
        content_type: MIME type from upload
        first_bytes: First bytes of file content

    Returns:
        Tuple of (validated_mime_type, extension)

    Raises:
        UnsupportedFileTypeError: If file type not supported
        InvalidFileError: If file validation failed
    """
    # Get extension
    ext = Path(filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"File extension {ext} not supported. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Check MIME
    if content_type not in SUPPORTED_MIMES:
        raise UnsupportedFileTypeError(
            f"MIME type {content_type} not supported"
        )

    # Validate PDF signature
    if ext == ".pdf":
        if not first_bytes.startswith(PDF_SIGNATURE):
            raise InvalidFileError("Invalid PDF file signature")
        return "application/pdf", ext

    # Text files
    if ext in {".txt", ".md", ".markdown"}:
        # Allow text/plain or text/markdown
        if content_type in {"text/plain", "text/markdown"}:
            return "text/markdown" if ext in {".md", ".markdown"} else "text/plain", ext
        # Allow octet-stream if extension is valid
        elif content_type == "application/octet-stream":
            return "text/markdown" if ext in {".md", ".markdown"} else "text/plain", ext
        else:
            raise UnsupportedFileTypeError(f"MIME {content_type} doesn't match extension {ext}")

    return content_type, ext


async def save_upload_file(
    upload_file: UploadFile,
    document_id: UUID,
    max_bytes: int | None = None,
    upload_root: Path | None = None,
) -> tuple[str, str, int, str]:
    """Save uploaded file with validation."""
    if upload_root is None:
        upload_root = settings.get_upload_root_path()

    if max_bytes is None:
        suffix = Path(upload_file.filename or "").suffix.lower()
        max_bytes = (
            settings.upload_pdf_max_bytes
            if suffix == ".pdf"
            else settings.upload_text_max_bytes
        )

    original_name = upload_file.filename or "unnamed"
    safe_name = sanitize_filename(original_name)

    staging_dir = upload_root / ".staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    temp_path = staging_dir / f"upload_{uuid4().hex}.tmp"
    doc_dir: Path | None = None
    directory_claimed = False

    try:
        total_size = 0
        sha256_hash = hashlib.sha256()
        first_chunk = b""

        with open(temp_path, "wb") as file_handle:
            while True:
                chunk = await upload_file.read(CHUNK_SIZE)
                if not chunk:
                    break

                if not first_chunk:
                    first_chunk = chunk

                total_size += len(chunk)
                if total_size > max_bytes:
                    raise FileTooLargeError(
                        f"File size {total_size} exceeds limit {max_bytes}"
                    )

                sha256_hash.update(chunk)
                file_handle.write(chunk)

        if total_size == 0:
            raise EmptyFileError("File is empty")

        validate_file_type(
            original_name,
            upload_file.content_type or "application/octet-stream",
            first_chunk[:10],
        )

        sha256 = sha256_hash.hexdigest()

        doc_dir = upload_root / str(document_id)
        try:
            doc_dir.mkdir(parents=True, exist_ok=False)
            directory_claimed = True
        except FileExistsError as exc:
            raise InvalidFileError(
                f"Storage directory already exists for document {document_id}"
            ) from exc

        final_path = doc_dir / safe_name
        try:
            final_path.resolve().relative_to(upload_root.resolve())
        except ValueError as exc:
            raise InvalidFileError("Invalid file path - outside upload root") from exc

        temp_path.replace(final_path)

        logger.info(
            "Saved upload: %s -> %s, %s bytes, SHA256: %s...",
            original_name,
            safe_name,
            total_size,
            sha256[:16],
        )
        return original_name, safe_name, total_size, sha256
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        if directory_claimed and doc_dir is not None and doc_dir.exists() and not any(doc_dir.iterdir()):
            doc_dir.rmdir()
        raise
    finally:
        await upload_file.close()


def get_document_file_path(document_id: UUID, safe_name: str) -> Path:
    """Get path to document file.

    Args:
        document_id: Document UUID
        safe_name: Safe filename

    Returns:
        Path to file
    """
    upload_root = settings.get_upload_root_path()
    return upload_root / str(document_id) / safe_name
