# Prompt A: Write Data Pipeline Test Cases

## Role
You are a QA engineer on the project. Write comprehensive tests covering the full data pipeline.

## Input Document
Read docs/data-pipeline-task.md for the complete pipeline specification.

## Task
Write unit, integration, and e2e tests. Create new files, do NOT modify existing tests.

### Unit Tests (backend/tests/unit/)
1. test_consult_service.py -- session create/resume, guest vs registered, TTL
2. test_event_writer.py -- write_event inserts, handles missing fields
3. test_profile_extraction.py -- regex extracts province, subject, score
4. test_lead_extraction.py -- lead data from event_logs + consult_session

### Integration Tests (backend/tests/integration/)
5. test_miniapp_pipeline.py -- POST /enter -> chat -> verify session + events
6. test_analytics_pipeline.py -- seed events -> analytics endpoints -> verify structure
7. test_knowledge_pipeline.py -- upload -> TenantData -> ChromaDB -> search
8. test_module_gating.py -- enable/disable module -> 200/403

### E2E Tests (backend/tests/e2e/)
9. test_student_journey.py -- Playwright: enter -> chat -> profile populated
10. test_admin_analytics.py -- Playwright: login -> insights -> no 403
11. test_knowledge_upload.py -- Playwright: login -> upload -> document in list
12. test_status_bubble.py -- Playwright: chat -> status inside bubble

### Constraints
- pytest + pytest-asyncio. Mock external LLM with AsyncMock.
- E2E uses sync_playwright API (not mcp__playwright__*)
- Docstring must state pipeline stage covered
- Integration uses real test DB, mock only external APIs
- Unit tests mock all I/O

### Output
Write files to backend/tests/. Print summary: path, test count, pipeline stage.
