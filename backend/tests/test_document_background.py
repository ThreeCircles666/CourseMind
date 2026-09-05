"""Background document processing integration tests."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.routes.documents import process_document_background
from app.db.base import Base
from app.models.document import Document, ProcessingJob
from app.models.user import User


class SuccessfulEmbeddingProvider:
    model_name = "fake"

    async def embed(self, texts):
        from app.ai.embedding_contracts import EmbeddingResult

        return EmbeddingResult(
            vectors=[[1.0] + [0.0] * 1023 for _ in texts],
            model="fake",
            dimension=1024,
        )


class FailingEmbeddingProvider:
    model_name = "fake"

    async def embed(self, texts):
        raise RuntimeError("provider secret should not be persisted")


class CountingEmbeddingProvider(SuccessfulEmbeddingProvider):
    def __init__(self):
        self.call_count = 0

    async def embed(self, texts):
        self.call_count += 1
        return await super().embed(texts)


@pytest.fixture
def database(tmp_path: Path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[User.__table__, Document.__table__, ProcessingJob.__table__])
    sessions: list[Session] = []

    def factory() -> Session:
        session = Session(engine)
        sessions.append(session)
        return session

    try:
        # Create a test user
        setup = factory()
        test_user = User(
            username="test_bg_user",
            nickname="Test BG User",
            password_hash="$2b$12$test",
            is_active=True,
        )
        setup.add(test_user)
        setup.commit()
        user_id = test_user.id
        setup.close()

        yield factory, tmp_path, sessions, user_id
    finally:
        for session in sessions:
            session.close()
        engine.dispose()


@pytest.mark.anyio
async def test_background_success_awaits_ingestion_and_closes_session(database, monkeypatch):
    factory, root, sessions, user_id = database
    document_id = uuid4()
    setup = factory()
    setup.add(Document(
        id=document_id,
        user_id=user_id,
        original_name="success.txt",
        safe_name="success.txt",
        mime_type="text/plain",
        size_bytes=21,
        sha256=uuid4().hex + uuid4().hex,
        status="pending",
    ))
    setup.commit()
    setup.close()
    (root / str(document_id)).mkdir()
    (root / str(document_id) / "success.txt").write_bytes(b"A successful document")

    async def fake_ingest_document(*, session, document_id, content, **kwargs):
        assert content == b"A successful document"
        document = session.get(Document, document_id)
        document.status = "succeeded"
        session.add(ProcessingJob(document_id=document_id, status="succeeded"))
        session.commit()

    from app.api.routes import documents as document_routes
    monkeypatch.setattr(document_routes, "ingest_document", fake_ingest_document)

    await process_document_background(
        document_id,
        user_id,
        "success.txt",
        session_factory=factory,
        embedding_provider=SuccessfulEmbeddingProvider(),
        upload_root=root,
    )

    check = factory()
    saved = check.get(Document, document_id)
    job = check.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id))
    assert saved is not None
    assert saved.status == "succeeded"
    assert job is not None
    assert job.status == "succeeded"
    assert len(sessions) >= 3
    check.close()


@pytest.mark.anyio
async def test_background_embedding_failure_marks_document_and_job_failed(database):
    factory, root, sessions, user_id = database
    document_id = uuid4()
    setup = factory()
    setup.add(Document(
        id=document_id,
        user_id=user_id,
        original_name="notes.txt",
        safe_name="notes.txt",
        mime_type="text/plain",
        size_bytes=11,
        sha256=uuid4().hex + uuid4().hex,
        status="pending",
    ))
    setup.commit()
    setup.close()
    (root / str(document_id)).mkdir()
    (root / str(document_id) / "notes.txt").write_bytes(b"hello world")

    await process_document_background(
        document_id,
        user_id,
        "notes.txt",
        session_factory=factory,
        embedding_provider=FailingEmbeddingProvider(),
        upload_root=root,
    )

    check = factory()
    saved = check.get(Document, document_id)
    job = check.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id))
    assert saved is not None
    assert saved.status == "failed"
    assert saved.error_message is not None
    assert len(saved.error_message) <= 220
    assert "provider secret" not in saved.error_message
    assert job is not None
    assert job.status == "failed"
    assert all(session.is_active for session in sessions)
    check.close()


@pytest.mark.anyio
async def test_background_missing_file_marks_document_failed(database):
    factory, root, _, user_id = database
    document_id = uuid4()
    setup = factory()
    setup.add(Document(
        id=document_id,
        user_id=user_id,
        original_name="missing.txt",
        safe_name="missing.txt",
        mime_type="text/plain",
        size_bytes=1,
        sha256=uuid4().hex + uuid4().hex,
        status="pending",
    ))
    setup.commit()
    setup.close()

    await process_document_background(
        document_id,
        user_id,
        "missing.txt",
        session_factory=factory,
        embedding_provider=FailingEmbeddingProvider(),
        upload_root=root,
    )

    check = factory()
    assert check.get(Document, document_id).status == "failed"
    assert check.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id)) is None
    check.close()


@pytest.mark.anyio
async def test_background_task_rejects_wrong_owner(database):
    factory, root, _, user_id = database
    document_id = uuid4()
    setup = factory()
    setup.add(Document(
        id=document_id,
        user_id=user_id,
        original_name="private.txt",
        safe_name="private.txt",
        mime_type="text/plain",
        size_bytes=7,
        sha256=uuid4().hex + uuid4().hex,
        status="pending",
    ))
    setup.commit()
    setup.close()
    (root / str(document_id)).mkdir()
    (root / str(document_id) / "private.txt").write_bytes(b"private")
    provider = CountingEmbeddingProvider()

    await process_document_background(
        document_id,
        user_id + 1,
        "private.txt",
        session_factory=factory,
        embedding_provider=provider,
        upload_root=root,
    )

    check = factory()
    saved = check.get(Document, document_id)
    assert saved is not None
    assert saved.status == "pending"
    assert saved.error_message is None
    assert check.scalar(
        select(ProcessingJob).where(ProcessingJob.document_id == document_id)
    ) is None
    assert provider.call_count == 0
    check.close()
