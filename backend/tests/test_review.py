"""Source validation, full-page jobs and owner isolation without external AI/DB."""
import asyncio
import io
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.api.dependencies import get_current_user
from app.api.routes import review as routes
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.schemas.review import GeneratedBatch
from app.services.review import batches, generate_review, read_json, validate_batch, write_json
from app.services.review_checks import arithmetic_candidates
from app.services.review_media import extract_pages, render_page


def batch(pages=(1,), quote="Definition"):
    return {"sections": [{"title": "Topic", "pages": list(pages),
        "blocks": [{"kind": "explanation", "text": "Source explanation", "evidence": [{"page": pages[0], "quote": quote}]}],
        "takeaways": [{"kind": "definition", "name": "Definition", "text": "Definition", "evidence": [{"page": pages[0], "quote": quote}]}]}]}


def test_coverage_and_evidence_validation():
    pages = [{"number": 1, "text": "Definition"}, {"number": 2, "text": "Example"}]
    validate_batch(GeneratedBatch.model_validate(batch((1, 2))), pages)
    for invalid in [batch((1,)), batch((1, 1, 2)), batch((2, 1)), batch((1, 2), "invented quote")]:
        with pytest.raises(ValueError):
            validate_batch(GeneratedBatch.model_validate(invalid), pages)
    invalid = batch((1, 2)); invalid["sections"][0]["blocks"][0]["evidence"] = []
    with pytest.raises(ValueError, match="requires source"):
        validate_batch(GeneratedBatch.model_validate(invalid), pages)


def test_quote_code_and_visual_provenance():
    payload = batch(); payload["sections"][0]["blocks"][0].update(kind="quote", text="made up")
    with pytest.raises(ValueError, match="quotations"):
        validate_batch(GeneratedBatch.model_validate(payload), [{"number": 1, "text": "Definition"}])
    payload["sections"][0]["blocks"][0].update(kind="code", text="print('not in source')")
    with pytest.raises(ValueError, match="Code must match"):
        validate_batch(GeneratedBatch.model_validate(payload), [{"number": 1, "text": "Definition"}])
    value = GeneratedBatch.model_validate(batch())
    validate_batch(value, [{"number": 1, "text": "", "visual_description": "Definition"}])
    assert value.sections[0].blocks[0].evidence[0].origin == "vision"


def test_no_truncation_and_page_budget():
    pages = [{"number": i, "text": "x" * 8000} for i in range(1, 8)]
    groups = batches(pages)
    assert [p for group in groups for p in group] == pages
    assert all(len(g) <= 4 for g in groups)
    with pytest.raises(ValueError, match="budget"):
        batches([{"number": 1, "text": "x" * 24001}])


class FakeAI:
    async def complete(self, system, content, *, vision=False):
        if vision:
            return "Definition from chart: 2 + 2 = 5"
        pages = json.loads(content.split("\nPrevious validation failed:")[0])
        return json.dumps(batch(tuple(p["number"] for p in pages),
                                "Definition" if "Definition" in pages[0]["text"] else "Definition from chart"))


def test_generation_persists_coverage_and_arithmetic(tmp_path):
    source = tmp_path / "source.txt"; source.write_text("Definition: 2 + 2 = 5")
    path = tmp_path / "review" / "review.json"
    write_json(path, {"id": str(uuid4()), "language": "zh-CN", "use_vision": False,
                     "documents": [], "sections": [], "duplicates": [], "completed_pages": 0})
    asyncio.run(generate_review(path, [{"id": str(uuid4()), "name": "source.txt", "path": str(source)}], FakeAI()))
    state = read_json(path)
    assert state["status"] == "ready" and state["completed_pages"] == 1
    assert state["sections"][0]["pages"] == [1]
    assert state["sections"][0]["errata"][0]["status"] == "candidate"
    assert state["sections"][0]["errata"][0]["correction"].endswith("4")


