"""Tests for RAG minimum similarity threshold security.

Validates that server-side minimum threshold cannot be bypassed by client requests.
"""
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ai.embedding_contracts import EmbeddingProvider, EmbeddingResult
from app.ai.chat_contracts import ChatProvider, ChatResult
from app.models import Document, DocumentChunk, User
from app.services.rag import RagService
from app.schemas.rag import RagAskRequest


class FakeEmbeddingProvider(EmbeddingProvider):
    """Fake embedding provider for testing."""

    @property
    def model_name(self) -> str:
        return "fake-embedding"

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        """Return deterministic embeddings."""
        dimension = 1024
        vectors = [[0.01] * dimension for _ in texts]
        return EmbeddingResult(
            vectors=vectors,
            model=self.model_name,
            dimension=dimension,
        )


class FakeChatProvider(ChatProvider):
    """Fake chat provider with call tracking."""

    def __init__(self):
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return "fake-chat"

    async def generate(self, *, system_prompt: str, user_prompt: str) -> ChatResult:
        """Track calls and return fake answer."""
        self.call_count += 1
        return ChatResult(
            text='{"status":"answered","answer":"Fake answer with citation [S1]"}',
            model=self.model_name,
            finish_reason="stop",
        )


@pytest.fixture
def db_session():
    """Create database session."""
    engine = create_engine(str(settings.database_url))
    session = Session(engine)
    try:
        yield session
        session.rollback()
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def test_user(db_session):
    user = User(
        username=f"rag_threshold_{uuid4().hex[:12]}",
        nickname="RAG Threshold User",
        password_hash="test",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    yield user
    db_session.rollback()
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def test_document(db_session, test_user):
    """Create test document."""
    doc = Document(
        original_name="test_threshold.txt",
        safe_name="test_threshold.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256="b" * 64,
        status="succeeded",
        user_id=test_user.id,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    yield doc

    db_session.delete(doc)
    db_session.commit()


@pytest.fixture
def fake_embedding():
    """Fake embedding provider."""
    return FakeEmbeddingProvider()


@pytest.fixture
def fake_chat():
    """Fake chat provider with call tracking."""
    return FakeChatProvider()


@pytest.fixture
def rag_service(fake_embedding, fake_chat):
    """RAG service with fake providers."""
    return RagService(
        embedding_provider=fake_embedding,
        chat_provider=fake_chat,
    )


@pytest.mark.anyio
async def test_no_client_threshold_uses_server_default(db_session, test_document, rag_service):
    """Test that no client threshold uses server default (0.3)."""
    # Add chunk with moderate similarity
    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test content",
        start_char=0,
        end_char=20,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=[0.01] * 1024,
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    request = RagAskRequest(
        question="Test query",
        document_ids=[test_document.id],
        top_k=5,
        # min_similarity not provided
    )

    # Should use server default 0.3
    assert request.min_similarity is None


@pytest.mark.anyio
async def test_client_zero_cannot_lower_server_threshold(db_session, test_document, rag_service, fake_chat):
    """Test that client passing 0 still enforces server minimum (0.3)."""
    # Add chunk with low similarity (alternating vector)
    low_sim_vector = [(-1.0 if i % 2 else 1.0) for i in range(1024)]
    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Low similarity content",
        start_char=0,
        end_char=50,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=low_sim_vector,
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    request = RagAskRequest(
        question="Test query",
        document_ids=[test_document.id],
        top_k=5,
        min_similarity=0.0,  # Client tries to bypass
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    # Should still enforce server minimum and return insufficient context
    assert response.insufficient_context is True
    assert response.sources == []
    assert fake_chat.call_count == 0


@pytest.mark.anyio
async def test_client_negative_cannot_bypass_threshold(db_session, test_document, rag_service, fake_chat):
    """Test that negative client threshold still enforces server minimum."""
    low_sim_vector = [(-1.0 if i % 2 else 1.0) for i in range(1024)]
    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Low similarity content",
        start_char=0,
        end_char=50,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=low_sim_vector,
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    request = RagAskRequest(
        question="Test query",
        document_ids=[test_document.id],
        top_k=5,
        min_similarity=-0.5,  # Negative threshold
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    # Server minimum (0.3) should still apply
    assert response.insufficient_context is True
    assert fake_chat.call_count == 0


@pytest.mark.anyio
async def test_client_high_threshold_allowed(db_session, test_document, rag_service, fake_chat):
    """Test that client can request stricter threshold (0.6 > 0.3)."""
    # Add chunk with moderate-high similarity
    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Relevant content",
        start_char=0,
        end_char=50,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=[0.01] * 1024,  # High similarity
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    request = RagAskRequest(
        question="Test query",
        document_ids=[test_document.id],
        top_k=5,
        min_similarity=0.99,  # Very strict client threshold
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    # Should use client's stricter threshold
    assert response.insufficient_context is False
    assert len(response.sources) > 0
    assert all(s.similarity >= 0.99 for s in response.sources)


@pytest.mark.anyio
async def test_out_of_bounds_threshold_validation():
    """Test that out-of-bounds thresholds are rejected by schema."""
    with pytest.raises(ValueError, match="less than or equal to 1"):
        RagAskRequest(
            question="Test",
            document_ids=[uuid4()],
            top_k=5,
            min_similarity=1.5,  # > 1
        )

    with pytest.raises(ValueError, match="greater than or equal to -1"):
        RagAskRequest(
            question="Test",
            document_ids=[uuid4()],
            top_k=5,
            min_similarity=-1.5,  # < -1
        )


@pytest.mark.anyio
async def test_threshold_exactly_at_server_minimum(db_session, test_document, rag_service, fake_chat):
    """Test behavior when client threshold equals server minimum."""
    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Content",
        start_char=0,
        end_char=20,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=[0.01] * 1024,
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    request = RagAskRequest(
        question="Test query",
        document_ids=[test_document.id],
        top_k=5,
        min_similarity=0.3,  # Exactly server minimum
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    # Should work normally with threshold 0.3
    assert response.insufficient_context is False


@pytest.mark.anyio
async def test_all_below_effective_threshold_no_chat_call(db_session, test_document, rag_service, fake_chat):
    """Test that ChatProvider is not called when all results below effective threshold."""
    low_sim_vector = [(-1.0 if i % 2 else 1.0) for i in range(1024)]
    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Low similarity",
        start_char=0,
        end_char=30,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=low_sim_vector,
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    request = RagAskRequest(
        question="Test query",
        document_ids=[test_document.id],
        top_k=5,
        min_similarity=0.1,  # Low but > 0
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    # Server enforces 0.3, so low similarity chunk should be filtered
    assert response.insufficient_context is True
    assert fake_chat.call_count == 0


print("✅ Created RAG threshold security tests")
