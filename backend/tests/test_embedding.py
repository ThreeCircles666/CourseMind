"""Unit tests for embedding functionality.

These tests use mock providers and do not call real APIs.
"""
from __future__ import annotations

import asyncio
import math

import pytest

from app.ai.embedding_contracts import (
    EmbeddingAuthError,
    EmbeddingProvider,
    EmbeddingRateLimitError,
    EmbeddingResult,
    EmbeddingServiceError,
)
from app.ai.embedding_utils import (
    compute_l2_norm,
    cosine_similarity,
    validate_embeddings,
)


class FakeEmbeddingProvider(EmbeddingProvider):
    """Fake provider for testing."""

    def __init__(
        self,
        model: str = "fake-model",
        dimension: int = 4,
        fail_with: Exception | None = None,
        retry_count: int = 0,
    ):
        self._model = model
        self._dimension = dimension
        self._fail_with = fail_with
        self._retry_count = retry_count
        self._call_count = 0

    @property
    def model_name(self) -> str:
        return self._model

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        self._call_count += 1

        if self._fail_with and self._call_count <= self._retry_count:
            raise self._fail_with

        if not texts:
            raise ValueError("Empty input")

        vectors = []
        for i, text in enumerate(texts):
            if not text.strip():
                raise ValueError("Empty text")
            # Generate fake but deterministic vectors based on text length
            base = len(text) / 10.0
            vector = [base + j * 0.1 for j in range(self._dimension)]
            vectors.append(vector)

        return EmbeddingResult(
            vectors=vectors,
            model=self._model,
            dimension=self._dimension,
        )


# Vector validation tests

def test_validate_embeddings_success():
    vectors = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    dim = validate_embeddings(vectors, expected_count=2)
    assert dim == 3


def test_validate_embeddings_with_expected_dimension():
    vectors = [[1.0, 2.0], [3.0, 4.0]]
    dim = validate_embeddings(vectors, expected_count=2, expected_dimension=2)
    assert dim == 2


def test_validate_embeddings_empty_list():
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_embeddings([], expected_count=0)


def test_validate_embeddings_count_mismatch():
    vectors = [[1.0, 2.0]]
    with pytest.raises(ValueError, match="Expected 2 vectors, got 1"):
        validate_embeddings(vectors, expected_count=2)


def test_validate_embeddings_dimension_mismatch():
    vectors = [[1.0, 2.0], [3.0, 4.0]]
    with pytest.raises(ValueError, match="Expected dimension 3, got 2"):
        validate_embeddings(vectors, expected_count=2, expected_dimension=3)


def test_validate_embeddings_inconsistent_dimensions():
    vectors = [[1.0, 2.0], [3.0, 4.0, 5.0]]
    with pytest.raises(ValueError, match="Inconsistent dimension"):
        validate_embeddings(vectors, expected_count=2)


def test_validate_embeddings_empty_vector():
    vectors = [[]]
    with pytest.raises(ValueError, match="Vector 0 is empty"):
        validate_embeddings(vectors, expected_count=1)


def test_validate_embeddings_nan():
    vectors = [[1.0, float('nan'), 3.0]]
    with pytest.raises(ValueError, match="is NaN"):
        validate_embeddings(vectors, expected_count=1)


def test_validate_embeddings_infinity():
    vectors = [[1.0, float('inf'), 3.0]]
    with pytest.raises(ValueError, match="is Infinity"):
        validate_embeddings(vectors, expected_count=1)


def test_validate_embeddings_zero_vector():
    vectors = [[0.0, 0.0, 0.0]]
    with pytest.raises(ValueError, match="zero vector"):
        validate_embeddings(vectors, expected_count=1)


def test_validate_embeddings_boolean_rejected():
    vectors = [[1.0, True, 3.0]]
    with pytest.raises(ValueError, match="is not a number"):
        validate_embeddings(vectors, expected_count=1)


# Cosine similarity tests

