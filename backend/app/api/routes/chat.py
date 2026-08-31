"""Chat streaming and session management routes."""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatStreamEvent,
    MessageResponse,
    SessionDetail,
    SessionRenameRequest,
    SessionSummary,
)
from app.services.qwen import (
    QwenAuthError,
    QwenModelError,
    QwenRateLimitError,
    QwenServiceError,
    stream_qwen_chat_with_context,
)

router = APIRouter(tags=["chat"])


def _generate_title(message: str) -> str:
    """Generate session title from first message."""
    clean = message.strip().replace("\n", " ")
    return clean[:50] + ("..." if len(clean) > 50 else "")


def _verify_session_ownership(session: ChatSession | None, user_id: int) -> ChatSession:
    """Verify session exists and belongs to current user."""
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if session.is_archived:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="会话已归档")
    return session


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream chat completion with session memory.

    Args:
        request: Chat request with user message and optional session_id.
        current_user: Authenticated user.
        db: Database session.

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

    # Get or create session
    session_obj: ChatSession | None = None
    is_new_session = request.session_id is None

    if is_new_session:
        # Create new session
        session_obj = ChatSession(
            user_id=current_user.id,
            title=_generate_title(request.message),
            model="qwen3.8-flash",
            message_count=0,
        )
        db.add(session_obj)
        db.flush()  # Get session ID without committing
    else:
        # Load existing session
        session_obj = db.get(ChatSession, request.session_id)
        _verify_session_ownership(session_obj, current_user.id)

    # Load recent message history (last 20 messages for context)
    history_messages = (
        db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_obj.id)
            .order_by(ChatMessage.sequence)
            .limit(20)
        )
        .scalars()
        .all()
    )

    # Save user message
    user_msg = ChatMessage(
        session_id=session_obj.id,
        role="user",
        content=request.message,
        sequence=len(history_messages),
    )
    db.add(user_msg)
    db.flush()

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from Qwen stream with session management."""
        assistant_content = ""
        session_sent = False

        try:
            # Send session ID in first event
            if not session_sent:
                session_event = ChatStreamEvent(type="session", session_id=session_obj.id)
                yield f"data: {session_event.model_dump_json()}\n\n"
                session_sent = True

            # Build context from history
            context = [{"role": msg.role, "content": msg.content} for msg in history_messages]
            context.append({"role": "user", "content": request.message})

            # Stream from Qwen
            async for chunk in stream_qwen_chat_with_context(
                api_key=api_key,
                context=context,
                user_nickname=current_user.nickname,
                model="qwen3.8-flash",
            ):
                assistant_content += chunk
                event = ChatStreamEvent(type="content", content=chunk)
                yield f"data: {event.model_dump_json()}\n\n"

            # Send done event
            done_event = ChatStreamEvent(type="done")
            yield f"data: {done_event.model_dump_json()}\n\n"

            # Save assistant message after stream completes
            assistant_msg = ChatMessage(
                session_id=session_obj.id,
                role="assistant",
                content=assistant_content,
                sequence=len(history_messages) + 1,
            )
            db.add(assistant_msg)

            # Update session metadata
            session_obj.message_count = len(history_messages) + 2
            db.commit()

        except QwenAuthError as e:
            db.rollback()
            error_event = ChatStreamEvent(type="error", error=str(e))
            yield f"data: {error_event.model_dump_json()}\n\n"
        except QwenModelError as e:
            db.rollback()
            error_event = ChatStreamEvent(type="error", error=str(e))
            yield f"data: {error_event.model_dump_json()}\n\n"
        except QwenRateLimitError as e:
            db.rollback()
            error_event = ChatStreamEvent(type="error", error=str(e))
            yield f"data: {error_event.model_dump_json()}\n\n"
        except QwenServiceError as e:
            db.rollback()
            error_event = ChatStreamEvent(type="error", error=str(e))
            yield f"data: {error_event.model_dump_json()}\n\n"
        except Exception as e:
            db.rollback()
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


@router.get("/chat/sessions", response_model=list[SessionSummary])
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionSummary]:
    """List user's chat sessions.

    Args:
        limit: Maximum number of sessions to return.
        offset: Number of sessions to skip.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of session summaries, ordered by most recent first.
    """
    sessions = (
        db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == current_user.id, ChatSession.is_archived == False)
            .order_by(desc(ChatSession.updated_at))
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return [SessionSummary.model_validate(s) for s in sessions]


@router.get("/chat/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionDetail:
    """Get session details with all messages.

    Args:
        session_id: Session ID to retrieve.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Session detail with messages.

    Raises:
        HTTPException: If session not found or access denied.
    """
    session = db.get(ChatSession, session_id)
    _verify_session_ownership(session, current_user.id)

    # Load all messages for display
    messages = (
        db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.sequence)
        )
        .scalars()
        .all()
    )

    return SessionDetail(
        id=session.id,
        title=session.title,
        model=session.model,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.patch("/chat/sessions/{session_id}")
async def rename_session(
    session_id: int,
    request: SessionRenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Rename a chat session.

    Args:
        session_id: Session ID to rename.
        request: New title.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Success message.

    Raises:
        HTTPException: If session not found or access denied.
    """
    session = db.get(ChatSession, session_id)
    _verify_session_ownership(session, current_user.id)

    session.title = request.title
    db.commit()

    return {"message": "会话已重命名"}


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete (archive) a chat session.

    Args:
        session_id: Session ID to delete.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Success message.

    Raises:
        HTTPException: If session not found or access denied.
    """
    session = db.get(ChatSession, session_id)
    _verify_session_ownership(session, current_user.id)

    session.is_archived = True
    db.commit()

    return {"message": "会话已删除"}
