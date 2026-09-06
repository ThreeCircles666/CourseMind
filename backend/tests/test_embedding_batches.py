"""Exercise the real adapter over a fake HTTP transport; no network or DB."""
import asyncio
import json

import httpx
import pytest

from app.ai.adapters.dashscope_embedding import DashScopeEmbeddingProvider
from app.ai.embedding_contracts import EmbeddingServiceError


def install_transport(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs),
    )


def response(texts, dimension=2, model="text-embedding-v3"):
    return httpx.Response(200, json={
        "model": model,
        "data": [
            {"index": i, "embedding": [float(text)] * dimension}
            for i, text in reversed(list(enumerate(texts)))
        ],
    })


@pytest.mark.parametrize("count", [1, 10, 11, 20, 64])
def test_batches_preserve_order_and_limit(monkeypatch, count):
    calls = []

    def handler(request):
        texts = json.loads(request.content)["input"]
        calls.append(texts)
        assert 1 <= len(texts) <= 10
        return response(texts)

    install_transport(monkeypatch, handler)
    result = asyncio.run(DashScopeEmbeddingProvider("fake").embed(
        [str(i) for i in range(1, count + 1)]
    ))
    assert [len(batch) for batch in calls] == [10] * (count // 10) + ([count % 10] if count % 10 else [])
    assert result.vectors == [[float(i)] * 2 for i in range(1, count + 1)]


def test_empty_positions_preserved_across_batches(monkeypatch):
    install_transport(monkeypatch, lambda req: response(json.loads(req.content)["input"]))
    texts = ["", *map(str, range(1, 12)), " ", "12"]
    result = asyncio.run(DashScopeEmbeddingProvider("fake").embed(texts))
    assert result.vectors == [[float(t)] * 2 if t.strip() else [0.0, 0.0] for t in texts]


@pytest.mark.parametrize("permanent", [False, True])
def test_retry_only_failed_batch_and_never_return_partial(monkeypatch, permanent):
    calls = []

    async def no_sleep(_):
        pass

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    def handler(request):
        texts = json.loads(request.content)["input"]
        calls.append(texts[0])
        if texts[0] == "11" and (permanent or calls.count("11") == 1):
            return httpx.Response(503, json={"message": "temporary failure"})
        return response(texts)

    install_transport(monkeypatch, handler)
    provider = DashScopeEmbeddingProvider("fake", max_retries=2)
    if permanent:
        with pytest.raises(EmbeddingServiceError):
            asyncio.run(provider.embed(list(map(str, range(1, 25)))))
        assert calls == ["1", "11", "11"]
    else:
        result = asyncio.run(provider.embed(list(map(str, range(1, 25)))))
        assert len(result.vectors) == 24
        assert calls == ["1", "11", "11", "21"]


@pytest.mark.parametrize("dimension,model", [(3, "text-embedding-v3"), (2, "other")])
def test_cross_batch_contract_mismatch_rejected(monkeypatch, dimension, model):
    def handler(request):
        texts = json.loads(request.content)["input"]
        return response(texts, dimension, model) if texts[0] == "11" else response(texts)

    install_transport(monkeypatch, handler)
    with pytest.raises(EmbeddingServiceError, match="across batches"):
        asyncio.run(DashScopeEmbeddingProvider("fake").embed(list(map(str, range(1, 12)))))
