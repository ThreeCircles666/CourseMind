"""FastAPI route integration tests for RAG."""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.rag import get_rag_service
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.services.rag import RagService
from app.models.user import User


class FakeChatProvider:
    """Fake chat provider."""

    def __init__(self, response="答案[S1]"):
        self.response = response
        self.call_count = 0

    @property
    def model_name(self):
        return "fake-model"

    async def generate(self, *, system_prompt, user_prompt):
        from app.ai.chat_contracts import ChatResult
        self.call_count += 1
        return ChatResult(text=self.response, model="fake-model")


class FakeEmbeddingProvider:
    """Fake embedding provider."""

    def __init__(self):
        self.call_count = 0

    @property
    def model_name(self):
        return "fake-embedding"

    async def embed(self, texts):
        self.call_count += 1
        raise AssertionError("Unauthorized request must not call embedding provider")


@pytest.fixture
def fake_user():
    """Fake authenticated user."""
    # Create a proper User instance matching the actual model
    user = User(
        username="testuser",
        nickname="测试用户",
        password_hash="fake_hash_value",
        is_active=True,
        token_version=0,
    )
    user.id = 1
    return user


@pytest.fixture
def fake_rag_service():
    """Fake RAG service."""
    fake_embedding = FakeEmbeddingProvider()
    fake_chat = FakeChatProvider()

    service = RagService(
        embedding_provider=fake_embedding,
        chat_provider=fake_chat,
    )

    # Mock answer method
    async def fake_answer(*, session, request, current_user_id):
        from app.schemas.rag import RagAskResponse
        return RagAskResponse(
            answer="这是测试答案[S1]",
            sources=[],
            model="fake-model",
            insufficient_context=False,
        )

    service.answer = fake_answer
    return service


@pytest.fixture
def client(fake_user, fake_rag_service):
    """Test client with overridden dependencies."""
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_rag_service] = lambda: fake_rag_service

    def override_db():
        db = MagicMock()
        db.scalar.return_value = 1
        yield db

    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        client.close()


