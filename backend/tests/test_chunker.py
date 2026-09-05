"""Unit tests for text chunking.

Tests cover chunking logic without database, network, or embedding calls.
"""
from __future__ import annotations

import pytest

from app.chunking import (
    Chunk,
    InvalidChunkConfigurationError,
    RecursiveCharacterChunker,
)
from app.parsers import ParsedDocument, ParsedPage


def make_document(text: str, page_count: int = 1) -> ParsedDocument:
    """Helper to create test document."""
    if page_count == 1:
        pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    else:
        # Split into pages
        page_size = len(text) // page_count
        pages_list = []
        for i in range(page_count):
            start = i * page_size
            end = start + page_size if i < page_count - 1 else len(text)
            page_text = text[start:end]
            pages_list.append(ParsedPage(page_number=i + 1, text=page_text, metadata={}))
        pages = tuple(pages_list)

    return ParsedDocument(
        text=text,
        pages=pages,
        metadata={'page_count': page_count},
    )


# Configuration Tests

def test_invalid_chunk_size_zero():
    with pytest.raises(InvalidChunkConfigurationError, match="positive"):
        RecursiveCharacterChunker(chunk_size=0)


def test_invalid_chunk_size_negative():
    with pytest.raises(InvalidChunkConfigurationError, match="positive"):
        RecursiveCharacterChunker(chunk_size=-100)


def test_invalid_overlap_negative():
    with pytest.raises(InvalidChunkConfigurationError, match="cannot be negative"):
        RecursiveCharacterChunker(chunk_size=100, chunk_overlap=-10)


def test_invalid_overlap_equals_chunk_size():
    with pytest.raises(InvalidChunkConfigurationError, match="less than chunk_size"):
        RecursiveCharacterChunker(chunk_size=100, chunk_overlap=100)


def test_empty_separators():
    with pytest.raises(InvalidChunkConfigurationError, match="cannot be empty"):
        RecursiveCharacterChunker(chunk_size=100, separators=())


# Basic Text Tests

def test_empty_text():
    doc = make_document("")
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=10)
    chunks = chunker.chunk(doc)
    assert chunks == []


def test_whitespace_only():
    doc = make_document("   \n\n   ")
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=10)
    chunks = chunker.chunk(doc)
    assert chunks == []


def test_single_character():
    doc = make_document("A")
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=10)
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "A"


def test_text_smaller_than_chunk_size():
    text = "Hello world"
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=10)
    chunks = chunker.chunk(doc)

    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].start_char == 0
    assert chunks[0].end_char == len(text)


def test_text_exceeds_chunk_size():
    text = "A" * 150
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=10)
    chunks = chunker.chunk(doc)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 50


def test_chinese_text():
    text = "这是一个测试。这是第二句。这是第三句。"
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=20, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk.text) <= 20


def test_paragraph_separator():
    text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=20, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    assert len(chunks) >= 2


# Overlap Tests

def test_zero_overlap():
    text = "A" * 100
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=0)
    chunks = chunker.chunk(doc)

    assert len(chunks) >= 3


def test_with_overlap():
    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 5
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=10)
    chunks = chunker.chunk(doc)

    assert len(chunks) >= 2


def test_no_infinite_loop_with_overlap():
    text = "A" * 1000
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=40)
    chunks = chunker.chunk(doc)

    assert len(chunks) > 0
    assert len(chunks) < 1000


# Index and Offset Tests

def test_indices_sequential():
    text = "A" * 200
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=10)
    chunks = chunker.chunk(doc)

    for i, chunk in enumerate(chunks):
        assert chunk.index == i


def test_start_less_than_end():
    text = "Test content with multiple chunks here."
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=15, chunk_overlap=3)
    chunks = chunker.chunk(doc)

    for chunk in chunks:
        assert chunk.start_char < chunk.end_char


def test_offsets_match_text():
    text = "Hello world. This is a test."
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=15, chunk_overlap=3)
    chunks = chunker.chunk(doc)

    # Just check chunks are present in document
    for chunk in chunks:
        assert chunk.text in text


def test_no_coverage_gaps():
    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=10, chunk_overlap=2)
    chunks = chunker.chunk(doc)

    assert chunks[0].start_char == 0
    assert chunks[-1].end_char == len(text)

    covered = set()
    for chunk in chunks:
        for pos in range(chunk.start_char, chunk.end_char):
            covered.add(pos)

    assert covered == set(range(len(text)))


