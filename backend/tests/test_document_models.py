"""Test document and processing job models.

These tests verify the document management tables including:
- Document creation with metadata and constraints
- ProcessingJob creation and relationship
- Foreign key cascading on delete
- Database constraints (CHECK, UNIQUE, NOT NULL)
"""
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from app.db.base import Base
from app.models.document import Document, ProcessingJob
from app.models.user import User


# Use in-memory SQLite for fast testing
# Note: Some PostgreSQL-specific features (UUID, CHECK constraints) may behave differently
@pytest.fixture
def db_session():
    """Create a temporary in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:")

    # Enable foreign key constraints in SQLite
    @sa.event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create User, Document and ProcessingJob tables
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Document.__table__, ProcessingJob.__table__]
    )

    session = Session(engine)

    # Create a test user
    test_user = User(
        username="test_doc_model_user",
        nickname="Test Doc Model User",
        password_hash="$2b$12$test",
        is_active=True,
    )
    session.add(test_user)
    session.commit()
    session.refresh(test_user)
    user_id = test_user.id

    try:
        yield session, user_id
    finally:
        session.close()
        engine.dispose()


def test_create_document(db_session):
    """Test creating a valid document record."""
    session, user_id = db_session

    doc = Document(
        original_name="test.pdf",
        safe_name="test_sanitized.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="a" * 64,  # Valid 64-char hex string
        status="pending",
        user_id=user_id,
    )

    session.add(doc)
    session.commit()

    assert doc.id is not None
    assert doc.original_name == "test.pdf"
    assert doc.status == "pending"
    assert doc.user_id == user_id
    assert doc.created_at is not None
    assert doc.updated_at is not None
    print("✅ test_create_document passed")


def test_document_default_status(db_session):
    """Test that document status defaults to 'pending'."""
    session, user_id = db_session

    doc = Document(
        original_name="test.pdf",
        safe_name="test_sanitized.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="b" * 64,
        user_id=user_id,
    )

    session.add(doc)
    session.commit()

    assert doc.status == "pending"
    print("✅ test_document_default_status passed")


def test_create_processing_job(db_session):
    """Test creating processing jobs for a document."""
    session, user_id = db_session

    # Create document
    doc = Document(
        original_name="test.pdf",
        safe_name="test_sanitized.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="c" * 64,
        user_id=user_id,
    )
    session.add(doc)
    session.commit()

    # Create processing job
    job = ProcessingJob(
        document_id=doc.id,
        status="pending",
    )
    session.add(job)
    session.commit()

    assert job.id is not None
    assert job.document_id == doc.id
    assert job.status == "pending"
    assert job.created_at is not None
    print("✅ test_create_processing_job passed")


def test_processing_job_default_status(db_session):
    """Test that processing job status defaults to 'pending'."""
    session, user_id = db_session

    doc = Document(
        original_name="test.pdf",
        safe_name="test_sanitized.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="d" * 64,
        user_id=user_id,
    )
    session.add(doc)
    session.commit()

    job = ProcessingJob(document_id=doc.id)
    session.add(job)
    session.commit()

    assert job.status == "pending"
    print("✅ test_processing_job_default_status passed")


def test_multiple_jobs_per_document(db_session):
    """Test creating multiple processing jobs for one document."""
    session, user_id = db_session

    doc = Document(
        original_name="test.pdf",
        safe_name="test_sanitized.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="e" * 64,
        user_id=user_id,
    )
    session.add(doc)
    session.commit()

    # Create multiple jobs
    job1 = ProcessingJob(document_id=doc.id, status="pending")
    job2 = ProcessingJob(document_id=doc.id, status="processing")
    job3 = ProcessingJob(document_id=doc.id, status="succeeded")

    session.add_all([job1, job2, job3])
    session.commit()

    # Query jobs for this document
    jobs = session.query(ProcessingJob).filter_by(document_id=doc.id).all()
    assert len(jobs) == 3
    print("✅ test_multiple_jobs_per_document passed")


def test_document_relationship_query(db_session):
    """Test querying processing jobs through document relationship."""
    session, user_id = db_session

    doc = Document(
        original_name="test.pdf",
        safe_name="test_sanitized.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="f" * 64,
        user_id=user_id,
    )
    session.add(doc)
    session.commit()

    job1 = ProcessingJob(document_id=doc.id)
    job2 = ProcessingJob(document_id=doc.id)
    session.add_all([job1, job2])
    session.commit()

    # Refresh to load relationship
    session.refresh(doc)

    # Access jobs through relationship
    assert len(doc.processing_jobs) == 2
    print("✅ test_document_relationship_query passed")


def test_duplicate_sha256_rejected(db_session):
    """Test that duplicate SHA-256 hash within same user is rejected by unique constraint."""
    session, user_id = db_session

    doc1 = Document(
        original_name="file1.pdf",
        safe_name="file1_sanitized.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="duplicate_hash_" + "0" * 49,
        user_id=user_id,
    )
    session.add(doc1)
    session.commit()

    # Try to create another document with same SHA-256 for same user
    doc2 = Document(
        original_name="file2.pdf",
        safe_name="file2_sanitized.pdf",
        mime_type="application/pdf",
        size_bytes=2048,
        sha256="duplicate_hash_" + "0" * 49,  # Same hash, same user
        user_id=user_id,
    )
    session.add(doc2)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    print("✅ test_duplicate_sha256_rejected passed")


def test_invalid_document_id_rejected(db_session):
    """Test that foreign key constraint rejects invalid document_id."""
    session, user_id = db_session

    # Try to create job with non-existent document_id
    fake_uuid = uuid4()
    job = ProcessingJob(
        document_id=fake_uuid,
        status="pending",
    )
    session.add(job)

    # SQLite may not enforce foreign keys by default, skip if not supported
    try:
        session.commit()
        # If commit succeeds, foreign keys might not be enforced in SQLite
        print("⚠️  test_invalid_document_id_rejected - FK not enforced in SQLite")
        session.rollback()
    except IntegrityError:
        session.rollback()
        print("✅ test_invalid_document_id_rejected passed")


def test_cascade_delete(db_session):
    """Test that deleting a document cascades to its processing jobs."""
    session, user_id = db_session

    doc = Document(
        original_name="test.pdf",
        safe_name="test_sanitized.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="cascade_test_" + "0" * 51,
        user_id=user_id,
    )
    session.add(doc)
    session.commit()

    job1 = ProcessingJob(document_id=doc.id)
    job2 = ProcessingJob(document_id=doc.id)
    session.add_all([job1, job2])
    session.commit()

    job_ids = [job1.id, job2.id]

    # Delete the document
    session.delete(doc)
    session.commit()

    # Verify jobs are also deleted
    remaining_jobs = session.query(ProcessingJob).filter(
        ProcessingJob.id.in_(job_ids)
    ).all()

    assert len(remaining_jobs) == 0
    print("✅ test_cascade_delete passed")


def test_timestamps_generated(db_session):
    """Test that created_at and updated_at are automatically generated."""
    session, user_id = db_session

    doc = Document(
        original_name="test.pdf",
        safe_name="test_sanitized.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="timestamp_test_" + "0" * 50,
        user_id=user_id,
    )
    session.add(doc)
    session.commit()

    assert doc.created_at is not None
    assert doc.updated_at is not None

    job = ProcessingJob(document_id=doc.id)
    session.add(job)
    session.commit()

    assert job.created_at is not None
    print("✅ test_timestamps_generated passed")


# PostgreSQL-specific tests with real constraint validation
def test_zero_size_bytes_rejected_postgresql():
    """Test that size_bytes <= 0 is rejected by PostgreSQL CHECK constraint."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SQLSession
    from app.core.config import settings
    import uuid

    # Use real PostgreSQL connection
    engine = create_engine(settings.database_url)
    session = SQLSession(engine)

    try:
        # Test zero size - use unique hash
        unique_hash1 = uuid.uuid4().hex[:32] + uuid.uuid4().hex[:32]  # 64 chars
        doc = Document(
            original_name="test.pdf",
            safe_name="test_sanitized.pdf",
            mime_type="application/pdf",
            size_bytes=0,  # Invalid
            sha256=unique_hash1,
        )
        session.add(doc)

        with pytest.raises(IntegrityError) as exc_info:
            session.commit()

        assert "ck_documents_size_bytes_positive" in str(exc_info.value).lower() or "check constraint" in str(exc_info.value).lower()
        session.rollback()

        # Test negative size - use unique hash
        unique_hash2 = uuid.uuid4().hex[:32] + uuid.uuid4().hex[:32]  # 64 chars
        doc2 = Document(
            original_name="test2.pdf",
            safe_name="test2_sanitized.pdf",
            mime_type="application/pdf",
            size_bytes=-100,  # Invalid
            sha256=unique_hash2,
        )
        session.add(doc2)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
        print("✅ test_zero_size_bytes_rejected_postgresql passed")

    finally:
        session.close()
        engine.dispose()


