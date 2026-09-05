"""Utility functions for embedding validation and similarity computation.

These functions are pure mathematical operations that don't depend on
any specific provider or database.
"""
from __future__ import annotations

import math


def validate_embeddings(
    vectors: list[list[float]],
    expected_count: int,
    expected_dimension: int | None = None,
) -> int:
    """Validate embedding vectors for correctness.

    Args:
        vectors: List of embedding vectors to validate.
        expected_count: Expected number of vectors.
        expected_dimension: If provided, all vectors must have this dimension.

    Returns:
        int: The actual dimension of the vectors.

    Raises:
        ValueError: If validation fails.
    """
    if not vectors:
        raise ValueError("Vectors list cannot be empty")

    if len(vectors) != expected_count:
        raise ValueError(
            f"Expected {expected_count} vectors, got {len(vectors)}"
        )

    # Determine dimension from first vector
    first_vector = vectors[0]
    if not isinstance(first_vector, list):
        raise ValueError(f"Vector 0 is not a list: {type(first_vector).__name__}")

    if not first_vector:
        raise ValueError("Vector 0 is empty")

    dimension = len(first_vector)

    # Validate expected dimension if provided
    if expected_dimension is not None and dimension != expected_dimension:
        raise ValueError(
            f"Expected dimension {expected_dimension}, got {dimension}"
        )

    # Validate each vector
    for i, vector in enumerate(vectors):
        if not isinstance(vector, list):
            raise ValueError(f"Vector {i} is not a list: {type(vector).__name__}")

        if len(vector) != dimension:
            raise ValueError(
                f"Inconsistent dimension at vector {i}: expected {dimension}, got {len(vector)}"
            )

        if not vector:
            raise ValueError(f"Vector {i} is empty")

        # Check all elements are valid floats
        has_nonzero = False
        for j, val in enumerate(vector):
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(
                    f"Vector {i}[{j}] is not a number: {type(val).__name__}"
                )

            float_val = float(val)
            if math.isnan(float_val):
                raise ValueError(f"Vector {i}[{j}] is NaN")
            if math.isinf(float_val):
                raise ValueError(f"Vector {i}[{j}] is Infinity")

            if float_val != 0.0:
                has_nonzero = True

        if not has_nonzero:
            raise ValueError(f"Vector {i} is a zero vector")

    return dimension


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Cosine similarity ranges from -1 to 1:
    - 1 means identical direction
    - 0 means orthogonal (unrelated)
    - -1 means opposite direction

    For text embeddings, higher values indicate greater semantic similarity.

    Args:
        left: First vector.
        right: Second vector.

    Returns:
        float: Cosine similarity in range [-1, 1].

    Raises:
        ValueError: If vectors are invalid (empty, different dimensions, zero norm, non-finite).
    """
    if not left or not right:
        raise ValueError("Vectors cannot be empty")

    if len(left) != len(right):
        raise ValueError(
            f"Vector dimensions must match: {len(left)} vs {len(right)}"
        )

    # Validate all values are finite
    for i, val in enumerate(left):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValueError(f"Left vector[{i}] is not a number")
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Left vector[{i}] is not finite")

    for i, val in enumerate(right):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValueError(f"Right vector[{i}] is not a number")
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Right vector[{i}] is not finite")

    # Compute dot product and norms
    dot_product = 0.0
    left_norm_sq = 0.0
    right_norm_sq = 0.0

    for l_val, r_val in zip(left, right):
        dot_product += l_val * r_val
        left_norm_sq += l_val * l_val
        right_norm_sq += r_val * r_val

    # Check for zero vectors
    if left_norm_sq == 0.0:
        raise ValueError("Left vector has zero norm")
    if right_norm_sq == 0.0:
        raise ValueError("Right vector has zero norm")

    # Compute cosine similarity
    left_norm = math.sqrt(left_norm_sq)
    right_norm = math.sqrt(right_norm_sq)
    similarity = dot_product / (left_norm * right_norm)

    # Clamp to [-1, 1] to handle floating-point errors
    similarity = max(-1.0, min(1.0, similarity))

    return similarity


def compute_l2_norm(vector: list[float]) -> float:
    """Compute L2 (Euclidean) norm of a vector.

    For normalized embeddings, this should be close to 1.0.

    Args:
        vector: Input vector.

    Returns:
        float: L2 norm (always non-negative).

    Raises:
        ValueError: If vector is invalid.
    """
    if not vector:
        raise ValueError("Vector cannot be empty")

    norm_sq = 0.0
    for i, val in enumerate(vector):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValueError(f"Vector[{i}] is not a number")
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Vector[{i}] is not finite")
        norm_sq += val * val

    return math.sqrt(norm_sq)
