"""Real service phase order, stream errors, authorization and resource cleanup."""
import asyncio
import contextlib
import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.ai.chat_contracts import ChatResult, ChatRateLimitError
from app.api.dependencies import get_current_user
from app.api.routes import rag as routes
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.schemas.rag import RagAskRequest
from app.services.rag import RagService, rag_progress
from app.services.retrieval import RetrievalHit


@pytest.fixture
def setup(monkeypatch):
    user = User(id=1, username='progress-test', nickname='Test', password_hash='unused', is_active=True, token_version=0)
    document_id = uuid4()
    hit = RetrievalHit(chunk_id=uuid4(), document_id=document_id, file_name='synthetic.pdf', chunk_index=0,
                       content='Source evidence', page_number=1, title_path=(), similarity=.9, distance=.1)
    search = AsyncMock(return_value=[hit]); monkeypatch.setattr('app.services.rag.search', search)
    chat = AsyncMock(); chat.generate.return_value = ChatResult(text='{"status":"answered","answer":"Answer [S1]"}', model='fake', finish_reason='stop')
    service = RagService(embedding_provider=AsyncMock(), chat_provider=chat)
    db = MagicMock(); db.scalar.return_value = 1; db.get.return_value = user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[routes.get_rag_service] = lambda: service
    app.dependency_overrides[routes.get_stream_session_factory] = lambda: lambda: contextlib.nullcontext(db)
    with TestClient(app) as client:
        yield client, document_id, search, chat, service, db, user
    app.dependency_overrides.clear()


def parse(response):
    result = []
    for frame in response.text.split('\n\n'):
        lines = frame.splitlines()
        kind = next((line[7:] for line in lines if line.startswith('event: ')), None)
        data = next((line[6:] for line in lines if line.startswith('data: ')), None)
        if kind and data: result.append((kind, json.loads(data)))
    return result


def test_stream_reports_real_phases_then_validated_result(setup):
    client, doc, *_ = setup
    response = client.post('/api/v1/rag/ask/stream', json={'question': 'Question', 'document_ids': [str(doc)]})
    assert response.status_code == 200 and response.headers['content-type'].startswith('text/event-stream')
    events = parse(response)
    assert [data['phase'] for kind, data in events if kind == 'phase'] == ['authorizing', 'retrieving', 'generating', 'validating']
    assert events[-1][0] == 'result' and events[-1][1]['answer'] == 'Answer [S1]'
    assert len(events[-1][1]['sources']) == 1
    assert all(set(data) == {'phase'} for kind, data in events if kind == 'phase')


def test_insufficient_material_skips_model_generation(setup):
    client, doc, search, chat, *_ = setup
    search.return_value = []
    events = parse(client.post('/api/v1/rag/ask/stream', json={'question': 'Unknown', 'document_ids': [str(doc)]}))
    assert [data['phase'] for kind, data in events if kind == 'phase'] == ['authorizing', 'retrieving']
    assert events[-1][1]['insufficient_context'] is True
    chat.generate.assert_not_awaited()


def test_stream_rejects_foreign_sources_before_opening(setup):
    client, doc, search, chat, service, db, _ = setup
    db.scalar.return_value = 0
    response = client.post('/api/v1/rag/ask/stream', json={'question': 'Question', 'document_ids': [str(doc)]})
    assert response.status_code == 404
    search.assert_not_awaited(); chat.generate.assert_not_awaited()


def test_stream_requires_authentication(setup):
    client, doc, *_ = setup
    app.dependency_overrides.pop(get_current_user)
    assert client.post('/api/v1/rag/ask/stream', json={'question': 'Question', 'document_ids': [str(doc)]}).status_code == 401


def test_invalid_citation_is_an_error_not_an_answer(setup):
    client, doc, _, chat, *_ = setup
    chat.generate.return_value = ChatResult(text='{"status":"answered","answer":"Invalid [S99]"}', model='fake', finish_reason='stop')
    events = parse(client.post('/api/v1/rag/ask/stream', json={'question': 'Question', 'document_ids': [str(doc)]}))
    assert events[-1][0] == 'error' and events[-1][1]['status'] == 502
    assert not any(kind == 'result' for kind, _ in events)


def test_provider_failure_ends_with_sanitized_error(setup):
    client, doc, _, chat, *_ = setup
    chat.generate.side_effect = ChatRateLimitError('private upstream detail')
    response = client.post('/api/v1/rag/ask/stream', json={'question': 'Question', 'document_ids': [str(doc)]})
    events = parse(response)
    assert events[-1][0] == 'error' and events[-1][1]['status'] == 503
    assert 'private upstream detail' not in response.text


def test_disconnect_cancels_generation_and_closes_session(setup):
    _, doc, _, chat, service, db, user = setup
    closed = []
    @contextlib.contextmanager
    def session_factory():
        try: yield db
        finally: closed.append(True)
    async def slow(**kwargs): await asyncio.sleep(60)
    chat.generate.side_effect = slow
    async def run():
        response = await routes.ask_question_stream(RagAskRequest(question='Question', document_ids=[doc]), user, db, service, session_factory)
        iterator = response.body_iterator
        assert 'authorizing' in await anext(iterator)
        await iterator.aclose()
    asyncio.run(run())
    assert closed == [True]


def test_concurrent_questions_keep_phase_observers_isolated(setup):
    _, doc, _, chat, service, *_ = setup
    async def generate(**kwargs):
        await asyncio.sleep(0)
        return ChatResult(text='{"status":"answered","answer":"Answer [S1]"}', model='fake', finish_reason='stop')
    chat.generate.side_effect = generate
    observations = [[], []]
    async def one(index):
        token = rag_progress.set(observations[index].append)
        try: await service.answer(session=None, request=RagAskRequest(question='Question', document_ids=[doc]), current_user_id=1)
        finally: rag_progress.reset(token)
    async def run(): await asyncio.gather(one(0), one(1))
    asyncio.run(run())
    assert observations == [['retrieving', 'generating', 'validating']] * 2
    assert rag_progress.get() is None
