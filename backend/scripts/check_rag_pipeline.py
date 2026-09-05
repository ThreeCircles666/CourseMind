"""End-to-end RAG pipeline validation script.

Tests the complete flow:
1. Parse Markdown document
2. Generate chunks
3. Call real DashScope Embedding API
4. Write to PostgreSQL with pgvector
5. Search with semantic queries
6. Validate results

⚠️ This script calls real APIs and writes to the database.
Run explicitly with network access to DashScope.

Usage:
    env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
      .venv/bin/python scripts/check_rag_pipeline.py
"""
import sys
import os
import asyncio
from uuid import uuid4

# Check environment
if os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY'):
    print("⚠️  Warning: Proxy environment variables detected")
    print("This may block DashScope API access")
    print("Run with: env -u HTTP_PROXY -u HTTPS_PROXY .venv/bin/python scripts/check_rag_pipeline.py")
    sys.exit(1)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ai.adapters.dashscope_embedding import DashScopeEmbeddingProvider
from app.parsers.registry import ParserRegistry
from app.chunking import RecursiveCharacterChunker
from app.models import Document, EMBEDDING_DIMENSION
from app.services import ingest_document, search, PROTECTED_DOCUMENT_ID

# Test document content
TEST_MARKDOWN = b"""# PostgreSQL Transaction

PostgreSQL uses transaction to ensure atomicity and consistency.
ACID properties include Atomicity, Consistency, Isolation, and Durability.

# pgvector

pgvector is a PostgreSQL extension for storing vectors and similarity search.
Text embeddings can be stored in vector columns and queried by cosine distance.

# Beach Activities

On sunny days, people can swim and walk on the beach.
"""

TEST_QUESTIONS = [
    ("What is pgvector used for?", ["pgvector", "vector", "similarity"]),
    ("How does database transaction ensure consistency?", ["transaction", "ACID", "consistency"]),
]

