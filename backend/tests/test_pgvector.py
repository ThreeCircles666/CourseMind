"""Test pgvector extension functionality.

These tests verify the pgvector extension including:
- Extension is properly enabled in the database
- vector(n) type works correctly
- Distance operators: <=> (cosine), <-> (L2), <#> (inner product)
- Dimension validation and constraints
- Proper isolation using temporary tables

Note: These tests require a real PostgreSQL database with pgvector extension.
They will be skipped if not available.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DataError, ProgrammingError

from app.core.config import settings


@pytest.fixture(scope="module")
def pg_engine():
    """Create a PostgreSQL engine for testing."""
    engine = create_engine(settings.database_url)

    # Verify we're connected to PostgreSQL
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()
        if "PostgreSQL" not in version:
            pytest.skip("pgvector tests require PostgreSQL")

    yield engine
    engine.dispose()


def test_pgvector_extension_enabled(pg_engine):
    """Test that pgvector extension is enabled in the database."""
    with pg_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT extname, extversion
            FROM pg_extension
            WHERE extname = 'vector'
        """))
        row = result.fetchone()

        assert row is not None, "pgvector extension is not enabled"
        assert row[0] == "vector"
        assert row[1] is not None

        print(f"✅ pgvector extension enabled, version: {row[1]}")