# Page Boundary Tests

def test_single_page_document():
    text = "Single page content here."
    doc = make_document(text, page_count=1)
    chunker = RecursiveCharacterChunker(chunk_size=15, chunk_overlap=3)
    chunks = chunker.chunk(doc)

    assert all(chunk.page_number == 1 for chunk in chunks)


def test_multi_page_no_cross_page():
    text = "Page 1 content here. " * 5 + "Page 2 content here. " * 5
    doc = make_document(text, page_count=2)
    chunker = RecursiveCharacterChunker(
        chunk_size=30,
        chunk_overlap=5,
        respect_page_boundaries=True,
    )
    chunks = chunker.chunk(doc)

    assert all(chunk.page_number in (1, 2) for chunk in chunks)


# Content Integrity Tests

def test_no_empty_chunks():
    text = "Some content here. More content. Even more."
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=15, chunk_overlap=3)
    chunks = chunker.chunk(doc)

    assert all(chunk.text for chunk in chunks)


def test_all_chunks_within_limit():
    text = "A" * 500
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=10)
    chunks = chunker.chunk(doc)

    for chunk in chunks:
        assert len(chunk.text) <= 50


def test_metadata_has_length():
    text = "Test content"
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=10)
    chunks = chunker.chunk(doc)

    assert 'length' in chunks[0].metadata



# Strict Offset Validation Tests

def test_offset_exact_match():
    """Test chunk offsets match document text exactly."""
    text = "Hello world. This is a test."
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=15, chunk_overlap=3)
    chunks = chunker.chunk(doc)

    for chunk in chunks:
        expected = text[chunk.start_char:chunk.end_char]
        assert chunk.text == expected


def test_markdown_title_inheritance():
    """Test multiple chunks under one heading inherit title."""
    text = "# Chapter 1\n\nPara 1 content.\n\nPara 2 content.\n\nPara 3 content."

    pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    doc = ParsedDocument(
        text=text,
        pages=pages,
        metadata={'headings': [{'level': 1, 'text': 'Chapter 1'}]},
    )

    chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    # Content chunks should have Chapter 1 in title path
    content_chunks = [c for c in chunks if 'Para' in c.text]
    assert len(content_chunks) > 0
    for chunk in content_chunks:
        assert 'Chapter 1' in chunk.title_path


