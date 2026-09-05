"""Integration tests for RAG services with real PostgreSQL.

Uses fake embedding provider for deterministic testing.
Does NOT call external APIs.
"""
import math
from uuid import uuid4, UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ai.embedding_contracts import EmbeddingProvider, EmbeddingResult
from app.models import Document, ProcessingJob, DocumentChunk, User
from app.parsers.registry import ParserRegistry
from app.chunking import RecursiveCharacterChunker
from app.services import (
    ingest_document,
    search,
    DocumentNotFoundError,
    DocumentAlreadyProcessingError,
    ProtectedDocumentError,
    ValidationError,
    InvalidQueryError,
    PROTECTED_DOCUMENT_ID,
)


@pytest.fixture(scope="function")
def session():
    """Create a database session for testing."""
    engine = create_engine(str(settings.database_url))
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def test_user(session):
    """Create a test user for RAG tests."""
    user = User(
        username=f"test_rag_user_{uuid4().hex[:8]}",
        nickname="Test RAG User",
        password_hash="$2b$12$test",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    user_id = user.id
    yield user
    session.rollback()
    stored = session.get(User, user_id)
    if stored is not None:
        session.delete(stored)
        session.commit()



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
            # Deterministic vector from text hash
            seed = hash(text) % 10000
            vector = []
            for i in range(self._dimension):
                val = math.sin(seed + i * 0.1) * 0.5
                vector.append(val)

            # Normalize to unit length (cosine similarity ready)
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
async def test_document(session, test_user):
    """Create a test document owned by test_user."""
    doc = Document(
        id=uuid4(),
        user_id=test_user.id,
        original_name=f"test_{uuid4().hex[:8]}.md",
        safe_name=f"test_{uuid4().hex[:8]}.md",
        mime_type="text/markdown",
        size_bytes=100,
        sha256=f"test_{uuid4().hex}",
        status="pending",
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
async def test_ingest_document_success(
    session,
    test_document,
    parser_registry,
    chunker,
    fake_provider
):
    """Test successful document ingestion."""
    content = b"""# Test Document

This is a test document for RAG pipeline.
It has multiple paragraphs to generate chunks.

# Another Section

More content here to ensure we get multiple chunks.
"""

    result = await ingest_document(
        session=session,
        document_id=test_document.id,
        content=content,
        filename=test_document.original_name,
        mime_type=test_document.mime_type,
        parser_registry=parser_registry,
        chunker=chunker,
        embedding_provider=fake_provider,
    )

    # Check result
    assert result.document_id == test_document.id
    assert result.chunk_count > 0
    assert result.embedding_model == "text-embedding-v3"
    assert result.embedding_dimension == 1024

    # Check database state
    session.refresh(test_document)
    assert test_document.status == "succeeded"
    assert test_document.error_message is None

    # Check job created
    job = session.get(ProcessingJob, result.job_id)
    assert job is not None
    assert job.status == "succeeded"
    assert job.finished_at is not None

    # Check chunks
    chunks = session.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == test_document.id
        ).order_by(DocumentChunk.chunk_index)
    ).scalars().all()

    assert len(chunks) == result.chunk_count

    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert len(chunk.content) > 0
        assert chunk.embedding_model == "text-embedding-v3"
        assert chunk.embedding_dimension == 1024
        assert len(chunk.embedding) == 1024


@pytest.mark.anyio
async def test_ingest_idempotency(
    session,
    test_document,
    parser_registry,
    chunker,
    fake_provider
):
    """Test that re-ingesting doesn't create duplicates."""
    content = b"# Test\n\nContent for idempotency test."

    # First ingestion
    result1 = await ingest_document(
        session=session,
        document_id=test_document.id,
        content=content,
        filename=test_document.original_name,
        mime_type=test_document.mime_type,
        parser_registry=parser_registry,
        chunker=chunker,
        embedding_provider=fake_provider,
    )

    count1 = session.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == test_document.id
        )
    ).scalars().all()

    # Second ingestion
    result2 = await ingest_document(
        session=session,
        document_id=test_document.id,
        content=content,
        filename=test_document.original_name,
        mime_type=test_document.mime_type,
        parser_registry=parser_registry,
        chunker=chunker,
        embedding_provider=fake_provider,
    )

    count2 = session.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == test_document.id
        )
    ).scalars().all()

    # Should have same count
    assert len(count1) == len(count2)
    assert result1.chunk_count == result2.chunk_count


@pytest.mark.anyio
async def test_ingest_document_not_found(
    session,
    parser_registry,
    chunker,
    fake_provider
):
    """Test ingestion fails for non-existent document."""
    with pytest.raises(DocumentNotFoundError):
        await ingest_document(
            session=session,
            document_id=uuid4(),
            content=b"test",
            filename="test.md",
            mime_type="text/markdown",
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=fake_provider,
        )