def test_vector_type_available(pg_engine):
    """Test that vector type is available in the database."""
    with pg_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT typname
            FROM pg_type
            WHERE typname = 'vector'
        """))
        row = result.fetchone()

        assert row is not None
        assert row[0] == "vector"

        print("✅ vector type is available")


def test_create_vector_column(pg_engine):
    """Test creating a table with vector column."""
    with pg_engine.connect() as conn:
        trans = conn.begin()

        try:
            # Create temporary table with vector column
            conn.execute(text("""
                CREATE TEMP TABLE test_vectors (
                    id integer PRIMARY KEY,
                    embedding vector(3) NOT NULL
                )
            """))

            # Insert test data
            conn.execute(text("""
                INSERT INTO test_vectors (id, embedding)
                VALUES (1, '[1,0,0]')
            """))

            # Query back
            result = conn.execute(text("""
                SELECT id, embedding
                FROM test_vectors
                WHERE id = 1
            """))
            row = result.fetchone()

            assert row[0] == 1
            assert row[1] == "[1,0,0]"

            print("✅ vector(3) column creation and insertion successful")

        finally:
            trans.rollback()


def test_cosine_distance_operator(pg_engine):
    """Test cosine distance operator (<=>)."""
    with pg_engine.connect() as conn:
        trans = conn.begin()

        try:
            # Create temp table
            conn.execute(text("""
                CREATE TEMP TABLE test_cosine (
                    id integer PRIMARY KEY,
                    embedding vector(3) NOT NULL
                )
            """))

            # Insert test vectors
            conn.execute(text("""
                INSERT INTO test_cosine (id, embedding) VALUES
                    (1, '[1,0,0]'),
                    (2, '[0.9,0.1,0]'),
                    (3, '[0,1,0]')
            """))

            # Query with cosine distance
            result = conn.execute(text("""
                SELECT
                    id,
                    embedding <=> '[1,0,0]'::vector AS cosine_distance,
                    1 - (embedding <=> '[1,0,0]'::vector) AS cosine_similarity
                FROM test_cosine
                ORDER BY embedding <=> '[1,0,0]'::vector
            """))
            rows = result.fetchall()

            # Verify ordering: id=1 should be first (closest)
            assert rows[0][0] == 1

            # Verify id=1 has distance ~0
            assert rows[0][1] < 0.01, f"Expected distance ~0, got {rows[0][1]}"

            # Verify id=1 has similarity ~1
            assert rows[0][2] > 0.99, f"Expected similarity ~1, got {rows[0][2]}"

            # Verify distances are in ascending order
            assert rows[0][1] <= rows[1][1] <= rows[2][1]

            print("✅ Cosine distance operator (<= >) works correctly")
            print(f"   id=1: distance={rows[0][1]:.6f}, similarity={rows[0][2]:.6f}")
            print(f"   id=2: distance={rows[1][1]:.6f}, similarity={rows[1][2]:.6f}")
            print(f"   id=3: distance={rows[2][1]:.6f}, similarity={rows[2][2]:.6f}")

        finally:
            trans.rollback()


def test_l2_distance_operator(pg_engine):
    """Test L2 (Euclidean) distance operator (<->)."""
    with pg_engine.connect() as conn:
        trans = conn.begin()

        try:
            # Create temp table
            conn.execute(text("""
                CREATE TEMP TABLE test_l2 (
                    id integer PRIMARY KEY,
                    embedding vector(3) NOT NULL
                )
            """))

            # Insert test vectors
            conn.execute(text("""
                INSERT INTO test_l2 (id, embedding) VALUES
                    (1, '[1,0,0]'),
                    (2, '[0.9,0.1,0]'),
                    (3, '[0,1,0]')
            """))

            # Query with L2 distance
            result = conn.execute(text("""
                SELECT
                    id,
                    embedding <-> '[1,0,0]'::vector AS l2_distance
                FROM test_l2
                ORDER BY embedding <-> '[1,0,0]'::vector
            """))
            rows = result.fetchall()

            # Verify id=1 is closest
            assert rows[0][0] == 1
            assert rows[0][1] < 0.01

            # Verify distances are in ascending order
            assert rows[0][1] <= rows[1][1] <= rows[2][1]

            print("✅ L2 distance operator (<->) works correctly")
            print(f"   id=1: distance={rows[0][1]:.6f}")
            print(f"   id=2: distance={rows[1][1]:.6f}")
            print(f"   id=3: distance={rows[2][1]:.6f}")

        finally:
            trans.rollback()


def test_inner_product_operator(pg_engine):
    """Test negative inner product operator (<#>)."""
    with pg_engine.connect() as conn:
        trans = conn.begin()

        try:
            # Create temp table
            conn.execute(text("""
                CREATE TEMP TABLE test_inner (
                    id integer PRIMARY KEY,
                    embedding vector(3) NOT NULL
                )
            """))

            # Insert test vectors
            conn.execute(text("""
                INSERT INTO test_inner (id, embedding) VALUES
                    (1, '[1,0,0]'),
                    (2, '[0.9,0.1,0]'),
                    (3, '[0,1,0]')
            """))

            # Query with negative inner product
            result = conn.execute(text("""
                SELECT
                    id,
                    embedding <#> '[1,0,0]'::vector AS negative_inner_product
                FROM test_inner
                ORDER BY embedding <#> '[1,0,0]'::vector
            """))
            rows = result.fetchall()

            # Verify we got results
            assert len(rows) == 3

            # For [1,0,0] · [1,0,0] = 1, so <#> = -1
            # The most negative value is the closest match
            assert rows[0][0] == 1
            assert abs(rows[0][1] - (-1.0)) < 0.01

            print("✅ Negative inner product operator (<#>) works correctly")
            print(f"   id=1: <#>={rows[0][1]:.6f}")
            print(f"   id=2: <#>={rows[1][1]:.6f}")
            print(f"   id=3: <#>={rows[2][1]:.6f}")

        finally:
            trans.rollback()


def test_dimension_mismatch_rejected(pg_engine):
    """Test that dimension mismatch is rejected."""
    with pg_engine.connect() as conn:
        trans = conn.begin()

        try:
            # Create temp table with vector(3)
            conn.execute(text("""
                CREATE TEMP TABLE test_dimension (
                    id integer PRIMARY KEY,
                    embedding vector(3) NOT NULL
                )
            """))

            # Try to insert 2D vector into 3D column
            with pytest.raises((DataError, ProgrammingError)) as exc_info:
                conn.execute(text("""
                    INSERT INTO test_dimension (id, embedding)
                    VALUES (1, '[1,2]')
                """))

            error_msg = str(exc_info.value).lower()
            assert "dimension" in error_msg or "expected 3" in error_msg

            print(f"✅ Dimension mismatch correctly rejected")
            print(f"   Error: {str(exc_info.value)[:100]}")

        finally:
            trans.rollback()


def test_no_permanent_test_tables_left(pg_engine):
    """Verify that no permanent test tables are left in the database."""
    with pg_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename LIKE 'test_%'
            OR tablename LIKE '%probe%'
        """))
        test_tables = result.fetchall()

        assert len(test_tables) == 0, f"Found unexpected test tables: {test_tables}"

        print("✅ No permanent test tables left in database")


def test_existing_tables_unchanged(pg_engine):
    """Verify that existing business tables are unchanged."""
    with pg_engine.connect() as conn:
        # Check that expected tables exist
        result = conn.execute(text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        tables = [row[0] for row in result.fetchall()]

        # Should have the core tables
        assert "documents" in tables
        assert "processing_jobs" in tables
        assert "alembic_version" in tables

        # After step 6, should have document_chunks table
        assert "document_chunks" in tables

        print(f"✅ Existing tables intact: {tables}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Running pgvector Integration Tests")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s"])
