"""PostgreSQL integration coverage for document reprocessing."""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.ai.embedding_contracts import EmbeddingResult
from app.api.routes.documents import claim_document_reprocessing, process_document_background
from app.db.session import SessionLocal
from app.models.document import Document, ProcessingJob
from app.models.document_chunk import DocumentChunk, EMBEDDING_DIMENSION
from app.models.user import User


class SuccessfulProvider:
    model_name = "reprocess-test-model"

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            vectors=[[1.0] + [0.0] * (EMBEDDING_DIMENSION - 1) for _ in texts],
            model=self.model_name,
            dimension=EMBEDDING_DIMENSION,
        )


class FailingProvider:
    model_name = "reprocess-test-model"

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        raise RuntimeError("provider failed with secret-token-that-must-not-leak")


def _create_fixture(root: Path, *, with_old_chunk: bool = False):
    session = SessionLocal()
    user = User(
        username=f"reprocess_pg_{uuid4().hex[:12]}",
        nickname="Reprocess PostgreSQL Test",
        password_hash="$2b$12$test",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    document = Document(
        id=uuid4(),
        user_id=user.id,
        original_name="reprocess.txt",
        safe_name="reprocess.txt",
        mime_type="text/plain",
        size_bytes=36,
        sha256=uuid4().hex + uuid4().hex,
        status="failed",
        error_message="old failure",
    )
    session.add(document)
    session.flush()
    old_chunk_id = None
    if with_old_chunk:
        old_chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            content="old content",
            page_number=1,
            title_path=[],
            start_char=0,
            end_char=11,
            embedding_model="reprocess-test-model",
            embedding_dimension=EMBEDDING_DIMENSION,
            embedding=[1.0] + [0.0] * (EMBEDDING_DIMENSION - 1),
            chunk_metadata={},
        )
        session.add(old_chunk)
        session.flush()
        old_chunk_id = old_chunk.id
    session.commit()
    directory = root / str(document.id)
    directory.mkdir(parents=True)
    (directory / document.safe_name).write_text(
        "CourseMind reprocessing integration content."
    )
    return session, user.id, document.id, old_chunk_id


def _cleanup(session, user_id: int, document_id) -> None:
    session.rollback()
    document = session.get(Document, document_id)
    if document is not None:
        session.delete(document)
        session.commit()
    user = session.get(User, user_id)
    if user is not None:
        session.delete(user)
        session.commit()
    session.close()


def test_reprocess_background_success_replaces_chunks(tmp_path: Path):
    session, user_id, document_id, old_chunk_id = _create_fixture(
        tmp_path, with_old_chunk=True
    )
    session.close()
    verification = SessionLocal()
    try:
        asyncio.run(
            process_document_background(
                document_id,
                user_id,
                "reprocess.txt",
                SessionLocal,
                SuccessfulProvider(),
                tmp_path,
            )
        )
        verification.expire_all()
        document = verification.get(Document, document_id)
        assert document.status == "succeeded"
        jobs = verification.scalars(
            select(ProcessingJob).where(ProcessingJob.document_id == document_id)
        ).all()
        assert len(jobs) == 1
        assert jobs[0].status == "succeeded"
        chunks = verification.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        ).all()
        assert chunks
        assert old_chunk_id not in {chunk.id for chunk in chunks}
        assert all(chunk.embedding_dimension == EMBEDDING_DIMENSION for chunk in chunks)
    finally:
        _cleanup(verification, user_id, document_id)


def test_reprocess_background_failure_preserves_old_chunks(tmp_path: Path):
    session, user_id, document_id, old_chunk_id = _create_fixture(
        tmp_path, with_old_chunk=True
    )
    session.close()
    verification = SessionLocal()
    try:
        asyncio.run(
            process_document_background(
                document_id,
                user_id,
                "reprocess.txt",
                SessionLocal,
                FailingProvider(),
                tmp_path,
            )
        )
        verification.expire_all()
        document = verification.get(Document, document_id)
        assert document.status == "failed"
        assert "secret-token-that-must-not-leak" not in (document.error_message or "")
        jobs = verification.scalars(
            select(ProcessingJob).where(ProcessingJob.document_id == document_id)
        ).all()
        assert len(jobs) == 1
        assert jobs[0].status == "failed"
        chunks = verification.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        ).all()
        assert [chunk.id for chunk in chunks] == [old_chunk_id]
    finally:
        _cleanup(verification, user_id, document_id)


def test_reprocess_claim_is_atomic_across_two_sessions(tmp_path: Path):
    setup, user_id, document_id, _ = _create_fixture(tmp_path)
    setup.close()
    barrier = threading.Barrier(2)
    results: list[bool] = []
    errors: list[BaseException] = []

    def contender() -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
            results.append(
                claim_document_reprocessing(session, document_id, user_id) is not None
            )
        except BaseException as error:
            errors.append(error)
        finally:
            session.close()

    threads = [threading.Thread(target=contender) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    verification = SessionLocal()
    try:
        assert errors == []
        assert not any(thread.is_alive() for thread in threads)
        assert sorted(results) == [False, True]
        assert verification.get(Document, document_id).status == "pending"
    finally:
        _cleanup(verification, user_id, document_id)
