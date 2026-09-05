"""Unit tests for upload service."""
import io
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.services.upload import (
    EmptyFileError,
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
    sanitize_filename,
    save_upload_file,
    validate_file_type,
)


def create_upload_file(content: bytes, filename: str, content_type: str = "text/plain") -> UploadFile:
    """Create a mock UploadFile for testing."""
    file_obj = io.BytesIO(content)
    return UploadFile(file=file_obj, filename=filename, headers={"content-type": content_type})


# Filename sanitization tests

def test_sanitize_filename_normal():
    """Test normal filename."""
    assert sanitize_filename("test.txt") == "test.txt"
    assert sanitize_filename("document.pdf") == "document.pdf"


def test_sanitize_filename_chinese():
    """Test UTF-8 Chinese filename."""
    result = sanitize_filename("测试文档.md")
    # Chinese characters get replaced with underscores
    assert result.endswith(".md")
    assert len(result) > 0


def test_sanitize_filename_posix_traversal():
    """Test POSIX path traversal prevention."""
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("../../../secret.txt") == "secret.txt"


def test_sanitize_filename_windows_traversal():
    """Test Windows path traversal prevention."""
    # Windows backslashes get removed, leaving base name
    result1 = sanitize_filename("..\\..\\windows\\system32\\config")
    assert "config" in result1
    assert "\\" not in result1

    result2 = sanitize_filename("C:\\Windows\\secret.txt")
    assert result2.endswith(".txt")
    assert "\\" not in result2


def test_sanitize_filename_dangerous_chars():
    """Test dangerous characters replacement."""
    result = sanitize_filename("file*with?bad<chars>.txt")
    assert "*" not in result
    assert "?" not in result
    assert "<" not in result
    assert result.endswith(".txt")


def test_sanitize_filename_long():
    """Test long filename truncation."""
    long_name = "a" * 250 + ".txt"
    result = sanitize_filename(long_name)
    assert len(result) <= 200
    assert result.endswith(".txt")


def test_sanitize_filename_empty():
    """Test empty filename."""
    result = sanitize_filename("")
    assert result == "unnamed_file"


def test_sanitize_filename_dots_only():
    """Test filename with only dots."""
    assert sanitize_filename(".") == "unnamed_file"
    assert sanitize_filename("..") == "unnamed_file"


# File type validation tests

def test_validate_file_type_txt():
    """Test TXT file validation."""
    mime, ext = validate_file_type("test.txt", "text/plain", b"Hello")
    assert mime == "text/plain"
    assert ext == ".txt"


def test_validate_file_type_markdown():
    """Test Markdown file validation."""
    mime, ext = validate_file_type("test.md", "text/markdown", b"# Title")
    assert mime == "text/markdown"
    assert ext == ".md"


def test_validate_file_type_markdown_plain():
    """Test Markdown with text/plain MIME (browser behavior)."""
    mime, ext = validate_file_type("test.md", "text/plain", b"# Title")
    assert mime == "text/markdown"
    assert ext == ".md"


def test_validate_file_type_pdf():
    """Test PDF file validation."""
    pdf_content = b"%PDF-1.4\n"
    mime, ext = validate_file_type("test.pdf", "application/pdf", pdf_content)
    assert mime == "application/pdf"
    assert ext == ".pdf"


def test_validate_file_type_pdf_invalid_signature():
    """Test PDF with invalid signature."""
    with pytest.raises(InvalidFileError, match="Invalid PDF"):
        validate_file_type("test.pdf", "application/pdf", b"Not a PDF")


def test_validate_file_type_unsupported_extension():
    """Test unsupported file extension."""
    with pytest.raises(UnsupportedFileTypeError, match="not supported"):
        validate_file_type("test.exe", "application/octet-stream", b"data")


def test_validate_file_type_unsupported_mime():
    """Test unsupported MIME type."""
    with pytest.raises(UnsupportedFileTypeError, match="MIME type"):
        validate_file_type("test.txt", "application/json", b"data")


