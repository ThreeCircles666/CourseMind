# CourseMind Docker Quick Start

## Start Everything

```bash
# Build and start all services
docker compose up --build

# Or run in the background
docker compose up -d --build
```

## Service URLs

- Frontend: http://127.0.0.1:5174
- Backend API: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/v1/health
- Database: `localhost:5432` with user `coursemind` and password `coursemind_dev`

## Demo Flow

1. Open http://127.0.0.1:5174.
2. Register a new account.
3. Choose English from the top-right language selector.
4. Open Learning Canvas at http://127.0.0.1:5174/canvas.
5. Click Load Demo Canvas.
6. Select any concept card to view details.
7. Click Explain Simply and Give Example.
8. Watch child cards appear on the canvas and weak point markers update.

## Services

### PostgreSQL + pgvector

- Starts automatically with the pgvector extension enabled.
- Persists data in a Docker volume.
- Uses a health check so the backend waits for the database.

### Backend (FastAPI)

- Waits for PostgreSQL before starting.
- Runs database migrations with `alembic upgrade head`.
- Exposes port `8000`.
- Stores uploaded files under `backend/data/uploads`.

### Frontend (Vue 3 + Vite)

- Runs in development-server mode.
- Exposes port `5174`.
- Uses the same-origin `/api` proxy to reach the backend.

## DashScope API Key

Real document processing, RAG Q&A, and document-based canvas generation require `DASHSCOPE_API_KEY`.

```bash
export DASHSCOPE_API_KEY=sk-your-key-here
docker compose up --build
```

Without an API key, registration, login, the demo canvas, and fallback flows still work.

## Stop Services

```bash
# Stop containers
docker compose down

# Stop containers and delete database data
docker compose down -v
```

Use `docker compose down -v` only when you intentionally want to clear the database.

## Rebuild

```bash
docker compose build --no-cache
docker compose up --build
```

## Logs

```bash
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
```

## Common Issues

### Port Conflicts

If `5432`, `8000`, or `5174` is already in use, change the port mappings in `docker-compose.yml`.

```yaml
services:
  postgres:
    ports:
      - "15432:5432"
  backend:
    ports:
      - "18000:8000"
  frontend:
    ports:
      - "15174:5174"
```

### Migration Fails

```bash
docker compose exec backend alembic upgrade head
```

### Frontend Cannot Reach Backend

The default Docker setup proxies frontend `/api` requests to the backend container. If you changed `frontend/.env`, clear `VITE_API_BASE_URL` or point it to a reachable backend URL.

### Reset All Data

```bash
docker compose down -v
docker compose up --build
```

## Minimum Requirements

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ available memory
- 10GB+ available disk space

## Stack

- Database: PostgreSQL 17 + pgvector
- Backend: Python 3.11 + FastAPI + SQLAlchemy + Alembic
- Frontend: Node 20 + Vue 3 + Vite + TypeScript + Element Plus
- Container runtime: Docker + Docker Compose
