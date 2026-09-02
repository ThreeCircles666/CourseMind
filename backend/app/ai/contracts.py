"""AI control layer internal contracts.

These types are internal to the AI control layer and should not leak to external APIs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChatMessage:
    """Internal representation of a chat message."""
    
    role: str  # 'user', 'assistant', or 'system'
    content: str


@dataclass
class ChatContext:
    """Context for AI chat execution."""
    
    messages: list[ChatMessage]  # Message history
    user_nickname: str = ""  # Optional user nickname for personalization
    model: str = "qwen3.8-flash"  # Model to use
