# Prompt C: Execute Test Suite (Read-Only)

Test execution agent. ONLY run tests and record results. NEVER modify tests or code.

## Input
- docs/data-pipeline-task.md -- pipeline spec
- reports/data-pipeline-fix-report.md -- fixes applied
- All tests under backend/tests/

## Execution

### Phase 1: Unit Tests
Run: docker compose exec backend python -m pytest tests/unit/ -v --tb=short

### Phase 2: Integration Tests
Run: docker compose exec backend python -m pytest tests/integration/ -v --tb=short

### Phase 3: E2E Tests
Run: docker compose exec backend python -m pytest tests/e2e/ -v --tb=short

### Phase 4: API Acceptance
curl each analytics endpoint, verify 200
curl index-status, verify total_docs > 0

## Output
Write reports/data-pipeline-test-results.md with tables: passed/failed/errors for each phase, individual failure details, API acceptance matrix, summary.

## RULES
1. DO NOT modify any test or code file
2. Record failures, do not fix them
3. Run every command, do not skip phases