def test_validate_file_type_mime_conflict():
    """Test MIME type conflict with extension."""
    with pytest.raises(UnsupportedFileTypeError, match="doesn't match"):
        validate_file_type("test.txt", "application/pdf", b"data")


def test_validate_file_type_octet_stream_valid():
    """Test octet-stream with valid extension."""
    mime, ext = validate_file_type("test.md", "application/octet-stream", b"# Title")
    assert mime == "text/markdown"
    assert ext == ".md"


# Upload file tests

@pytest.mark.anyio
async def test_save_upload_file_txt(tmp_path):
    """Test normal TXT file upload."""
    content = b"Hello, World!"
    doc_id = uuid4()
    upload_file = create_upload_file(content, "test.txt", "text/plain")

    original, safe, size, sha = await save_upload_file(
        upload_file, doc_id, upload_root=tmp_path
    )

    assert original == "test.txt"
    assert safe == "test.txt"
    assert size == len(content)
    assert len(sha) == 64  # SHA-256 hex

    # Verify file exists
    final_path = tmp_path / str(doc_id) / "test.txt"
    assert final_path.exists()
    assert final_path.read_bytes() == content


@pytest.mark.anyio
async def test_save_upload_file_markdown(tmp_path):
    """Test Markdown file upload."""
    content = b"# Title\n\nContent"
    doc_id = uuid4()
    upload_file = create_upload_file(content, "test.md", "text/markdown")

    original, safe, size, sha = await save_upload_file(
        upload_file, doc_id, upload_root=tmp_path
    )

    assert safe == "test.md"
    assert size == len(content)

    final_path = tmp_path / str(doc_id) / "test.md"
    assert final_path.exists()


@pytest.mark.anyio
async def test_save_upload_file_pdf(tmp_path):
    """Test PDF file upload."""
    content = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n" + b"x" * 100
    doc_id = uuid4()
    upload_file = create_upload_file(content, "test.pdf", "application/pdf")

    original, safe, size, sha = await save_upload_file(
        upload_file, doc_id, upload_root=tmp_path
    )

    assert safe == "test.pdf"
    assert size == len(content)

    final_path = tmp_path / str(doc_id) / "test.pdf"
    assert final_path.exists()


@pytest.mark.anyio
async def test_save_upload_file_empty(tmp_path):
    """Test empty file rejection."""
    doc_id = uuid4()
    upload_file = create_upload_file(b"", "empty.txt", "text/plain")

    with pytest.raises(EmptyFileError, match="empty"):
        await save_upload_file(upload_file, doc_id, upload_root=tmp_path)

    # Verify no file created
    doc_dir = tmp_path / str(doc_id)
    if doc_dir.exists():
        assert list(doc_dir.iterdir()) == []


@pytest.mark.anyio
async def test_save_upload_file_too_large(tmp_path):
    """Test file size limit."""
    # Use small limit for testing
    small_limit = 1000
    doc_id = uuid4()
    large_content = b"x" * 2000
    upload_file = create_upload_file(large_content, "large.txt", "text/plain")

    with pytest.raises(FileTooLargeError, match="exceeds limit"):
        await save_upload_file(upload_file, doc_id, max_bytes=small_limit, upload_root=tmp_path)

    # Verify staging temp file cleaned up
    staging_dir = tmp_path / ".staging"
    if staging_dir.exists():
        assert len(list(staging_dir.glob("*.tmp"))) == 0


@pytest.mark.anyio
async def test_save_upload_file_at_limit(tmp_path):
    """Test file exactly at size limit."""
    limit = 1000
    content = b"x" * limit
    doc_id = uuid4()
    upload_file = create_upload_file(content, "exact.txt", "text/plain")

    original, safe, size, sha = await save_upload_file(
        upload_file, doc_id, max_bytes=limit, upload_root=tmp_path
    )

    assert size == limit
    final_path = tmp_path / str(doc_id) / "exact.txt"
    assert final_path.exists()


