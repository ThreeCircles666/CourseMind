# AI Usage and Disclosure

Use this text in the Devpost submission if the form asks how AI was used in the project or how AI tools contributed to development.

## Product AI Usage

CourseMind uses AI as part of the learning product:

- Document embeddings are generated with DashScope text-embedding-v3.
- Retrieved document chunks are used as context for grounded answers.
- DashScope Qwen generates knowledge base answers, learning canvas concept cards, follow-up explanations, and quiz content.
- The UI shows cited sources where available and marks insufficient-context answers when uploaded materials do not support a confident answer.

## Development AI Assistance

AI coding assistants were used to support implementation, debugging, UI polish, documentation drafting, and review. The team remains responsible for the final project behavior, code, testing, privacy, licensing, and submission accuracy.

The final submitted project includes original application logic, product design decisions, integration work, documentation, and testing performed by the team.

## Third-Party Technologies

CourseMind uses open-source frameworks and libraries including Vue 3, TypeScript, Vite, Element Plus, Pinia, Vue I18n, FastAPI, SQLAlchemy, Alembic, PostgreSQL, and pgvector.

CourseMind uses DashScope Qwen and DashScope text-embedding-v3 for model-backed functionality.

## Data Handling

Uploaded documents are used for the user's own RAG and study-canvas workflows. The app scopes documents to authenticated users. Judges should avoid uploading confidential, private, or regulated data during evaluation.

