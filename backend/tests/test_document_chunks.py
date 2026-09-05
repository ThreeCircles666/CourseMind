"""Integration tests for document_chunks table and model.

These tests require PostgreSQL with pgvector extension.
They verify table structure, constraints, relationships, and vector operations.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Document, DocumentChunk, EMBEDDING_DIMENSION


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    engine = create_engine(str(settings.database_url))
    session = Session(engine)
    try:
        yield session
        session.rollback()
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def test_document(db_session):
    """Create a test document."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    doc = Document(
        original_name=f"test_{unique_id}.txt",
        safe_name=f"test_{unique_id}.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256=f"test{unique_id}" + "0" * (64 - 4 - len(unique_id)),
        status="pending",
    )
    db_session.add(doc)
    db_session.commit()
    doc_id = doc.id  # Save ID for cleanup
    db_session.refresh(doc)
    yield doc
    # Cleanup - use a fresh query to avoid detached instance issues
    db_session.rollback()  # Clear any pending changes
    doc_to_delete = db_session.get(Document, doc_id)
    if doc_to_delete:
        db_session.delete(doc_to_delete)
        db_session.commit()


def test_table_exists(db_session):
    """Test document_chunks table exists."""
    result = db_session.execute(select(DocumentChunk).limit(1))
    assert result is not None


def test_create_chunk(db_session, test_document):
    """Test creating a document chunk with valid data."""
    vector = [1.0] + [0.0] * (EMBEDDING_DIMENSION - 1)

    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test content",
        page_number=1,
        title_path=["Chapter 1"],
        start_char=0,
        end_char=12,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={"length": 12},
    )

    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)

    assert chunk.id is not None
    assert chunk.document_id == test_document.id
    assert chunk.chunk_index == 0
    assert chunk.content == "Test content"
    assert chunk.embedding_dimension == 1024
    assert len(chunk.embedding) == 1024


def test_chunk_index_nonnegative(db_session, test_document):
    """Test chunk_index must be >= 0."""
    from sqlalchemy.exc import IntegrityError

    vector = [1.0] * EMBEDDING_DIMENSION

    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=-1,
        content="Test",
        start_char=0,
        end_char=4,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={},
    )

    db_session.add(chunk)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_content_not_empty(db_session, test_document):
    """Test content cannot be empty or whitespace."""
    from sqlalchemy.exc import IntegrityError

    vector = [1.0] * EMBEDDING_DIMENSION

    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="   ",
        start_char=0,
        end_char=3,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={},
    )

    db_session.add(chunk)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_page_number_positive(db_session, test_document):
    """Test page_number must be NULL or > 0."""
    from sqlalchemy.exc import IntegrityError

    vector = [1.0] * EMBEDDING_DIMENSION

    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test",
        page_number=0,
        start_char=0,
        end_char=4,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={},
    )

    db_session.add(chunk)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_char_range_valid(db_session, test_document):
    """Test end_char must be > start_char."""
    from sqlalchemy.exc import IntegrityError

    vector = [1.0] * EMBEDDING_DIMENSION

    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test",
        start_char=10,
        end_char=10,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={},
    )

    db_session.add(chunk)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_embedding_dimension_fixed(db_session, test_document):
    """Test embedding_dimension must equal 1024."""
    from sqlalchemy.exc import IntegrityError

    # Create a VALID 1024-dim vector but claim wrong dimension
    # This should be rejected by CHECK constraint, not vector type
    vector = [1.0] * EMBEDDING_DIMENSION  # Correct size!

    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test",
        start_char=0,
        end_char=4,
        embedding_model="text-embedding-v3",
        embedding_dimension=512,  # Wrong metadata
        embedding=vector,  # But correct vector size
        chunk_metadata={},
    )

    db_session.add(chunk)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_vector_wrong_size(db_session, test_document):
    """Test vector must have exactly 1024 dimensions."""
    vector = [1.0] * 512

    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test",
        start_char=0,
        end_char=4,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={},
    )

    db_session.add(chunk)
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()


