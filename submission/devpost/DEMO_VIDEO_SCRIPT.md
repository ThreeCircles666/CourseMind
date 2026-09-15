# CourseMind Demo Video Script

Recommended length: 3 to 5 minutes.

## Recording Setup

- Browser width: 1440px if possible.
- Zoom: 100%.
- Start logged in on the CourseMind home page.
- Keep a processed document ready if you have a DashScope API key.
- If no API key is available, use Load Demo Canvas for the canvas flow.

## 0:00 to 0:25 Opening

Say:

"Hi, this is CourseMind. Students often review from long PDFs, lecture notes, or Markdown files, but they do not know what to study first, which answers to trust, or which concepts they personally need to revisit. CourseMind turns course materials into a traceable AI study canvas."

Show:

- Home page
- Language selector
- Four core workflow cards

## 0:25 to 1:05 Document and Q&A Workflow

Actions:

1. Open Knowledge Base.
2. Show upload area and document status.
3. Open Knowledge Q&A.
4. Select a processed document.
5. Ask a short question.

Say:

"The workflow starts with uploaded course materials. CourseMind parses files, creates embeddings, and lets students ask questions against selected documents. The answer includes cited sources, so the student can verify where the information came from."

Show:

- Document status
- Question input
- Answer
- Sources and similarity score

## 1:05 to 2:15 Learning Canvas

Actions:

1. Open Learning Canvas.
2. Select a document and generate the canvas, or click Load Demo Canvas.
3. Click a concept card.

Say:

"CourseMind also generates a learning canvas. Instead of reading a long answer, students get review cards for definitions, formulas, examples, common mistakes, and exam focus points. Each card keeps source context where available."

Show:

- Canvas cards
- Card labels
- Detail panel
- Source excerpt

## 2:15 to 3:10 Follow-ups and Weak Points

Actions:

1. Click Explain Simply or ask a custom follow-up.
2. Show the child card added to the canvas.
3. Ask another follow-up or generate a quiz.
4. Show weak-point or quiz area.

Say:

"The important part is local follow-up. A student can ask about one concept, and the answer becomes a child card on the canvas. Repeated follow-ups create a weak-point signal, which helps students see what deserves more review."

Show:

- Follow-up action
- Child card
- Quiz content
- Weak-point badge

## 3:10 to 3:40 AI Chat and Language Support

Actions:

1. Open AI Chat.
2. Send a short message or show the input.
3. Switch language between English and Simplified Chinese.

Say:

"CourseMind also includes a general AI chat for learning support, plus full English and Simplified Chinese interface support. The language switcher is available on every page."

Show:

- Chat layout
- Language switching

## 3:40 to 4:20 Technical Summary

Say:

"The frontend uses Vue 3, TypeScript, Element Plus, Pinia, and Vue I18n. The backend uses FastAPI, SQLAlchemy, PostgreSQL, and pgvector. DashScope text-embedding-v3 powers embeddings, and Qwen powers grounded answers and learning canvas generation."

Show:

- About page technical stack
- Optional architecture slide

## 4:20 to 4:50 Closing

Say:

"CourseMind is built for students who want a more active and trustworthy way to review. It connects uploaded materials, grounded Q&A, visual concept maps, follow-up learning, self-check questions, and weak-point review in one workflow."

Show:

- Home page or canvas page

## If The AI API Is Unavailable

Say:

"This environment does not include a DashScope key, so I will use the demo canvas. The same UI connects to the RAG and generation pipeline when the key is configured."

Then show:

- Load Demo Canvas
- Follow-up and quiz demo behavior

