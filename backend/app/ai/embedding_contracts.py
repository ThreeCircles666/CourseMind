"""Embedding provider contracts.

This module defines the provider-agnostic interface for text embedding services.
Business code should depend only on these abstractions, not on specific providers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingResult:
    """Result of an embedding operation.

    Attributes:
        vectors: List of embedding vectors, one per input text.
                 Order matches input order.
        model: Actual model name/ID used by the provider.
        dimension: Dimensionality of each vector.
    """
    vectors: list[list[float]]
    model: str
    dimension: int


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers.

    Implementations must:
    - Accept a list of text strings
    - Return vectors in the same order as input
    - Report the actual model name and dimension
    - Handle errors appropriately (auth, rate limit, network, etc.)
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier used by this provider."""
        raise NotImplementedError

    @abstractmethod
    async def embed(self, texts: list[str]) -> EmbeddingResult:
        """Generate embeddings for the given texts.

        Args:
            texts: List of text strings to embed. Can be empty.

        Returns:
            EmbeddingResult with vectors matching input order and count.

        Raises:
            ValueError: Invalid input (e.g., all texts are empty/whitespace).
            EmbeddingAuthError: Authentication failure.
            EmbeddingRateLimitError: Rate limit exceeded.
            EmbeddingServiceError: Network or service errors.
        """
        raise NotImplementedError


class EmbeddingError(Exception):
    """Base exception for embedding operations."""
    pass


class EmbeddingAuthError(EmbeddingError):
    """Authentication or API key error."""
    pass


class EmbeddingRateLimitError(EmbeddingError):
    """Rate limit exceeded."""
    pass


class EmbeddingServiceError(EmbeddingError):
    """Network or service errors."""
    pass
