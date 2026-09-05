"""Tests for chat streaming endpoint."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_current_user
from app.main import app
from app.models.user import User


@pytest.mark.anyio
async def test_chat_stream_no_api_key(monkeypatch):
    """Test that endpoint returns error when API key is not configured."""
    user = User(id=1, username="chat-test", nickname="Chat Test", password_hash="test", is_active=True, token_version=0)
    app.dependency_overrides[get_current_user] = lambda: user
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setattr("app.core.config.settings.dashscope_api_key", "")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": "Hello"},
        )
        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_chat_stream_empty_message():
    """Test that endpoint rejects empty messages."""
    user = User(id=1, username="chat-test", nickname="Chat Test", password_hash="test", is_active=True, token_version=0)
    app.dependency_overrides[get_current_user] = lambda: user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": ""},
        )
        assert response.status_code == 422
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_chat_stream_invalid_request():
    """Test that endpoint rejects invalid request body."""
    user = User(id=1, username="chat-test", nickname="Chat Test", password_hash="test", is_active=True, token_version=0)
    app.dependency_overrides[get_current_user] = lambda: user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={},
        )
        assert response.status_code == 422
    app.dependency_overrides.clear()
