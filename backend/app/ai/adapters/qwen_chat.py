"""Qwen chat provider adapter for RAG."""
from __future__ import annotations

from app.ai.chat_contracts import (
    ChatProvider,
    ChatResult,
    ChatAuthError,
    ChatRateLimitError,
    ChatServiceError,
)
from app.ai.adapters import qwen


class QwenChatProvider(ChatProvider):
    """Qwen/DashScope chat provider for RAG."""

    def __init__(
        self,
        api_key: str,
        model: str = "qwen3.8-flash",
        timeout: float = 60.0,
    ):
        """Initialize Qwen chat provider.

        Args:
            api_key: DashScope API key
            model: Model name
            timeout: Request timeout
        """
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> ChatResult:
        """Generate non-streaming chat completion.

        Args:
            system_prompt: System instructions
            user_prompt: User message

        Returns:
            ChatResult with complete text

        Raises:
            ChatAuthError: Authentication failed
            ChatRateLimitError: Rate limit exceeded
            ChatServiceError: Other service errors
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            # Collect streaming chunks into complete text
            text_chunks = []
            async for chunk in qwen.stream_chat(
                api_key=self._api_key,
                messages=messages,
                model=self._model,
                timeout=self._timeout,
            ):
                text_chunks.append(chunk)

            complete_text = "".join(text_chunks)

            return ChatResult(
                text=complete_text,
                model=self._model,
                finish_reason="stop",
            )

        except qwen.QwenAuthError as e:
            raise ChatAuthError(str(e)) from e
        except qwen.QwenRateLimitError as e:
            raise ChatRateLimitError(str(e)) from e
        except (qwen.QwenServiceError, qwen.QwenError) as e:
            raise ChatServiceError(str(e)) from e
