# CourseGuard API (Backend)

FastAPI backend skeleton for the YWP Labs AI teaching-assist platform.

This is a **skeleton only**. It provides a health check endpoint and a
configured (but unused) database layer. No business features exist yet.

## Requirements

- Python 3.11+
- PostgreSQL is **not** required to run the health check.

## Setup

Create and activate a virtual environment, then install dependencies.

### macOS / Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Windows PowerShell

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Then copy the environment file:

```bash
# macOS / Linux
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

- API root: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/v1/health

## Test

```bash
pytest
```

## Notes

- The health endpoint does not touch the database.
- SQLAlchemy 2, psycopg 3, and Alembic are installed and minimally
  configured for future use. There are no models or migrations yet.
