"""Unit tests for RAG service."""
import pytest
from uuid import uuid4

from app.schemas.rag import RagAskRequest, RagSource
from app.services.rag import RagService, INSUFFICIENT_CONTEXT_ANSWER


class FakeChatProvider:
    def __init__(self, response="答案[S1][S2]", fail=False):
        self.response = response
        self.fail = fail
        self.called = False

    @property
    def model_name(self):
        return "fake-model"

    async def generate(self, *, system_prompt, user_prompt):
        self.called = True
        self.last_system = system_prompt
        self.last_user = user_prompt
        if self.fail:
            raise RuntimeError("Fake failure")
        from app.ai.chat_contracts import ChatResult
        return ChatResult(text=self.response, model="fake-model")


@pytest.mark.anyio
async def test_extract_citations():
    """Test citation extraction."""
    from app.services.rag import RagService

    service = RagService(
        embedding_provider=None,
        chat_provider=None,
    )

    # Single citation
    assert service._extract_citation_ids("答案[S1]") == ["S1"]

    # Multiple citations
    assert service._extract_citation_ids("答案[S1]和[S2]") == ["S1", "S2"]

    # Deduplication
    assert service._extract_citation_ids("[S1][S1][S2]") == ["S1", "S2"]

    # No citations
    assert service._extract_citation_ids("无引用") == []


def test_validate_citations():
    """Test citation validation."""
    from app.services.rag import RagService, InvalidCitationError

    service = RagService(
        embedding_provider=None,
        chat_provider=None,
    )

    available = {"S1", "S2", "S3"}

    # Valid
    service._validate_citations(["S1", "S2"], available)

    # Invalid
    with pytest.raises(InvalidCitationError):
        service._validate_citations(["S1", "S99"], available)


print("✅ Created RAG unit tests")
