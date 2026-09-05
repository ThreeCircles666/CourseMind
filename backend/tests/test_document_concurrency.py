"""Route-level concurrent upload tests against PostgreSQL.

These tests use FastAPI's real ASGI app and real PostgreSQL uniqueness
constraints. External providers are replaced with fakes so no network is used.
"""
from __future__ import annotations

import asyncio
import hashlib
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embedding_contracts import EmbeddingResult
from app.api.dependencies import get_current_user
from app.api.routes import documents as document_routes
from app.api.routes.documents import (
    get_background_processor,
    get_background_session_factory,
    get_embedding_provider,
    get_upload_root,
)
from app.db.session import SessionLocal, get_db
from app.main import app
from app.models.document import Document
from app.models.user import User


class FakeEmbeddingProvider:
    @property
    def model_name(self) -> str:
        return "fake"

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            vectors=[[1.0] + [0.0] * 1023 for _ in texts],
            model="fake",
            dimension=1024,
        )


def _cleanup_exact_document_ids(document_ids: list[UUID], upload_root: Path) -> None:
    session = SessionLocal()
    try:
        for document_id in document_ids:
            document = session.get(Document, document_id)
            if document is not None:
                session.delete(document)
        session.commit()
    finally:
        session.close()

    for document_id in document_ids:
        document_dir = upload_root / str(document_id)
        if document_dir.exists():
            shutil.rmtree(document_dir)


def test_concurrent_same_bytes_upload_uses_postgres_unique_constraint(tmp_path, monkeypatch):
    content = f"concurrent-upload-{uuid4()}".encode()
    sha256 = hashlib.sha256(content).hexdigest()
    candidate_ids = [uuid4(), uuid4()]
    id_lock = threading.Lock()
    commit_barrier = threading.Barrier(2)
    background_calls: list[UUID] = []
    background_lock = threading.Lock()
    original_uuid4 = document_routes.uuid4
    original_commit = Session.commit

    def deterministic_uuid4():
        with id_lock:
            if candidate_ids:
                return candidate_ids.pop(0)
        return original_uuid4()

    def synchronized_commit(self: Session):
        if any(isinstance(obj, Document) and obj.sha256 == sha256 for obj in self.new):
            commit_barrier.wait(timeout=10)
        return original_commit(self)

    async def fake_background_processor(document_id: UUID, *args, **kwargs):
        with background_lock:
            background_calls.append(document_id)

    user = User(
        id=1,
        username="concurrent-route-test",
        nickname="Concurrent Route Test",
        password_hash="test",
        is_active=True,
        token_version=0,
    )

    created_ids = candidate_ids.copy()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_upload_root] = lambda: tmp_path
    app.dependency_overrides[get_embedding_provider] = lambda: FakeEmbeddingProvider()
    app.dependency_overrides[get_background_session_factory] = lambda: SessionLocal
    app.dependency_overrides[get_background_processor] = lambda: fake_background_processor
    app.dependency_overrides.pop(get_db, None)
    monkeypatch.setattr(document_routes, "uuid4", deterministic_uuid4)
    monkeypatch.setattr(Session, "commit", synchronized_commit)

    try:
        def upload(filename: str):
            async def request():
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await client.post(
                        "/api/v1/documents",
                        files={"file": (filename, content, "text/plain")},
                    )

            return asyncio.run(request())

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(upload, ["same-a.txt", "same-b.txt"]))

        assert {response.status_code for response in responses} == {202}
        payloads = [response.json() for response in responses]
        response_ids = {payload["id"] for payload in payloads}
        assert len(response_ids) == 1
        assert sorted(payload["duplicate"] for payload in payloads) == [False, True]

        session = SessionLocal()
        try:
            matching_documents = session.execute(
                select(Document).where(Document.sha256 == sha256)
            ).scalars().all()
            assert len(matching_documents) == 1
            winner = matching_documents[0]
        finally:
            session.close()

        winner_dir = tmp_path / str(winner.id)
        assert winner_dir.is_dir()
        files = [path for path in winner_dir.iterdir() if path.is_file()]
        assert len(files) == 1
        assert files[0].read_bytes() == content
        assert sorted(path.name for path in tmp_path.iterdir()) == sorted([".staging", str(winner.id)])
        assert list((tmp_path / ".staging").glob("*.tmp")) == []
        assert background_calls == [winner.id]
    finally:
        app.dependency_overrides.clear()
        _cleanup_exact_document_ids(created_ids, tmp_path)

    session = SessionLocal()
    try:
        for document_id in created_ids:
            assert session.get(Document, document_id) is None
    finally:
        session.close()
    for document_id in created_ids:
        assert not (tmp_path / str(document_id)).exists()
