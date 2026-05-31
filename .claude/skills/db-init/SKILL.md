---
name: db-init
description: Initialize or migrate the database with seed data. Invoke when user says "init db", "setup database", "seed db", "reset db", or "migrate and seed".
---

# Database Initialize / Migrate

Run database migrations and seed with fixture data.

## Steps

1. **Run migrations**:
   ```bash
   cd backend && alembic upgrade head
   ```

2. **Seed data**:
   ```bash
   python scripts/seed_db.py
   ```

3. **Verify**:
   - Check core tables exist: `tenants`, `users`, `consult_sessions`, `chat_messages`, `recommendations`, `event_logs`
   - Confirm demo login works: `admin` / `admin123`

## Prerequisites
- PostgreSQL and Redis running (`docker compose up -d db redis`)
- `.env` file with `DATABASE_URL` configured