def test_unique_document_index_model(db_session, test_document):
    """Test unique constraint on (document_id, chunk_index, embedding_model)."""
    from sqlalchemy.exc import IntegrityError

    vector = [1.0] * EMBEDDING_DIMENSION

    chunk1 = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test 1",
        start_char=0,
        end_char=6,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={},
    )

    db_session.add(chunk1)
    db_session.commit()

    chunk2 = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test 2",
        start_char=0,
        end_char=6,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={},
    )

    db_session.add(chunk2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete(db_session):
    """Test deleting document cascades to chunks."""
    # Create document
    doc = Document(
        original_name="cascade_test.txt",
        safe_name="cascade_test.txt",
        mime_type="text/plain",
        size_bytes=100,
        sha256="cascade" + "0" * 57,
        status="pending",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # Create chunks
    vector = [1.0] * EMBEDDING_DIMENSION
    for i in range(3):
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=i,
            content=f"Chunk {i}",
            start_char=i * 10,
            end_char=(i + 1) * 10,
            embedding_model="text-embedding-v3",
            embedding_dimension=EMBEDDING_DIMENSION,
            embedding=vector,
            chunk_metadata={},
        )
        db_session.add(chunk)

    db_session.commit()

    # Verify chunks exist
    result = db_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    )
    chunks_before = result.scalars().all()
    assert len(chunks_before) == 3

    # Delete document
    db_session.delete(doc)
    db_session.commit()

    # Verify chunks are gone
    result = db_session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    )
    chunks_after = result.scalars().all()
    assert len(chunks_after) == 0


def test_cosine_distance_query(db_session, test_document):
    """Test cosine distance query with <=> operator."""
    # Create test vectors
    vector_a = [1.0] + [0.0] * (EMBEDDING_DIMENSION - 1)
    vector_b = [0.9, 0.1] + [0.0] * (EMBEDDING_DIMENSION - 2)
    vector_c = [0.0, 1.0] + [0.0] * (EMBEDDING_DIMENSION - 2)

    chunks = []
    for i, vec in enumerate([vector_a, vector_b, vector_c]):
        chunk = DocumentChunk(
            document_id=test_document.id,
            chunk_index=i,
            content=f"Content {i}",
            start_char=i * 10,
            end_char=(i + 1) * 10,
            embedding_model="text-embedding-v3",
            embedding_dimension=EMBEDDING_DIMENSION,
            embedding=vec,
            chunk_metadata={},
        )
        db_session.add(chunk)
        chunks.append(chunk)

    db_session.commit()

    # Query with vector_a
    query_vector = vector_a

    result = db_session.execute(
        text("""
            SELECT chunk_index, embedding <=> CAST(:query as vector) as distance
            FROM document_chunks
            WHERE document_id = :doc_id
            ORDER BY distance ASC
        """),
        {"query": str(query_vector), "doc_id": str(test_document.id)}
    )

    rows = result.all()
    assert len(rows) == 3

    # First should be vector_a itself (distance ~0)
    assert rows[0][0] == 0
    assert rows[0][1] < 0.01

    # Second should be vector_b (more similar than vector_c)
    assert rows[1][0] == 1

    # Third should be vector_c
    assert rows[2][0] == 2


def test_title_path_array(db_session, test_document):
    """Test title_path ARRAY field."""
    vector = [1.0] * EMBEDDING_DIMENSION

    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test",
        title_path=["Chapter 1", "Section 1.1", "Subsection"],
        start_char=0,
        end_char=4,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={},
    )

    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)

    assert chunk.title_path == ["Chapter 1", "Section 1.1", "Subsection"]


def test_metadata_jsonb(db_session, test_document):
    """Test metadata JSONB field."""
    vector = [1.0] * EMBEDDING_DIMENSION

    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test",
        start_char=0,
        end_char=4,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={"length": 4, "tags": ["important"]},
    )

    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)

    assert chunk.chunk_metadata["length"] == 4
    assert chunk.chunk_metadata["tags"] == ["important"]




@pytest.mark.parametrize("wrong_dimension", [1023, 1025])
def test_vector_dimension_mismatch(db_session, test_document, wrong_dimension):
    """Test vector must have exactly 1024 dimensions."""
    vector = [1.0] * wrong_dimension

    chunk = DocumentChunk(
        document_id=test_document.id,
        chunk_index=0,
        content="Test",
        start_char=0,
        end_char=4,
        embedding_model="text-embedding-v3",
        embedding_dimension=EMBEDDING_DIMENSION,
        embedding=vector,
        chunk_metadata={},
    )

    db_session.add(chunk)
    with pytest.raises(Exception) as exc_info:
        db_session.commit()
    # Should be DataError from pgvector
    assert "dimension" in str(exc_info.value).lower()
    db_session.rollback()
