"""Transaction and concurrency tests for RAG services."""
import pytest
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ai.embedding_contracts import EmbeddingProvider, EmbeddingResult
from app.models import Document, DocumentChunk, ProcessingJob
from app.parsers.registry import ParserRegistry
from app.chunking import RecursiveCharacterChunker
from app.services import (
    ingest_document,
    DocumentAlreadyProcessingError,
)


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic fake provider."""

    def __init__(self, dimension=1024, fail=False):
        self._model = "text-embedding-v3"
        self._dimension = dimension
        self.fail = fail

    @property
    def model_name(self) -> str:
        return self._model

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        if self.fail:
            raise RuntimeError("Fake embedding failure")

        import math
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


@pytest.fixture(scope="function")
def session():
    """Create a database session."""
    engine = create_engine(str(settings.database_url))
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def parser_registry():
    return ParserRegistry()


@pytest.fixture
def chunker():
    return RecursiveCharacterChunker(chunk_size=200, chunk_overlap=30)


@pytest.fixture
def test_document(session):
    """Create a test document."""
    doc = Document(
        id=uuid4(),
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
async def test_ingestion_preserves_old_chunks_when_embedding_fails(
    session,
    test_document,
    parser_registry,
    chunker,
):
    """Test that old chunks are preserved when embedding fails."""
    # Step 1: Create and commit old chunks
    old_provider = FakeEmbeddingProvider()
    content = b"# Old Content\n\nThis is the old version of the document."

    result = await ingest_document(
        session=session,
        document_id=test_document.id,
        content=content,
        filename=test_document.original_name,
        mime_type=test_document.mime_type,
        parser_registry=parser_registry,
        chunker=chunker,
        embedding_provider=old_provider,
    )

    old_chunk_count = result.chunk_count

    # Step 2: Save old chunk details
    old_chunks = session.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == test_document.id
        ).order_by(DocumentChunk.chunk_index)
    ).scalars().all()

    old_chunk_ids = [chunk.id for chunk in old_chunks]
    old_chunk_contents = [chunk.content for chunk in old_chunks]

    assert len(old_chunks) == old_chunk_count
    assert len(old_chunks) > 0

    # Step 3: Attempt re-ingestion with failing provider
    failing_provider = FakeEmbeddingProvider(fail=True)
    new_content = b"# New Content\n\nThis is the new version that will fail."

    with pytest.raises(Exception):
        await ingest_document(
            session=session,
            document_id=test_document.id,
            content=new_content,
            filename=test_document.original_name,
            mime_type=test_document.mime_type,
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=failing_provider,
        )

    # Step 4: Verify old chunks are still intact in new session
    session.rollback()  # Clear any pending state

    current_chunks = session.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == test_document.id
        ).order_by(DocumentChunk.chunk_index)
    ).scalars().all()

    # Verify old chunks preserved
    assert len(current_chunks) == old_chunk_count
    current_chunk_ids = [chunk.id for chunk in current_chunks]
    current_chunk_contents = [chunk.content for chunk in current_chunks]

    assert current_chunk_ids == old_chunk_ids
    assert current_chunk_contents == old_chunk_contents

    # Verify document status is failed
    session.refresh(test_document)
    assert test_document.status == "failed"


@pytest.mark.anyio
async def test_ingestion_preserves_old_chunks_when_write_fails(
    session,
    test_document,
    parser_registry,
    chunker,
):
    """Test that old chunks are preserved when database write fails."""
    # Step 1: Create old chunks
    old_provider = FakeEmbeddingProvider()
    content = b"# Old Content\n\nThis is the old version."

    result = await ingest_document(
        session=session,
        document_id=test_document.id,
        content=content,
        filename=test_document.original_name,
        mime_type=test_document.mime_type,
        parser_registry=parser_registry,
        chunker=chunker,
        embedding_provider=old_provider,
    )

    old_chunk_count = result.chunk_count

    # Save old chunk IDs
    old_chunks = session.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == test_document.id
        )
    ).scalars().all()

    old_chunk_ids = {chunk.id for chunk in old_chunks}
    old_chunk_contents = [chunk.content for chunk in old_chunks]

    # Step 2: Create provider that returns invalid dimension to cause write failure
    bad_provider = FakeEmbeddingProvider(dimension=512)  # Wrong dimension
    new_content = b"# New Content\n\nThis should fail to write."

    with pytest.raises(Exception):
        await ingest_document(
            session=session,
            document_id=test_document.id,
            content=new_content,
            filename=test_document.original_name,
            mime_type=test_document.mime_type,
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=bad_provider,
        )

    # Step 3: Verify old chunks still exist
    session.rollback()

    current_chunks = session.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == test_document.id
        )
    ).scalars().all()

    assert len(current_chunks) == old_chunk_count
    current_chunk_ids = {chunk.id for chunk in current_chunks}
    current_chunk_contents = [chunk.content for chunk in current_chunks]

    # Old chunks preserved
    assert current_chunk_ids == old_chunk_ids
    assert current_chunk_contents == old_chunk_contents


@pytest.mark.anyio
async def test_concurrent_ingestion_rejected(
    parser_registry,
    chunker,
):
    """Test that concurrent ingestion of same document is rejected."""
    # Create test document
    engine = create_engine(str(settings.database_url))
    session1 = Session(engine)
    session2 = Session(engine)

    doc = Document(
        id=uuid4(),
        original_name=f"test_{uuid4().hex[:8]}.md",
        safe_name=f"test_{uuid4().hex[:8]}.md",
        mime_type="text/markdown",
        size_bytes=100,
        sha256=f"test_{uuid4().hex}",
        status="pending",
    )
    session1.add(doc)
    session1.commit()
    doc_id = doc.id

    try:
        # First ingestion starts
        provider1 = FakeEmbeddingProvider()
        content = b"# Test\n\nContent"

        # Start first ingestion - this will set status to processing
        result1 = await ingest_document(
            session=session1,
            document_id=doc_id,
            content=content,
            filename=doc.original_name,
            mime_type=doc.mime_type,
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=provider1,
        )

        # Refresh document in session2
        doc2 = session2.get(Document, doc_id)
        assert doc2.status == "succeeded"

        # Second ingestion should be rejected if document is processing
        # But since first already succeeded, let's test with a fresh document
        doc3 = Document(
            id=uuid4(),
            original_name=f"test_{uuid4().hex[:8]}.md",
            safe_name=f"test_{uuid4().hex[:8]}.md",
            mime_type="text/markdown",
            size_bytes=100,
            sha256=f"test_{uuid4().hex}",
            status="processing",  # Already processing
        )
        session2.add(doc3)
        session2.commit()
        doc3_id = doc3.id

        provider2 = FakeEmbeddingProvider()

        # Should be rejected
        with pytest.raises(DocumentAlreadyProcessingError):
            await ingest_document(
                session=session2,
                document_id=doc3_id,
                content=content,
                filename=doc3.original_name,
                mime_type=doc3.mime_type,
                parser_registry=parser_registry,
                chunker=chunker,
                embedding_provider=provider2,
            )

        # Cleanup doc3
        session2.rollback()
        doc3_to_delete = session2.get(Document, doc3_id)
        if doc3_to_delete:
            session2.delete(doc3_to_delete)
            session2.commit()

    finally:
        # Cleanup
        session1.rollback()
        session2.rollback()

        doc_to_delete = session1.get(Document, doc_id)
        if doc_to_delete:
            session1.delete(doc_to_delete)
            session1.commit()

        session1.close()
        session2.close()
