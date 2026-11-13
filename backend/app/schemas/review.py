"""Typed, source-bound courseware review contract."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    document_ids: list[UUID] = Field(min_length=1, max_length=8)
    response_language: Literal["zh-CN", "en-US"] = "zh-CN"
    use_vision: bool = False


class Evidence(BaseModel):
    page: int = Field(ge=1)
    quote: str = Field(default="", max_length=1500)
    source_id: str | None = Field(default=None, max_length=60)
    origin: Literal["text", "vision"] = "text"


class ReviewBlock(BaseModel):
    kind: Literal["explanation", "quote", "inference", "missing", "code", "formula", "table"]
    text: str = Field(min_length=1, max_length=12000)
    evidence: list[Evidence] = Field(default_factory=list, max_length=12)
    rows: list[list[str]] = Field(default_factory=list, max_length=100)


class QuickEntry(BaseModel):
    kind: Literal["definition", "formula", "rule", "conclusion", "steps", "list"]
    name: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=3000)
    evidence: list[Evidence] = Field(min_length=1, max_length=12)


class Demo(BaseModel):
    kind: Literal["steps", "linear"]
    title: str = Field(min_length=1, max_length=200)
    steps: list[str] = Field(default_factory=list, max_length=30)
    a: float = Field(default=1, ge=-10000, le=10000)
    b: float = Field(default=0, ge=-10000, le=10000)
    minimum: float = Field(default=0, ge=-10000, le=10000)
    maximum: float = Field(default=10, ge=-10000, le=10000)
    illustrative: bool = True
    evidence: list[Evidence] = Field(min_length=1, max_length=12)


class Erratum(BaseModel):
    original: str = Field(min_length=1, max_length=1500)
    correction: str = Field(min_length=1, max_length=1500)
    reason: str = Field(min_length=1, max_length=3000)
    impact: str = Field(min_length=1, max_length=1500)
    evidence: list[Evidence] = Field(min_length=1, max_length=12)


class GeneratedSection(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    pages: list[int] = Field(min_length=1, max_length=4)
    blocks: list[ReviewBlock] = Field(min_length=1, max_length=40)
    takeaways: list[QuickEntry] = Field(default_factory=list, max_length=4)
    quick_reference: list[QuickEntry] = Field(default_factory=list, max_length=30)
    demos: list[Demo] = Field(default_factory=list, max_length=4)
    errata: list[Erratum] = Field(default_factory=list, max_length=10)


class GeneratedBatch(BaseModel):
    sections: list[GeneratedSection] = Field(min_length=1, max_length=4)


class ReviewStatePatch(BaseModel):
    reviewed_sections: list[str] | None = Field(default=None, max_length=1000)
    erratum_id: str | None = None
    decision: Literal["confirmed", "dismissed", "candidate"] | None = None
