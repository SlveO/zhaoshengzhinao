# Operations Runbook

> Last updated: 2026-05-23. Covers the Docker Compose deployment introduced in the infrastructure hardening pass.

## Daily Commands

```bash
docker compose ps
docker compose logs -f nginx backend
docker compose restart backend
docker compose pull
docker compose up -d --build
```

If the host uses legacy Docker Compose, use `docker-compose` for the same commands. Use the production overlay when operating production:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
# or
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

## Health Checks

```bash
curl http://localhost/api/health
docker compose exec db pg_isready -U gaokao -d gaokao
docker compose exec redis redis-cli ping
```

Expected results:

- API: `{"status":"ok"}`
- PostgreSQL: `accepting connections`
- Redis: `PONG`

## PostgreSQL Backup And Restore

Backup:

```bash
docker compose exec -T db pg_dump -U gaokao -d gaokao > backups/gaokao_$(date +%Y%m%d_%H%M%S).sql
```

Restore to an empty database:

```bash
docker compose exec -T db psql -U gaokao -d gaokao < backups/gaokao_latest.sql
```

Always stop write traffic or take a maintenance window before restoring.

## ChromaDB Reindex

For tenant data already imported into PostgreSQL:

```bash
docker compose exec backend python -m scripts.index_chroma
```

For SCNU tenant onboarding data, use the project import scripts from the repository docs and then trigger the admin reindex endpoint:

```bash
curl -X POST http://localhost/api/v1/admin/knowledge/reindex \
  -H "X-Tenant: scnu" \
  -H "Authorization: Bearer <token>"
```

## Logs

```bash
docker compose logs --tail=200 backend
docker compose logs --tail=200 nginx
docker compose logs --tail=200 db
docker compose logs --tail=200 redis
```

In production mode, JSON log files are rotated at 10 MB with 5 retained files.

## Release And Rollback

Release:

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
curl http://localhost/api/health
```

Rollback:

```bash
git checkout <previous-good-commit>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Restore database only if the release included an incompatible migration and a backup was taken immediately before deployment.

## Monitoring Signals

- API health latency and non-200 rates.
- WebSocket disconnect/error counts.
- PostgreSQL disk usage and slow queries.
- Redis memory usage and key eviction.
- ChromaDB volume size and query latency.
- Admin analytics empty-state rate after real traffic exists.
