# Mini-app Patterns

## Tenant config at build time

The mini-app is tenant-specific at build time. `TENANT=scnu node build.config.js` reads `mini-app/tenants/{TENANT}.json` and generates `src/tenant.config.ts` with brand colors, features, and app ID. Each tenant's mini-app is a separate build artifact.

## Chat: SSE + polling fallback

The chat page uses `fetch` + `ReadableStream` for SSE streaming from `/api/v1/chat/messages`. If no SSE data arrives within 8 seconds (HF Spaces proxy buffers SSE), it falls back to polling `/miniapp/enter` for the assistant's reply. A separate `wsManager` (WebSocket singleton in `mini-app/src/utils/websocket.ts`) handles real-time profile/stage updates.

## API response format

C-end mini-app API responses use unified format: `{"data": T | null, "error": {"code": string, "message": string} | null}` (helpers: `ok(data)`, `err(code, message)` in `backend/api/routes/miniapp.py`)
