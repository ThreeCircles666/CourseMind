#!/usr/bin/env python3
"""Real API validation script for embedding functionality.

This script calls the actual DashScope embedding API to verify:
- API connectivity and authentication
- Actual vector dimensions
- Semantic similarity properties
- Numeric validity

Usage:
    python scripts/check_embedding.py

Environment:
    Requires DASHSCOPE_API_KEY to be set.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ai.adapters.dashscope_embedding import DashScopeEmbeddingProvider
from app.ai.embedding_utils import (
    compute_l2_norm,
    cosine_similarity,
    validate_embeddings,
)
from app.core.config import settings


# Test samples (Chinese as required)
TEST_TEXTS = [
    "PostgreSQL 支持事务和关系数据管理。",           # A: PostgreSQL transactions
    "PostgreSQL 可以通过事务保证数据操作的一致性。",  # B: PostgreSQL consistency
    "海边的天气适合游泳。",                          # C: Beach weather
    "pgvector 为 PostgreSQL 提供向量相似度检索能力。", # D: pgvector for PostgreSQL
]

TEXT_LABELS = ["A", "B", "C", "D"]


async def main() -> int:
    """Run embedding validation.

    Returns:
        0 if validation passes, non-zero otherwise.
    """
    print("=" * 70)
    print("DashScope Embedding API Validation")
    print("=" * 70)
    print()

    # Check API key
    if not settings.is_dashscope_configured():
        print("❌ DASHSCOPE_API_KEY not configured")
        print("Please set it in backend/.env or as environment variable")
        return 1

    print("✅ DashScope API key configured")
    print()

    # Initialize provider
    try:
        provider = DashScopeEmbeddingProvider(
            api_key=settings.get_dashscope_key(),
            model=settings.embedding_model,
            timeout=settings.embedding_timeout_seconds,
            max_retries=settings.embedding_max_retries,
            trust_env=settings.embedding_trust_env,
        )
    except Exception as e:
        print(f"❌ Failed to initialize provider: {e}")
        return 1

    print(f"Provider: DashScope")
    print(f"Model: {provider.model_name}")
    print(f"Timeout: {settings.embedding_timeout_seconds}s")
    print(f"Max retries: {settings.embedding_max_retries}")
    print()

    # Call API
    print("Calling DashScope API...")
    print(f"Input texts: {len(TEST_TEXTS)}")
    for i, (label, text) in enumerate(zip(TEXT_LABELS, TEST_TEXTS)):
        print(f"  {label}: {text}")
    print()

    try:
        result = await provider.embed(TEST_TEXTS)
    except Exception as e:
        print(f"❌ API call failed: {type(e).__name__}: {e}")
        return 1

    print("✅ API call succeeded")
    print()

    # Report basic info
    print("=" * 70)
    print("API Response")
    print("=" * 70)
    print(f"Model returned: {result.model}")
    print(f"Input count: {len(TEST_TEXTS)}")
    print(f"Output count: {len(result.vectors)}")
    print(f"Reported dimension: {result.dimension}")
    print(f"Vector type (outer): {type(result.vectors).__name__}")
    if result.vectors:
        print(f"Vector type (inner): {type(result.vectors[0]).__name__}")
    print()

    # Validate vectors
    print("=" * 70)
    print("Vector Validation")
    print("=" * 70)

    try:
        actual_dim = validate_embeddings(
            result.vectors,
            expected_count=len(TEST_TEXTS),
            expected_dimension=result.dimension,
        )
        print(f"✅ All vectors valid")
        print(f"✅ Actual dimension: {actual_dim}")
        print(f"✅ Count matches: {len(result.vectors)} == {len(TEST_TEXTS)}")
        print(f"✅ Dimensions consistent")
        print(f"✅ No NaN/Infinity")
        print(f"✅ No empty/zero vectors")
    except ValueError as e:
        print(f"❌ Validation failed: {e}")
        return 1

    print()

    # Show sample values
    print("=" * 70)
    print("Sample Values (first 5 elements of each vector)")
    print("=" * 70)
    for i, (label, vector) in enumerate(zip(TEXT_LABELS, result.vectors)):
        preview = vector[:5]
        preview_str = ", ".join(f"{v:.6f}" for v in preview)
        print(f"{label}: [{preview_str}, ...]")
    print()

    # Compute L2 norms
    print("=" * 70)
    print("L2 Norms")
    print("=" * 70)
    norms = [compute_l2_norm(v) for v in result.vectors]
    for label, norm in zip(TEXT_LABELS, norms):
        print(f"{label}: {norm:.6f}")

    min_norm = min(norms)
    max_norm = max(norms)
    print(f"\nRange: [{min_norm:.6f}, {max_norm:.6f}]")

    # Check if approximately normalized
    all_near_one = all(0.95 <= n <= 1.05 for n in norms)
    if all_near_one:
        print("✅ Vectors appear to be approximately normalized (L2 norm ≈ 1)")
    else:
        print("ℹ️  Vectors are not normalized (this is acceptable)")
    print()

    # Compute similarities
    print("=" * 70)
    print("Cosine Similarity")
    print("=" * 70)
    print("Note: Cosine similarity ranges from -1 to 1")
    print("      Higher values = more similar")
    print()

    vec_a, vec_b, vec_c, vec_d = result.vectors

    sim_ab = cosine_similarity(vec_a, vec_b)
    sim_ac = cosine_similarity(vec_a, vec_c)
    sim_ad = cosine_similarity(vec_a, vec_d)

    print(f"A-B (both about PostgreSQL transactions): {sim_ab:.6f}")
    print(f"A-C (PostgreSQL vs beach weather):        {sim_ac:.6f}")
    print(f"A-D (both about PostgreSQL):              {sim_ad:.6f}")
    print()

    # Also show cosine distance for reference
    print("Cosine Distance (1 - similarity):")
    print(f"A-B: {1 - sim_ab:.6f}")
    print(f"A-C: {1 - sim_ac:.6f}")
    print(f"A-D: {1 - sim_ad:.6f}")
    print()

    # Assertions
    print("=" * 70)
    print("Semantic Validation")
    print("=" * 70)

    if sim_ab > sim_ac:
        print(f"✅ A-B similarity ({sim_ab:.4f}) > A-C similarity ({sim_ac:.4f})")
        print("   Semantically related texts are more similar than unrelated ones")
    else:
        print(f"❌ Expected A-B > A-C, but got {sim_ab:.4f} <= {sim_ac:.4f}")
        return 1

    print()
    print(f"ℹ️  A-D similarity: {sim_ad:.4f}")
    print("   Both A and D mention PostgreSQL, but focus on different aspects")
    print("   (A: transactions, D: pgvector extension)")
    if sim_ad > sim_ac:
        print("   A-D > A-C as expected (shared topic)")
    else:
        print("   A-D <= A-C (unexpected but not necessarily wrong)")

    print()

    # Summary
    print("=" * 70)
    print("Validation Summary")
    print("=" * 70)
    print("✅ API authentication successful")
    print("✅ Batch embedding supported (4 texts in one call)")
    print(f"✅ Actual dimension confirmed: {actual_dim}")
    print("✅ All vectors valid (finite, non-zero)")
    print("✅ Semantic similarity behaves as expected")
    print()

    # Recommendations
    print("=" * 70)
    print("Recommendations for Future Database Schema")
    print("=" * 70)
    print(f"✅ Confirmed embedding model: {result.model}")
    print(f"✅ Confirmed vector dimension: {actual_dim}")
    print(f"Recommended distance metric: cosine")
    print(f"Corresponding pgvector operator: <=>")
    print()
    print("Note: Do NOT create tables or indexes at this stage.")
    print("These parameters will be used in Step 4 (text parsing) and beyond.")
    print()

    print("=" * 70)
    print("✅ All validations passed")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
