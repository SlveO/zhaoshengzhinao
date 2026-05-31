# Data Pipeline Test Results

**Date**: 2026-05-29 | **Branch**: feat/admin-redesign-v2

---

## Phase 0: Environment Check

| Step | Status | Detail |
|------|--------|--------|
| 0.1 Test dirs exist | PASS | unit/ (28), integration/ (7), e2e/ (5) |
| 0.2 Test collection | PASS | 209 items collected |
| 0.3 Backend reachable | PASS | 200 |

## Phase 1: Unit Tests (174/180)

| Test | Type | Error Summary |
|------|------|---------------|
| `test_save_message_returns_message_dict` | TEST | Mock doesn't set `msg.created_at` → `.isoformat()` on None |
| `test_extract_leads_*` (×5) | TEST | `No module named 'backend'` — patch path unresolvable in container |

**Note**: Prior baseline failure `test_different_tenants_separate_urls` now PASSES.

## Phase 2: Integration Tests (3/7)

**Passed**: `test_register_login_refresh_flow`, `test_chat_session_create_and_read`, `test_knowledge_documents_are_tenant_scoped`

| Test File | Type | Error Summary |
|-----------|------|---------------|
| `test_{analytics,knowledge,miniapp,module}*` (×4) | TEST | `from conftest import TEST_TENANT_ID` — not on sys.path |

## Phase 3: E2E Tests (0/4)

| Test File | Type | Error Summary |
|-----------|------|---------------|
| All 4 e2e tests | INFRA | `No module named 'playwright'` — not installed in container |

## Phase 4: API Acceptance (4/4)

| Endpoint | Status | Note |
|----------|--------|------|
| `topic-cloud?days=30` | 200 | `[]` (no events) |
| `emotion-timeline?days=30` | 200 | empty |
| `hot-questions?days=30` | 200 | `[]` (no events) |
| `knowledge/index-status` | 200 | total=3994, indexed=3994 |

---

## Summary

| Phase | Status | Detail |
|-------|--------|--------|
| Env Check | PASS | All 3 steps green |
| Unit Tests | FAILED | 174 pass, 6 TEST-type failures (mock/patch) |
| Integration Tests | FAILED | 3 pass, 4 TEST-type collection errors |
| E2E Tests | FAILED | 0 collected, 4 INFRA errors (playwright) |
| API Acceptance | PASS | All 200, KB 3994 docs indexed |

**Overall**: Baseline brand-URL fix confirmed. All 10 failures are TEST/INFRA (no CODE bugs). 6 unit: mock misconfiguration. 4 integration: conftest import pattern. 4 e2e: missing playwright. KB healthy at 3994 docs.
