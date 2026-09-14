# CourseMind Demo Script

## 3-Minute Core Version

### Opening (30 seconds)

Show the home page after login.

Script:

"Hi everyone, we are the CourseMind team. When students review course materials, they often face a whole slide deck or PDF without knowing what matters most, which concepts they still do not understand, or where an AI answer came from.

CourseMind is not just another Q&A tool. It turns course materials into an interactive learning canvas."

### Step 1: Open Learning Canvas (20 seconds)

Actions:

1. Click the Learning Canvas card on the home page.
2. Open `/canvas`.

Script:

"This is the Learning Canvas. On the left, students can select course materials. The center area is the canvas, and the right panel shows concept details and follow-up actions."

### Step 2: Load Demo Canvas (20 seconds)

Actions:

1. Click Load Demo Canvas.
2. Wait for cards to appear.

Script:

"The demo canvas contains six concept cards. Different colors represent different types: definitions, formulas, examples, common mistakes, and exam focus points. This is easier to scan than a plain text list."

### Step 3: Inspect a Concept (30 seconds)

Actions:

1. Click the first concept card.
2. Show the detail panel.

Script:

"Every concept has a title, a review summary, and source information. For real uploaded materials, CourseMind shows the source file, page number, and excerpt, so students can verify where the concept came from."

### Step 4: Ask a Local Follow-Up (40 seconds)

Actions:

1. Click Explain Simply.
2. Wait for a child card.
3. Point to the new card on the canvas.

Script:

"Instead of asking a broad question about the whole document, students can ask about one concept. The answer is written back to the canvas as a child card, creating a personal study path."

### Step 5: Weak Point Marker (30 seconds)

Actions:

1. Click Give Example.
2. Watch the parent card update.

Script:

"After repeated follow-ups on the same concept, CourseMind marks it as a weak point. This is based on the student's behavior: if they keep asking about a concept, it probably deserves more review."

### Step 6: Language Selection (20 seconds)

Actions:

1. Use the top-right language selector.
2. Switch between English and Simplified Chinese.

Script:

"The app supports English and Simplified Chinese. The selected language applies across the app, including the home page, knowledge base, Q&A, and learning canvas."

### Closing (20 seconds)

Script:

"CourseMind helps students review in four ways: it extracts key concepts, organizes them visually, supports local follow-up, and keeps answers traceable to uploaded materials. The stack is Vue 3, FastAPI, PostgreSQL with pgvector, and DashScope."

## 5-Minute Extended Version

Add these sections after the core canvas flow.

### Document Upload (1 minute)

Actions:

1. Go to Knowledge Base.
2. Upload a TXT, Markdown, or text-selectable PDF.
3. Show document status, file size, and processing result.

Script:

"CourseMind has a real RAG pipeline underneath the demo. Uploaded documents are parsed, chunked, embedded, and stored in PostgreSQL with pgvector. Once processing succeeds, the material can be used for Q&A and canvas generation."

### Knowledge Base Q&A (30 seconds)

Actions:

1. Go to Knowledge Q&A.
2. Select a processed document.
3. Ask a question.
4. Show the answer and sources.

Script:

"Answers are grounded in uploaded materials. CourseMind returns cited sources with similarity scores and marks the answer as insufficient when the document does not contain enough information."

### Real Canvas Generation (1 minute)

Actions:

1. Go back to the Learning Canvas.
2. Select a processed document.
3. Click Generate Canvas.
4. Show generated cards and source details.

Script:

"The learning canvas reuses the same RAG backend. It asks the model to extract review concepts with citations, then turns the result into visual cards. If the model or network fails, the UI falls back to demo data instead of breaking the presentation."
