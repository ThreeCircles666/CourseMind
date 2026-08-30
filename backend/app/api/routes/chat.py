"""Chat streaming route."""
from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatStreamEvent
from app.services.qwen import (
    QwenAuthError,
    QwenModelError,
    QwenRateLimitError,
    QwenServiceError,
    stream_qwen_chat,
)

router = APIRouter(tags=["chat"])


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream chat completion from Qwen model.

    Args:
        request: Chat request with user message.

    Returns:
        StreamingResponse: SSE stream with incremental text chunks.

    Raises:
        HTTPException: If API key is not configured or service error occurs.
    """
    if not settings.is_dashscope_configured():
        raise HTTPException(
            status_code=500,
            detail="DashScope API key is not configured. Please set DASHSCOPE_API_KEY environment variable.",
        )

    try:
        api_key = settings.get_dashscope_key()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from Qwen stream."""
        try:
            async for chunk in stream_qwen_chat(
                api_key=api_key,
                message=request.message,
                model="qwen3.8-flash",
            ):
                event = ChatStreamEvent(type="content", content=chunk)
                yield f"data: {event.model_dump_json()}\n\n"

            done_event = ChatStreamEvent(type="done")
            yield f"data: {done_event.model_dump_json()}\n\n"

        except QwenAuthError as e:
            error_event = ChatStreamEvent(type="error", error=str(e))
            yield f"data: {error_event.model_dump_json()}\n\n"
        except QwenModelError as e:
            error_event = ChatStreamEvent(type="error", error=str(e))
            yield f"data: {error_event.model_dump_json()}\n\n"
        except QwenRateLimitError as e:
            error_event = ChatStreamEvent(type="error", error=str(e))
            yield f"data: {error_event.model_dump_json()}\n\n"
        except QwenServiceError as e:
            error_event = ChatStreamEvent(type="error", error=str(e))
            yield f"data: {error_event.model_dump_json()}\n\n"
        except Exception as e:
            error_event = ChatStreamEvent(
                type="error", error=f"Unexpected server error: {type(e).__name__}"
            )
            yield f"data: {error_event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