@pytest.mark.anyio
async def test_save_upload_file_sha256_correct(tmp_path):
    """Test SHA-256 is computed from original bytes."""
    import hashlib

    content = b"Test content for SHA-256"
    expected_sha = hashlib.sha256(content).hexdigest()

    doc_id = uuid4()
    upload_file = create_upload_file(content, "test.txt", "text/plain")

    _, _, _, sha = await save_upload_file(upload_file, doc_id, upload_root=tmp_path)

    assert sha == expected_sha


@pytest.mark.anyio
async def test_save_upload_file_no_overwrite(tmp_path):
    """Test existing file is not overwritten."""
    doc_id = uuid4()

    # First upload
    upload_file1 = create_upload_file(b"First", "test.txt", "text/plain")
    await save_upload_file(upload_file1, doc_id, upload_root=tmp_path)

    # Second upload with same filename
    upload_file2 = create_upload_file(b"Second", "test.txt", "text/plain")

    with pytest.raises(InvalidFileError, match="already exists"):
        await save_upload_file(upload_file2, doc_id, upload_root=tmp_path)

    # Verify original content unchanged
    final_path = tmp_path / str(doc_id) / "test.txt"
    assert final_path.read_bytes() == b"First"


@pytest.mark.anyio
async def test_save_upload_file_staging_cleanup_on_error(tmp_path):
    """Test temp file cleanup on upload error."""
    doc_id = uuid4()
    # Invalid PDF signature
    upload_file = create_upload_file(b"Not PDF", "test.pdf", "application/pdf")

    with pytest.raises(InvalidFileError):
        await save_upload_file(upload_file, doc_id, upload_root=tmp_path)

    # Verify staging directory is clean
    staging_dir = tmp_path / ".staging"
    if staging_dir.exists():
        tmp_files = list(staging_dir.glob("*.tmp"))
        assert len(tmp_files) == 0, f"Found leftover temp files: {tmp_files}"


@pytest.mark.anyio
async def test_save_upload_file_path_within_root(tmp_path):
    """Test final path is within upload root."""
    doc_id = uuid4()
    upload_file = create_upload_file(b"Test", "test.txt", "text/plain")

    await save_upload_file(upload_file, doc_id, upload_root=tmp_path)

    # Verify path is within root
    final_path = tmp_path / str(doc_id) / "test.txt"
    assert final_path.resolve().is_relative_to(tmp_path.resolve())


@pytest.mark.anyio
async def test_save_upload_file_read_failure_cleans_own_temp(tmp_path):
    """Read failures remove the request's staging file."""
    class FailingUploadFile:
        filename = "broken.txt"
        content_type = "text/plain"
        calls = 0

        async def read(self, size=-1):
            self.calls += 1
            if self.calls == 1:
                return b"partial"
            raise OSError("stream interrupted")

        async def close(self):
            return None

    with pytest.raises(OSError, match="interrupted"):
        await save_upload_file(FailingUploadFile(), uuid4(), upload_root=tmp_path)

    assert list((tmp_path / ".staging").glob("*.tmp")) == []


@pytest.mark.anyio
async def test_save_upload_file_publish_failure_preserves_existing_data(tmp_path, monkeypatch):
    """Publish failures remove only the current temp file and empty claim."""
    from pathlib import Path as RealPath

    original_replace = RealPath.replace

    def fail_replace(self, target):
        raise OSError("publish failed")

    monkeypatch.setattr(RealPath, "replace", fail_replace)
    document_id = uuid4()
    with pytest.raises(OSError, match="publish failed"):
        await save_upload_file(
            create_upload_file(b"new", "new.txt"), document_id, upload_root=tmp_path
        )
    monkeypatch.setattr(RealPath, "replace", original_replace)

    assert list((tmp_path / ".staging").glob("*.tmp")) == []
    assert not (tmp_path / str(document_id)).exists()
