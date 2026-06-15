# File Distribution

File pushing to external channels (企业微信群机器人) with scheduled publishing.

## Module Structure

| File | Purpose |
|------|---------|
| `backend/distribution/models.py` | SQLAlchemy models: `DistributionChannel`, `DistributionFile`, `DistributionTask`, `DistributionLog`, `DistributionFileAccessToken` |
| `backend/distribution/router.py` | 21 REST endpoints under `/api/v1/distribution` |
| `backend/distribution/schemas.py` | Pydantic schemas with WeChat webhook URL validation |
| `backend/distribution/service.py` | Business logic |
| `backend/distribution/security.py` | Fernet encryption, file validation (MIME/extension/size), SHA-256 hashing, access tokens |
| `backend/distribution/scheduler.py` | APScheduler polling (every 30s) |
| `backend/distribution/wechat_service.py` | 企业微信群机器人 webhook client (text/markdown/file) |

## Channels

Only `wechat_group` type is currently supported:
- Webhook URL regex: `^https://qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=[a-f0-9\-]+$`
- URLs encrypted at rest with Fernet symmetric encryption
- Auth: channels are tenant-scoped, soft-deleted (`deleted_at` column)

## Scheduling

APScheduler polls every 30 seconds for due tasks. Schedule types:
- `once` — one-time
- `daily` — recurring daily
- `weekly` — recurring weekly
- `monthly` — recurring monthly

## WeChat Bot Flow

1. Send optional caption text via webhook
2. Upload file to WeChat `upload_media` API → get `media_id`
3. Send file message with returned `media_id`
4. Retry on failure: 1s → 5s → 25s (exponential backoff)

## File Storage

- Path pattern: `file_store/{tenant_id}/{YYYY}/{MM}/{filename}`
- File validation: MIME type whitelist, extension check, max 20 MB
- SHA-256 hash computed and stored for integrity verification
- Downloads gated by single-use access tokens with expiry

## Tenant Isolation

All queries are tenant-scoped. Soft deletes used throughout. Migration file: `backend/migrations/versions/005_distribution_tables.py`

## API Conventions

- All endpoints require `X-Tenant` header + JWT Bearer
- Response format follows admin API conventions (not mini-app unified format)
- Router mounted at `/api/v1/distribution` in `backend/main.py`
- Scheduler started in lifespan, shut down on app exit