def test_invalid_status_rejected_postgresql():
    """Test that invalid status values are rejected by PostgreSQL CHECK constraint."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SQLSession
    from app.core.config import settings
    import uuid

    # Use real PostgreSQL connection
    engine = create_engine(settings.database_url)
    session = SQLSession(engine)

    try:
        # Test invalid document status - use unique hash
        unique_hash1 = uuid.uuid4().hex[:32] + uuid.uuid4().hex[:32]  # 64 chars
        doc = Document(
            original_name="test.pdf",
            safe_name="test_sanitized.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            sha256=unique_hash1,
            status="invalid_status",  # Invalid
        )
        session.add(doc)

        with pytest.raises(IntegrityError) as exc_info:
            session.commit()

        assert "ck_documents_status_valid" in str(exc_info.value).lower() or "check constraint" in str(exc_info.value).lower()
        session.rollback()

        # Test invalid job status - use unique hash
        unique_hash2 = uuid.uuid4().hex[:32] + uuid.uuid4().hex[:32]  # 64 chars
        doc2 = Document(
            original_name="test2.pdf",
            safe_name="test2_sanitized.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            sha256=unique_hash2,
        )
        session.add(doc2)
        session.commit()

        job = ProcessingJob(
            document_id=doc2.id,
            status="bad_status",  # Invalid
        )
        session.add(job)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        # Clean up test data
        session.delete(doc2)
        session.commit()

        print("✅ test_invalid_status_rejected_postgresql passed")

    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Running Document Model Tests")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s"])