def test_cors_allowed_origin_and_preflight(client):
    response = client.options(
        "/api/v1/rag/ask",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"

    denied = client.get(
        "/api/v1/health",
        headers={"Origin": "http://evil.example"},
    )
    assert "access-control-allow-origin" not in denied.headers


def test_rag_timeout_maps_to_504(client):
    async def timed_out(*, session, request, current_user_id):
        raise TimeoutError("provider timeout")

    service = RagService(
        embedding_provider=FakeEmbeddingProvider(),
        chat_provider=FakeChatProvider(),
    )
    service.answer = timed_out
    app.dependency_overrides[get_rag_service] = lambda: service

    response = client.post(
        "/api/v1/rag/ask",
        json={"question": "测试问题", "document_ids": [str(uuid4())]},
    )
    assert response.status_code == 504
    assert "provider timeout" not in response.text
    app.dependency_overrides.clear()



    """Test OpenAPI schema includes RAG endpoint."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi = response.json()
    assert "/api/v1/rag/ask" in openapi["paths"]
    assert "post" in openapi["paths"]["/api/v1/rag/ask"]


def test_rag_ask_success(client):
    """Test successful RAG request."""
    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "测试问题",
            "document_ids": [str(uuid4())],
            "top_k": 5,
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "sources" in data
    assert "model" in data
    assert "insufficient_context" in data


def test_rag_ask_empty_question(client):
    """Test empty question returns 422."""
    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "",
            "document_ids": [str(uuid4())],
        }
    )

    assert response.status_code == 422


def test_rag_ask_empty_document_ids(client):
    """Test empty document_ids returns 422."""
    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "测试",
            "document_ids": [],
        }
    )

    assert response.status_code == 422


def test_rag_ask_invalid_top_k(client):
    """Test invalid top_k returns 422."""
    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "测试",
            "document_ids": [str(uuid4())],
            "top_k": 0,
        }
    )

    assert response.status_code == 422

    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "测试",
            "document_ids": [str(uuid4())],
            "top_k": 100,
        }
    )

    assert response.status_code == 422


def test_existing_health_endpoint(client):
    """Test existing health endpoint still works."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_existing_chat_endpoint(client):
    """Test existing chat endpoint remains registered."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/chat/sessions" in response.json()["paths"]


def test_rag_no_recall_not_call_chat(client, fake_user):
    """Test no recall returns insufficient without calling chat provider."""
    from app.schemas.rag import RagAskResponse

    fake_embedding = FakeEmbeddingProvider()
    fake_chat = FakeChatProvider()

    service = RagService(
        embedding_provider=fake_embedding,
        chat_provider=fake_chat,
    )

    # Mock answer to return insufficient context
    async def fake_answer_insufficient(*, session, request, current_user_id):
        return RagAskResponse(
            answer="现有文档不足以回答该问题。",
            sources=[],
            model=None,
            insufficient_context=True,
        )

    service.answer = fake_answer_insufficient
    app.dependency_overrides[get_rag_service] = lambda: service

    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "测试问题",
            "document_ids": [str(uuid4())],
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["insufficient_context"] is True
    assert data["model"] is None
    assert data["sources"] == []

    app.dependency_overrides.clear()


def test_rag_invalid_citation_502(client, fake_user):
    """Test invalid citation maps to 502."""
    from app.services.rag import InvalidCitationError

    fake_embedding = FakeEmbeddingProvider()
    fake_chat = FakeChatProvider()

    service = RagService(
        embedding_provider=fake_embedding,
        chat_provider=fake_chat,
    )

    # Mock answer to raise InvalidCitationError
    async def fake_answer_invalid_citation(*, session, request, current_user_id):
        raise InvalidCitationError("Invalid citation [S99]")

    service.answer = fake_answer_invalid_citation
    app.dependency_overrides[get_rag_service] = lambda: service

    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "测试问题",
            "document_ids": [str(uuid4())],
        }
    )

    assert response.status_code == 502
    app.dependency_overrides.clear()


def test_rag_chat_auth_error_503(client, fake_user):
    """Test chat auth error maps to 503."""
    from app.ai.chat_contracts import ChatAuthError

    fake_embedding = FakeEmbeddingProvider()
    fake_chat = FakeChatProvider()

    service = RagService(
        embedding_provider=fake_embedding,
        chat_provider=fake_chat,
    )

    # Mock answer to raise ChatAuthError
    async def fake_answer_auth_error(*, session, request, current_user_id):
        raise ChatAuthError("Authentication failed")

    service.answer = fake_answer_auth_error
    app.dependency_overrides[get_rag_service] = lambda: service

    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "测试问题",
            "document_ids": [str(uuid4())],
        }
    )

    assert response.status_code == 503
    app.dependency_overrides.clear()


def test_rag_chat_rate_limit_503(client, fake_user):
    """Test chat rate limit maps to 503."""
    from app.ai.chat_contracts import ChatRateLimitError

    fake_embedding = FakeEmbeddingProvider()
    fake_chat = FakeChatProvider()

    service = RagService(
        embedding_provider=fake_embedding,
        chat_provider=fake_chat,
    )

    # Mock answer to raise ChatRateLimitError
    async def fake_answer_rate_limit(*, session, request, current_user_id):
        raise ChatRateLimitError("Rate limit exceeded")

    service.answer = fake_answer_rate_limit
    app.dependency_overrides[get_rag_service] = lambda: service

    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "测试问题",
            "document_ids": [str(uuid4())],
        }
    )

    assert response.status_code == 503
    app.dependency_overrides.clear()


def test_rag_chat_service_error_503(client, fake_user):
    """Test chat service error maps to 503."""
    from app.ai.chat_contracts import ChatServiceError

    fake_embedding = FakeEmbeddingProvider()
    fake_chat = FakeChatProvider()

    service = RagService(
        embedding_provider=fake_embedding,
        chat_provider=fake_chat,
    )

    # Mock answer to raise ChatServiceError
    async def fake_answer_service_error(*, session, request, current_user_id):
        raise ChatServiceError("Service temporarily unavailable")

    service.answer = fake_answer_service_error
    app.dependency_overrides[get_rag_service] = lambda: service

    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "测试问题",
            "document_ids": [str(uuid4())],
        }
    )

    assert response.status_code == 503
    app.dependency_overrides.clear()


def test_rag_response_schema_complete(client):
    """Test response includes all required fields."""
    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "测试问题",
            "document_ids": [str(uuid4())],
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Check all required fields
    assert "answer" in data
    assert "sources" in data
    assert "model" in data
    assert "insufficient_context" in data

    assert isinstance(data["answer"], str)
    assert isinstance(data["sources"], list)
    assert isinstance(data["insufficient_context"], bool)


print("✅ Created RAG route integration tests")


def _assert_rag_access_denied_without_provider_calls(document_ids):
    user = User(
        username="requesting_user",
        nickname="Requesting User",
        password_hash="test",
        is_active=True,
        token_version=0,
    )
    user.id = 9001
    embedding = FakeEmbeddingProvider()
    chat = FakeChatProvider()
    service = RagService(embedding_provider=embedding, chat_provider=chat)
    service.answer = AsyncMock(
        side_effect=AssertionError("Authorization must happen before RagService.answer")
    )
    unauthorized_db = MagicMock()
    unauthorized_db.scalar.return_value = 0

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_db] = lambda: unauthorized_db
    try:
        with TestClient(app) as test_client:
            response = test_client.post(
                "/api/v1/rag/ask",
                json={"question": "private question", "document_ids": document_ids},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}
    service.answer.assert_not_awaited()
    assert embedding.call_count == 0
    assert chat.call_count == 0


def test_rag_rejects_other_users_document():
    _assert_rag_access_denied_without_provider_calls([str(uuid4())])


def test_unauthorized_rag_does_not_call_providers():
    _assert_rag_access_denied_without_provider_calls([str(uuid4())])


def test_rag_rejects_mixed_owned_and_foreign_documents():
    _assert_rag_access_denied_without_provider_calls(
        [str(uuid4()), str(uuid4())]
    )


def test_rag_rejects_null_owner_document():
    _assert_rag_access_denied_without_provider_calls([str(uuid4())])
