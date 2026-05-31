# Quick Start

```bash
# Infrastructure
docker compose up -d db redis

# Backend (port 8000)
cd backend && uvicorn main:app --host 127.0.0.1 --port 8000

# Admin SPA (port 3001)
cd admin-spa && npm install && npm run dev -- --port 3001

# Mini-app / student-facing (port 3002)
cd mini-app && npm install && TENANT=scnu node build.config.js && npm run dev:h5 -- --port 3002
```

Demo login: `admin` / `admin123` at `http://localhost:3001?tenant=scnu`

## Testing, Lint, DB

```bash
# Run all tests (asyncio_mode=auto in pytest.ini)
pytest backend/tests/

# Single test file
pytest backend/tests/unit/test_evidence_accumulator.py

# With coverage
pytest backend/tests/ --cov=backend --cov-report=term-missing

# Lint backend only
ruff check backend/

# DB migrations (run from repo root)
cd backend && alembic upgrade head

# Seed DB with fixture data
python scripts/seed_db.py
```
