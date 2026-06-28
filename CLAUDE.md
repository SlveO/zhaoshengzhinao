# CLAUDE.md

B2B multi-tenant SaaS for Chinese university admissions ("招生智脑"). Three subsystems on free-tier infra.

## Architecture

| Subsystem | Directory | Stack | Production |
|-----------|-----------|-------|-------------|
| Backend API | `backend/` | FastAPI + LangGraph + ChromaDB | [HF Spaces](https://slveo-gaokao-api.hf.space) |
| Admin-SPA | `admin-spa/` | React 19 + Vite + Zustand | [CF Pages](https://zhaoshengzhinao.pages.dev) |
| Mini-App | `mini-app/` | Vue 3 + uni-app | [CF Pages](https://zhaoshengzhinao-mini-app.pages.dev) |
| File Distribution | `backend/distribution/` | FastAPI + APScheduler + 企业微信 | — (admin panel) |

External: Supabase (PostgreSQL), Upstash (Redis), DeepSeek (LLM).

## Deployment

- **CF Pages (admin-spa, mini-app):** Auto-deploys on `git push`. `VITE_*` env vars inlined at build time — "Retry deployment" after change.
- **HF Space (backend):** Own git repo at `https://huggingface.co/spaces/SlveO/gaokao_api`. Push to GitHub does NOT update it. Clone HF repo → copy `backend/` + `hf-space/Dockerfile` + `data/approved/` + `scripts/` → push.
- **Local:** `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`

Docs: `docs/ARCHITECTURE.md` | `docs/DEPLOYMENT.md` | `docs/OPERATIONS.md` | `docs/DEVELOPER.md` | `docs/EXECUTION_PLAN.md` | `docs/DEVELOPMENT_ROADMAP.md`

## Quick Start

```bash
cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
cd admin-spa && npm install && npm run dev -- --port 3001
cd mini-app && npm install && npm run dev:h5 -- --port 3002
```

Demo login: `admin` / `admin123` at `http://localhost:3001?tenant=scnu`

## Key Conventions

- API needs `X-Tenant: scnu` header (admin URLs: `?tenant=scnu`)
- Middleware: TenantResolution → UserAuth → ModuleGate (403 if module disabled)
- Backend lifespan: init_db → ensure_tenant → auto-import knowledge → seed+index → warmup
- Mini-app chat: raw `fetch` for SSE (not `api` wrapper — needs ReadableStream)
- Mini-app cross-tab: `uni.setStorageSync` (fallback) + `uni.$emit` (fast path)
- Auth: JWT Bearer, login via `/api/v1/auth/login`, guest sessions expire 1d
- File Distribution: channels (企业微信群机器人), scheduled tasks (APScheduler), webhook URLs encrypted at rest (Fernet)
- Testing: implementation and test code MUST be written by different sub-agent instances (HARD RULE); AAA pattern mandatory; LLM tests require mock/benchmark/snapshot layers; no PR merges without tests for new modules

See `.claude/rules/` for detailed guidance on agents, analytics, recommendations, testing, distribution.

## Consultation Module (咨询模块)

Dual-mode chat system: **consultation** (咨询) and **recommendation** (推荐), isolated by session ID prefix.

- **Session isolation**: `sess_consult_*` for consultation, `sess_recommend_*` (or plain `sess_*`) for recommendation. Prefix validated explicitly to prevent cross-module reuse (substring pitfall: `"sess_consult_x".startswith("sess_")` is True).
- **Consult SSE endpoint**: `POST /api/v1/consult/messages` — event sequence: `thinking → intent → admission_data → [search_start → source* → search_end] → token* → [validation → regeneration → token* → validation] → done`. SSE format: `data: {"type": "<event>", ...}\n\n` (no `event:` line; type embedded in JSON). Token events use `data.text` (not `content`).
- **Dual-layer retrieval**: SQL admission data (`consult_retrieval_service.query_admission_data`) + RAG vector retrieval (`search_similar` from `knowledge_base.chroma_client`).
- **Post-validation regeneration**: `consult_validator.validate_response` detects data mismatches; on failure + non-empty admission_rows, regenerate up to `consult_max_regeneration_attempts` times (config in `config.py`).
- **Context sharing**: `services/consult_context_service.build_consult_context` enriches recommendation prompts with consultation history (summary preferred, falls back to recent messages). B2B system prompt has `{consult_context}` placeholder. Recommend sessions auto-bind the user's most recent consult session via `context_ref_session_id` at creation time (registered users only).
- **Prompt management**: `api/routes/prompt_admin.py` provides CRUD with version control + dual-write (DB template + code constants in `agents/conversation/prompts_consult.py`). Lifespan checks `PROMPT_FILE_MAP` ↔ `CODE_DEFAULTS` consistency on startup.
- **Prompt loading**: `services/prompt_service.load_prompt(key, tenant_slug)` — DB first, code constant fallback.
- **Mini-app dual mode**: TabBar splits "AI 咨询" (`pages/consult/`, objective data Q&A via SSE) and "个性化推荐" (`pages/chat/`, WebSocket-based B2B recommendation). Consult session stored in `consultSession.ts` (key `scnu_consult_module_session_id`). Chat page shows a green "已结合咨询历史" indicator when a consult session exists.

## Project Files Index

| Directory / File | Purpose |
|---|---|
| `backend/api/routes/` | REST endpoints (auth, chat, miniapp, knowledge, distribution, admin, consult, prompt_admin) |
| `backend/services/` | Business logic (recommendation, chat, consult_context, consult_retrieval, consult_validator, prompt_service) |
| `backend/schemas/consult.py` | Consultation request/event payload schemas |
| `backend/agents/conversation/` | LangGraph conversation agent (B2B chat) |
| `backend/distribution/` | File distribution: channels, scheduling, WeChat bot |
| `backend/knowledge/` | Tenant-aware ChromaDB indexing |
| `backend/knowledge_base/` | Low-level ChromaDB client + embeddings |
| `backend/models/` | SQLAlchemy ORM models |
| `backend/core/` | Middleware (tenant, auth, module gate), event writer, guard chain |
| `backend/analytics/` | SQL aggregation queries per analytics module |
| `backend/tests/unit/` | Unit tests (pure logic, no I/O) |
| `backend/tests/integration/` | Integration tests (real DB, mock LLM) |
| `backend/tests/benchmarks/` | Accuracy benchmarks (ground truth datasets) |
| `backend/config.py` | Pydantic-settings env config |
| `admin-spa/src/api/` | Axios client + endpoint modules |
| `admin-spa/src/stores/` | Zustand stores (auth, mobile) |
| `admin-spa/src/components/` | Shared UI components |
| `admin-spa/src/pages/` | Analytics dashboard pages |
| `mini-app/src/pages/` | Student-facing pages (consult, chat, school, profile, recommendations) |
| `mini-app/src/stores/consult.ts` | Consult store: SSE streaming, session mgmt, validation state |
| `mini-app/src/utils/` | API client (uni.request), WebSocket manager, consultSession |
| `mini-app/tenants/` | Per-tenant build config (brand, features) |
| `docker/` | Dockerfiles + nginx config for Compose deploys |
| `hf-space/` | HF Spaces Dockerfile + README |
| `data/approved/` | Curated knowledge JSON |
| `data/seed/` | Seed data (schools, scores) |
| `scripts/` | Utility scripts (import, seed, monitor) |
| `docs/` | Architecture, deployment, operations, developer guides |
| `.github/workflows/` | CI: backend tests, frontend builds, lint |

## For Collaborators

See `docs/DEVELOPER.md` for the full onboarding guide.

## Write/Edit file operations (HARD RULE)

Write and Edit tools are UNSTABLE on DeepSeek models (Opus, Haiku). Use Bash heredoc for file creation:
```bash
cat > filepath << 'ENDOFFILE'
...content...
ENDOFFILE
```
For editing, use Bash sed or python3 string replace. Fallback: spawn `tool-writer` Sonnet sub-agent. Max 2 retries, then record to reports/block.md.