def test_scanned_pdf_visual_reading_and_render(tmp_path):
    writer = PdfWriter(); writer.add_blank_page(400, 300)
    source = tmp_path / "scan.pdf"
    with source.open("wb") as f: writer.write(f)
    media = tmp_path / "media"
    assert extract_pages(source, media, 2)[0]["text"] == ""
    assert render_page(source, media, 1).startswith(b"\xff\xd8")
    with pytest.raises(ValueError): extract_pages(source, media, 0)
    path = tmp_path / "review" / "review.json"
    write_json(path, {"id": str(uuid4()), "language": "en-US", "use_vision": True,
                     "documents": [], "sections": [], "duplicates": [], "completed_pages": 0})
    asyncio.run(generate_review(path, [{"id": str(uuid4()), "name": "scan.pdf", "path": str(source)}], FakeAI()))
    state = read_json(path)
    assert state["status"] == "ready"
    assert state["documents"][0]["pages"][0]["read_mode"] == "vision"
    assert state["sections"][0]["blocks"][0]["evidence"][0]["origin"] == "vision"


def test_invalid_ai_never_publishes_ready(tmp_path):
    class InvalidAI:
        async def complete(self, *args, **kwargs): return json.dumps(batch((99,), "invented"))
    path = tmp_path / "review.json"; source = tmp_path / "source.txt"; source.write_text("Definition")
    write_json(path, {"id": str(uuid4()), "language": "en-US", "use_vision": False,
                     "documents": [], "sections": [], "completed_pages": 0})
    asyncio.run(generate_review(path, [{"id": str(uuid4()), "name": "source.txt", "path": str(source)}], InvalidAI()))
    state = read_json(path)
    assert state["status"] == "failed" and not state["sections"]


def test_arithmetic_rounding_and_no_execution():
    pages = [{"number": 1, "text": "1 / 3 = 0.33; 2 × 3 = 7; 3 - 1 = 2; __import__('os').system('unsafe')"}]
    found = arithmetic_candidates(pages, "en-US")
    assert len(found) == 1 and found[0]["correction"] == "2 × 3 = 6"


def test_pptx_parser():
    from pptx import Presentation
    from app.parsers.registry import ParserRegistry
    from app.services.upload import validate_file_type
    presentation = Presentation(); slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Definition"; slide.placeholders[1].text = "Example"
    stream = io.BytesIO(); presentation.save(stream); data = stream.getvalue()
    validate_file_type("source.pptx", "application/octet-stream", data[:10])
    parsed = ParserRegistry().get_parser("source.pptx").parse(data, "source.pptx")
    assert parsed.pages[0].page_number == 1 and "Definition" in parsed.pages[0].text


@pytest.fixture
def owner_client(tmp_path, monkeypatch):
    document_id = uuid4()
    document = SimpleNamespace(id=document_id, user_id=1, safe_name="source.txt", original_name="Source", status="failed")
    storage = tmp_path / str(document_id); storage.mkdir(); (storage / "source.txt").write_text("Definition")
    class DB:
        def execute(self, query):
            params = query.compile().params
            found = [document] if document.user_id == params.get("user_id_1") and document.id in params.get("id_1", []) else []
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: found))
    user = SimpleNamespace(id=1)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: DB()
    app.dependency_overrides[routes.get_upload_root] = lambda: tmp_path
    monkeypatch.setattr(settings, "dashscope_api_key", "test-not-real")
    async def local_generate(path, sources):
        state = read_json(path)
        section = GeneratedBatch.model_validate(batch()).sections[0].model_dump()
        section.update(id="section-one", document_id=str(document_id))
        section["errata"] = [{"id": "erratum-one", "status": "candidate"}]
        state.update(status="ready", sections=[section], documents=[{"id": str(document_id), "name": "Source", "pages": [{"number": 1, "text": "Definition", "has_image": False}]}])
        write_json(path, state)
    monkeypatch.setattr(routes, "generate_review", local_generate)
    with TestClient(app) as client:
        yield client, tmp_path, user, document
    app.dependency_overrides.clear()


