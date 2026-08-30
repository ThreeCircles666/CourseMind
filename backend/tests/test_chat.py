"""Tests for chat streaming endpoint."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_chat_stream_no_api_key(monkeypatch):
    """Test that endpoint returns error when API key is not configured."""
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setattr("app.core.config.settings.dashscope_api_key", "")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": "Hello"},
        )
        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_stream_empty_message():
    """Test that endpoint rejects empty messages."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": ""},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_invalid_request():
    """Test that endpoint rejects invalid request body."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={},
        )
        assert response.status_code == 422
