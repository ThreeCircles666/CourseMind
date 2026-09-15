# CourseMind Devpost Submission Copy

Use this file to fill the AI Builders Hackathon submission form.

## Project Title

CourseMind

## Short Tagline

Turn course materials into an AI study canvas for notes, follow-ups, quizzes, and personalized review.

## Project Description

CourseMind is an AI learning workspace for students who need to review dense course materials. Instead of leaving learners with a long PDF, scattered notes, or a generic chatbot, CourseMind turns uploaded materials into a traceable study workflow.

Students can upload course documents, ask grounded questions, generate a visual learning canvas, inspect source-backed concept cards, ask follow-up questions on individual concepts, create self-check questions, and mark weak points for review.

The product focuses on a practical education problem: students often do not know which parts of their materials matter most, where an AI answer came from, or what they personally need to review again. CourseMind combines document-grounded retrieval, a bilingual interface, and a study canvas to make that workflow visible and easier to trust.

## Problem

Students preparing for exams or self-study often face three problems:

- Course materials are long, dense, and hard to prioritize.
- AI answers can be difficult to trust when they do not show sources.
- Review tools rarely connect questions, notes, follow-ups, quizzes, and weak points in one place.

CourseMind addresses these problems by turning uploaded materials into a guided review workspace rather than a single-purpose chatbot.

## Solution

CourseMind supports a complete learning workflow:

1. Upload TXT, Markdown, or text-selectable PDF course materials.
2. Parse, chunk, embed, and store documents in PostgreSQL with pgvector.
3. Ask questions against selected documents and inspect cited sources.
4. Generate a learning canvas with review concept cards.
5. Ask follow-up questions on one concept and save answers as child cards.
6. Generate self-check questions and identify weak points based on repeated follow-up behavior.
7. Switch between English and Simplified Chinese across the full interface.

## What We Built

- A Vue 3 + TypeScript frontend with a polished, responsive, bilingual UI.
- A FastAPI backend with authentication, document upload, parsing, ingestion, and RAG endpoints.
- A PostgreSQL + pgvector retrieval layer for semantic search.
- DashScope Qwen integration for answers and study-card generation.
- A learning canvas that connects concepts, follow-ups, source excerpts, quizzes, and weak-point signals.
- Docker Compose setup for local evaluation.

## Key Features

### Document Management

Users can upload supported course files, see processing status, retry failed parsing, and move directly from a processed document to Q&A or canvas generation.

### Knowledge Base Q&A

Users can select processed documents and ask questions. CourseMind returns answers with cited source snippets, page numbers when available, and similarity scores.

### AI Learning Canvas

CourseMind extracts review concepts from materials and presents them as cards. Cards include type labels such as definition, formula, example, common mistake, and exam focus. Each card can be expanded through follow-up questions.

### Follow-ups, Quizzes, and Weak Points

Students can ask local follow-up questions, generate self-check questions, and see concepts marked as weak points after repeated follow-up behavior.

### Bilingual Product Experience

The interface supports English and Simplified Chinese with a visible language selector on every page.

## Technical Architecture

Frontend:

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Vue I18n
- Element Plus

Backend:

- FastAPI
- Python 3.11
- SQLAlchemy
- Alembic
- JWT authentication

Data and AI:

- PostgreSQL 17
- pgvector
- DashScope Qwen
- DashScope text-embedding-v3

Deployment:

- Docker
- Docker Compose

## How AI Is Used

CourseMind uses AI in two core places:

- Embeddings: uploaded documents are split into chunks and embedded with DashScope text-embedding-v3.
- Generation: DashScope Qwen generates grounded Q&A answers, learning canvas concepts, follow-up explanations, and quiz content.

The AI responses are grounded in uploaded materials. CourseMind also exposes source snippets and insufficient-context states so students can understand answer reliability.

## Impact

CourseMind helps students move from passive document reading to active review. It reduces the friction of finding key concepts, asking targeted questions, verifying sources, and identifying weak points.

The project is especially useful for:

- University students reviewing lecture notes
- Online learners organizing course materials
- Students working across English and Chinese learning contexts
- Learners who want AI help without losing source traceability

## Current Limitations

- Supported uploads are TXT, Markdown, and text-selectable PDF.
- PPTX, DOCX, scanned PDF OCR, and image OCR are not implemented yet.
- The learning canvas is currently a card-grid canvas rather than a freeform drag-and-drop infinite canvas.
- Weak-point detection uses interaction signals, not a long-term learner model.
- Real document processing requires a DashScope API key.

## Future Roadmap

- Add PPTX, DOCX, scanned PDF, and image OCR support.
- Add drag-and-drop canvas organization.
- Add long-term learner memory and spaced review scheduling.
- Add export to notes, flashcards, and study plans.
- Add instructor-facing analytics for course-level weak points.

## Demo Link

TODO: Add deployed app URL or testing instructions.

Local testing instructions are available in `submission/devpost/JUDGE_TESTING_INSTRUCTIONS.md`.

## Source Code

TODO: Add public GitHub repository URL.

Recommended repository: `https://github.com/ThreeCircles666/CourseMind`

## Demo Video

TODO: Add public YouTube, Vimeo, or Devpost-supported video URL.

Use `submission/devpost/DEMO_VIDEO_SCRIPT.md` for recording.

## Presentation Deck

TODO: Add deck link or upload `submission/devpost/CourseMind_AI_Builders_Hackathon_Deck_v2.pptx`.

## Team Members

TODO: Add every Devpost team member with name, email, role, and Devpost account.

Suggested roles:

- Product and UX
- Frontend engineering
- Backend and RAG
- Demo and documentation
