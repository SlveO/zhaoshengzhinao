# CLAUDE.md

B2B multi-tenant SaaS for Chinese university admissions ("招生智脑"). Three subsystems on free-tier infra.

**Active branch:** `feat/admin-redesign-v2`

## Architecture

| Subsystem | Directory | Stack | Production |
|-----------|-----------|-------|-------------|
| Backend API | `backend/` | FastAPI + LangGraph + ChromaDB | [HF Spaces](https://slveo-gaokao-api.hf.space) |
| Admin-SPA | `admin-spa/` | React 19 + Vite + Zustand | [CF Pages](https://zhaoshengzhinao.pages.dev) |
| Mini-App | `mini-app/` | Vue 3 + uni-app | [CF Pages](https://zhaoshengzhinao-mini-app.pages.dev) |

External: Supabase (PostgreSQL), Upstash (Redis), DeepSeek (LLM).

## Deployment

- **CF Pages (admin-spa, mini-app):** Auto-deploys on `git push`. `VITE_*` env vars inlined at build time — "Retry deployment" after change.
- **HF Space (backend):** Own git repo at `huggingface.co/spaces/SlveO/gaokao_api`. Push to GitHub does NOT update it. Clone HF repo → copy `backend/` + `hf-space/Dockerfile` + `data/approved/` + `scripts/` → push.
- **Local:** `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`

Docs: `docs/ARCHITECTURE.md` | `docs/DEPLOYMENT.md` | `docs/OPERATIONS.md`

## Quick Start

```bash
cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
cd admin-spa && npm install && npm run dev      # http://localhost:5173
cd mini-app && npm install && npm run dev:h5     # http://localhost:5174
```

## Key Conventions

- API needs `X-Tenant: scnu` header (admin URLs: `?tenant=scnu`)
- Middleware: TenantResolution → UserAuth → ModuleGate (403 if module disabled)
- Backend lifespan: init_db → ensure_tenant → auto-import knowledge → seed+index → warmup
- Mini-app chat: raw `fetch` for SSE (not `api` wrapper — needs ReadableStream)
- Mini-app cross-tab: `uni.setStorageSync` (fallback) + `uni.$emit` (fast path)
- Auth: JWT Bearer, login via `/api/v1/auth/login`, guest sessions expire 1d

See `.claude/rules/` for detailed guidance on agents, analytics, recommendations, testing.
