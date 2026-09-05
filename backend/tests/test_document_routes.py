"""Integration tests for document HTTP routes."""
from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.api.routes.documents import (
    get_background_processor,
    get_background_session_factory,
    get_embedding_provider,
    get_upload_root,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.document import Document, ProcessingJob
from app.models.user import User


class FakeEmbeddingProvider:
    @property
    def model_name(self) -> str:
        return "fake"

    async def embed(self, texts: list[str]):
        from app.ai.embedding_contracts import EmbeddingResult

        return EmbeddingResult(
            vectors=[[1.0] + [0.0] * 1023 for _ in texts],
            model="fake",
            dimension=1024,
        )


@pytest.fixture
def route_context(tmp_path: Path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Document.__table__, ProcessingJob.__table__])
    session = Session(engine)
    user = User(
        id=1,
        username="route-test",
        nickname="Route Test",
        password_hash="test",
        is_active=True,
        token_version=0,
    )

    async def no_op_background(*args, **kwargs):
        return None

    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_upload_root] = lambda: tmp_path
    app.dependency_overrides[get_embedding_provider] = lambda: FakeEmbeddingProvider()
    app.dependency_overrides[get_background_session_factory] = lambda: lambda: session
    app.dependency_overrides[get_background_processor] = lambda: no_op_background
    client = TestClient(app)
    try:
        yield client, session, tmp_path
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_openapi_and_document_routes(route_context):
    client, _, _ = route_context
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/documents" in paths
    assert "/api/v1/documents/{document_id}" in paths
    assert set(paths["/api/v1/documents"]) == {"get", "post"}


def test_upload_txt_returns_202_and_persists_bytes(route_context):
    client, session, root = route_context
    response = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", b"hello route", "text/plain")},
    )
    assert response.status_code == 202
    payload = response.json()
    assert UUID(payload["id"])
    assert payload["original_name"] == "notes.txt"
    assert payload["duplicate"] is False
    assert payload["status"] == "pending"
    assert (root / payload["id"] / "notes.txt").read_bytes() == b"hello route"
    assert session.get(Document, UUID(payload["id"])) is not None


def test_duplicate_upload_reuses_document_and_removes_private_copy(route_context):
    client, session, root = route_context
    first = client.post(
        "/api/v1/documents",
        files={"file": ("one.txt", b"same bytes", "text/plain")},
    ).json()
    second = client.post(
        "/api/v1/documents",
        files={"file": ("two.txt", b"same bytes", "text/plain")},
    )
    assert second.status_code == 202
    payload = second.json()
    assert payload["id"] == first["id"]
    assert payload["duplicate"] is True
    assert len(session.query(Document).all()) == 1
    assert not (root / payload["id"] / "two.txt").exists()
    assert (root / first["id"] / "one.txt").read_bytes() == b"same bytes"


def test_upload_markdown_and_pdf(route_context):
    client, _, root = route_context
    markdown = client.post(
        "/api/v1/documents",
        files={"file": ("guide.md", b"# Guide\ncontent", "text/markdown")},
    )
    pdf = client.post(
        "/api/v1/documents",
        files={"file": ("guide.pdf", b"%PDF-1.7\nbody", "application/pdf")},
    )
    assert markdown.status_code == 202
    assert pdf.status_code == 202
    assert (root / markdown.json()["id"] / "guide.md").read_bytes() == b"# Guide\ncontent"
    assert (root / pdf.json()["id"] / "guide.pdf").read_bytes().startswith(b"%PDF-")
    for payload in (markdown.json(), pdf.json()):
        assert "absolute_path" not in payload
        assert "embedding" not in payload


def test_upload_validation_and_missing_file(route_context):
    client, _, root = route_context
    assert client.post("/api/v1/documents", files={"file": ("empty.txt", b"", "text/plain")}).status_code == 400
    assert client.post("/api/v1/documents", files={"file": ("bad.exe", b"x", "application/octet-stream")}).status_code == 415
    assert client.post("/api/v1/documents", files={"wrong": ("x.txt", b"x", "text/plain")}).status_code == 422
    assert list(root.glob(".staging/*.tmp")) == []


def test_document_listing_and_status(route_context):
    client, _, _ = route_context
    ids = []
    for name in ("a.txt", "b.md", "c.txt"):
        response = client.post(
            "/api/v1/documents",
            files={"file": (name, b"content-" + name.encode(), "text/plain")},
        )
        ids.append(response.json()["id"])
    page = client.get("/api/v1/documents?limit=2&offset=1")
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert page.json()["limit"] == 2
    assert page.json()["offset"] == 1
    assert client.get(f"/api/v1/documents/{ids[0]}").status_code == 200
    assert client.get(f"/api/v1/documents/{uuid4()}").status_code == 404
    assert client.get("/api/v1/documents/not-a-uuid").status_code == 422
    assert client.get("/api/v1/documents?limit=0").status_code == 422
    assert client.get("/api/v1/documents?offset=-1").status_code == 422


def test_database_failure_removes_only_current_upload(route_context, monkeypatch):
    client, _, root = route_context
    from app.api.routes import documents

    original_commit = Session.commit
    def fail_commit(self):
        raise RuntimeError("database unavailable")
    monkeypatch.setattr(Session, "commit", fail_commit)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("failed.txt", b"will be removed", "text/plain")},
    )
    monkeypatch.setattr(Session, "commit", original_commit)
    assert response.status_code == 500
    assert list(root.glob("*/failed.txt")) == []
    assert list((root / ".staging").glob("*.tmp")) == []
