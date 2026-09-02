"""AI control layer for orchestrating AI capabilities.

This layer coordinates AI-related operations including prompt organization,
context assembly, model selection, and model invocation.
"""
from __future__ import annotations

from typing import AsyncGenerator

from app.ai.contracts import ChatContext, ChatMessage
from app.ai.adapters import qwen


class AIControlError(Exception):
    """Base exception for AI control layer errors."""
    pass


class AIAuthError(AIControlError):
    """AI authentication error."""
    pass


class AIModelError(AIControlError):
    """AI model error."""
    pass


class AIRateLimitError(AIControlError):
    """AI rate limit error."""
    pass


class AIServiceError(AIControlError):
    """AI service error."""
    pass


async def execute_chat(
    api_key: str,
    context: ChatContext,
) -> AsyncGenerator[str, None]:
    """Execute AI chat with given context.

    This is the main entry point for chat-based AI interactions. It handles:
    - System prompt assembly (user nickname personalization)
    - Message context organization
    - Model invocation
    - Error transformation

    Args:
        api_key: API key for the model provider.
        context: Chat context including messages, user info, and model selection.

    Yields:
        str: Incremental text chunks from the AI model.

    Raises:
        AIAuthError: Authentication failed.
        AIModelError: Model error.
        AIRateLimitError: Rate limit exceeded.
        AIServiceError: Other service errors.
    """
    # Assemble messages with system prompt if user nickname is provided
    messages = []
    
    if context.user_nickname:
        messages.append({
            "role": "system",
            "content": f"用户昵称是「{context.user_nickname}」，在自然且合适的情况下可以这样称呼用户。"
        })
    
    # Add all context messages
    for msg in context.messages:
        messages.append({
            "role": msg.role,
            "content": msg.content,
        })
    
    # Execute model call with error transformation
    try:
        async for chunk in qwen.stream_chat(
            api_key=api_key,
            messages=messages,
            model=context.model,
        ):
            yield chunk
    except qwen.QwenAuthError as e:
        raise AIAuthError(str(e)) from e
    except qwen.QwenModelError as e:
        raise AIModelError(str(e)) from e
    except qwen.QwenRateLimitError as e:
        raise AIRateLimitError(str(e)) from e
    except qwen.QwenServiceError as e:
        raise AIServiceError(str(e)) from e
    except qwen.QwenError as e:
        raise AIServiceError(str(e)) from e
