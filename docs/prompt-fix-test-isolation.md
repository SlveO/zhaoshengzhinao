# Prompt: Fix Test Data Leak via Missing Table Cleanup

## Root Cause

@backend/tests/conftest.py:80-82 — `setup_db` fixture cleans 10 tables after each test, but `chat_messages` and `consult_sessions` are missing. Tests that insert into these tables leak data across runs. `test_message_persistence` is one symptom of this systemic gap.

## Fix: Add 2 tables to cleanup loop

**File:** `backend/tests/conftest.py`

Lines 80-82:

```python
# Before
        for table in ["event_logs", "session_profiles", "tenant_data", "tenant_users",
                       "departments", "tenants", "recommendation_feedback",
                       "recommendations", "user_profiles", "users"]:

# After
        for table in ["event_logs", "session_profiles", "tenant_data", "tenant_users",
                       "departments", "tenants", "recommendation_feedback",
                       "recommendations", "user_profiles", "users",
                       "chat_messages", "consult_sessions"]:
```

No FK between these two tables — order doesn't matter.

## Verify

```bash
# Run 3 times — all pass
docker compose exec backend python -m pytest tests/test_miniapp_apis.py::test_message_persistence -v --tb=short
docker compose exec backend python -m pytest tests/test_miniapp_apis.py::test_message_persistence -v --tb=short
docker compose exec backend python -m pytest tests/test_miniapp_apis.py::test_message_persistence -v --tb=short

# Full regression
docker compose exec backend python -m pytest tests/ -q
```

## Constraints

- Do NOT modify test files
- Do NOT modify business code
- 2-line change only
