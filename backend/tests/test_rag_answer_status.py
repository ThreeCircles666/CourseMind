"""Answer sufficiency is independent of retrieval similarity."""
import asyncio
import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.ai.chat_contracts import ChatResult
from app.schemas.rag import RagAskRequest
from app.services.rag import (
    RagService, InvalidAnswerError, InvalidCitationError, INSUFFICIENT_CONTEXT_ANSWER,
)
from app.services.retrieval import RetrievalHit


def run_answer(monkeypatch, text, finish_reason="stop"):
    doc_id = uuid4()
    hits = [RetrievalHit(
        chunk_id=uuid4(), document_id=doc_id, file_name="test.pdf",
        chunk_index=i, content="课程复习内容", page_number=i + 1,
        title_path=(), similarity=0.9, distance=0.1,
    ) for i in range(2)]
    monkeypatch.setattr("app.services.rag.search", AsyncMock(return_value=hits))
    chat = AsyncMock()
    chat.generate.return_value = ChatResult(text=text, model="fake", finish_reason=finish_reason)
    service = RagService(embedding_provider=AsyncMock(), chat_provider=chat)
    return asyncio.run(service.answer(
        session=None, request=RagAskRequest(question="考试安排？", document_ids=[doc_id]),
        current_user_id=123,
    ))


@pytest.mark.parametrize("answer", ["资料没有提供。", "现有文档不足以回答该问题。[S1][S2]"])
def test_model_refusal_clears_sources_even_with_high_similarity(monkeypatch, answer):
    result = run_answer(monkeypatch, json.dumps({"status": "insufficient", "answer": answer}))
    assert result.insufficient_context is True
    assert result.answer == INSUFFICIENT_CONTEXT_ANSWER
    assert result.sources == []
    assert result.model == "fake"


@pytest.mark.parametrize("status", ["answered", "partial"])
def test_only_cited_evidence_returned(monkeypatch, status):
    answer = "该部分不考[S2]。" + ("资料未提供考试时间。" if status == "partial" else "")
    result = run_answer(monkeypatch, json.dumps({"status": status, "answer": answer}))
    assert result.answer == answer
    assert result.insufficient_context is (status == "partial")
    assert [s.source_id for s in result.sources] == ["S2"]


@pytest.mark.parametrize("text", [
    "现有文档不足以回答该问题。", "not json", "[]",
    '{"status":"unknown","answer":"x"}',
    '{"status":"answered","answer":1}',
    '{"status":"answered","answer":""}',
    '{"answer":"x"}',
])
def test_invalid_protocol_is_not_presented_as_success(monkeypatch, text):
    with pytest.raises(InvalidAnswerError):
        run_answer(monkeypatch, text)


@pytest.mark.parametrize("answer", ["没有引用的结论", "结论[S99]"])
def test_missing_or_fabricated_citation_is_rejected(monkeypatch, answer):
    with pytest.raises(InvalidCitationError):
        run_answer(monkeypatch, json.dumps({"status": "answered", "answer": answer}))


def test_truncated_output_is_rejected(monkeypatch):
    with pytest.raises(InvalidAnswerError):
        run_answer(monkeypatch, '{"status":"answered","answer":"事实[S1]"}', "length")
