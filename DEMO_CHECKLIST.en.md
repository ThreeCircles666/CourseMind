# CourseMind Demo Checklist

Use this checklist before recording or presenting CourseMind.

## Environment

- Docker Desktop is running.
- `docker compose ps` shows `coursemind-postgres`, `coursemind-backend`, and `coursemind-frontend` as running.
- Backend health check works: http://127.0.0.1:8000/api/v1/health
- Frontend opens: http://127.0.0.1:5174
- Optional: `DASHSCOPE_API_KEY` is set if you need real document processing, RAG Q&A, or document-based canvas generation.

## Account

- You can register a new account.
- You can log in.
- Refresh token flow works after reloading the page.
- Logout returns to the login page.

## Language Selection

- The top-right language selector is visible.
- English displays English UI text.
- 简体中文 displays Chinese UI text.
- The selected language remains after refreshing the page.

## Document Upload

- TXT upload succeeds.
- Markdown upload succeeds.
- Text-selectable PDF upload succeeds.
- Unsupported formats are rejected.
- Oversized files are rejected.
- Processed documents show Succeeded.
- Failed documents can be reprocessed.
- Processing documents cannot be deleted.

## Knowledge Q&A

- The page lists processed documents.
- Asking without selecting a document shows a validation message.
- A grounded question returns an answer with sources.
- A question not covered by the materials returns an insufficient-context response.
- Sources show file name, page number when available, excerpt, and similarity.

## Learning Canvas

- The Learning Canvas page opens.
- Load Demo Canvas creates six demo cards.
- Clicking a card opens the detail panel.
- Source and excerpt fields render cleanly.
- Explain Simply creates a child card.
- Give Example creates another child card.
- Repeated follow-ups mark the parent as a weak point.
- Generate Quiz creates a quiz-style child card.
- Selecting text in the detail panel enables Ask Selection.
- Clear Canvas removes cards.
- Reset Learning Signals resets demo follow-up counts and weak point markers.

## Real Canvas Generation

Only run this section when `DASHSCOPE_API_KEY` is configured.

- Select a processed document.
- Click Generate Canvas.
- Cards are generated from the selected material.
- Generated cards show source information when available.
- If generation fails, fallback cards appear and are clearly labeled.

## Browser and Layout

- No important text overlaps at desktop width.
- The three-column canvas layout is usable.
- The language selector does not cover critical controls.
- Chrome console does not show blocking runtime errors.

## Final Reset Before Demo

- Clear old canvas state if needed.
- Use a known working account.
- Keep a known working document uploaded.
- Keep the demo canvas as backup in case the AI provider is slow.
