"""RAG (Retrieval-Augmented Generation) API routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.adapters.qwen_chat import QwenChatProvider
from app.ai.adapters.dashscope_embedding import DashScopeEmbeddingProvider
from app.ai.chat_contracts import (
    ChatAuthError,
    ChatRateLimitError,
    ChatServiceError,
)
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.rag import RagAskRequest, RagAskResponse
from app.services.rag import (
    RagService,
    RagValidationError,
    RagRetrievalError,
    InvalidCitationError,
)
from app.services.retrieval import RetrievalError, InvalidQueryError

router = APIRouter(tags=["rag"])
logger = logging.getLogger(__name__)


def get_rag_service() -> RagService:
    """Create RAG service with providers.

    Returns:
        Configured RAG service

    Raises:
        HTTPException: If API key not configured
    """
    if not settings.dashscope_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DashScope API key not configured",
        )

    embedding_provider = DashScopeEmbeddingProvider(
        api_key=settings.dashscope_api_key,
        model="text-embedding-v3",
    )

    chat_provider = QwenChatProvider(
        api_key=settings.dashscope_api_key,
        model=getattr(settings, "rag_chat_model", "qwen3.8-flash"),
    )

    return RagService(
        embedding_provider=embedding_provider,
        chat_provider=chat_provider,
        max_context_chars=getattr(settings, "rag_max_context_chars", 12000),
        max_excerpt_chars=getattr(settings, "rag_max_excerpt_chars", 300),
    )


@router.post("/rag/ask", response_model=RagAskResponse)
async def ask_question(
    request: RagAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    rag_service: RagService = Depends(get_rag_service),
) -> RagAskResponse:
    """Answer question using RAG over specified documents.

    This endpoint retrieves relevant document chunks and generates
    an answer grounded in the retrieved content.

    Document access control: All document_ids must belong to current user.

    Args:
        request: RAG request with question and document IDs
        current_user: Authenticated user
        db: Database session
        rag_service: RAG service instance

    Returns:
        Answer with source references

    Raises:
        HTTPException: 404 if any document not found or unauthorized
    """
    try:
        logger.info(
            f"RAG request from user {current_user.id}: "
            f"question_len={len(request.question)}, "
            f"docs={len(request.document_ids)}"
        )

        # Verify all documents belong to current user BEFORE calling any provider
        from app.models import Document as DocumentModel
        verified_count = db.scalar(
            select(func.count())
            .select_from(DocumentModel)
            .where(DocumentModel.id.in_(request.document_ids))
            .where(DocumentModel.user_id == current_user.id)
        )

        if verified_count != len(request.document_ids):
            # Some documents don't exist, belong to another user, or have NULL owner
            logger.warning(
                f"User {current_user.id} attempted to access unauthorized documents. "
                f"Requested: {len(request.document_ids)}, Verified: {verified_count}"
            )
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )

        response = await rag_service.answer(
            session=db,
            request=request,
            current_user_id=current_user.id,
        )

        logger.info(
            f"RAG response: answer_len={len(response.answer)}, "
            f"sources={len(response.sources)}, "
            f"insufficient={response.insufficient_context}"
        )

        return response

    except (RagValidationError, InvalidQueryError) as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    except RagRetrievalError as e:
        logger.error(f"Retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents",
        )

    except ChatAuthError as e:
        logger.error(f"Chat auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service authentication failed",
        )

    except ChatRateLimitError as e:
        logger.warning(f"Chat rate limit: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service rate limit exceeded, please try again later",
        )

    except ChatServiceError as e:
        logger.error(f"Chat service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable",
        )
    except TimeoutError as e:
        logger.warning(f"RAG request timed out: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="RAG request timed out",
        )

    except InvalidCitationError as e:
        logger.warning(f"Invalid citation: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI response contains invalid citations",
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Unexpected error in RAG: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
