# Code Style

## Python (backend/)

- Follow PEP 8 — enforced by `ruff check backend/`
- Use type hints for all function signatures
- Async/await for all database and API calls
- Use Pydantic models for request/response schemas
- Use `ContextVar` dependency injection (`get_current_tenant()`, `get_current_tenant_user()`), never pass tenant/user manually
- Event logging: always wrap in try/except, never let logging failures block the main flow
- LLM calls: always include retry logic (min 2 attempts with exponential backoff)
- Database queries: use SQLAlchemy async session, never raw SQL unless in analytics aggregation files (`backend/analytics/`)

## TypeScript/React (admin-spa/)

- Strict TypeScript — no `any` without explicit justification
- Prefer functional components with hooks, no class components
- Use Tailwind CSS 4 utility classes for all styling
- API calls through `admin-spa/src/api/client.ts` — never raw `fetch` or `axios.create()`
- Always handle loading, error, and empty states in components
- ECharts: use the project's chart wrapper pattern, don't instantiate ECharts directly

## Vue (mini-app/)

- Vue 3 Composition API with `<script setup>` syntax
- Use `uni.request` (from `mini-app/src/utils/api.ts`) — never raw `fetch`
- Handle SSE buffer issues: always include 8s polling fallback
- Tenant config values from `src/tenant.config.ts` (generated), never hardcoded
- Test on H5 first, then verify on 微信小程序 before deploy

## General

- No commented-out code in commits — delete it
- No emojis in code or commit messages unless user explicitly requests
- Commit messages: focus on WHY, not WHAT
- File names: kebab-case for config/docs, snake_case for Python, PascalCase for React components, camelCase for Vue components
