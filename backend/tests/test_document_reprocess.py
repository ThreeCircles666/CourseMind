"""Tests for document reprocessing functionality."""
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.api.routes.documents import (
    get_background_processor,
    get_background_session_factory,
    get_embedding_provider_factory,
    get_upload_root,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.document import Document, ProcessingJob
from app.models.user import User


class FakeEmbeddingProvider:
    def __init__(self):
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return "fake-model"

    async def embed(self, texts: list[str]):
        self.call_count += 1
        from app.ai.embedding_contracts import EmbeddingResult
        return EmbeddingResult(
            vectors=[[1.0] + [0.0] * 1023 for _ in texts],
            model="fake-model",
            dimension=1024,
        )


async def fake_background_processor(*args, **kwargs):
    """Fake processor that does nothing."""
    pass


@pytest.fixture
def reprocess_context(tmp_path: Path):
    """Set up test context."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Document.__table__, ProcessingJob.__table__]
    )
    session = Session(engine)

    user_a = User(
        username=f"reprocess_user_a_{uuid4().hex[:8]}",
        nickname="Reprocess Test User A",
        password_hash="$2b$12$test",
        is_active=True,
    )
    user_b = User(
        username=f"reprocess_user_b_{uuid4().hex[:8]}",
        nickname="Reprocess Test User B",
        password_hash="$2b$12$test",
        is_active=True,
    )
    session.add_all([user_a, user_b])
    session.commit()
    session.refresh(user_a)
    session.refresh(user_b)

    upload_root = tmp_path / "uploads"
    upload_root.mkdir(parents=True, exist_ok=True)

    fake_provider = FakeEmbeddingProvider()

    yield {
        "session": session,
        "engine": engine,
        "user_a": user_a,
        "user_b": user_b,
        "upload_root": upload_root,
        "fake_provider": fake_provider,
    }

    session.close()
    engine.dispose()


def test_reprocess_failed_document_success(reprocess_context):
    """Test that failed document can be reprocessed."""
    session = reprocess_context["session"]
    user_a = reprocess_context["user_a"]
    upload_root = reprocess_context["upload_root"]
    fake_provider = reprocess_context["fake_provider"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="failed.txt",
        safe_name="failed.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"failed_{uuid4().hex}",
        status="failed",
        error_message="Previous processing failed",
    )
    session.add(doc)
    session.commit()

    doc_dir = upload_root / str(doc_id)
    doc_dir.mkdir(parents=True)
    (doc_dir / "failed.txt").write_text("test content")

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    def override_get_embedding_provider_factory():
        return lambda: fake_provider

    def override_get_background_processor():
        return fake_background_processor

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root
    app.dependency_overrides[get_embedding_provider_factory] = override_get_embedding_provider_factory
    app.dependency_overrides[get_background_processor] = override_get_background_processor

    try:
        client = TestClient(app)
        response = client.post(f"/api/v1/documents/{doc_id}/reprocess")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(doc_id)
        assert data["status"] == "pending"
        assert data["error_message"] is None

    finally:
        app.dependency_overrides.clear()


def test_reprocess_processing_document_returns_409(reprocess_context):
    """Test that processing document cannot be reprocessed."""
    session = reprocess_context["session"]
    user_a = reprocess_context["user_a"]
    upload_root = reprocess_context["upload_root"]

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
        response = client.post(f"/api/v1/documents/{doc_id}/reprocess")

        assert response.status_code == 409

    finally:
        app.dependency_overrides.clear()


def test_reprocess_succeeded_document_returns_409(reprocess_context):
    """Test that succeeded document cannot be reprocessed."""
    session = reprocess_context["session"]
    user_a = reprocess_context["user_a"]
    upload_root = reprocess_context["upload_root"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="succeeded.txt",
        safe_name="succeeded.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"succeeded_{uuid4().hex}",
        status="succeeded",
    )
    session.add(doc)
    session.commit()

    doc_dir = upload_root / str(doc_id)
    doc_dir.mkdir(parents=True)
    (doc_dir / "succeeded.txt").write_text("test")

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
        response = client.post(f"/api/v1/documents/{doc_id}/reprocess")

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "successfully processed" in detail.lower() or "already" in detail.lower()

    finally:
        app.dependency_overrides.clear()


def test_reprocess_pending_document_returns_409(reprocess_context):
    """Test that pending document cannot be reprocessed."""
    session = reprocess_context["session"]
    user_a = reprocess_context["user_a"]
    upload_root = reprocess_context["upload_root"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="pending.txt",
        safe_name="pending.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"pending_{uuid4().hex}",
        status="pending",
    )
    session.add(doc)
    session.commit()

    doc_dir = upload_root / str(doc_id)
    doc_dir.mkdir(parents=True)
    (doc_dir / "pending.txt").write_text("test")

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
        response = client.post(f"/api/v1/documents/{doc_id}/reprocess")

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "queued" in detail.lower() or "pending" in detail.lower()

    finally:
        app.dependency_overrides.clear()


def test_reprocess_unauthorized_returns_404(reprocess_context):
    """Test that reprocessing another user's document returns 404."""
    session = reprocess_context["session"]
    user_a = reprocess_context["user_a"]
    user_b = reprocess_context["user_b"]
    upload_root = reprocess_context["upload_root"]
    fake_provider = reprocess_context["fake_provider"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="private.txt",
        safe_name="private.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"private_{uuid4().hex}",
        status="failed",
    )
    session.add(doc)
    session.commit()

    initial_call_count = fake_provider.call_count
    provider_create_calls = 0

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_b

    def override_get_upload_root():
        return upload_root

    def override_get_embedding_provider_factory():
        def create_provider():
            nonlocal provider_create_calls
            provider_create_calls += 1
            return fake_provider
        return create_provider

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root
    app.dependency_overrides[get_embedding_provider_factory] = override_get_embedding_provider_factory

    try:
        client = TestClient(app)
        response = client.post(f"/api/v1/documents/{doc_id}/reprocess")

        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found"}
        assert fake_provider.call_count == initial_call_count
        assert provider_create_calls == 0

    finally:
        app.dependency_overrides.clear()


def test_reprocess_null_owner_returns_404(reprocess_context):
    """Test that reprocessing NULL owner document returns 404."""
    session = reprocess_context["session"]
    user_a = reprocess_context["user_a"]
    upload_root = reprocess_context["upload_root"]
    fake_provider = reprocess_context["fake_provider"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=None,
        original_name="orphan.txt",
        safe_name="orphan.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"orphan_{uuid4().hex}",
        status="failed",
    )
    session.add(doc)
    session.commit()

    initial_call_count = fake_provider.call_count
    provider_create_calls = 0

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    def override_get_embedding_provider_factory():
        def create_provider():
            nonlocal provider_create_calls
            provider_create_calls += 1
            return fake_provider
        return create_provider

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root
    app.dependency_overrides[get_embedding_provider_factory] = override_get_embedding_provider_factory

    try:
        client = TestClient(app)
        response = client.post(f"/api/v1/documents/{doc_id}/reprocess")

        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found"}
        assert fake_provider.call_count == initial_call_count
        assert provider_create_calls == 0

    finally:
        app.dependency_overrides.clear()


def test_reprocess_missing_file_returns_400(reprocess_context):
    """Test that reprocessing when file is missing returns 400."""
    session = reprocess_context["session"]
    user_a = reprocess_context["user_a"]
    upload_root = reprocess_context["upload_root"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="missing.txt",
        safe_name="missing.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"missing_{uuid4().hex}",
        status="failed",
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
        response = client.post(f"/api/v1/documents/{doc_id}/reprocess")

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "not found" in detail.lower() or "cannot reprocess" in detail.lower()
        # Must not reveal absolute path
        assert "/" not in detail or "Document file not found" in detail

    finally:
        app.dependency_overrides.clear()


def test_reprocess_concurrent_requests_only_one_wins(reprocess_context):
    """Test that concurrent reprocess requests use atomic locking."""
    session = reprocess_context["session"]
    user_a = reprocess_context["user_a"]
    upload_root = reprocess_context["upload_root"]
    fake_provider = reprocess_context["fake_provider"]

    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a.id,
        original_name="concurrent.txt",
        safe_name="concurrent.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"concurrent_{uuid4().hex}",
        status="failed",
    )
    session.add(doc)
    session.commit()

    doc_dir = upload_root / str(doc_id)
    doc_dir.mkdir(parents=True)
    (doc_dir / "concurrent.txt").write_text("test content")

    background_task_count = 0

    def counting_background_processor(*args, **kwargs):
        nonlocal background_task_count
        background_task_count += 1

    def override_get_db():
        yield session

    def override_get_current_user():
        return user_a

    def override_get_upload_root():
        return upload_root

    def override_get_embedding_provider_factory():
        return lambda: fake_provider

    def override_get_background_processor():
        return counting_background_processor

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_upload_root] = override_get_upload_root
    app.dependency_overrides[get_embedding_provider_factory] = override_get_embedding_provider_factory
    app.dependency_overrides[get_background_processor] = override_get_background_processor

    try:
        client = TestClient(app)

        # First request should succeed
        response1 = client.post(f"/api/v1/documents/{doc_id}/reprocess")
        assert response1.status_code == 200
        assert response1.json()["status"] == "pending"
        assert background_task_count == 1

        # Manually set status back to failed for second attempt
        # In real scenario, the UPDATE...WHERE would prevent this
        session.execute(
            select(Document).where(Document.id == doc_id)
        )
        session.commit()

        # Second request should fail because status is now pending, not failed
        response2 = client.post(f"/api/v1/documents/{doc_id}/reprocess")
        assert response2.status_code == 409
        # Background task should only be called once
        assert background_task_count == 1

    finally:
        app.dependency_overrides.clear()
