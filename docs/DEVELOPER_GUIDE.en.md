# CourseMind Developer Guide

This guide describes the current implementation of CourseMind: local setup, architecture, major data flows, APIs, safety boundaries, tests, and troubleshooting.

For the Chinese version, see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).

## 1. Current Capabilities

CourseMind is a Vue 3 + FastAPI + PostgreSQL/pgvector learning application. It currently supports:

- User registration, login, token refresh, and logout.
- Regular Qwen streaming chat with session history.
- TXT, Markdown, and PDF upload, validation, deduplication, and background processing.
- Text parsing, structured chunking, and DashScope embeddings.
- pgvector cosine-similarity retrieval.
- RAG Q&A with source citations and insufficient-context handling.
- Per-user document ownership, deletion, and failed-document reprocessing.
- Knowledge Base and Knowledge Q&A frontend pages.
- Learning Canvas: document-based concept cards, sources, local follow-up, child-card writeback, quiz cards, and weak point markers.
- Demo canvas and generation fallback, so the product remains demonstrable without an API key or when the model fails.
- English and Simplified Chinese UI with global language selection.

## 2. Stack and Structure

- Frontend: Vue 3, TypeScript, Vite, Element Plus, Pinia, Vue Router, vue-i18n.
- Backend: Python, FastAPI, SQLAlchemy 2, Pydantic, Alembic, httpx.
- Database: PostgreSQL 17, pgvector.
- AI: DashScope `text-embedding-v3` and Qwen Chat.

```text
CourseMind/
├── backend/
│   ├── app/
│   │   ├── ai/             # Chat/Embedding contracts and DashScope adapters
│   │   ├── api/routes/     # auth, chat, documents, rag, health
│   │   ├── chunking/       # Recursive character chunking
│   │   ├── core/           # Configuration
│   │   ├── models/         # SQLAlchemy models
│   │   ├── parsers/        # TXT, Markdown, PDF parsers
│   │   ├── schemas/        # API DTOs
│   │   └── services/       # Upload, ingestion, retrieval, RAG
│   ├── alembic/            # Database migrations
│   ├── data/uploads/       # Runtime uploads, ignored by Git
│   └── tests/
├── frontend/src/
│   ├── api/
│   ├── i18n/               # en-US and zh-CN dictionaries
│   ├── router/
│   ├── stores/
│   └── views/
└── docker-compose.yml
```

## 3. Local Setup

### Requirements

- Docker Desktop.
- Python 3.11 or newer.
- Node.js 18 or newer.
- npm.

### Backend Configuration

Copy and edit environment files when needed:

```bash
cp backend/.env.example backend/.env
```

Important backend settings:

- `DATABASE_URL`: PostgreSQL connection string.
- `JWT_SECRET_KEY`: at least 32 characters.
- `DASHSCOPE_API_KEY`: required for real embeddings, chat, RAG, and document-based canvas generation.
- `CORS_ORIGINS`: allowed frontend origins.
- `EMBEDDING_TRUST_ENV`: whether the embedding adapter reads proxy environment variables.
- `RAG_MIN_SIMILARITY`: server-side minimum similarity threshold, default `0.3`.

Never commit real secrets, uploaded files, or database dumps.

### Start PostgreSQL

```bash
docker compose up -d postgres
docker compose ps postgres
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check: http://127.0.0.1:8000/api/v1/health

Swagger: http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173 for local Vite development, or http://127.0.0.1:5174 for Docker.

## 4. Data Model

### User

Stores account data, password hash, active state, and `token_version`. Logout invalidates existing access tokens.

### Document

Stores file metadata, SHA-256, processing status, and owner. Status flow:

```text
pending -> processing -> succeeded
                     \-> failed
```

Documents are deduplicated per user by `(user_id, sha256)`.

### ProcessingJob

Records processing attempts. Jobs are deleted by database cascade when their document is deleted.

### DocumentChunk

Stores chunk content, page number, Markdown title path, character offsets, model metadata, and `vector(1024)`.

## 5. Upload and Ingestion Flow

```text
multipart upload
  -> extension / MIME / PDF signature / size checks
  -> staging file under backend/data/uploads/.staging
  -> streaming SHA-256
  -> per-user deduplication
  -> create Document
  -> atomically publish file under backend/data/uploads/{document_uuid}/{safe_name}
  -> background session
  -> parse -> chunk -> embed -> atomically replace chunks
```

TXT and Markdown are limited to 10 MiB. PDFs are limited to 50 MiB.

Remote embedding calls happen outside long database transactions. Successful ingestion replaces chunks atomically; failures do not destroy existing valid chunks.

## 6. RAG Flow

```text
question + current user + document_ids
  -> validate all document ownership before provider calls
  -> embed query
  -> pgvector cosine Top-K with user_id filtering
  -> similarity threshold filtering
  -> context budget
  -> Qwen returns a JSON object with status and answer
  -> validate answer status and protocol
  -> validate citations
  -> return only actually cited sources
