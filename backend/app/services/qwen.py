"""Qwen/DashScope streaming service layer.

DEPRECATED: This module is maintained for backward compatibility with existing tests.
New code should use app.ai.control.execute_chat instead.

This module now acts as a thin wrapper around the AI control layer.
"""
from __future__ import annotations

from typing import AsyncGenerator

# Import from AI control layer
from app.ai.adapters.qwen import (
    QwenError as QwenServiceError,
    QwenAuthError,
    QwenModelError,
    QwenRateLimitError,
    QwenServiceError as _QwenServiceError,
)
from app.ai import execute_chat, ChatContext, ChatMessage


# Re-export exceptions for backward compatibility
__all__ = [
    "stream_qwen_chat",
    "stream_qwen_chat_with_context",
    "QwenServiceError",
    "QwenAuthError",
    "QwenModelError",
    "QwenRateLimitError",
]


async def stream_qwen_chat(
    api_key: str,
    message: str,
    model: str = "qwen3.8-flash",
    timeout: float = 60.0,
) -> AsyncGenerator[str, None]:
    """Stream chat completion from DashScope Qwen model.

    DEPRECATED: This function is maintained for backward compatibility.
    Use app.ai.control.execute_chat with ChatContext instead.

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
    # Delegate to AI control layer
    context = ChatContext(
        messages=[ChatMessage(role="user", content=message)],
        user_nickname="",
        model=model,
    )
    
    try:
        async for chunk in execute_chat(api_key=api_key, context=context):
            yield chunk
    except Exception:
        # Exceptions are already properly typed from AI control layer
        raise


async def stream_qwen_chat_with_context(
    api_key: str,
    context: list[dict[str, str]],
    user_nickname: str = "",
    model: str = "qwen3.8-flash",
    timeout: float = 60.0,
) -> AsyncGenerator[str, None]:
    """Stream chat with multi-turn context and optional user nickname.

    DEPRECATED: This function is maintained for backward compatibility.
    Use app.ai.control.execute_chat with ChatContext instead.

    Args:
        api_key: DashScope API key.
        context: List of message dicts with 'role' and 'content'.
        user_nickname: User's nickname for personalized responses.
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
    # Convert dict-based context to ChatMessage objects
    messages = [
        ChatMessage(role=msg["role"], content=msg["content"])
        for msg in context
    ]
    
    # Delegate to AI control layer
    chat_context = ChatContext(
        messages=messages,
        user_nickname=user_nickname,
        model=model,
    )
    
    try:
        async for chunk in execute_chat(api_key=api_key, context=chat_context):
            yield chunk
    except Exception:
        # Exceptions are already properly typed from AI control layer
        raise
