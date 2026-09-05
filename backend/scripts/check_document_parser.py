#!/usr/bin/env python3
"""Document parser verification script.

This script parses a local file and displays parsing results.
Does not access database, network, or embedding services.

Usage:
    python scripts/check_document_parser.py <file_path>

Example:
    python scripts/check_document_parser.py test.pdf
    python scripts/check_document_parser.py document.md
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.parsers import (
    DocumentParseError,
    parse_document,
)


def main() -> int:
    """Parse and display document information.

    Returns:
        0 if successful, non-zero otherwise.
    """
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_document_parser.py <file_path>")
        print("\nSupported formats: .txt, .md, .markdown, .pdf")
        return 1

    file_path = Path(sys.argv[1])

    # Check file exists
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return 1

    if not file_path.is_file():
        print(f"❌ Not a file: {file_path}")
        return 1

    print("=" * 70)
    print("Document Parser Verification")
    print("=" * 70)
    print()
    print(f"File: {file_path.name}")
    print(f"Size: {file_path.stat().st_size:,} bytes")
    print()

    # Read file
    try:
        content = file_path.read_bytes()
    except Exception as e:
        print(f"❌ Failed to read file: {e}")
        return 1

    # Parse document
    print("Parsing...")
    try:
        result = parse_document(
            content=content,
            filename=file_path.name,
            mime_type=None,
        )
    except DocumentParseError as e:
        print(f"❌ Parse error: {type(e).__name__}")
        print(f"   {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}")
        print(f"   {e}")
        return 1

    print("✅ Parsing successful")
    print()

    # Display metadata
    print("=" * 70)
    print("Metadata")
    print("=" * 70)
    metadata = result.metadata
    print(f"Parser: {metadata.get('parser', 'unknown')}")
    print(f"MIME type: {metadata.get('mime_type', 'unknown')}")

    if 'encoding' in metadata:
        print(f"Encoding: {metadata['encoding']}")

    print(f"Page count: {metadata.get('page_count', 0)}")
    print(f"Total characters: {metadata.get('character_count', 0):,}")

    if 'encrypted' in metadata:
        print(f"Encrypted: {metadata['encrypted']}")

    if 'possibly_scanned' in metadata:
        print(f"Possibly scanned: {metadata['possibly_scanned']}")

    if 'heading_count' in metadata:
        print(f"Headings: {metadata['heading_count']}")

    print()

    # Display page information
    print("=" * 70)
    print("Pages")
    print("=" * 70)
    for page in result.pages:
        char_count = len(page.text)
        preview = page.text[:50].replace('\n', ' ') if page.text else "(empty)"
        print(f"Page {page.page_number}: {char_count:,} characters")
        if char_count > 0:
            print(f"  Preview: {preview}...")
    print()

    # Display headings for markdown
    if 'headings' in metadata and metadata['headings']:
        print("=" * 70)
        print("Markdown Headings")
        print("=" * 70)
        for heading in metadata['headings'][:10]:  # Show first 10
            indent = "  " * (heading['level'] - 1)
            print(f"{indent}{'#' * heading['level']} {heading['text']}")

        if len(metadata['headings']) > 10:
            print(f"... and {len(metadata['headings']) - 10} more")
        print()

    # Display text preview
    print("=" * 70)
    print("Text Preview (first 200 characters)")
    print("=" * 70)
    preview = result.text[:200]
    print(preview)
    if len(result.text) > 200:
        print("...")
    print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"✅ Successfully parsed {file_path.name}")
    print(f"✅ {len(result.pages)} page(s)")
    print(f"✅ {len(result.text):,} total characters")
    print()

    # Warnings
    if metadata.get('possibly_scanned'):
        print("⚠️  This PDF may be a scanned image and require OCR")

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
