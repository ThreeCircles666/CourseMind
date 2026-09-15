# Judge Testing Instructions

This file gives judges a practical way to run and evaluate CourseMind.

## Fastest Demo Path

If a deployed link is available, open:

TODO: Add deployed URL.

If no deployed link is available, run CourseMind locally with Docker.

## Local Setup With Docker

Requirements:

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ available memory
- Optional DashScope API key for real AI generation

```bash
git clone https://github.com/ThreeCircles666/CourseMind.git
cd CourseMind

# Optional, but recommended for real document processing
export DASHSCOPE_API_KEY=sk-your-key-here

docker compose up --build
```

Open:

- Frontend: http://127.0.0.1:5174
- Backend API docs: http://127.0.0.1:8000/docs

## Local Setup Without API Key

CourseMind still supports login, navigation, demo canvas, and fallback demo flows without a DashScope key.

The real RAG pipeline and document-based canvas generation require `DASHSCOPE_API_KEY`.

## Demo Account

Create a new account from the registration page:

- Username: `demo_user`
- Display name: `Demo User`
- Password: `demo123456`

## Suggested Evaluation Flow

1. Register and log in.
2. Switch the interface language between English and Simplified Chinese.
3. Open Knowledge Base and upload a TXT, Markdown, or text-selectable PDF file.
4. Wait for the document to reach the succeeded state.
5. Open Knowledge Q&A, select the document, and ask a question.
6. Inspect the answer and cited sources.
7. Open Learning Canvas.
8. Select a processed document and generate a canvas, or use Load Demo Canvas if no API key is configured.
9. Click a concept card.
10. Ask a follow-up question or use Explain Simply.
11. Generate a quiz and inspect weak-point indicators.
12. Open AI Chat and test a normal message.

## What To Look For

- The product supports a complete learning workflow rather than only a chat interface.
- Answers and concept cards expose source information where available.
- Follow-up answers become part of the learning canvas.
- The UI works in English and Simplified Chinese.
- The app keeps document access scoped to the authenticated user.

## Known Limits

- PPTX, DOCX, scanned PDFs, and image OCR are not supported.
- The canvas is a structured card canvas, not a freeform drag-and-drop canvas.
- Weak points use interaction frequency, not long-term spaced-repetition modeling.
- Public deployment may require configuring backend environment variables and DashScope credentials.

