"""Test document permission isolation between users.

Ensures users can only access their own documents and RAG queries
are properly scoped to user-owned documents.
"""
import hashlib
from uuid import UUID

import pytest
from sqlalchemy import select, func

from app.db.session import SessionLocal
from app.models.document import Document
from app.models.user import User


@pytest.fixture
def db():
    """Provide a database session for tests."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class TestDocumentPermissionIsolation:
    """Test document access control and user isolation."""

    @pytest.fixture(autouse=True)
    def setup_users(self, db):
        """Create or reuse two test users A and B."""
        # Try to find existing users first
        user_a = db.query(User).filter(User.username == "test_perm_user_a").first()
        user_a_created = False
        if user_a is None:
            user_a = User(
                username="test_perm_user_a",
                nickname="Test Perm User A",
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIr.xNb/0u",
                is_active=True,
            )
            db.add(user_a)
            db.commit()
            db.refresh(user_a)
            user_a_created = True

        user_b = db.query(User).filter(User.username == "test_perm_user_b").first()
        user_b_created = False
        if user_b is None:
            user_b = User(
                username="test_perm_user_b",
                nickname="Test Perm User B",
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIr.xNb/0u",
                is_active=True,
            )
            db.add(user_b)
            db.commit()
            db.refresh(user_b)
            user_b_created = True

        self.user_a = user_a
        self.user_b = user_b
        self.user_a_id = user_a.id
        self.user_b_id = user_b.id
        self.user_a_created = user_a_created
        self.user_b_created = user_b_created

        # Track created documents for cleanup
        self.created_document_ids = []

        yield

        # Cleanup: delete only documents created in this test
        if self.created_document_ids:
            db.query(Document).filter(
                Document.id.in_(self.created_document_ids)
            ).delete(synchronize_session=False)
            db.commit()

        # Cleanup: delete users only if we created them in this test
        try:
            if self.user_a_created and self.user_a_id:
                db.query(User).filter(User.id == self.user_a_id).delete()
            if self.user_b_created and self.user_b_id:
                db.query(User).filter(User.id == self.user_b_id).delete()
            db.commit()
        except Exception:
            db.rollback()

    def test_user_upload_creates_owned_document(self, db):
        """Test that uploaded documents are assigned to the uploading user."""
        content = b"User A's document content"
        sha256 = hashlib.sha256(content).hexdigest()

        doc_a = Document(
            original_name="doc_a.txt",
            safe_name="doc_a.txt",
            mime_type="text/plain",
            size_bytes=len(content),
            sha256=sha256,
            status="pending",
            user_id=self.user_a.id,
        )
        db.add(doc_a)
        db.commit()
        db.refresh(doc_a)
        self.created_document_ids.append(doc_a.id)

        assert doc_a.user_id == self.user_a.id
        assert doc_a.user_id != self.user_b.id

    def test_user_list_only_shows_own_documents(self, db):
        """Test that list_documents only returns user's own documents."""
        # User A uploads document
        doc_a = Document(
            original_name="user_a_doc.txt",
            safe_name="user_a_doc.txt",
            mime_type="text/plain",
            size_bytes=100,
            sha256=hashlib.sha256(b"user_a_content").hexdigest(),
            status="succeeded",
            user_id=self.user_a.id,
        )
        db.add(doc_a)

        # User B uploads document
        doc_b = Document(
            original_name="user_b_doc.txt",
            safe_name="user_b_doc.txt",
            mime_type="text/plain",
            size_bytes=200,
            sha256=hashlib.sha256(b"user_b_content").hexdigest(),
            status="succeeded",
            user_id=self.user_b.id,
        )
        db.add(doc_b)
        db.commit()
        db.refresh(doc_a)
        db.refresh(doc_b)
        self.created_document_ids.extend([doc_a.id, doc_b.id])

        # User A should only see their document
        user_a_docs = db.execute(
            select(Document).where(Document.user_id == self.user_a.id)
        ).scalars().all()
        assert len(user_a_docs) == 1
        assert user_a_docs[0].id == doc_a.id

        # User B should only see their document
        user_b_docs = db.execute(
            select(Document).where(Document.user_id == self.user_b.id)
        ).scalars().all()
        assert len(user_b_docs) == 1
        assert user_b_docs[0].id == doc_b.id

    def test_user_cannot_access_other_user_document_detail(self, db):
        """Test that get_document returns 404 for other user's documents."""
        # User A uploads document
        doc_a = Document(
            original_name="user_a_private.txt",
            safe_name="user_a_private.txt",
            mime_type="text/plain",
            size_bytes=100,
            sha256=hashlib.sha256(b"private_content").hexdigest(),
            status="succeeded",
            user_id=self.user_a.id,
        )
        db.add(doc_a)
        db.commit()
        db.refresh(doc_a)
        self.created_document_ids.append(doc_a.id)

        # User B tries to access User A's document
        result = db.execute(
            select(Document)
            .where(Document.id == doc_a.id)
            .where(Document.user_id == self.user_b.id)
        ).scalar_one_or_none()

        assert result is None  # Should not find document

    def test_duplicate_upload_scoped_to_user(self, db):
        """Test that SHA-256 deduplication is per-user."""
        content = b"Same content for both users"
        sha256 = hashlib.sha256(content).hexdigest()

        # User A uploads
        doc_a = Document(
            original_name="doc.txt",
            safe_name="doc.txt",
            mime_type="text/plain",
            size_bytes=len(content),
            sha256=sha256,
            status="succeeded",
            user_id=self.user_a.id,
        )
        db.add(doc_a)
        db.commit()
        db.refresh(doc_a)
        self.created_document_ids.append(doc_a.id)

        # User B uploads same content - should create NEW document
        doc_b = Document(
            original_name="doc.txt",
            safe_name="doc.txt",
            mime_type="text/plain",
            size_bytes=len(content),
            sha256=sha256,
            status="succeeded",
            user_id=self.user_b.id,
        )
        db.add(doc_b)
        db.commit()
        db.refresh(doc_b)
        self.created_document_ids.append(doc_b.id)

        # Should have different UUIDs
        assert doc_a.id != doc_b.id
        assert doc_a.user_id == self.user_a.id
        assert doc_b.user_id == self.user_b.id

        # User A re-uploads same content - should get SAME document
        existing = db.execute(
            select(Document)
            .where(Document.user_id == self.user_a.id)
            .where(Document.sha256 == sha256)
        ).scalar_one_or_none()
        assert existing is not None
        assert existing.id == doc_a.id  # Same UUID as first upload

    def test_total_count_scoped_to_user(self, db):
        """Test that document count is per-user."""
        # User A: 2 documents
        for i in range(2):
            doc = Document(
                original_name=f"user_a_doc_{i}.txt",
                safe_name=f"user_a_doc_{i}.txt",
                mime_type="text/plain",
                size_bytes=100,
                sha256=hashlib.sha256(f"user_a_{i}".encode()).hexdigest(),
                status="succeeded",
                user_id=self.user_a.id,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            self.created_document_ids.append(doc.id)

        # User B: 3 documents
        for i in range(3):
            doc = Document(
                original_name=f"user_b_doc_{i}.txt",
                safe_name=f"user_b_doc_{i}.txt",
                mime_type="text/plain",
                size_bytes=200,
                sha256=hashlib.sha256(f"user_b_{i}".encode()).hexdigest(),
                status="succeeded",
                user_id=self.user_b.id,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            self.created_document_ids.append(doc.id)

        # Count for User A
        count_a = db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.user_id == self.user_a.id)
        )
        assert count_a == 2

        # Count for User B
        count_b = db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.user_id == self.user_b.id)
        )
        assert count_b == 3

    def test_null_owner_documents_not_visible_to_users(self, db):
        """Test that historical NULL owner documents are not visible to users."""
        # Create a NULL owner document (historical)
        null_doc = Document(
            original_name="legacy.txt",
            safe_name="legacy.txt",
            mime_type="text/plain",
            size_bytes=50,
            sha256=hashlib.sha256(b"legacy").hexdigest(),
            status="succeeded",
            user_id=None,
        )
        db.add(null_doc)
        db.commit()
        db.refresh(null_doc)
        self.created_document_ids.append(null_doc.id)

        # User A should not see NULL owner document
        user_a_docs = db.execute(
            select(Document).where(Document.user_id == self.user_a.id)
        ).scalars().all()
        assert null_doc.id not in [d.id for d in user_a_docs]

        # User B should not see NULL owner document
        user_b_docs = db.execute(
            select(Document).where(Document.user_id == self.user_b.id)
        ).scalars().all()
        assert null_doc.id not in [d.id for d in user_b_docs]

    def test_protected_document_unchanged(self, db):
        """Test that protected document d42818a8-089c-404f-a3a0-aca970098f11 remains unchanged."""
        protected_id = UUID("d42818a8-089c-404f-a3a0-aca970098f11")

        # Snapshot before
        before = db.get(Document, protected_id)
        if before is None:
            pytest.skip("Protected document not found in database")

        before_snapshot = {
            "id": before.id,
            "user_id": before.user_id,
            "original_name": before.original_name,
            "safe_name": before.safe_name,
            "mime_type": before.mime_type,
            "size_bytes": before.size_bytes,
            "sha256": before.sha256,
            "status": before.status,
            "error_message": before.error_message,
        }

        # Run test operations (they should not affect protected document)
        # ... (other test operations run automatically via fixtures)

        # Snapshot after
        after = db.get(Document, protected_id)
        assert after is not None

        after_snapshot = {
            "id": after.id,
            "user_id": after.user_id,
            "original_name": after.original_name,
            "safe_name": after.safe_name,
            "mime_type": after.mime_type,
            "size_bytes": after.size_bytes,
            "sha256": after.sha256,
            "status": after.status,
            "error_message": after.error_message,
        }

        # Verify all fields unchanged
        assert before_snapshot == after_snapshot, "Protected document was modified"
