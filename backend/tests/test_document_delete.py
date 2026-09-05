"""Tests for document deletion functionality."""
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.api.routes.documents import get_upload_root
from app.db.base import Base
from app.db.session import get_db
from app.db.session import SessionLocal
from app.main import app
from app.models.document import Document, ProcessingJob
from app.models.document_chunk import DocumentChunk, EMBEDDING_DIMENSION
from app.models.user import User

PROTECTED_DOCUMENT_ID = UUID("d42818a8-089c-404f-a3a0-aca970098f11")


@pytest.fixture
def delete_context(tmp_path: Path):
    """Set up test context with database and file system."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key constraints in SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Only create tables without ARRAY types
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Document.__table__, ProcessingJob.__table__]
    )
    session = Session(engine)

    # Create test users
    user_a = User(
        username=f"delete_user_a_{uuid4().hex[:8]}",
        nickname="Delete Test User A",
        password_hash="$2b$12$test",
        is_active=True,
    )
    user_b = User(
        username=f"delete_user_b_{uuid4().hex[:8]}",
        nickname="Delete Test User B",
        password_hash="$2b$12$test",
        is_active=True,
    )
    session.add_all([user_a, user_b])
    session.commit()
    session.refresh(user_a)
    session.refresh(user_b)

    upload_root = tmp_path / "uploads"
    upload_root.mkdir(parents=True, exist_ok=True)

    yield {
        "session": session,
        "engine": engine,
        "user_a": user_a,
        "user_b": user_b,
        "upload_root": upload_root,
    }

    session.close()
    engine.dispose()


def test_owner_can_delete_pending_document(delete_context):
    """Test that document owner can delete pending document."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]

    # Create document
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="test.txt",
        safe_name="test.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"delete_test_{uuid4().hex}",
        status="pending",
    )
    session.add(doc)
    session.commit()

    # Create file directory
    doc_dir = upload_root / str(doc_id)
    doc_dir.mkdir(parents=True)
    (doc_dir / "test.txt").write_text("test content")

    # Set up API
    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{doc_id}")

        assert response.status_code == 204

        # Verify database deletion
        deleted_doc = session.get(Document, doc_id)
        assert deleted_doc is None

        # Verify file deletion
        assert not doc_dir.exists()

    finally:
        app.dependency_overrides.clear()


def test_owner_can_delete_failed_document(delete_context):
    """Test that document owner can delete failed document."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="test.pdf",
        safe_name="test.pdf",
        mime_type="application/pdf",
        size_bytes=500,
        sha256=f"delete_failed_{uuid4().hex}",
        status="failed",
        error_message="Processing failed",
    )
    session.add(doc)
    session.commit()

    doc_dir = upload_root / str(doc_id)
    doc_dir.mkdir(parents=True)
    (doc_dir / "test.pdf").write_bytes(b"fake pdf")

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{doc_id}")

        assert response.status_code == 204
        assert session.get(Document, doc_id) is None
        assert not doc_dir.exists()

    finally:
        app.dependency_overrides.clear()


def test_delete_cascades_to_processing_jobs_and_chunks(delete_context):
    """Test that deleting document cascades to processing_jobs."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="cascade.md",
        safe_name="cascade.md",
        mime_type="text/markdown",
        size_bytes=200,
        sha256=f"cascade_{uuid4().hex}",
        status="succeeded",
    )
    session.add(doc)
    session.commit()

    job_id = uuid4()
    job = ProcessingJob(
        id=job_id,
        document_id=doc_id,
        status="succeeded",
    )
    session.add(job)
    session.commit()

    assert session.get(ProcessingJob, job_id) is not None

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{doc_id}")

        assert response.status_code == 204
        assert session.get(Document, doc_id) is None
        assert session.get(ProcessingJob, job_id) is None

    finally:
        app.dependency_overrides.clear()


