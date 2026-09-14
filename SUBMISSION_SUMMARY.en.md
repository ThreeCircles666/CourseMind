# CourseMind Project Summary

## One-Line Positioning

> CourseMind turns course materials into an interactive learning canvas and helps students find their weak points.

## Problem

Students often struggle during review because:

1. They do not know which parts of a long document are important.
2. They may understand a topic only partially and need repeated local explanations.
3. They do not know their own weak points.
4. AI answers are hard to trust when sources are unclear.

CourseMind addresses these issues by combining document-grounded RAG with a visual learning canvas.

## Target Users

- University and graduate students preparing for exams.
- Online learners organizing course notes.
- Learners who need repeated explanations of complex concepts.

## Core Features

### 1. AI Learning Canvas

CourseMind extracts review concepts from uploaded materials and turns them into visual cards.

Capabilities:

- Extract 6-10 review concepts from course materials.
- Categorize cards as definitions, formulas, examples, common mistakes, or exam focus.
- Show source file, page number, and excerpt.
- Ask follow-up questions on a single concept.
- Write follow-up answers back to the canvas as child cards.
- Mark frequently queried concepts as weak points.

Value:

- Reduces cognitive load with card-based review.
- Supports deep local exploration of one concept.
- Personalizes review based on user behavior.
- Builds trust through source-backed answers.

### 2. Knowledge Base RAG

CourseMind includes a real RAG pipeline rather than a static demo.

Capabilities:

- Upload TXT, Markdown, and PDF files.
- Parse, chunk, and embed documents.
- Store embeddings in PostgreSQL with pgvector.
- Retrieve relevant chunks by cosine similarity.
- Generate answers with cited sources.
- Detect insufficient context.

### 3. User System

Capabilities:

- Registration and login.
- JWT access tokens and refresh tokens.
- HttpOnly refresh token cookie.
- Per-user document ownership isolation.

### 4. Language Selection

Capabilities:

- English and Simplified Chinese UI.
- Global language selector.
- Language preference stored locally.
- Language-aware fallback/demo content.

## Architecture

```text
Browser
  |
  | HTTP / REST
  v
Frontend (Vue 3 + Vite + Element Plus + vue-i18n)
  |
  | JWT-authenticated API calls
  v
Backend (FastAPI)
  |              \
  | SQL           \ DashScope Qwen / Embedding
  v               v
PostgreSQL + pgvector
```

## Stack

Frontend:

- Vue 3
- TypeScript
- Vite
- Element Plus
- vue-i18n

Backend:

- Python 3.11
- FastAPI
- SQLAlchemy
- Alembic
- PyJWT

Database:

- PostgreSQL 17
- pgvector

AI:

- DashScope Qwen for answer generation.
- DashScope `text-embedding-v3` for embeddings.

Deployment:

- Docker
- Docker Compose

## Key Design Choices

### Why pgvector?

pgvector keeps vector search inside PostgreSQL, which simplifies the MVP stack while still supporting semantic retrieval.

### Why DashScope?

DashScope provides Qwen chat models and `text-embedding-v3`, matching the project's Chinese/English learning use case and local deployment assumptions.

### Why a Canvas?

Students do not only need answers. They need a way to organize, revisit, and expand concepts while studying. The canvas makes this study path visible.

## Current Limits

- PPTX, DOCX, image OCR, and scanned PDF OCR are not implemented.
- The canvas is a card grid, not a fully draggable infinite canvas.
- Weak point detection is based on follow-up counts, not a long-term learner model.
- RAG answers are grounded only in uploaded documents and do not use web search.
- Demo fallback data is intentionally labeled and should not be treated as generated evidence.

## Demo Value

CourseMind demonstrates a complete learning workflow:

1. Upload course material.
2. Parse and embed it.
3. Ask grounded questions.
4. Generate a learning canvas.
5. Ask local follow-ups.
6. Build a personal map of weak points.

This makes CourseMind more than a document chatbot: it is a study workspace built around traceable concepts.