async def main():
    print("=" * 70)
    print("RAG Pipeline End-to-End Validation")
    print("=" * 70)
    print()

    # Check configuration
    if not settings.dashscope_api_key:
        print("❌ DASHSCOPE_API_KEY not configured")
        sys.exit(1)

    print(f"✓ API Key configured")

    # Check database
    engine = create_engine(str(settings.database_url))
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        head = result.scalar()
        print(f"✓ Alembic head: {head}")

        result = conn.execute(text(
            "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
        ))
        if not result.scalar():
            print("❌ pgvector extension not found")
            sys.exit(1)
        print("✓ pgvector extension exists")

        # Check protected document
        result = conn.execute(text(
            f"SELECT COUNT(*) FROM documents WHERE id = '{PROTECTED_DOCUMENT_ID}'"
        ))
        if result.scalar() != 1:
            print(f"❌ Protected document {PROTECTED_DOCUMENT_ID} not found")
            sys.exit(1)
        print(f"✓ Protected document exists")

    print()
    print("-" * 70)
    print("Phase 1: Ingestion")
    print("-" * 70)

    # Create test document
    test_doc_id = uuid4()
    test_sha256 = f"test_rag_{test_doc_id.hex[:16]}" + "0" * 38

    session = Session(engine)
    try:
        # Create document record
        test_doc = Document(
            id=test_doc_id,
            original_name=f"test_rag_{test_doc_id.hex[:8]}.md",
            safe_name=f"test_rag_{test_doc_id.hex[:8]}.md",
            mime_type="text/markdown",
            size_bytes=len(TEST_MARKDOWN),
            sha256=test_sha256,
            status="pending",
        )
        session.add(test_doc)
        session.commit()
        print(f"✓ Created test document: {test_doc_id}")

        # Initialize providers
        parser_registry = ParserRegistry()
        chunker = RecursiveCharacterChunker(chunk_size=200, chunk_overlap=30)
        embedding_provider = DashScopeEmbeddingProvider(
            api_key=settings.dashscope_api_key,
            model="text-embedding-v3",
        )

        print("✓ Initialized providers")

        # Ingest
        print("Calling DashScope API...")
        result = await ingest_document(
            session=session,
            document_id=test_doc_id,
            content=TEST_MARKDOWN,
            filename=test_doc.original_name,
            mime_type=test_doc.mime_type,
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=embedding_provider,
        )

        print(f"✓ Ingestion succeeded")
        print(f"  Job ID: {result.job_id}")
        print(f"  Chunks: {result.chunk_count}")
        print(f"  Model: {result.embedding_model}")
        print(f"  Dimension: {result.embedding_dimension}")

        assert result.embedding_dimension == EMBEDDING_DIMENSION
        assert result.chunk_count > 0

        # Verify in database
        with engine.connect() as conn:
            result_db = conn.execute(text(
                f"SELECT COUNT(*) FROM document_chunks WHERE document_id = '{test_doc_id}'"
            ))
            chunk_count_db = result_db.scalar()
            print(f"✓ Database has {chunk_count_db} chunks")
            assert chunk_count_db == result.chunk_count

        # Test idempotency
        print()
        print("Testing idempotency (re-ingesting)...")
        result2 = await ingest_document(
            session=session,
            document_id=test_doc_id,
            content=TEST_MARKDOWN,
            filename=test_doc.original_name,
            mime_type=test_doc.mime_type,
            parser_registry=parser_registry,
            chunker=chunker,
            embedding_provider=embedding_provider,
        )

        with engine.connect() as conn:
            result_db = conn.execute(text(
                f"SELECT COUNT(*) FROM document_chunks WHERE document_id = '{test_doc_id}'"
            ))
            chunk_count_after = result_db.scalar()
            print(f"✓ After re-ingestion: {chunk_count_after} chunks (no duplication)")
            assert chunk_count_after == chunk_count_db

        print()
        print("-" * 70)
        print("Phase 2: Retrieval")
        print("-" * 70)

        for i, (question, expected_keywords) in enumerate(TEST_QUESTIONS, 1):
            print(f"\nQuestion {i}: {question}")

            hits = await search(
                session=session,
                embedding_provider=embedding_provider,
                question=question,
                top_k=3,
                document_ids=[test_doc_id],
            )

            print(f"Retrieved {len(hits)} hits:")
            for rank, hit in enumerate(hits, 1):
                preview = hit.content[:100].replace('\n', ' ')
                print(f"  {rank}. similarity={hit.similarity:.3f} distance={hit.distance:.3f}")
                print(f"     chunk={hit.chunk_index} page={hit.page_number} title={hit.title_path}")
                print(f"     {preview}...")

            # Check expected keywords
            found = False
            for hit in hits:
                content_lower = hit.content.lower()
                if any(kw in content_lower for kw in expected_keywords):
                    found = True
                    break

            if found:
                print(f"  ✓ Expected keywords found in top-{len(hits)}")
            else:
                print(f"  ⚠️  Expected keywords not in top results")

        print()
        print("-" * 70)
        print("Phase 3: Cleanup")
        print("-" * 70)

        # Clean up test data
        session.rollback()
        test_doc = session.get(Document, test_doc_id)
        if test_doc:
            session.delete(test_doc)
            session.commit()
            print(f"✓ Deleted test document {test_doc_id}")

        # Verify cleanup
        with engine.connect() as conn:
            result_db = conn.execute(text(
                f"SELECT COUNT(*) FROM documents WHERE id = '{test_doc_id}'"
            ))
            assert result_db.scalar() == 0

            result_db = conn.execute(text(
                f"SELECT COUNT(*) FROM document_chunks WHERE document_id = '{test_doc_id}'"
            ))
            assert result_db.scalar() == 0
            print("✓ No test data remaining")

            # Verify protected document still exists
            result_db = conn.execute(text(
                f"SELECT COUNT(*) FROM documents WHERE id = '{PROTECTED_DOCUMENT_ID}'"
            ))
            assert result_db.scalar() == 1
            print(f"✓ Protected document still exists")

        print()
        print("=" * 70)
        print("✅ All validations passed")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

        # Attempt cleanup
        try:
            session.rollback()
            test_doc = session.get(Document, test_doc_id)
            if test_doc:
                session.delete(test_doc)
                session.commit()
                print(f"\n✓ Cleaned up test document {test_doc_id}")
        except Exception as cleanup_error:
            print(f"\n⚠️  Cleanup error: {cleanup_error}")

        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
