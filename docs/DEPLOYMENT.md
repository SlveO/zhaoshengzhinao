# Deployment Guide

> Last updated: 2026-05-23. This guide covers the current hardened demo deployment. Phase 5 data expansion is not part of this deployment pass.

## Local Docker Compose

1. Create an environment file from the example:

```bash
cp .env.example .env
```

2. Set required secrets in `.env`:

```bash
JWT_SECRET=replace-with-a-long-random-secret
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

3. Build and start all services. Prefer Docker Compose v2; if the host only has the legacy binary, replace `docker compose` with `docker-compose`.

```bash
docker compose up -d --build
# or
docker-compose up -d --build
```

4. Verify health:

```bash
curl http://localhost/api/health
```

Expected response:

```json
{"status":"ok"}
```

5. Open the apps:

- Student H5: `http://localhost/`
- Admin SPA: `http://localhost/admin/?tenant=scnu`

## Services

| Service | Purpose | Internal port |
|---------|---------|---------------|
| `db` | PostgreSQL 16 data store | 5432 |
| `redis` | Dialog/session cache | 6379 |
| `backend` | FastAPI API + WebSocket | 8000 |
| `admin-spa` | Built React admin static app | 80 |
| `mini-app` | Built uni-app H5 static app | 80 |
| `nginx` | Public reverse proxy | 80 |

## Production Checklist

- Set `JWT_SECRET` and `DEEPSEEK_API_KEY` from a secret manager or protected `.env`.
- Run with the production override:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# or
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

- Put TLS in front of nginx using your cloud load balancer, CDN, or a host-level reverse proxy.
- Back up the `postgres_data` volume before each release.
- Keep `chroma_data` and `uploads` volumes persistent.
- Confirm admin and student apps load after a hard refresh on nested routes.

## HTTPS Notes

The bundled nginx config listens on plain HTTP because TLS termination varies by host. For direct VM deployment, terminate HTTPS with a host-level nginx/Caddy/Traefik proxy and forward to `127.0.0.1:80`.

Required proxy headers:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

WebSocket paths are under `/api/`, so the outer proxy must preserve `Upgrade` and `Connection` headers.

## Common Issues

- `MISSING_TENANT`: add `?tenant=scnu` to admin URLs or send `X-Tenant: scnu` in API calls.
- Backend cannot connect to database: verify `db` is healthy and `DATABASE_URL` uses host `db` inside Compose.
- Student chat connects but AI fails: verify `DEEPSEEK_API_KEY`, base URL, and model.
- Admin route refresh 404: rebuild `admin-spa`; Docker build sets `VITE_BASE_PATH=/admin/`.