@pytest.mark.anyio
async def test_ingest_protected_document(
    session,
    parser_registry,
    chunker,
    fake_provider
):
    """Test that protected document cannot be ingested."""
    with pytest.raises(ProtectedDocumentError):
        await ingest_document(
            session=session,
            document_id=PROTECTED_DOCUMENT_ID,
            content=b"test",
            filename="test.md",
            mime_type="text/markdown",
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=fake_provider,
        )


@pytest.mark.anyio
async def test_ingest_embedding_failure_no_partial_data(
    session,
    test_document,
    parser_registry,
    chunker
):
    """Test that embedding failure doesn't leave partial chunks."""
    failing_provider = FakeEmbeddingProvider(fail=True)

    with pytest.raises(Exception):
        await ingest_document(
            session=session,
            document_id=test_document.id,
            content=b"# Test\n\nContent",
            filename=test_document.original_name,
            mime_type=test_document.mime_type,
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=failing_provider,
        )

    # Should have no chunks
    chunks = session.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == test_document.id
        )
    ).scalars().all()

    assert len(chunks) == 0

    # Document should be marked as failed
    session.refresh(test_document)
    assert test_document.status == "failed"
    assert test_document.error_message is not None


@pytest.mark.anyio
async def test_search_success(
    session,
    test_document,
    test_user,
    parser_registry,
    chunker,
    fake_provider
):
    """Test successful search."""
    # Ingest first
    content = b"""# PostgreSQL

PostgreSQL is a powerful database system.

# Python

Python is a programming language.
"""

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

    # Search
    hits = await search(
        session=session,
        embedding_provider=fake_provider,
        question="What is PostgreSQL?",
        top_k=3,
    current_user_id=test_user.id,
    )

    assert len(hits) > 0

    for hit in hits:
        # Distance should be non-negative for cosine distance
        assert hit.distance >= 0
        # Similarity = 1 - distance, can be negative if distance > 1
        # For normalized vectors, distance should be in [0, 2]
        assert hit.distance <= 2
        # Similarity and distance relationship
        assert abs((1.0 - hit.distance) - hit.similarity) < 0.01


@pytest.mark.anyio
async def test_search_empty_question(session, test_user, fake_provider):
    """Test that empty question is rejected."""
    with pytest.raises(InvalidQueryError):
        await search(
            session=session,
            embedding_provider=fake_provider,
            question="",
            top_k=5,
        current_user_id=test_user.id,
        )


@pytest.mark.anyio
async def test_search_invalid_top_k(session, test_user, fake_provider):
    """Test that invalid top_k is rejected."""
    with pytest.raises(InvalidQueryError):
        await search(
            session=session,
            embedding_provider=fake_provider,
            question="test",
            top_k=0,
        current_user_id=test_user.id,
        )

    with pytest.raises(InvalidQueryError):
        await search(
            session=session,
            embedding_provider=fake_provider,
            question="test",
            top_k=100,
        current_user_id=test_user.id,
        )


@pytest.mark.anyio
async def test_search_empty_document_ids_returns_empty(session, test_user, fake_provider):
    """Test that empty document_ids list returns no results."""
    hits = await search(
        session=session,
        embedding_provider=fake_provider,
        question="test",
        top_k=5,
        document_ids=[],
    current_user_id=test_user.id,
    )

    assert len(hits) == 0


@pytest.mark.anyio
async def test_search_filters_by_document_ids(
    session,
    test_document,
    test_user,
    parser_registry,
    chunker,
    fake_provider
):
    """Test that document_ids filter works."""
    # Ingest
    await ingest_document(
        session=session,
        document_id=test_document.id,
        content=b"# Test\n\nContent",
        filename=test_document.original_name,
        mime_type=test_document.mime_type,
        parser_registry=parser_registry,
        chunker=chunker,
        embedding_provider=fake_provider,
    )

    # Search with correct ID
    hits1 = await search(
        session=session,
        embedding_provider=fake_provider,
        question="test",
        top_k=5,
        document_ids=[test_document.id],
    current_user_id=test_user.id,
    )

    assert len(hits1) > 0

    # Search with wrong ID
    hits2 = await search(
        session=session,
        embedding_provider=fake_provider,
        question="test",
        top_k=5,
        document_ids=[uuid4()],
    current_user_id=test_user.id,
    )

    assert len(hits2) == 0


@pytest.mark.anyio
async def test_protected_document_remains_intact(session):
    """Test that protected document exists and is not affected by tests."""
    doc = session.get(Document, PROTECTED_DOCUMENT_ID)
    assert doc is not None
    assert doc.original_name == "test2.pdf"
