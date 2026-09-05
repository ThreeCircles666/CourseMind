"""Additional contract and edge case tests for RAG services."""
import math
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ai.embedding_contracts import EmbeddingProvider, EmbeddingResult
from app.models import Document, DocumentChunk, User
from app.parsers.registry import ParserRegistry
from app.chunking import RecursiveCharacterChunker
from app.services import (
    ingest_document,
    search,
    ValidationError,
    IngestionError,
)


@pytest.fixture(scope="function")
def session():
    """Create a database session for testing."""
    engine = create_engine(str(settings.database_url))
    session = Session(engine)
    yield session
    session.close()


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic fake embedding provider for testing."""

    def __init__(self, dimension=1024, fail=False):
        self._model = "text-embedding-v3"
        self._dimension = dimension
        self.fail = fail

    @property
    def model_name(self) -> str:
        return self._model

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        """Generate deterministic embeddings based on text hash."""
        if self.fail:
            raise RuntimeError("Fake embedding failure")

        vectors = []
        for text in texts:
            seed = hash(text) % 10000
            vector = []
            for i in range(self._dimension):
                val = math.sin(seed + i * 0.1) * 0.5
                vector.append(val)

            magnitude = math.sqrt(sum(v * v for v in vector))
            vector = [v / magnitude for v in vector]

            vectors.append(vector)

        return EmbeddingResult(
            vectors=vectors,
            model=self._model,
            dimension=self._dimension,
        )


@pytest.fixture
def parser_registry():
    return ParserRegistry()


@pytest.fixture
def chunker():
    return RecursiveCharacterChunker(chunk_size=200, chunk_overlap=30)


@pytest.fixture
def fake_provider():
    return FakeEmbeddingProvider()


@pytest.fixture
def test_user(session):
    user = User(
        username=f"rag_contract_{uuid4().hex[:12]}",
        nickname="RAG Contract User",
        password_hash="test",
        is_active=True,
    )
    session.add(user)
    session.commit()
    yield user
    session.rollback()
    session.delete(user)
    session.commit()


@pytest.fixture
def test_document(session, test_user):
    """Create a test document."""
    doc = Document(
        id=uuid4(),
        original_name=f"test_{uuid4().hex[:8]}.md",
        safe_name=f"test_{uuid4().hex[:8]}.md",
        mime_type="text/markdown",
        size_bytes=100,
        sha256=f"test_{uuid4().hex}",
        status="pending",
        user_id=test_user.id,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    doc_id = doc.id
    yield doc

    # Cleanup
    session.rollback()
    doc_to_delete = session.get(Document, doc_id)
    if doc_to_delete:
        session.delete(doc_to_delete)
        session.commit()


@pytest.mark.anyio
async def test_embedding_result_model_mismatch_rejected(
    session,
    test_document,
    parser_registry,
    chunker,
):
    """Test that model mismatch in EmbeddingResult is rejected."""
    # Create a provider that returns wrong model
    provider = AsyncMock()
    provider.model_name = "text-embedding-v3"
    provider.embed.return_value = EmbeddingResult(
        vectors=[[0.1] * 1024],
        model="wrong-model",  # Mismatch
        dimension=1024,
    )

    content = b"# Test\n\nContent"

    with pytest.raises(IngestionError):
        await ingest_document(
            session=session,
            document_id=test_document.id,
            content=content,
            filename=test_document.original_name,
            mime_type=test_document.mime_type,
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=provider,
        )

    # Verify no chunks were written
    chunks = session.query(DocumentChunk).filter_by(
        document_id=test_document.id
    ).all()
    assert len(chunks) == 0


@pytest.mark.anyio
async def test_embedding_result_dimension_mismatch_rejected(
    session,
    test_document,
    parser_registry,
    chunker,
):
    """Test that dimension mismatch is rejected."""
    provider = AsyncMock()
    provider.model_name = "text-embedding-v3"
    provider.embed.return_value = EmbeddingResult(
        vectors=[[0.1] * 1024],
        model="text-embedding-v3",
        dimension=768,  # Wrong dimension
    )

    content = b"# Test\n\nContent"

    with pytest.raises(IngestionError):
        await ingest_document(
            session=session,
            document_id=test_document.id,
            content=content,
            filename=test_document.original_name,
            mime_type=test_document.mime_type,
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=provider,
        )

    # No chunks written
    chunks = session.query(DocumentChunk).filter_by(
        document_id=test_document.id
    ).all()
    assert len(chunks) == 0


@pytest.mark.anyio
async def test_embedding_vector_count_mismatch_rejected(
    session,
    test_document,
    parser_registry,
    chunker,
):
    """Test that vector count mismatch is rejected."""
    provider = AsyncMock()
    provider.model_name = "text-embedding-v3"
    # Return fewer vectors than chunks
    provider.embed.return_value = EmbeddingResult(
        vectors=[[0.1] * 1024],  # Only 1 vector
        model="text-embedding-v3",
        dimension=1024,
    )

    # Use longer content to ensure multiple chunks
    content = b"""# Test Document

