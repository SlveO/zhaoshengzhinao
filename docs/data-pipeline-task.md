# Task: Data Pipeline Completion & Error Fix — SCNU Single-Tenant

## Role
You are a full-stack developer on **招生智脑** (B2B multi-tenant SaaS for Chinese university admissions).
You work across the stack: Python/FastAPI backend, React/TypeScript admin-spa, Vue3/uni-app mini-app.

## Current State
- Branch: `feat/admin-redesign-v2`
- Infrastructure: Docker Compose (all services running on `localhost:80` via nginx)
- Backend: FastAPI on port 8000, tests: 134 unit / 3 integration passed
- Admin SPA: `http://localhost/admin/?tenant=scnu` (login: `admin` / `admin123`)
- Mini-app: `http://localhost/` (H5 mode)
- Tenant: `scnu` (华南师范大学)
- Seed data: `schools.json` (150+ universities), `scores.json` (admission records)

## Data Pipeline (Reference)

### Stage 1: Student Entry
- mini-app -> POST /api/v1/miniapp/enter -> get_or_create_session() in backend/services/consult_service.py
- Registered users: persistent ConsultSession (30-day TTL). Guests: temporary (1-day TTL)
- Event: chat_session_started -> event_logs

### Stage 2: AI Conversation + RAG
- mini-app chat -> POST /api/v1/chat/messages (SSE streaming) -> backend/api/routes/miniapp.py
- Saves user message -> chat_messages table. Retrieves RAG context from ChromaDB via search_similar()
- Calls DeepSeek LLM, streams tokens over SSE. Extracts profile info via regex
- Events: chat_message_sent, chat_rag_completed, chat_response_completed -> event_logs

### Stage 3: Admin Dashboard (Analytics)
- admin-spa -> GET /api/v1/admin/analytics/* -> backend/analytics/router.py
- Raw SQL aggregation on event_logs. Gated by ModuleGateMiddleware (tenant.config.modules)
- Funnel, Profile Dashboard, Insights (topic cloud/emotion/hot questions), Reports

### Stage 4: Lead & Consultation Management
- Data source: event_logs + consult_sessions + chat_messages

## Errors to Fix

### Error 1: 403 on Insights Analytics Pages [HIGH]
- Root cause: scripts/create_scnu_tenant.py:31-41 missing topic_cloud, emotion_timeline, hot_questions
- Fix: Add the 3 missing module keys, re-run the script
- AC: GET /api/v1/admin/analytics/topic-cloud returns 200

### Error 2: Knowledge Base Shows 0 Documents [HIGH]
- Root cause: ChromaDB scnu_colleges collection empty (data on feat/d-infrastructure branch)
- Reference: docs/ROLE_D_RAG_INTEGRATION_REPORT.md
- Fix: Import seed data into TenantData table + ChromaDB
- AC: GET /api/v1/admin/knowledge/index-status returns total_docs > 0

### Error 3: Mini-app Status Message Position [LOW]
- Root cause: SSE thinking events rendered as standalone element, not in chat bubble
- Fix: Move status into assistant's message bubble component
- AC: Status messages appear inline with chat bubbles

## Testing Strategy

| Pipeline Stage | Unit Test | Integration Test | E2E Test |
|---|---|---|---|
| Student Entry | session create/resume | POST /enter validation | Playwright: session creation |
| AI Chat + RAG | slot filling logic | SSE flow + mocked LLM | Playwright: chat + RAG source |
| Profile Extraction | regex accuracy | profile after chat | Playwright: multi-turn profile |
| Admin Analytics | SQL aggregation | endpoint structure | Playwright: dashboard data |
| Lead Management | event extraction | lead list API | Playwright: leads after chat |
| Knowledge Base | text builder | upload-index-search | Playwright: upload + verify |
| Module Gating | dependency chain | 403 on disabled | Playwright: error state |
