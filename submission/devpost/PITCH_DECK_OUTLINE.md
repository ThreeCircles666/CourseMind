# CourseMind Pitch Deck Outline

Devpost asks for a presentation deck of up to 10 slides. This outline is the source content for the PPTX.

## Slide 1: CourseMind

Turn course materials into an AI study canvas for notes, follow-ups, quizzes, and personalized review.

Presenter note:

CourseMind targets students who need help reviewing long course materials with source-backed AI support.

## Slide 2: Problem Statement

Students lose time during review because long course materials do not reveal what matters most.

Key points:

- Long PDFs and lecture notes create review overload.
- Generic AI answers can be hard to trust.
- Follow-up learning often gets lost outside the original notes.
- Students lack a clear weak-point map.

## Slide 3: Solution Overview

CourseMind connects document upload, grounded Q&A, visual study cards, follow-ups, quizzes, and weak-point review.

Workflow:

1. Upload course material.
2. Ask grounded questions.
3. Generate a learning canvas.
4. Expand concepts with follow-ups.
5. Review weak points and quizzes.

## Slide 4: Target Users

Primary users:

- University students preparing for exams.
- Online learners organizing course notes.
- Bilingual learners using English and Chinese materials.

Use cases:

- Exam review
- Lecture note digestion
- Concept clarification
- Self-check before assessment

## Slide 5: Product Features

Core features:

- Document management for TXT, Markdown, and PDF.
- Knowledge base Q&A with citations.
- AI learning canvas with concept cards.
- Local follow-ups saved as child cards.
- Quiz generation and weak-point markers.
- English and Simplified Chinese interface.

## Slide 6: Technical Architecture

Stack:

- Vue 3, TypeScript, Vite, Element Plus, Pinia, Vue I18n.
- FastAPI, SQLAlchemy, Alembic, JWT authentication.
- PostgreSQL 17 with pgvector.
- DashScope Qwen and text-embedding-v3.
- Docker Compose.

Architecture:

Browser to Vue frontend to FastAPI backend to PostgreSQL and DashScope.

## Slide 7: AI Technologies Used

AI components:

- Embeddings from DashScope text-embedding-v3.
- Semantic retrieval with pgvector.
- Qwen for grounded Q&A answers.
- Qwen for concept extraction, follow-ups, and quiz generation.

Trust and safety:

- Source snippets shown where available.
- Insufficient-context states.
- Demo fallback clearly labeled.

## Slide 8: Impact and Value

CourseMind helps learners review faster and with more confidence.

Impact:

- Reduces time spent finding key concepts.
- Makes AI answers easier to verify.
- Turns repeated confusion into visible weak-point signals.
- Keeps notes, questions, follow-ups, and quizzes in one workflow.

## Slide 9: Current Status

Built:

- Bilingual frontend across eight pages.
- Authentication and user-scoped documents.
- Document upload, parsing, status, retry, and deletion.
- RAG Q&A with sources.
- Learning canvas with follow-ups, quizzes, and weak points.
- Docker Compose local setup.

Current limits:

- No PPTX, DOCX, scanned PDF OCR, or image OCR yet.
- Card-grid canvas, not freeform drag-and-drop.
- Real AI flows require DashScope credentials.

## Slide 10: Roadmap

Next steps:

- Add PPTX, DOCX, scanned PDF, and image OCR support.
- Add freeform drag-and-drop canvas organization.
- Add spaced repetition and long-term learner memory.
- Export notes to Markdown, flashcards, or study plans.
- Add instructor analytics for class-level weak points.

