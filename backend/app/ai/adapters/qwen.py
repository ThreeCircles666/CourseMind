"""Qwen/DashScope adapter for AI control layer.

This module handles the low-level communication with Alibaba Cloud DashScope API.
"""
from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx


class QwenError(Exception):
    """Base exception for Qwen adapter errors."""
    pass


class QwenAuthError(QwenError):
    """Authentication or API key error."""
    pass


class QwenModelError(QwenError):
    """Model not found or not accessible."""
    pass


class QwenRateLimitError(QwenError):
    """Rate limit exceeded."""
    pass


class QwenServiceError(QwenError):
    """Other service errors."""
    pass


async def stream_chat(
    api_key: str,
    messages: list[dict[str, str]],
    model: str = "qwen3.8-flash",
    timeout: float = 60.0,
) -> AsyncGenerator[str, None]:
    """Stream chat completion from DashScope.

    Args:
        api_key: DashScope API key.
        messages: List of message dicts with 'role' and 'content'.
        model: Model ID to use.
        timeout: Request timeout in seconds.

    Yields:
        str: Incremental text chunks from the model.

    Raises:
        QwenAuthError: Invalid API key.
        QwenModelError: Model not found.
        QwenRateLimitError: Rate limit exceeded.
        QwenServiceError: Other API or network errors.
    """
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
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
