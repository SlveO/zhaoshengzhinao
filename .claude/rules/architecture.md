# Architecture

This is a **B2B multi-tenant SaaS** platform for Chinese university admissions ("招生智脑"). Three subsystems:

| System | Stack | Port | Audience |
|--------|-------|------|----------|
| backend | Python 3.11 / FastAPI / LangGraph | 8000 | API for admin + student apps |
| admin-spa | React 19 / TypeScript / Vite / Tailwind CSS 4 / ECharts | 3001 | University admissions staff |
| mini-app | Vue 3 / uni-app (H5 + 微信小程序) | 3002 | High school students |

Databases: PostgreSQL (primary), ChromaDB (vector search for college info), Redis (session state + rate limiting).

## Middleware chain (order matters)

`TenantResolutionMiddleware` → `UserAuthMiddleware` → `ModuleGateMiddleware`

All three use `ContextVar` context variables (`_current_tenant`, `_current_user`) set during request processing and consumed via FastAPI dependency injection (`get_current_tenant()`, `get_current_tenant_user()`).

**Tenant resolution**: Extracts `X-Tenant` header (or `?tenant=` query param for admin pages), resolves tenant from DB, stores in contextvar. Public paths (login, register, miniapp enter, chat) are exempt — mini-app routes read `tenant_slug` from the request body instead.

**Module gating**: Per-tenant feature flags stored in `tenant.config.modules` JSONB. Each analytics endpoint maps to a `ModuleKey` enum with optional dependencies enforced by `check_module_enabled()`.

## Tenant-aware ChromaDB

Each tenant has its own ChromaDB collection named `{tenant_slug}_colleges`. The `backend/knowledge/` module handles indexing tenant data (admission scores, majors) into vector embeddings. The old `backend/knowledge_base/` provides the global/historical ChromaDB client.