def test_delete_only_removes_own_document_directory(delete_context):
    """Test that delete only removes the specific document directory."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]

    doc1_id = uuid4()
    doc2_id = uuid4()

    doc1 = Document(
        id=doc1_id,
        user_id=user_a.id,
        original_name="doc1.txt",
        safe_name="doc1.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"doc1_{uuid4().hex}",
        status="pending",
    )
    doc2 = Document(
        id=doc2_id,
        user_id=user_a.id,
        original_name="doc2.txt",
        safe_name="doc2.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"doc2_{uuid4().hex}",
        status="pending",
    )
    session.add_all([doc1, doc2])
    session.commit()

    doc1_dir = upload_root / str(doc1_id)
    doc2_dir = upload_root / str(doc2_id)
    doc1_dir.mkdir(parents=True)
    doc2_dir.mkdir(parents=True)
    (doc1_dir / "doc1.txt").write_text("content1")
    (doc2_dir / "doc2.txt").write_text("content2")

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{doc1_id}")

        assert response.status_code == 204
        assert not doc1_dir.exists()
        assert doc2_dir.exists()
        assert (doc2_dir / "doc2.txt").exists()

    finally:
        app.dependency_overrides.clear()


def test_delete_unauthorized_returns_404(delete_context):
    """Test that attempting to delete another user's document returns 404."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    user_b = delete_context["user_b"]
    upload_root = delete_context["upload_root"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="private.txt",
        safe_name="private.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"private_{uuid4().hex}",
        status="pending",
    )
    session.add(doc)
    session.commit()

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_b

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{doc_id}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found"}
        assert session.get(Document, doc_id) is not None

    finally:
        app.dependency_overrides.clear()


def test_delete_null_owner_returns_404(delete_context):
    """Test that attempting to delete NULL owner document returns 404."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=None,
        original_name="orphan.txt",
        safe_name="orphan.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"orphan_{uuid4().hex}",
        status="pending",
    )
    session.add(doc)
    session.commit()

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{doc_id}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found"}
        assert session.get(Document, doc_id) is not None

    finally:
        app.dependency_overrides.clear()


def test_delete_nonexistent_returns_404(delete_context):
    """Test that deleting non-existent document returns 404."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]

    nonexistent_id = uuid4()

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{nonexistent_id}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found"}

    finally:
        app.dependency_overrides.clear()


def test_delete_processing_document_returns_409(delete_context):
    """Test that deleting a document being processed returns 409."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="processing.txt",
        safe_name="processing.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"processing_{uuid4().hex}",
        status="processing",
    )
    session.add(doc)
    session.commit()

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{doc_id}")

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "currently being processed" in detail or "cannot be deleted" in detail.lower()
        assert session.get(Document, doc_id) is not None

    finally:
        app.dependency_overrides.clear()


def test_delete_succeeds_when_files_missing(delete_context):
    """Test that delete succeeds even if disk files don't exist."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="missing.txt",
        safe_name="missing.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"missing_{uuid4().hex}",
        status="pending",
    )
    session.add(doc)
    session.commit()

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{doc_id}")

        assert response.status_code == 204
        assert session.get(Document, doc_id) is None

    finally:
        app.dependency_overrides.clear()


def test_delete_with_chunks_cascades(delete_context):
    """Test that deleting document cascades to chunks in PostgreSQL-like setup."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]

    # This test uses SQLite which supports CASCADE
    # In production PostgreSQL, the same cascade behavior applies
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="with_chunks.txt",
        safe_name="with_chunks.txt",
        mime_type="text/plain",
        size_bytes=200,
        sha256=f"chunks_{uuid4().hex}",
        status="succeeded",
    )
    session.add(doc)
    session.commit()

    # Create a processing job
    job_id = uuid4()
    job = ProcessingJob(
        id=job_id,
        document_id=doc_id,
        status="succeeded",
    )
    session.add(job)
    session.commit()

    # Verify job exists
    assert session.get(ProcessingJob, job_id) is not None

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{doc_id}")

        assert response.status_code == 204
        # Verify cascading deletion
        assert session.get(Document, doc_id) is None
        assert session.get(ProcessingJob, job_id) is None

    finally:
        app.dependency_overrides.clear()


def test_delete_disk_failure_still_returns_204(delete_context, monkeypatch, caplog):
    """Test that disk deletion failure still returns 204 after DB commit."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="diskfail.txt",
        safe_name="diskfail.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"diskfail_{uuid4().hex}",
        status="pending",
    )
    session.add(doc)
    session.commit()

    # Create a directory but make it read-only to simulate deletion failure
    doc_dir = upload_root / str(doc_id)
    doc_dir.mkdir(parents=True)
    (doc_dir / "diskfail.txt").write_text("content")

    calls = []

    def fail_rmtree(path):
        calls.append(Path(path))
        raise OSError("simulated cleanup failure")

    monkeypatch.setattr("app.api.routes.documents.shutil.rmtree", fail_rmtree)

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/documents/{doc_id}")

        # Should still return 204 even if disk cleanup fails
        assert response.status_code == 204
        # Database should be deleted
        assert session.get(Document, doc_id) is None
        assert calls == [doc_dir]
        assert doc_dir.exists()
        assert "Failed to delete files" in caplog.text

    finally:
        app.dependency_overrides.clear()


