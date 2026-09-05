"""Chat provider abstraction for RAG."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatResult:
    """Result of a chat completion."""

    text: str
    model: str
    finish_reason: str | None = None


class ChatProvider(ABC):
    """Abstract interface for chat completion providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name."""
        raise NotImplementedError

    @abstractmethod
    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> ChatResult:
        """Generate chat completion.

        Args:
            system_prompt: System instructions
            user_prompt: User message

        Returns:
            ChatResult with generated text

        Raises:
            ChatAuthError: Authentication failed
            ChatRateLimitError: Rate limit exceeded
            ChatServiceError: Other service errors
        """
        raise NotImplementedError


class ChatError(Exception):
    """Base exception for chat provider errors."""
    pass


class ChatAuthError(ChatError):
    """Authentication error."""
    pass


class ChatRateLimitError(ChatError):
    """Rate limit exceeded."""
    pass


class ChatServiceError(ChatError):
    """Service error."""
    pass
