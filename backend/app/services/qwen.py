"""Qwen/DashScope streaming service layer.

This module provides reusable async functions for calling Alibaba Cloud
DashScope API with streaming support.
"""
from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx


class QwenServiceError(Exception):
    """Base exception for Qwen service errors."""

    pass


class QwenAuthError(QwenServiceError):
    """Authentication or API key error."""

    pass


class QwenModelError(QwenServiceError):
    """Model not found or not accessible."""

    pass


class QwenRateLimitError(QwenServiceError):
    """Rate limit exceeded."""

    pass


async def stream_qwen_chat(
    api_key: str,
    message: str,
    model: str = "qwen3.8-flash",
    timeout: float = 60.0,
) -> AsyncGenerator[str, None]:
    """Stream chat completion from DashScope Qwen model.

    Args:
        api_key: DashScope API key (never logged or exposed).
        message: User message to send.
        model: Model ID to use.
        timeout: Request timeout in seconds.

    Yields:
        str: Incremental text chunks from the model.

    Raises:
        QwenAuthError: If API key is invalid or missing.
        QwenModelError: If model is not found or not accessible.
        QwenRateLimitError: If rate limit is exceeded.
        QwenServiceError: For other service errors.
    """
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code == 401:
                    raise QwenAuthError("API key authentication failed. Please check DASHSCOPE_API_KEY.")
                elif response.status_code == 404:
                    raise QwenModelError(
                        f"Model '{model}' not found or not accessible. "
                        "Please verify model ID and account permissions."
                    )
                elif response.status_code == 429:
                    raise QwenRateLimitError("Rate limit exceeded. Please try again later.")
                elif response.status_code >= 400:
                    error_text = await response.aread()
                    error_summary = _extract_error_summary(error_text)
                    raise QwenServiceError(
                        f"DashScope API error (HTTP {response.status_code}): {error_summary}"
                    )

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

    except httpx.TimeoutException as e:
        raise QwenServiceError(f"Request timeout: {e}")
    except httpx.NetworkError as e:
        raise QwenServiceError(f"Network error: {e}")
    except (QwenAuthError, QwenModelError, QwenRateLimitError):
        raise
    except Exception as e:
        raise QwenServiceError(f"Unexpected error: {type(e).__name__}")


def _extract_error_summary(error_bytes: bytes) -> str:
    """Extract sanitized error summary from API response.

    Args:
        error_bytes: Raw error response body.

    Returns:
        str: Sanitized error message (no API keys or sensitive data).
    """
    try:
        text = error_bytes.decode("utf-8")[:500]
        data = json.loads(text)
        if "error" in data:
            error_info = data["error"]
            if isinstance(error_info, dict):
                return error_info.get("message", "Unknown error")
            return str(error_info)
        return text[:200]
    except Exception:
        return "Unable to parse error response"