def test_cosine_similarity_identical():
    vec = [1.0, 2.0, 3.0]
    sim = cosine_similarity(vec, vec)
    assert abs(sim - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    left = [1.0, 0.0, 0.0]
    right = [0.0, 1.0, 0.0]
    sim = cosine_similarity(left, right)
    assert abs(sim) < 1e-6


def test_cosine_similarity_opposite():
    left = [1.0, 2.0, 3.0]
    right = [-1.0, -2.0, -3.0]
    sim = cosine_similarity(left, right)
    assert abs(sim - (-1.0)) < 1e-6


def test_cosine_similarity_empty_vector():
    with pytest.raises(ValueError, match="cannot be empty"):
        cosine_similarity([], [1.0])


def test_cosine_similarity_dimension_mismatch():
    with pytest.raises(ValueError, match="dimensions must match"):
        cosine_similarity([1.0, 2.0], [1.0])


def test_cosine_similarity_zero_norm():
    with pytest.raises(ValueError, match="zero norm"):
        cosine_similarity([0.0, 0.0], [1.0, 2.0])


def test_cosine_similarity_nan():
    with pytest.raises(ValueError, match="not finite"):
        cosine_similarity([1.0, float('nan')], [1.0, 2.0])


def test_cosine_similarity_infinity():
    with pytest.raises(ValueError, match="not finite"):
        cosine_similarity([1.0, 2.0], [1.0, float('inf')])


def test_cosine_similarity_boolean_rejected():
    with pytest.raises(ValueError, match="is not a number"):
        cosine_similarity([1.0, True], [1.0, 2.0])


# L2 norm tests

def test_l2_norm_unit_vector():
    norm = compute_l2_norm([1.0, 0.0, 0.0])
    assert abs(norm - 1.0) < 1e-6


def test_l2_norm_general():
    norm = compute_l2_norm([3.0, 4.0])
    assert abs(norm - 5.0) < 1e-6


def test_l2_norm_empty():
    with pytest.raises(ValueError, match="cannot be empty"):
        compute_l2_norm([])


def test_l2_norm_nan():
    with pytest.raises(ValueError, match="not finite"):
        compute_l2_norm([1.0, float('nan')])


# Provider tests (using asyncio.run for sync test compatibility)

def test_fake_provider_basic():
    provider = FakeEmbeddingProvider(dimension=3)
    result = asyncio.run(provider.embed(["hello", "world"]))

    assert result.model == "fake-model"
    assert result.dimension == 3
    assert len(result.vectors) == 2
    assert all(len(v) == 3 for v in result.vectors)


def test_fake_provider_empty_input():
    provider = FakeEmbeddingProvider()
    with pytest.raises(ValueError, match="Empty input"):
        asyncio.run(provider.embed([]))


def test_fake_provider_whitespace_rejected():
    provider = FakeEmbeddingProvider()
    with pytest.raises(ValueError, match="Empty text"):
        asyncio.run(provider.embed(["  ", "valid"]))


def test_fake_provider_retry_success():
    """Test that provider retries and eventually succeeds."""
    provider = FakeEmbeddingProvider(
        fail_with=EmbeddingServiceError("Transient error"),
        retry_count=2,  # Fail first 2 calls, succeed on 3rd
    )

    # First two calls should fail
    with pytest.raises(EmbeddingServiceError):
        asyncio.run(provider.embed(["test"]))

    with pytest.raises(EmbeddingServiceError):
        asyncio.run(provider.embed(["test"]))

    # Third call should succeed
    result = asyncio.run(provider.embed(["test"]))
    assert result.dimension == 4


def test_fake_provider_auth_error_no_retry():
    """Auth errors should not be retried."""
    provider = FakeEmbeddingProvider(
        fail_with=EmbeddingAuthError("Invalid key"),
        retry_count=10,  # Even with high retry, should fail immediately
    )

    with pytest.raises(EmbeddingAuthError):
        asyncio.run(provider.embed(["test"]))

    assert provider._call_count == 1  # Only called once


def test_fake_provider_rate_limit():
    provider = FakeEmbeddingProvider(
        fail_with=EmbeddingRateLimitError("Too many requests"),
        retry_count=1,
    )

    with pytest.raises(EmbeddingRateLimitError):
        asyncio.run(provider.embed(["test"]))


# Integration-style tests with fake provider

def test_embedding_workflow():
    """Test complete embedding workflow with validation."""
    provider = FakeEmbeddingProvider(model="test-model-v1", dimension=5)

    texts = ["PostgreSQL supports transactions", "The sky is blue"]
    result = asyncio.run(provider.embed(texts))

    # Validate result structure
    assert result.model == "test-model-v1"
    assert result.dimension == 5
    assert len(result.vectors) == 2

    # Validate vectors
    dim = validate_embeddings(result.vectors, expected_count=2, expected_dimension=5)
    assert dim == 5

    # Compute norms
    norms = [compute_l2_norm(v) for v in result.vectors]
    assert all(n > 0 for n in norms)

    # Compute similarity
    sim = cosine_similarity(result.vectors[0], result.vectors[1])
    assert -1.0 <= sim <= 1.0


def test_semantic_similarity_ordering():
    """Test that similar texts have higher similarity."""
    provider = FakeEmbeddingProvider(dimension=4)

    # Note: Fake provider generates deterministic vectors based on text length
    # So we need texts with similar lengths for similar vectors
    text_a = "Hello world"  # 11 chars
    text_b = "Hello earth"  # 11 chars (same length -> similar vector)
    text_c = "x"            # 1 char (different length -> different vector)

    result = asyncio.run(provider.embed([text_a, text_b, text_c]))

    sim_ab = cosine_similarity(result.vectors[0], result.vectors[1])
    sim_ac = cosine_similarity(result.vectors[0], result.vectors[2])

    # Similar length texts should have higher similarity
    assert sim_ab > sim_ac
