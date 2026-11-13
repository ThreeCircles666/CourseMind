"""Paid-provider smoke check using synthetic courseware, never user uploads.

From backend: PYTHONPATH=. .venv/bin/python scripts/smoke_review.py --pptx --vision
Requires DASHSCOPE_API_KEY and (for PPTX) LibreOffice. Artifacts are temporary.
"""
import argparse
import asyncio
import tempfile
from pathlib import Path
from uuid import uuid4

from app.services.review import generate_review, read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pptx', action='store_true')
    parser.add_argument('--vision', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='coursemind-review-smoke-') as directory:
        root = Path(directory)
        if args.pptx:
            from pptx import Presentation
            presentation = Presentation()
            for title, text in [('Linear relation', 'y = 2x + 1\nSlope = 2; intercept = 1.'),
                                ('Example', 'For x = 3, y = 2 * 3 + 1 = 7.\n2 + 2 = 5')]:
                slide = presentation.slides.add_slide(presentation.slide_layouts[1])
                slide.shapes.title.text = title
                slide.placeholders[1].text = text
            source = root / 'synthetic.pptx'
            presentation.save(source)
        else:
            source = root / 'synthetic.txt'
            source.write_text('Linear relation: y = 2x + 1. For x = 3, y = 7. Slope = 2; intercept = 1.')
        path = root / 'review' / 'review.json'
        write_json(path, {'id': str(uuid4()), 'language': 'zh-CN', 'use_vision': args.vision,
                         'documents': [], 'sections': [], 'duplicates': [], 'completed_pages': 0})
        asyncio.run(generate_review(path, [{'id': str(uuid4()), 'name': source.name, 'path': str(source)}]))
        state = read_json(path)
        print({'status': state['status'], 'pages': state['completed_pages'], 'sections': len(state['sections']),
               'quick_entries': sum(len(s['quick_reference']) for s in state['sections']),
               'errata_candidates': sum(len(s['errata']) for s in state['sections'])})
        if state['status'] != 'ready':
            raise SystemExit(1)


if __name__ == '__main__':
    main()
