"""Tests for the health check endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_payload():
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "courseguard-api"
    assert set(data.keys()) == {"status", "service", "version"}
    assert isinstance(data["version"], str)