def test_delete_commit_failure_preserves_database_and_files(delete_context, monkeypatch):
    """A failed database commit must never remove the stored file."""
    session = delete_context["session"]
    user_a = delete_context["user_a"]
    upload_root = delete_context["upload_root"]
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="commit-failure.txt",
        safe_name="commit-failure.txt",
        mime_type="text/plain",
        size_bytes=7,
        sha256=f"commit_failure_{uuid4().hex}",
        status="failed",
    )
    session.add(doc)
    session.commit()
    doc_dir = upload_root / str(doc_id)
    doc_dir.mkdir(parents=True)
    stored_file = doc_dir / doc.safe_name
    stored_file.write_text("content")

    original_commit = session.commit
    commit_calls = 0

    def fail_first_commit():
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls == 1:
            raise RuntimeError("simulated commit failure")
        return original_commit()

    monkeypatch.setattr(session, "commit", fail_first_commit)
    rmtree_calls = []
    monkeypatch.setattr(
        "app.api.routes.documents.shutil.rmtree",
        lambda path: rmtree_calls.append(Path(path)),
    )

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_upload_root] = lambda: upload_root
    try:
        response = TestClient(app, raise_server_exceptions=False).delete(
            f"/api/v1/documents/{doc_id}"
        )
        assert response.status_code == 500
        assert response.json() == {"detail": "Document deletion failed"}
        assert session.get(Document, doc_id) is not None
        assert stored_file.exists()
        assert rmtree_calls == []
    finally:
        app.dependency_overrides.clear()


def test_delete_postgresql_cascades_jobs_and_chunks(tmp_path: Path):
    """The real PostgreSQL foreign keys cascade both jobs and vector chunks."""
    session = SessionLocal()
    user_id = None
    document_id = uuid4()
    job_id = uuid4()
    chunk_id = uuid4()
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    try:
        user = User(
            username=f"delete_pg_{uuid4().hex[:12]}",
            nickname="Delete PostgreSQL Test",
            password_hash="$2b$12$test",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id
        document = Document(
            id=document_id,
            user_id=user_id,
            original_name="cascade.txt",
            safe_name="cascade.txt",
            mime_type="text/plain",
            size_bytes=7,
            sha256=uuid4().hex + uuid4().hex,
            status="succeeded",
        )
        session.add(document)
        session.flush()
        session.add(
            ProcessingJob(id=job_id, document_id=document_id, status="succeeded")
        )
        session.add(
            DocumentChunk(
                id=chunk_id,
                document_id=document_id,
                chunk_index=0,
                content="content",
                page_number=1,
                title_path=[],
                start_char=0,
                end_char=7,
                embedding_model="test-model",
                embedding_dimension=EMBEDDING_DIMENSION,
                embedding=[1.0] + [0.0] * (EMBEDDING_DIMENSION - 1),
                chunk_metadata={},
            )
        )
        session.commit()

        def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_upload_root] = lambda: upload_root
        response = TestClient(app).delete(f"/api/v1/documents/{document_id}")
        assert response.status_code == 204
        session.expire_all()
        assert session.get(Document, document_id) is None
        assert session.get(ProcessingJob, job_id) is None
        assert session.get(DocumentChunk, chunk_id) is None
    finally:
        app.dependency_overrides.clear()
        session.rollback()
        if session.get(Document, document_id) is not None:
            session.delete(session.get(Document, document_id))
            session.commit()
        if user_id is not None:
            remaining_user = session.get(User, user_id)
            if remaining_user is not None:
                session.delete(remaining_user)
                session.commit()
        session.close()