```

Effective similarity threshold:

```python
max(RAG_MIN_SIMILARITY, request.min_similarity or 0.0)
```

The client may raise the threshold but cannot lower the server minimum.

Model `status` values:

| Status | Response behavior |
|---|---|
| `answered` | Keep answer, `insufficient_context=false`, return cited sources |
| `partial` | Keep grounded content, mark `insufficient_context=true`, return cited sources |
| `insufficient` | Return the fixed insufficient-context answer and no sources |

Complete or partial answers must cite valid `[S1]`, `[S2]`, etc. Fabricated citations return 502. The service tolerates JSON wrapped in Markdown fences or surrounding text by extracting the JSON object and then applying the same validation.

## 7. Learning Canvas

The Learning Canvas lives in `frontend/src/views/LearningCanvasView.vue`. It does not introduce a separate backend endpoint; real generation and follow-ups reuse `/api/v1/rag/ask`.

```text
select processed document
  -> ask RAG to extract review concepts
  -> backend retrieves chunks and calls Qwen
  -> model answer includes source citations
  -> frontend parses answer into CanvasCard objects
  -> cards show title, summary, tag, file, page, and excerpt
```

Canvas capabilities:

- Load demo canvas.
- Generate canvas from uploaded materials.
- Clear canvas.
- Reset demo learning signals.
- View card details, source, and excerpt.
- Ask follow-up questions for a whole card.
- Select text and ask about only that selected passage.
- Use quick actions: Explain Simply, Give Example, Generate Quiz.
- Write follow-up answers back as child cards.
- Mark weak points based on repeated follow-ups.
- Display exam focus, quiz, and follow-up tags.

Canvas card state is currently frontend state. Demo follow-up counts and weak point signals are stored in browser local storage, not in the database.

## 8. API Overview

All business APIs use the `/api/v1` prefix.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/auth/register` | Register |
| POST | `/auth/login` | Login |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/auth/me` | Current user |
| POST | `/auth/logout` | Logout |
| POST | `/chat/stream` | Streaming chat |
| GET | `/chat/sessions` | List chat sessions |
| GET/PATCH/DELETE | `/chat/sessions/{id}` | Read, rename, delete session |
| POST | `/documents` | Upload document, returns 202 |
| GET | `/documents` | List current user's documents |
| GET | `/documents/{id}` | Get document status |
| DELETE | `/documents/{id}` | Delete non-processing document |
| POST | `/documents/{id}/reprocess` | Reprocess failed document |
| POST | `/rag/ask` | Knowledge-base Q&A over selected documents |

All protected routes require `Authorization: Bearer <access_token>`. Refresh tokens use HttpOnly cookies.

## 9. Frontend Pages

- `/login`, `/register`: authentication.
- `/`: feature entry page.
- `/chat`: regular AI chat.
- `/documents`: upload, status, reprocess, and delete documents.
- `/knowledge-ask`: select documents, ask questions, and inspect cited sources.
- `/canvas`: learning canvas.
- `/about`: project information.

`App.vue` renders the global language selector. Language changes should go through `setLocale()`.

## 10. Tests and Checks

Backend:

```bash
cd backend
.venv/bin/python -m pytest
```

Frontend:

```bash
cd frontend
npm run type-check
npm run build
```

Recent targeted validation:

- `tests/test_rag_answer_status.py`: `15 passed`.
- This covers answer status handling, citation validation, and fenced JSON parsing.
- It is not a full production-quality RAG evaluation.

## 11. Known Limits

- Background processing uses FastAPI `BackgroundTasks`; production should use a durable task queue.
- PPTX, DOCX, image OCR, and scanned-PDF OCR are not implemented.
- Some PDFs with custom font encodings may parse as garbled text.
- The canvas is a card grid, not a fully draggable infinite canvas.
- Weak point detection is based on follow-up counts, not a long-term learner model.
- RAG answers are grounded only in uploaded materials and do not use web search.

## 12. Safety Rules

- Do not trust document content as instructions.
- Verify document ownership before provider calls.
- Do not return absolute paths, secrets, provider raw errors, or stack traces to clients.
- Do not accept `user_id` from the client for authorization.
- Do not commit `.env`, uploaded files, or database dumps.
- Avoid `docker compose down -v` unless the goal is to delete local database data.

## 13. Minimum Checklist Before Changing Features

- Does the change preserve user ownership isolation?
- Does it avoid long transactions around remote API calls?
- Does failure preserve existing valid chunks?
- Are positive, failure, unauthorized, and boundary cases tested?
- Did backend tests pass?
- Did frontend type-check and build pass?
- Does this guide need an update?
