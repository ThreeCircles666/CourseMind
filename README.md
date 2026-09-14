# CourseMind - AI Learning Canvas

Language: [English](README.md) | [简体中文](README.zh-CN.md)

> Turn course materials into a traceable, interactive study canvas.

CourseMind is an AI-assisted learning platform for student review workflows. After users upload TXT, Markdown, or PDF materials, the system parses the files, builds vector indexes, and turns the content into grounded Q&A and visual concept cards. The interface supports English and Simplified Chinese with a global language selector in the top-right corner.

## Features

### Learning Canvas

- Extracts 6-10 review concepts from uploaded course materials.
- Categorizes cards as definitions, formulas, examples, common mistakes, or exam focus points.
- Supports follow-up questions on a single concept.
- Writes follow-up answers back to the canvas as child cards.
- Automatically marks frequently queried concepts as weak points.
- Shows source file, page number, and excerpt for generated cards.
- Falls back to demo cards when AI generation is unavailable, keeping demos reliable.

### Knowledge Base Q&A

- Supports TXT, Markdown, and PDF uploads.
- Parses, chunks, embeds, and stores materials in PostgreSQL + pgvector.
- Answers questions from selected documents using RAG.
- Displays cited sources and similarity scores.
- Distinguishes insufficient context, partial answers, and complete answers.

### Accounts and Language Selection

- Includes registration, login, token refresh, and document ownership isolation.
- Uses `vue-i18n` with built-in `en-US` and `zh-CN` dictionaries.
- The language selector is global and works across login, home, knowledge base, Q&A, and learning canvas pages.
- The selected language is stored locally and reused on the next visit.

## Quick Start

### Requirements

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ available memory
- Optional: Alibaba Cloud DashScope API Key

### Start with Docker

```bash
git clone https://github.com/ThreeCircles666/CourseMind.git
cd CourseMind

# Required for real document processing and RAG
export DASHSCOPE_API_KEY=sk-your-key-here

docker compose up --build
```

Open:

- Frontend: http://127.0.0.1:5174
- Backend API: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

You can also run:

```bash
chmod +x start-docker.sh
./start-docker.sh
```

## DashScope Setup

CourseMind uses DashScope for real AI workflows:

- `text-embedding-v3` for document embeddings.
- `qwen-turbo` for RAG answers and learning canvas generation.

Without `DASHSCOPE_API_KEY`:

- Registration, login, demo canvas, and fallback flows still work.
- Real document vectorization, knowledge Q&A, and document-based canvas generation are unavailable.

Recommended startup:

```bash
export DASHSCOPE_API_KEY=sk-your-key-here
docker compose up --build
```

## Demo Flow

1. Open http://127.0.0.1:5174.
2. Register and log in.
3. Choose English or Simplified Chinese from the top-right selector.
4. Go to Knowledge Base and upload TXT, Markdown, or a text-selectable PDF.
5. Wait until the document status becomes Succeeded.
6. Click Canvas to open the Learning Canvas.
7. Click Generate Canvas to create concept cards from the material.
8. Select a card, then ask follow-up questions or generate a quiz.

Without an API key, use Load Demo Canvas to try the full interaction flow.

## Architecture

### Stack

- Frontend: Vue 3, TypeScript, Vite, Element Plus, vue-i18n
- Backend: Python 3.11, FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL 17, pgvector
- AI: DashScope Qwen, DashScope `text-embedding-v3`
- Deployment: Docker, Docker Compose

### System

```text
Browser
  |
  | HTTP / REST
  v
Frontend (Vue 3 + Element Plus + vue-i18n)
  |
  | /api proxy
  v
Backend (FastAPI)
  |              \
  | SQL           \ DashScope Qwen / Embedding
  v               v
PostgreSQL + pgvector
```

## Repository Structure

```text
CourseMind/
├── frontend/
│   ├── src/
│   │   ├── api/              # API client
│   │   ├── i18n/             # en-US / zh-CN dictionaries
│   │   ├── stores/           # Auth state
│   │   └── views/            # Pages
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── ai/               # DashScope adapters
│   │   ├── api/              # FastAPI routes
│   │   ├── models/           # Database models
│   │   ├── parsers/          # TXT / Markdown / PDF parsers
│   │   └── services/         # RAG, retrieval, upload, ingestion
│   ├── alembic/              # Database migrations
│   └── Dockerfile
├── docker-compose.yml
├── start-docker.sh
├── DEMO_SCRIPT.md
└── README.md
```

## Local Development

```bash
# Terminal 1: database
docker compose up postgres

# Terminal 2: backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
export DASHSCOPE_API_KEY=sk-your-key-here
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Terminal 3: frontend
cd frontend
npm install
npm run dev
```

The local Vite server usually runs at http://localhost:5173. The Docker frontend runs at http://127.0.0.1:5174.

## Current Limits

- Supports TXT, Markdown, and PDF; PPTX, DOCX, and image OCR are not implemented yet.
- PDFs should contain selectable text. Scanned PDFs or custom font encodings may fail.
- The learning canvas is currently a card grid, not an infinite drag-and-drop canvas.
- Weak points are based on follow-up counts, not a long-term learner model.
- RAG answers are grounded only in uploaded materials and do not use web search.

## Checks

```bash
# Frontend type check
cd frontend
npm run type-check

# Backend tests, after installing test dependencies locally
cd backend
pytest
```

## Documents

- [Docker Quick Start](DOCKER_QUICKSTART.md)
- [Demo Script](DEMO_SCRIPT.md)
- [Demo Checklist](DEMO_CHECKLIST.md)
- [Project Summary](SUBMISSION_SUMMARY.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)

## License

MIT License
