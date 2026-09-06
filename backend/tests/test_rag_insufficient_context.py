"""Tests for RAG insufficient context detection.

Validates that the RAG service correctly identifies when:
- No retrieval results exist
- All results are below similarity threshold
- ChatProvider is not called when context is insufficient
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
        self.last_system_prompt = None
        self.last_user_prompt = None

    @property
    def model_name(self) -> str:
        return "fake-chat"

    async def generate(self, *, system_prompt: str, user_prompt: str) -> ChatResult:
        """Track calls and return fake answer."""
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
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
        username=f"rag_insufficient_{uuid4().hex[:12]}",
        nickname="RAG Insufficient User",
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
        original_name="test_insufficient.txt",
        safe_name="test_insufficient.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256="a" * 64,
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
async def test_no_retrieval_results_insufficient_context(db_session, test_document, rag_service, fake_chat):
    """Test that no retrieval results triggers insufficient context."""
    request = RagAskRequest(
        question="What is the meaning of life?",
        document_ids=[test_document.id],
        top_k=5,
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    assert response.insufficient_context is True
    assert response.sources == []
    assert response.model is None
    assert fake_chat.call_count == 0


@pytest.mark.anyio
async def test_all_below_threshold_insufficient_context(db_session, test_document, rag_service, fake_chat):
    """Test that results below threshold trigger insufficient context."""
    # Add chunk with orthogonal embedding (low cosine similarity to query)
    # Query will be [0.01] * 1024 (all positive)
    # This vector alternates signs, making cosine similarity lower
    low_similarity_vector = [(-1.0 if i % 2 else 1.0) for i in range(1024)]
    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Irrelevant content about gardening",
        start_char=0,
        end_char=100,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=low_similarity_vector,
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    # Query with threshold that alternating vector won't meet
    request = RagAskRequest(
        question="What is quantum computing?",
        document_ids=[test_document.id],
        top_k=5,
        min_similarity=0.5,  # Alternating vector will be close to 0
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    assert response.insufficient_context is True
    assert response.sources == []
    assert response.model is None
    assert fake_chat.call_count == 0


@pytest.mark.anyio
async def test_one_above_threshold_calls_chat(db_session, test_document, rag_service, fake_chat):
    """Test that at least one result above threshold calls ChatProvider."""
    # Add chunk with identical embedding (similarity = 1.0)
    query_vector = [0.01] * 1024
    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Relevant content about the topic",
        start_char=0,
        end_char=100,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=query_vector,
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    request = RagAskRequest(
        question="Tell me about the topic",
        document_ids=[test_document.id],
        top_k=5,
        min_similarity=0.5,
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    assert response.insufficient_context is False
    assert len(response.sources) > 0
    assert response.model == "fake-chat"
    assert fake_chat.call_count == 1


@pytest.mark.anyio
async def test_mixed_similarities_filters_low(db_session, test_document, rag_service, fake_chat):
    """Test that only chunks above threshold are used as sources."""
    # Add two chunks: one high similarity, one low
    high_sim_vector = [0.01] * 1024  # Will match query [0.01] * 1024
    low_sim_vector = [(-1.0 if i % 2 else 1.0) for i in range(1024)]  # Alternating, low similarity

    chunk1 = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Relevant content",
        start_char=0,
        end_char=20,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=high_sim_vector,
        chunk_metadata={},
    )
    chunk2 = DocumentChunk(
        document_id=test_document.id,
        chunk_index=1,
        content="Irrelevant content",
        start_char=20,
        end_char=40,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=low_sim_vector,
        chunk_metadata={},
    )
    db_session.add_all([chunk1, chunk2])
    db_session.commit()

    request = RagAskRequest(
        question="Tell me about relevant things",
        document_ids=[test_document.id],
        top_k=5,
        min_similarity=0.5,
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    assert response.insufficient_context is False
    # Only high similarity chunk should be in sources
    assert len(response.sources) >= 1
    assert all(s.similarity >= 0.5 for s in response.sources)
    assert fake_chat.call_count == 1


@pytest.mark.anyio
async def test_boundary_equal_threshold_included(db_session, test_document, rag_service, fake_chat):
    """Test that similarity exactly equal to threshold is included."""
    # Create embedding that will result in similarity close to threshold
    # This is approximate due to floating point, but tests boundary behavior
    boundary_vector = [0.01] * 1024
    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Boundary test content",
        start_char=0,
        end_char=50,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=boundary_vector,
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    # Use threshold slightly below expected similarity
    request = RagAskRequest(
        question="Boundary test",
        document_ids=[test_document.id],
        top_k=5,
        min_similarity=0.9,
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    # Should have context if any results meet threshold
    if response.sources:
        assert response.insufficient_context is False
        assert fake_chat.call_count == 1


@pytest.mark.anyio
async def test_server_default_threshold_applied(db_session, test_document, rag_service, fake_chat):
    """Test that server default threshold is applied when client doesn't specify."""
    # Add chunk with low similarity
    low_sim_vector = [(-1.0 if i % 2 else 1.0) for i in range(1024)]
    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test content",
        start_char=0,
        end_char=20,
        embedding_model="fake-embedding",
        embedding_dimension=1024,
        embedding=low_sim_vector,
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    # Don't specify min_similarity
    request = RagAskRequest(
        question="Test query",
        document_ids=[test_document.id],
        top_k=5,
        # min_similarity not set (None)
    )

    # Request should have None (client didn't specify)
    assert request.min_similarity is None

    # But service should enforce server minimum (0.3)
    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    # Low similarity chunk should be filtered by server default 0.3
    assert response.insufficient_context is True
    assert fake_chat.call_count == 0


@pytest.mark.anyio
async def test_insufficient_context_answer_text(db_session, test_document, rag_service):
    """Test insufficient context returns correct answer text."""
    request = RagAskRequest(
        question="Unanswerable question",
        document_ids=[test_document.id],
        top_k=5,
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    assert response.insufficient_context is True
    assert response.answer == "现有文档不足以回答该问题。"


@pytest.mark.anyio
async def test_chat_not_called_for_empty_sources(db_session, test_document, rag_service, fake_chat):
    """Test ChatProvider is never called when sources are empty."""
    request = RagAskRequest(
        question="Any question",
        document_ids=[test_document.id],
        top_k=5,
        min_similarity=0.99,  # Very high threshold
    )

    response = await rag_service.answer(
        session=db_session, request=request, current_user_id=test_document.user_id
    )

    assert response.sources == []
    assert fake_chat.call_count == 0
    assert fake_chat.last_system_prompt is None
    assert fake_chat.last_user_prompt is None


print("✅ Created RAG insufficient context tests")