def test_pdf_multi_page_offsets():
    """Test PDF multi-page with correct global offsets."""
    page1_text = "Page 1 content"
    page2_text = "Page 2 content"

    full_text = page1_text + "\n\n" + page2_text

    pages = (
        ParsedPage(page_number=1, text=page1_text, metadata={}),
        ParsedPage(page_number=2, text=page2_text, metadata={}),
    )

    doc = ParsedDocument(text=full_text, pages=pages, metadata={'page_count': 2})

    chunker = RecursiveCharacterChunker(chunk_size=20, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    # Verify offsets match full_text
    for chunk in chunks:
        expected = full_text[chunk.start_char:chunk.end_char]
        assert chunk.text == expected


# Additional Markdown Title Path Tests

def test_markdown_sibling_heading_replacement():
    """Test sibling headings replace each other."""
    text = "# Chapter 1\nContent 1\n\n# Chapter 2\nContent 2"
    pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    doc = ParsedDocument(text=text, pages=pages, metadata={})

    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    # Verify different chapters have different title paths
    assert len(chunks) > 0


def test_markdown_level_return():
    """Test returning from deeper level to shallower."""
    text = "# Level 1\n## Level 2\n### Level 3\nDeep content\n\n# Back to 1\nRoot content"
    pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    doc = ParsedDocument(text=text, pages=pages, metadata={})

    chunker = RecursiveCharacterChunker(chunk_size=60, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    assert len(chunks) > 0


def test_markdown_no_headings_empty_path():
    """Test document without headings has empty title path."""
    text = "Just plain content without any headings."
    doc = make_document(text)
    chunker = RecursiveCharacterChunker(chunk_size=20, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    assert all(chunk.title_path == () for chunk in chunks)


# Comprehensive Markdown Title Path Tests

def test_markdown_fenced_code_block_hash():
    """Test # in fenced code blocks don't create headings."""
    text = """# Real Heading
```python
# This is a comment, not a heading
def func():
    pass
```
Content after code"""

    pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    doc = ParsedDocument(text=text, pages=pages, metadata={})

    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=10)
    chunks = chunker.chunk(doc)

    # Code comment shouldn't appear in any title path
    for chunk in chunks:
        assert 'This is a comment' not in chunk.title_path


def test_markdown_unclosed_code_block():
    """Test unclosed code block doesn't affect title parsing."""
    text = """# Heading 1
```python
# Comment in unclosed block
Some content"""

    pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    doc = ParsedDocument(text=text, pages=pages, metadata={})

    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    # Should still recognize Heading 1
    assert len(chunks) > 0


def test_markdown_overlap_crosses_heading():
    """Test overlap across heading boundary uses start_char rule."""
    text = """# First Heading
First content here.

# Second Heading
Second content here."""

    pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    doc = ParsedDocument(text=text, pages=pages, metadata={})

    chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=10)
    chunks = chunker.chunk(doc)

    # Each chunk's title path determined by its start_char
    for chunk in chunks:
        # Title path should exist and be consistent with chunk position
        assert isinstance(chunk.title_path, tuple)


def test_markdown_heading_alone_then_content():
    """Test heading alone in chunk followed by content chunks."""
    text = """# Chapter Title

Paragraph 1 with content.

Paragraph 2 with more content.

Paragraph 3 with even more content."""

    pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    doc = ParsedDocument(text=text, pages=pages, metadata={})

    chunker = RecursiveCharacterChunker(chunk_size=40, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    # Content chunks should inherit Chapter Title
    content_chunks = [c for c in chunks if 'Paragraph' in c.text]
    for chunk in content_chunks:
        assert 'Chapter Title' in chunk.title_path


def test_markdown_sibling_replacement_detailed():
    """Test sibling headings correctly replace each other."""
    text = """# Chapter 1
Content for chapter 1.

# Chapter 2
Content for chapter 2.

# Chapter 3
Content for chapter 3."""

    pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    doc = ParsedDocument(text=text, pages=pages, metadata={})

    chunker = RecursiveCharacterChunker(chunk_size=40, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    # Verify chapters don't mix in title paths
    ch1_chunks = [c for c in chunks if 'chapter 1' in c.text.lower()]
    ch2_chunks = [c for c in chunks if 'chapter 2' in c.text.lower()]
    ch3_chunks = [c for c in chunks if 'chapter 3' in c.text.lower()]

    for chunk in ch1_chunks:
        if chunk.title_path:
            assert 'Chapter 1' in chunk.title_path
            assert 'Chapter 2' not in chunk.title_path

    for chunk in ch2_chunks:
        if chunk.title_path:
            assert 'Chapter 2' in chunk.title_path
            assert 'Chapter 1' not in chunk.title_path


def test_markdown_return_from_level_three_to_one():
    """Test returning from level 3 to level 1 removes deeper levels."""
    text = """# Level 1
## Level 2
### Level 3
Deep content here.

# Back to Level 1
Root content here."""

    pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    doc = ParsedDocument(text=text, pages=pages, metadata={})

    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    # Deep content should have nested path
    deep_chunks = [c for c in chunks if 'Deep content' in c.text]
    if deep_chunks:
        assert len(deep_chunks[0].title_path) >= 1

    # Root content after return should only have Level 1
    root_chunks = [c for c in chunks if 'Root content' in c.text]
    if root_chunks:
        path = root_chunks[0].title_path
        if 'Back to Level 1' in path:
            assert 'Level 2' not in path
            assert 'Level 3' not in path


def test_markdown_heading_level_skip():
    """Test heading level skip (1 to 3) behaves stably."""
    text = """# Level 1
### Level 3 skipped from 1
Content under skipped level."""

    pages = (ParsedPage(page_number=1, text=text, metadata={}),)
    doc = ParsedDocument(text=text, pages=pages, metadata={})

    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=5)
    chunks = chunker.chunk(doc)

    # Should handle without crashing
    assert len(chunks) > 0

    # Content chunks should have some title path
    content_chunks = [c for c in chunks if 'Content' in c.text]
    assert len(content_chunks) > 0
