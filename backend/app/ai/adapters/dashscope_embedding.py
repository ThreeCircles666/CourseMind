"""DashScope text embedding adapter.

This adapter implements the EmbeddingProvider interface for Alibaba Cloud
DashScope text embedding models.

API Documentation: https://help.aliyun.com/zh/dashscope/developer-reference/text-embedding-api-details
"""
from __future__ import annotations

import asyncio
import math
from typing import Any

import httpx

from app.ai.embedding_contracts import (
    EmbeddingAuthError,
    EmbeddingError,
    EmbeddingProvider,
    EmbeddingRateLimitError,
    EmbeddingResult,
    EmbeddingServiceError,
)


class DashScopeEmbeddingProvider(EmbeddingProvider):
    """DashScope text embedding provider.

    Supports batch embedding with automatic retry on transient errors.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-v3",
        timeout: float = 60.0,
        max_retries: int = 3,
        trust_env: bool = True,
    ):
        """Initialize DashScope embedding provider.

        Args:
            api_key: DashScope API key.
            model: Model ID (default: text-embedding-v3).
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts (including initial request).
            trust_env: Whether to trust environment proxy settings (default: True).
        """
        if not api_key:
            raise ValueError("DashScope API key is required")
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1")

        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._trust_env = trust_env
        # DashScope uses OpenAI-compatible endpoint for embeddings
        self._base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"

    @property
    def model_name(self) -> str:
        return self._model

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        """Generate embeddings for the given texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            EmbeddingResult with vectors matching input order.

        Raises:
            ValueError: Empty input or all texts are whitespace.
            EmbeddingAuthError: Authentication failure.
            EmbeddingRateLimitError: Rate limit exceeded.
            EmbeddingServiceError: Network or service errors.
        """
        if not texts:
            raise ValueError("Input texts list cannot be empty")

        # Filter out empty/whitespace texts but remember their positions
        non_empty_texts = []
        non_empty_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                non_empty_texts.append(text)
                non_empty_indices.append(i)

        if not non_empty_texts:
            raise ValueError("All input texts are empty or whitespace")

        # The v3/v4 synchronous API accepts at most ten texts per request.
        # Keep results local until every batch succeeds: callers must never
        # receive partial embeddings and replace their existing chunks.
        vectors: list[list[float]] = []
        model: str | None = None
        dimension: int | None = None
        for start in range(0, len(non_empty_texts), 10):
            result = await self._call_with_retry(non_empty_texts[start:start + 10])
            if model is not None and (
                result["model"] != model or result["dimension"] != dimension
            ):
                raise EmbeddingServiceError("Inconsistent model or dimension across batches")
            model, dimension = result["model"], result["dimension"]
            vectors.extend(result["embeddings"])

        full_vectors = [[0.0] * dimension for _ in texts]
        for index, vector in zip(non_empty_indices, vectors, strict=True):
            full_vectors[index] = vector
        return EmbeddingResult(vectors=full_vectors, model=model, dimension=dimension)

    async def _call_with_retry(self, texts: list[str]) -> dict[str, Any]:
        """Retry only the failed batch, without resending successful batches."""
        for attempt in range(self._max_retries):
            try:
                return await self._call_api(texts)

            except (EmbeddingAuthError, ValueError):
                # Don't retry auth errors or validation errors
                raise

            except (EmbeddingRateLimitError, EmbeddingServiceError) as e:
                if attempt == self._max_retries - 1:
                    raise

                # Exponential backoff: 1s, 2s, 4s (capped at 5s)
                wait_time = min(2 ** attempt, 5.0)
                await asyncio.sleep(wait_time)

        raise EmbeddingServiceError("Max retries exceeded")

    async def _call_api(self, texts: list[str]) -> dict[str, Any]:
        """Call DashScope embedding API.

        Args:
            texts: Non-empty texts to embed.

        Returns:
            Dict with keys: embeddings, model, dimension.

        Raises:
            EmbeddingAuthError: Authentication failure.
            EmbeddingRateLimitError: Rate limit exceeded.
            EmbeddingServiceError: Other errors.
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # DashScope compatible-mode uses OpenAI format
        payload = {
            "model": self._model,
            "input": texts,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout, trust_env=self._trust_env) as client:
                response = await client.post(
                    self._base_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 401:
                    raise EmbeddingAuthError(
                        "DashScope authentication failed. Please check DASHSCOPE_API_KEY."
                    )
                elif response.status_code == 403:
                    raise EmbeddingAuthError(
                        "DashScope access forbidden. Please verify API key permissions."
                    )
                elif response.status_code == 429:
                    raise EmbeddingRateLimitError(
                        "DashScope rate limit exceeded. Please try again later."
                    )
                elif response.status_code == 400:
                    error_msg = self._extract_error_message(response)
                    raise EmbeddingServiceError(
                        f"Invalid request (HTTP 400): {error_msg}"
                    )
                elif response.status_code >= 500:
                    error_msg = self._extract_error_message(response)
                    raise EmbeddingServiceError(
                        f"DashScope service error (HTTP {response.status_code}): {error_msg}"
                    )
                elif response.status_code != 200:
                    error_msg = self._extract_error_message(response)
                    raise EmbeddingServiceError(
                        f"Unexpected response (HTTP {response.status_code}): {error_msg}"
                    )

                try:
                    data = response.json()
                except Exception as e:
                    raise EmbeddingServiceError(f"Invalid JSON response: {e}")

                # Parse DashScope response format
                return self._parse_response(data, len(texts))

        except httpx.TimeoutException as e:
            raise EmbeddingServiceError(f"Request timeout after {self._timeout}s")
        except httpx.ProxyError as e:
            # Provide more detailed proxy error information
            error_msg = str(e)
            # Remove any sensitive proxy credentials from error message
            if '@' in error_msg:
                # Sanitize proxy URLs with credentials
                import re
                error_msg = re.sub(r'//[^@]+@', '//***@', error_msg)
            raise EmbeddingServiceError(f"Proxy error: {error_msg}. Try setting EMBEDDING_TRUST_ENV=false")
        except httpx.ConnectError as e:
            raise EmbeddingServiceError(f"Connection error: {type(e).__name__}. Check network or proxy settings")
        except httpx.NetworkError as e:
            raise EmbeddingServiceError(f"Network error: {type(e).__name__}")
        except (EmbeddingAuthError, EmbeddingRateLimitError, EmbeddingServiceError):
            raise
        except Exception as e:
            raise EmbeddingServiceError(f"Unexpected error: {type(e).__name__}")

    def _parse_response(self, data: dict[str, Any], expected_count: int) -> dict[str, Any]:
        """Parse and validate DashScope API response.

        Args:
            data: Response JSON (OpenAI-compatible format).
            expected_count: Expected number of embeddings.

        Returns:
            Dict with embeddings, model, dimension.

        Raises:
            EmbeddingServiceError: Invalid response structure.
        """
        # OpenAI-compatible format: {"data": [{"embedding": [...], "index": 0}], "model": "..."}
        if "data" not in data:
            raise EmbeddingServiceError("Response missing 'data' field")

        embeddings_data = data["data"]
        if not isinstance(embeddings_data, list):
            raise EmbeddingServiceError("'data' field is not a list")

        if len(embeddings_data) != expected_count:
            raise EmbeddingServiceError(
                f"Expected {expected_count} embeddings, got {len(embeddings_data)}"
            )

        # Sort by index to ensure correct order
        sorted_data = sorted(embeddings_data, key=lambda x: x.get("index", 0))

        # Extract vectors and validate
        vectors: list[list[float]] = []
        dimension: int | None = None

        for i, item in enumerate(sorted_data):
            if not isinstance(item, dict):
                raise EmbeddingServiceError(f"Embedding {i} is not a dict")

            if "embedding" not in item:
                raise EmbeddingServiceError(f"Embedding {i} missing 'embedding' field")

            vector = item["embedding"]
            if not isinstance(vector, list):
                raise EmbeddingServiceError(f"Embedding {i} is not a list")

            if not vector:
                raise EmbeddingServiceError(f"Embedding {i} is empty")

            # Check dimension consistency
            if dimension is None:
                dimension = len(vector)
            elif len(vector) != dimension:
                raise EmbeddingServiceError(
                    f"Inconsistent dimensions: expected {dimension}, got {len(vector)} at index {i}"
                )

            # Validate numeric values
            validated_vector: list[float] = []
            for j, val in enumerate(vector):
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    raise EmbeddingServiceError(
                        f"Embedding {i}[{j}] is not a number: {type(val).__name__}"
                    )

                float_val = float(val)
                if math.isnan(float_val):
                    raise EmbeddingServiceError(f"Embedding {i}[{j}] is NaN")
                if math.isinf(float_val):
                    raise EmbeddingServiceError(f"Embedding {i}[{j}] is Infinity")

                validated_vector.append(float_val)

            # Check for zero vectors
            if all(v == 0.0 for v in validated_vector):
                raise EmbeddingServiceError(f"Embedding {i} is a zero vector")

            vectors.append(validated_vector)

        # Get model name from response
        model_used = data.get("model", self._model)

        return {
            "embeddings": vectors,
            "model": model_used,
            "dimension": dimension or 0,
        }

    def _extract_error_message(self, response: httpx.Response) -> str:
        """Extract sanitized error message from response.

        Args:
            response: HTTP response.

        Returns:
            Sanitized error message (no API keys).
        """
        try:
            data = response.json()
            if "message" in data:
                return str(data["message"])[:200]
            if "error" in data:
                error = data["error"]
                if isinstance(error, dict) and "message" in error:
                    return str(error["message"])[:200]
                return str(error)[:200]
            return "Unknown error"
        except Exception:
            return response.text[:200] if response.text else "Unable to parse error"