def test_review_lifecycle_and_ownership(owner_client):
    client, root, user, document = owner_client
    response = client.post('/api/v1/reviews', json={"document_ids": [str(document.id)]})
    assert response.status_code == 202
    review_id = response.json()["id"]; url = f'/api/v1/reviews/{review_id}'
    assert client.get(url).json()["status"] == "ready"
    assert len(client.get('/api/v1/reviews').json()) == 1
    response = client.patch(url + '/state', json={"reviewed_sections": ["section-one"], "erratum_id": "erratum-one", "decision": "confirmed"})
    assert response.status_code == 200
    assert response.json()["reviewed_sections"] == ["section-one"]
    assert response.json()["sections"][0]["errata"][0]["status"] == "confirmed"
    assert client.patch(url + '/state', json={"reviewed_sections": ["invented"]}).status_code == 422
    user.id = 2
    assert client.get(url).status_code == 404
    assert client.patch(url + '/state', json={"reviewed_sections": []}).status_code == 404
    assert client.get(url + f'/documents/{document.id}/pages/1/image').status_code == 404
    assert client.delete(url).status_code == 404
    assert client.post('/api/v1/reviews', json={"document_ids": [str(document.id)]}).status_code == 404
    assert client.get('/api/v1/reviews').json() == []
    user.id = 1; document.user_id = 2
    assert client.get(url).status_code == 404
    document.user_id = 1
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


def test_active_job_limit_and_stale_removal(owner_client):
    client, root, user, document = owner_client
    for _ in range(2):
        state = {"id": str(uuid4()), "document_ids": [str(document.id)], "status": "queued", "created_at": "2020-01-01T00:00:00+00:00"}
        write_json(routes.artifact_path(root, user.id, UUID(state['id'])), state)
    assert client.post('/api/v1/reviews', json={"document_ids": [str(document.id)]}).status_code == 429
    assert client.delete(f"/api/v1/reviews/{state['id']}").status_code == 204


def test_requires_authentication(owner_client):
    client, *_ = owner_client
    app.dependency_overrides.pop(get_current_user)
    assert client.get('/api/v1/reviews').status_code == 401


def test_linear_demo_rejects_wrong_coefficients():
    from app.services.review_checks import supports_linear
    assert supports_linear(2, 1, 'y = 2x + 1')
    assert not supports_linear(2, 3, 'y = 2x + 1')
    payload = batch()
    payload['sections'][0]['demos'] = [{'kind': 'linear', 'title': 'Demo', 'a': 2, 'b': 3,
        'evidence': [{'page': 1, 'quote': 'y = 2x + 1'}]}]
    with pytest.raises(ValueError, match='coefficients'):
        validate_batch(GeneratedBatch.model_validate(payload), [{'number': 1, 'text': 'Definition y = 2x + 1'}])


def test_invalid_batch_is_retried_once():
    from app.services.review import summarize
    class RetryingAI:
        calls = 0
        async def complete(self, *args, **kwargs):
            self.calls += 1
            return json.dumps(batch(quote='invented' if self.calls == 1 else 'Definition'))
    ai = RetryingAI()
    result = asyncio.run(summarize(ai, [{'number': 1, 'text': 'Definition'}], 'en-US'))
    assert len(result.sections) == 1 and ai.calls == 2


def test_job_timeout_publishes_failure(tmp_path, monkeypatch):
    import app.services.review as service
    async def stalled(*args): await asyncio.sleep(10)
    monkeypatch.setattr(service, '_generate_review', stalled)
    monkeypatch.setattr(settings, 'review_job_timeout_seconds', .01)
    path = tmp_path / 'review.json'; write_json(path, {'status': 'queued'})
    asyncio.run(generate_review(path, []))
    assert read_json(path)['status'] == 'failed'
