# Key Conventions

- Default LLM is **DeepSeek** — configured via `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` env vars in `backend/config.py`
- All admin API requests require `X-Tenant` header. Mini-app student endpoints read `tenant_slug` from the request body instead
- CORS origins are listed in `backend/config.py` `cors_origins` — add new origins there
- Admin SPA Axios client (`admin-spa/src/api/client.ts`) auto-injects `X-Tenant` from URL query param or localStorage, plus `Authorization` Bearer token. 401 responses trigger immediate logout (no token refresh)
- Mini-app API client (`mini-app/src/utils/api.ts`) uses `uni.request` with automatic token refresh on 401
- Database engine is lazy-initialized via proxy pattern in `backend/models/__init__.py`
- `.env` file goes at repo root; `backend/.env` overrides for backend-specific settings
- Seed data JSON files are read from `$DATA_DIR` (defaults to `data/seed/`)
- Admin SPA pages use mock data as fallback when API calls fail — the UI degrades gracefully for demo purposes
