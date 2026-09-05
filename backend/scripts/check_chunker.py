#!/usr/bin/env python3
"""Text chunking verification script.

This script demonstrates chunking with different parameters.
Does not access database, network, or embedding services.

Usage:
    python scripts/check_chunker.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chunking import RecursiveCharacterChunker
from app.parsers import ParsedDocument, ParsedPage


# Test document with various features
TEST_MARKDOWN = """# 第一章：介绍

本文档用于演示文本切片功能。

## 1.1 背景

PostgreSQL 是一个功能强大的开源关系数据库管理系统。它支持事务、ACID 特性和复杂查询。

## 1.2 pgvector 扩展

pgvector 是 PostgreSQL 的向量相似度检索扩展。它为 PostgreSQL 提供了向量数据类型和相似度搜索能力。

# 第二章：技术细节

## 2.1 向量表示

文本可以被转换为高维向量表示。这种表示可以捕捉语义信息。

```python
def embed_text(text: str) -> list[float]:
    # 调用 Embedding API
    return model.embed(text)
```

## 2.2 相似度计算

常用的相似度度量包括：

1. 余弦相似度（cosine similarity）
2. 欧氏距离（Euclidean distance）
3. 点积（dot product）

对于文本检索任务，余弦相似度通常是首选。

# 第三章：实践应用

这是一段没有明显分隔符的长文本用于测试硬切功能AAAAAAAAAABBBBBBBBBBCCCCCCCCCCDDDDDDDDDDEEEEEEEEEEFFFFFFFFFF

最后一段简短总结。
"""


def main() -> int:
    """Run chunking verification."""
    print("=" * 70)
    print("Text Chunking Verification")
    print("=" * 70)
    print()

    # Create test document
    doc = ParsedDocument(
        text=TEST_MARKDOWN,
        pages=(ParsedPage(page_number=1, text=TEST_MARKDOWN, metadata={}),),
        metadata={
            'filename': 'test.md',
            'parser': 'MarkdownParser',
            'page_count': 1,
            'character_count': len(TEST_MARKDOWN),
            'headings': [
                {'level': 1, 'text': '第一章：介绍'},
                {'level': 2, 'text': '1.1 背景'},
                {'level': 2, 'text': '1.2 pgvector 扩展'},
                {'level': 1, 'text': '第二章：技术细节'},
                {'level': 2, 'text': '2.1 向量表示'},
                {'level': 2, 'text': '2.2 相似度计算'},
                {'level': 1, 'text': '第三章：实践应用'},
            ],
        },
    )

    print(f"Document length: {len(doc.text)} characters")
    print(f"Pages: {len(doc.pages)}")
    print()

    # Configuration A: Smaller chunks
    config_a = {
        'chunk_size': 200,
        'chunk_overlap': 30,
    }

    # Configuration B: Larger chunks
    config_b = {
        'chunk_size': 400,
        'chunk_overlap': 60,
    }

    # Test both configurations
    for config_name, config in [('A', config_a), ('B', config_b)]:
        print("=" * 70)
        print(f"Configuration {config_name}")
        print("=" * 70)
        print(f"Chunk size: {config['chunk_size']} characters")
        print(f"Overlap: {config['chunk_overlap']} characters")
        print()

        chunker = RecursiveCharacterChunker(**config)
        chunks = chunker.chunk(doc)

        print(f"Generated {len(chunks)} chunks")
        print()

        # Statistics
        lengths = [len(chunk.text) for chunk in chunks]
        print(f"Length statistics:")
        print(f"  Min: {min(lengths)} characters")
        print(f"  Max: {max(lengths)} characters")
        print(f"  Avg: {sum(lengths) / len(lengths):.1f} characters")
        print()

        # Show first 3 chunks
        print("Sample chunks:")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n--- Chunk {chunk.index} ---")
            print(f"Page: {chunk.page_number}")
            print(f"Position: [{chunk.start_char}:{chunk.end_char}]")
            print(f"Length: {len(chunk.text)} characters")
            print(f"Title path: {chunk.title_path}")
            preview = chunk.text[:100].replace('\n', ' ')
            print(f"Preview: {preview}...")

        if len(chunks) > 3:
            print(f"\n... and {len(chunks) - 3} more chunks")

        print()

    # Validation
    print("=" * 70)
    print("Validation")
    print("=" * 70)

    # Test with config A
    chunker_a = RecursiveCharacterChunker(**config_a)
    chunks_a = chunker_a.chunk(doc)

    # Check no empty chunks
    assert all(chunk.text for chunk in chunks_a), "❌ Found empty chunk"
    print("✅ No empty chunks")

    # Check indices are sequential
    for i, chunk in enumerate(chunks_a):
        assert chunk.index == i, f"❌ Index mismatch at {i}"
    print("✅ Indices are sequential")

    # Check start < end
    for chunk in chunks_a:
        assert chunk.start_char < chunk.end_char, "❌ Invalid offsets"
    print("✅ All offsets valid (start < end)")

    # Check offsets match text (accounting for overlap)
    for i, chunk in enumerate(chunks_a):
        # The chunk text should be a substring of the document
        if chunk.text not in doc.text:
            print(f"❌ Chunk {i} text not found in document")
            assert False
    print("✅ All chunk texts are present in document")

    # Check offsets are reasonable
    for chunk in chunks_a:
        assert 0 <= chunk.start_char < len(doc.text), "❌ Invalid start offset"
        assert 0 < chunk.end_char <= len(doc.text), "❌ Invalid end offset"
    print("✅ All offsets within document bounds")

    # Check length limits
    for chunk in chunks_a:
        assert len(chunk.text) <= config_a['chunk_size'], "❌ Chunk exceeds size limit"
    print(f"✅ All chunks <= {config_a['chunk_size']} characters")

    # Check coverage
    covered = set()
    for chunk in chunks_a:
        for pos in range(chunk.start_char, chunk.end_char):
            covered.add(pos)

    # All non-whitespace content should be covered
    doc_range = set(range(len(doc.text.strip())))
    assert doc_range.issubset(covered), "❌ Coverage gap detected"
    print("✅ Complete coverage (no gaps)")

    # Check first and last
    assert chunks_a[0].start_char == 0, "❌ First chunk doesn't start at 0"
    print("✅ First chunk starts at position 0")

    # Check no infinite loops (reasonable chunk count)
    assert len(chunks_a) < len(doc.text), "❌ Too many chunks (possible loop)"
    print("✅ Reasonable chunk count")

    print()
    print("=" * 70)
    print("Comparison")
    print("=" * 70)

    chunker_b = RecursiveCharacterChunker(**config_b)
    chunks_b = chunker_b.chunk(doc)

    print(f"Config A: {len(chunks_a)} chunks (size={config_a['chunk_size']}, overlap={config_a['chunk_overlap']})")
    print(f"Config B: {len(chunks_b)} chunks (size={config_b['chunk_size']}, overlap={config_b['chunk_overlap']})")
    print()

    print("Analysis:")
    print(f"- Smaller chunk size produces more chunks ({len(chunks_a)} vs {len(chunks_b)})")
    print(f"- More chunks = finer granularity but higher storage/compute cost")
    print(f"- Larger chunks = more context but may mix multiple topics")
    print(f"- Overlap helps preserve boundary information")
    print()

    print("=" * 70)
    print("✅ All validations passed")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
