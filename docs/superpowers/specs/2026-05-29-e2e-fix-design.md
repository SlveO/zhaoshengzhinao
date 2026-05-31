# E2E Test Fix Design

**Date**: 2026-05-29 | **Status**: approved

## Problem

12 E2E tests collected but 9 failed + 3 errors. Two root causes:

### Root Cause 1: Docker Network Isolation (9 tests)

Backend container runs Playwright. Tests navigate to `http://localhost:3001/` (admin-spa) and `http://localhost:3002/` (mini-app). Inside the backend container, `localhost` resolves to the backend container itself, not the admin-spa or mini-app containers. Connections are refused.

Fix: change `localhost` to the Docker Compose service names (`admin-spa`, `mini-app`).

Affected files:
- `backend/tests/e2e/test_admin_analytics.py` — `ADMIN_URL`
- `backend/tests/e2e/test_knowledge_upload.py` — `ADMIN_URL`
- `backend/tests/e2e/test_student_journey.py` — `BASE_URL`

### Root Cause 2: Async Fixture Event Loop Conflict (3 tests)

`test_status_bubble.py` uses `async def browser()` and `async def page()` generator fixtures + `async def` test methods. `pytest.ini` sets `asyncio_default_fixture_loop_scope=session`, which creates a single event loop for the session. pytest-asyncio's `Runner.run()` cannot start a new event loop inside an already-running one.

The other 3 E2E files use synchronous Playwright API (`sync_playwright()`, `with sync_playwright() as p:`) with plain `def` fixtures and test methods. This works correctly.

Fix: convert `test_status_bubble.py` fixtures and tests to synchronous Playwright API, matching the pattern in `test_student_journey.py`.

## Changes

### Fix 1: Container hostnames

| File | Line | Before | After |
|------|------|--------|-------|
| `test_admin_analytics.py` | ~15 | `ADMIN_URL = "http://localhost:3001"` | `ADMIN_URL = "http://admin-spa:3001"` |
| `test_knowledge_upload.py` | ~13 | `ADMIN_URL = "http://localhost:3001"` | `ADMIN_URL = "http://admin-spa:3001"` |
| `test_student_journey.py` | ~12 | `BASE_URL = "http://localhost:3002"` | `BASE_URL = "http://mini-app:3002"` |

### Fix 2: Async → Sync Playwright

`test_status_bubble.py`:
- Imports: `from playwright.async_api import async_playwright, Page, Browser` → `from playwright.sync_api import sync_playwright, Page, Browser`
- `browser` fixture: `async def` generator → `def` generator with `with sync_playwright() as p:`
- `page` fixture: `async def` → `def`
- Test methods: `async def` → `def`, remove `await` from method bodies

Pattern reference: `test_student_journey.py` fixture and test method structure.

## Verification

```bash
docker compose exec backend python -m pytest tests/e2e/ -v --tb=short
```

Expected: 12 passed, 0 failed, 0 errors.
