# Testing

## TDD Workflow (mandatory)

1. **Write test first** — before any implementation code
2. **Present test to user** — confirm the test case covers the requirement
3. **User confirms** — proceed to implementation
4. **Implement** — write minimal code to pass the test
5. **Verify** — dispatch `test-runner` agent to run full suite
6. **Refactor** — only after green, clean up if needed

## Test Structure

```
backend/tests/
├── unit/           # Single function/class, no I/O
├── integration/    # Database, Redis, ChromaDB with test fixtures
└── e2e/            # Full API flow through FastAPI TestClient
```

## Python Testing

- Framework: pytest with `asyncio_mode=auto` (configured in `pytest.ini`)
- Run: `pytest backend/tests/`
- Coverage: `pytest backend/tests/ --cov=backend --cov-report=term-missing`

### Mock policy
- Unit tests: mock external I/O (DB, Redis, ChromaDB, LLM API calls)
- Integration tests: use real test database (dockerized PostgreSQL), mock only external LLM APIs
- E2E tests: use FastAPI `TestClient`, real test DB, mock only DeepSeek API

### Test naming
- Files: `test_<module_name>.py`
- Functions: `test_<action>_<scenario>_<expected_result>()`
- Example: `test_evidence_accumulator_3_dimensions_transitions_to_focus()`

## Frontend Testing

- Admin SPA: Vitest + React Testing Library
- Mini-app: uni-app test utilities (when available), manual H5 testing as fallback
- Component tests: render + user interaction + state assertion
- API mocking: mock Axios/uni.request at the request level

## Coverage Thresholds

- Backend core logic (agents, services): target 80%+
- Backend API routes: target 60%+ (thin routes, heavy logic in services)
- Frontend: no strict threshold, but all user-facing flows should have at least smoke tests

## Test Runner Agent

Always use the `test-runner` agent to execute tests — it filters noise and returns condensed results, protecting main context from test output bloat.