This is the first paragraph with enough content to create a chunk.
We need to make sure this content is long enough to generate multiple chunks.

# Another Section

This is the second section with more content.
We want to ensure that the chunker creates at least two separate chunks from this document.
This way we can test that the vector count mismatch is properly detected.
"""

    with pytest.raises(IngestionError):
        await ingest_document(
            session=session,
            document_id=test_document.id,
            content=content,
            filename=test_document.original_name,
            mime_type=test_document.mime_type,
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=provider,
        )

    # No chunks written
    chunks = session.query(DocumentChunk).filter_by(
        document_id=test_document.id
    ).all()
    assert len(chunks) == 0


@pytest.mark.anyio
async def test_empty_document_ids_does_not_call_provider(
    session,
):
    """Test that empty document_ids returns empty without calling provider."""
    provider = AsyncMock()
    provider.model_name = "text-embedding-v3"

    hits = await search(
        session=session,
        embedding_provider=provider,
        question="test question",
        top_k=5,
        document_ids=[],
        current_user_id=uuid4(),
    )

    assert len(hits) == 0
    # Provider should not have been called
    provider.embed.assert_not_called()


@pytest.mark.anyio
async def test_ingestion_awaits_embedding_provider(
    session,
    test_document,
    parser_registry,
    chunker,
):
    """Test that embed() is properly awaited."""
    provider = AsyncMock()
    provider.model_name = "text-embedding-v3"
    provider.embed.return_value = EmbeddingResult(
        vectors=[[0.1] * 1024],
        model="text-embedding-v3",
        dimension=1024,
    )

    content = b"# Test\n\nContent"

    await ingest_document(
        session=session,
        document_id=test_document.id,
        content=content,
        filename=test_document.original_name,
        mime_type=test_document.mime_type,
        parser_registry=parser_registry,
        chunker=chunker,
        embedding_provider=provider,
    )

    # Verify embed was awaited (called once)
    provider.embed.assert_awaited_once()


@pytest.mark.anyio
async def test_retrieval_awaits_embedding_provider(
    session,
    test_document,
    parser_registry,
    chunker,
    fake_provider,
):
    """Test that retrieval properly awaits embed()."""
    # First ingest a document
    content = b"# Test\n\nContent for search"

    await ingest_document(
        session=session,
        document_id=test_document.id,
        content=content,
        filename=test_document.original_name,
        mime_type=test_document.mime_type,
        parser_registry=parser_registry,
        chunker=chunker,
        embedding_provider=fake_provider,
    )

    # Now test retrieval with mock
    mock_provider = AsyncMock()
    mock_provider.model_name = "text-embedding-v3"
    mock_provider.embed.return_value = EmbeddingResult(
        vectors=[[0.1] * 1024],
        model="text-embedding-v3",
        dimension=1024,
    )

    await search(
        session=session,
        embedding_provider=mock_provider,
        question="test question",
        top_k=5,
        current_user_id=test_document.user_id,
    )

    # Verify embed was awaited
    mock_provider.embed.assert_awaited_once()
