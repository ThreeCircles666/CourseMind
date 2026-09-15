# CourseMind - AI Study Canvas

Language: [English](README.md) | [简体中文](README.zh-CN.md)

> **CourseMind: Turn course materials into an AI study canvas for notes, follow-ups, quizzes, and personalized review.**

CourseMind is an AI learning workflow for students and educators. It turns uploaded course materials into a traceable knowledge base, grounded answers, visual study cards, AI conversations, quizzes, and review focus points. The product is designed as a complete study loop: upload course documents, ask grounded questions, organize knowledge on a learning canvas, and continue learning with AI assistance.

## What Is New

- Refined page-level UI/UX across all 8 primary routes.
- Global language selector on every page.
- AI answers follow the selected CourseMind interface language.
- English and Simplified Chinese copy are maintained through `vue-i18n`.
- A reusable design token layer keeps colors, spacing, cards, buttons, and page rhythm consistent.
- Devpost submission materials are included under `submission/devpost/`.

## Core Features

### AI Learning Canvas

- Extracts review concepts from uploaded course materials.
- Organizes knowledge as cards for definitions, formulas, examples, common mistakes, and exam focus points.
- Supports follow-up questions on a selected concept.
- Writes follow-up answers back to the canvas as child cards.
- Marks frequently queried concepts as weak points.
- Provides source file, page, and excerpt references where available.
- Includes demo-mode fallback so the workflow remains easy to present.

### Knowledge Base Q&A

- Supports TXT, Markdown, and text-selectable PDF uploads.
- Parses, chunks, embeds, and stores materials in PostgreSQL + pgvector.
- Answers questions from selected documents using retrieval-augmented generation.
- Shows cited sources and similarity information.
- Distinguishes complete answers, partial answers, and insufficient context.
- Responds in English or Simplified Chinese based on the selected UI language.

### AI Chat

- Provides a focused chat interface for study assistance.
- Supports session history, session switching, renaming, and deletion.
- Streams assistant responses.
- Uses the selected interface language as the preferred answer language.

### Documents

- Uploads and manages course materials.
- Tracks parsing and indexing status.
- Supports document deletion and refresh.
- Keeps documents isolated by authenticated user.

### Internationalized Product Experience

- Built-in `en-US` and `zh-CN` dictionaries.
- Language selector is available on home, login, register, documents, knowledge Q&A, learning canvas, AI chat, and about pages.
- Selected language is persisted locally.
- Main AI workflows receive the selected language and answer accordingly.

## Pages

| Route | Page |
| --- | --- |
| `/` | Study workspace / home |
| `/login` | Login |
| `/register` | Register |
| `/documents` | Document management |
| `/knowledge-ask` | Knowledge base Q&A |
| `/canvas` | Learning canvas |
| `/chat` | AI chat |
| `/about` | Product overview and system status |

## Quick Start

### Requirements

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ available memory
- Optional: Alibaba Cloud DashScope API key for real AI workflows

### Start with Docker

```bash
git clone https://github.com/ThreeCircles666/CourseMind.git
cd CourseMind

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

CourseMind uses DashScope for production AI workflows:

- `text-embedding-v3` for document embeddings.
- Qwen chat models for RAG answers, AI chat, and learning canvas generation.

Without `DASHSCOPE_API_KEY`:

- Registration, login, the optimized UI, demo canvas, and fallback flows remain available.
- Real document vectorization, grounded Q&A, and document-based canvas generation require the key.

## Demo Flow

1. Open http://127.0.0.1:5174.
2. Register and log in.
3. Choose English or Simplified Chinese from the language selector.
4. Go to Documents and upload TXT, Markdown, or a text-selectable PDF.
5. Wait until the document status becomes succeeded.
6. Ask a question in Knowledge Base Q&A and inspect citations.
7. Open Learning Canvas and generate a study canvas from the document.
8. Select a card, ask a follow-up, and generate a quiz.
9. Open AI Chat and verify that answers follow the selected interface language.

Without an API key, use the demo canvas path to present the interactive workflow.

## Architecture

### Stack

- Frontend: Vue 3, TypeScript, Vite, Vue Router, Pinia, Element Plus, vue-i18n
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
│   │   ├── api/              # API clients
│   │   ├── assets/           # Design tokens and global styles
│   │   ├── components/       # Shared UI components
│   │   ├── composables/      # Streaming chat and reusable logic
│   │   ├── i18n/             # en-US / zh-CN dictionaries
│   │   ├── stores/           # Auth and app state
│   │   └── views/            # Page-level views
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── ai/               # AI contracts and adapters
│   │   ├── api/              # FastAPI routes
│   │   ├── models/           # Database models
│   │   ├── parsers/          # TXT / Markdown / PDF parsers
│   │   └── services/         # RAG, retrieval, upload, ingestion
│   ├── alembic/              # Database migrations
│   └── Dockerfile
├── submission/devpost/       # Hackathon submission package
├── docker-compose.yml
├── start-docker.sh
├── README.md                 # English
└── README.zh-CN.md           # Simplified Chinese
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
pip install -e ".[dev]"
export DASHSCOPE_API_KEY=sk-your-key-here
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Terminal 3: frontend
cd frontend
npm install
npm run dev
```

The local Vite server usually runs at http://localhost:5173. The Docker frontend runs at http://127.0.0.1:5174.

## Checks

```bash
# Frontend type check and production build
cd frontend
npm run type-check
npm run build

# Backend tests, after installing test dependencies locally
cd backend
.venv/bin/python -m pytest
```

## Hackathon Submission

The Devpost-ready submission package is in `submission/devpost/`:

- `DEVPOST_SUBMISSION.md`
- `JUDGE_TESTING_INSTRUCTIONS.md`
- `DEMO_VIDEO_SCRIPT.md`
- `PITCH_DECK_OUTLINE.md`
- `AI_USAGE_AND_DISCLOSURE.md`
- `SUBMISSION_CHECKLIST.md`
- `CourseMind_AI_Builders_Hackathon_Deck_v2.pptx`

## Current Limits

- Supports TXT, Markdown, and text-selectable PDF; PPTX, DOCX, and image OCR are not implemented yet.
- Scanned PDFs or PDFs with custom font encodings may fail to parse.
- The learning canvas is currently a structured card workspace, not a fully freeform infinite canvas.
- Weak points are based on interaction frequency, not a long-term learner model.
- RAG answers are grounded only in uploaded materials and do not use web search.

## Documents

- [Docker Quick Start](DOCKER_QUICKSTART.en.md)
- [Demo Script](DEMO_SCRIPT.en.md)
- [Demo Checklist](DEMO_CHECKLIST.en.md)
- [Project Summary](SUBMISSION_SUMMARY.en.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.en.md)

## License

MIT License
