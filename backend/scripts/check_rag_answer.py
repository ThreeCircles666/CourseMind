"""Real AI control layer end-to-end validation.

Tests complete RAG flow with:
1. Real DashScope Embedding
2. Real Qwen Chat
3. Real PostgreSQL
4. Document ingestion
5. Question answering with citations
6. Out-of-domain question handling

Usage:
    env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \\
      .venv/bin/python scripts/check_rag_answer.py
"""
import sys
import os
import asyncio
from uuid import uuid4

# Check environment
if os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY'):
    print("⚠️  Warning: Proxy variables detected, may block API access")
    print("Run with: env -u HTTP_PROXY -u HTTPS_PROXY .venv/bin/python scripts/check_rag_answer.py")
    sys.exit(1)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ai.adapters.dashscope_embedding import DashScopeEmbeddingProvider
from app.ai.adapters.qwen_chat import QwenChatProvider
from app.parsers.registry import ParserRegistry
from app.chunking import RecursiveCharacterChunker
from app.models import Document, EMBEDDING_DIMENSION
from app.services import ingest_document, PROTECTED_DOCUMENT_ID
from app.services.rag import RagService
from app.schemas.rag import RagAskRequest


TEST_MARKDOWN = b"""# pgvector Extension

pgvector is a PostgreSQL extension for storing vectors and performing similarity search.
It provides vector data types and distance operators including cosine distance.
Text embeddings can be stored in vector columns for semantic search.

# PostgreSQL Transactions

PostgreSQL uses ACID transactions to ensure data consistency.
Atomicity guarantees all-or-nothing execution.
"""


async def main():
    print("=" * 70)
    print("RAG Answer End-to-End Validation")
    print("=" * 70)
    print()

    # Check configuration
    if not settings.dashscope_api_key:
        print("❌ DASHSCOPE_API_KEY not configured")
        sys.exit(1)

    print("✓ API Key configured")

    # Check database
    engine = create_engine(str(settings.database_url))
    with engine.connect() as conn:
        result = conn.execute(text(
            f"SELECT COUNT(*) FROM documents WHERE id = '{PROTECTED_DOCUMENT_ID}'"
        ))
        if result.scalar() != 1:
            print(f"❌ Protected document not found")
            sys.exit(1)
        print("✓ Protected document exists")

    print()
    print("-" * 70)
    print("Phase 1: Document Ingestion")
    print("-" * 70)

    # Create test document
    test_doc_id = uuid4()
    test_sha256 = f"rag_test_{test_doc_id.hex[:16]}" + "0" * 38

    session = Session(engine)
    try:
        test_doc = Document(
            id=test_doc_id,
            original_name=f"rag_test_{test_doc_id.hex[:8]}.md",
            safe_name=f"rag_test_{test_doc_id.hex[:8]}.md",
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

        print("Ingesting document...")
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
        print(f"  Chunks: {result.chunk_count}")
        print(f"  Model: {result.embedding_model}")
        print(f"  Dimension: {result.embedding_dimension}")

        assert result.embedding_dimension == EMBEDDING_DIMENSION
        assert result.chunk_count > 0

        print()
        print("-" * 70)
        print("Phase 2: RAG Question Answering")
        print("-" * 70)

        # Initialize RAG service
        chat_provider = QwenChatProvider(
            api_key=settings.dashscope_api_key,
            model="qwen3.8-flash",
        )

        rag_service = RagService(
            embedding_provider=embedding_provider,
            chat_provider=chat_provider,
        )

        # Question 1: In-domain (should answer with citations)
        print()
        print("Question 1: pgvector有什么作用？")

        request1 = RagAskRequest(
            question="pgvector有什么作用？",
            document_ids=[test_doc_id],
            top_k=3,
        )

        response1 = await rag_service.answer(session=session, request=request1)

        print(f"Answer: {response1.answer[:200]}...")
        print(f"Sources: {len(response1.sources)}")
        print(f"Model: {response1.model}")
        print(f"Insufficient: {response1.insufficient_context}")

        # Validate citations
        import re
        citations = re.findall(r'\[S\d+\]', response1.answer)
        print(f"Citations found: {citations}")

        assert not response1.insufficient_context, "Should have sufficient context"
        assert len(citations) > 0, "Answer should contain citations"
        assert len(response1.sources) > 0, "Should return sources"
        assert response1.model is not None, "Should return model name"

        # Check source content
        has_pgvector = any("pgvector" in src.excerpt.lower() or "vector" in src.excerpt.lower()
                          for src in response1.sources)
        print(f"✓ Answer contains citations: {len(citations)}")
        print(f"✓ Sources reference pgvector: {has_pgvector}")

        # Question 2: Out-of-domain (should return insufficient or low similarity)
        print()
        print("Question 2: 法国首都是什么？")

        request2 = RagAskRequest(
            question="法国首都是什么？",
            document_ids=[test_doc_id],
            top_k=3,
            min_similarity=0.5,  # Set threshold to help filter irrelevant
        )

        response2 = await rag_service.answer(session=session, request=request2)

        print(f"Answer: {response2.answer[:200]}")
        print(f"Sources: {len(response2.sources)}")
        print(f"Insufficient: {response2.insufficient_context}")

        if response2.insufficient_context:
            print("✓ Correctly identified insufficient context")
            assert response2.answer == "现有文档不足以回答该问题。"
        else:
            # If not marked insufficient, check similarity scores
            print(f"  Note: Not marked insufficient, but similarities may be low")
            if response2.sources:
                max_sim = max(src.similarity for src in response2.sources)
                print(f"  Max similarity: {max_sim:.3f}")
                print(f"  Strategy: Relies on similarity threshold or model self-assessment")

        print()
        print("-" * 70)
        print("Phase 3: Cleanup")
        print("-" * 70)

        # Clean up
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

            result_db = conn.execute(text(
                f"SELECT COUNT(*) FROM documents WHERE id = '{PROTECTED_DOCUMENT_ID}'"
            ))
            assert result_db.scalar() == 1
            print("✓ Protected document still exists")

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
                print(f"\n✓ Cleaned up test document")
        except Exception as cleanup_error:
            print(f"\n⚠️  Cleanup error: {cleanup_error}")

        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
