"""PostgreSQL-backed defense-in-depth tests for RAG ownership."""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai.embedding_contracts import EmbeddingResult
from app.api.routes.rag import ask_question
from app.core.config import settings
from app.models import Document, DocumentChunk, User
from app.schemas.rag import RagAskRequest
from app.services.retrieval import search


class CountingEmbeddingProvider:
    model_name = "permission-test"

    def __init__(self):
        self.call_count = 0

    async def embed(self, texts):
        self.call_count += 1
        return EmbeddingResult(
            vectors=[[1.0] + [0.0] * 1023 for _ in texts],
            model=self.model_name,
            dimension=1024,
        )


@pytest.fixture
def ownership_data():
    engine = create_engine(str(settings.database_url))
    session = Session(engine)
    marker = uuid4().hex[:12]
    user_a = User(
        username=f"rag_db_a_{marker}",
        nickname="RAG DB A",
        password_hash="test",
        is_active=True,
    )
    user_b = User(
        username=f"rag_db_b_{marker}",
        nickname="RAG DB B",
        password_hash="test",
        is_active=True,
    )
    session.add_all([user_a, user_b])
    session.commit()

    documents = []
    for owner, suffix in ((user_a, "a"), (user_b, "b"), (None, "legacy")):
        document = Document(
            user_id=owner.id if owner else None,
            original_name=f"rag-db-{suffix}-{marker}.txt",
            safe_name=f"rag-db-{suffix}-{marker}.txt",
            mime_type="text/plain",
            size_bytes=20,
            sha256=(suffix + marker).ljust(64, suffix[0]),
            status="succeeded",
        )
        session.add(document)
        session.flush()
        session.add(DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            content=f"private content {suffix}",
            start_char=0,
            end_char=20,
            embedding_model="permission-test",
            embedding_dimension=1024,
            embedding=[1.0] + [0.0] * 1023,
            chunk_metadata={},
        ))
        documents.append(document)
    session.commit()

    try:
        yield session, user_a, user_b, documents
    finally:
        session.rollback()
        for document in documents:
            stored = session.get(Document, document.id)
            if stored is not None:
                session.delete(stored)
        session.commit()
        for user in (user_a, user_b):
            stored = session.get(User, user.id)
            if stored is not None:
                session.delete(stored)
        session.commit()
        session.close()
        engine.dispose()


@pytest.mark.anyio
async def test_retrieval_filters_by_current_user(ownership_data):
    session, user_a, user_b, documents = ownership_data
    document_a, document_b, legacy_document = documents
    provider = CountingEmbeddingProvider()

    hits = await search(
        session=session,
        embedding_provider=provider,
        question="private content",
        document_ids=[document_a.id, document_b.id, legacy_document.id],
        current_user_id=user_b.id,
    )

    assert provider.call_count == 1
    assert hits
    assert {hit.document_id for hit in hits} == {document_b.id}
    assert all(hit.document_id != document_a.id for hit in hits)
    assert all(hit.document_id != legacy_document.id for hit in hits)


@pytest.mark.anyio
async def test_database_backed_rag_rejects_foreign_document_before_service(
    ownership_data,
):
    session, _, user_b, documents = ownership_data
    document_a = documents[0]
    service = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await ask_question(
            request=RagAskRequest(
                question="private question",
                document_ids=[document_a.id],
            ),
            current_user=user_b,
            db=session,
            rag_service=service,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Document not found"
    service.answer.assert_not_awaited()


@pytest.mark.anyio
async def test_database_backed_rag_rejects_mixed_ownership_before_service(
    ownership_data,
):
    session, user_a, _, documents = ownership_data
    document_a, document_b, _ = documents
    service = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await ask_question(
            request=RagAskRequest(
                question="mixed question",
                document_ids=[document_a.id, document_b.id],
            ),
            current_user=user_a,
            db=session,
            rag_service=service,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Document not found"
    service.answer.assert_not_awaited()


@pytest.mark.anyio
async def test_database_backed_rag_rejects_null_owner_before_service(
    ownership_data,
):
    session, user_a, _, documents = ownership_data
    legacy_document = documents[2]
    service = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await ask_question(
            request=RagAskRequest(
                question="legacy question",
                document_ids=[legacy_document.id],
            ),
            current_user=user_a,
            db=session,
            rag_service=service,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Document not found"
    service.answer.assert_not_awaited()
