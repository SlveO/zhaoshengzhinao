# Stage 1: Student Entry — Registered & Guest Dual-Mode Design (v3)

**Date**: 2026-05-30 | **Status**: approved
**Branch**: feat/admin-redesign-v2

## Problem

`data_pipeline_error.md` Stage 1 要求双入口（注册用户 30 天 TTL + 游客 1 天 TTL），当前实现将所有用户视为无 TTL 访客。

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| TTL 存储 | DB 列 `expires_at` | 不引入 Redis |
| TTL 续期 | 不续期 | 创建时设定，resume 不变 |
| 过期会话重建 | 生成新 `session_id` | 旧 ID 有 UNIQUE 约束，复用会 IntegrityError |
| JWT key | `"user_id"` | 与 `utils/jwt.py` 一致 |
| 用户来源 | 仅 JWT Header | 不在 `EnterRequest` 加字段（防客户端伪造）|
| 入口页 | chat 页面内 `v-if` overlay | 全屏覆盖 tabBar |
| `expires_at = NULL` | 永不过期 | 迁移遗漏数据安全网 |
| 迁移方式 | 新建 `006_add_session_ttl.py` | 追加已有迁移不会重新执行 |

## Data Model

### Migration: `backend/migrations/versions/006_add_session_ttl.py`

```python
def upgrade():
    op.add_column("consult_sessions", sa.Column(
        "expires_at", sa.DateTime(timezone=True), nullable=True,
        comment="会话过期时间，null=永不过期"
    ))
    # Backfill 现有游客会话
    op.execute("""
        UPDATE consult_sessions
        SET expires_at = created_at + INTERVAL '1 day'
        WHERE user_id IS NULL AND expires_at IS NULL
    """)
```

### Model: `backend/models/consult_session.py`

```python
expires_at = Column(DateTime(timezone=True), nullable=True,
                    comment="会话过期时间，null=永不过期")
```

## Service: `backend/services/consult_service.py`

```python
GUEST_TTL = timedelta(days=1)
REGISTERED_TTL = timedelta(days=30)


async def get_or_create_session(
    session_id: str | None, tenant_slug: str, user_id: UUID | None = None
) -> tuple[ConsultSession, bool]:

    async with async_session() as db:
        # 尝试恢复已有会话
        if session_id:
            stmt = select(ConsultSession).where(
                ConsultSession.session_id == session_id
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                now = datetime.now(timezone.utc)
                if existing.expires_at is None or existing.expires_at > now:
                    return existing, False
                # 过期 → 不复用旧 session_id（UNIQUE 约束），创建全新 ID

        # 创建新会话 — 始终生成新 ID 避免 UNIQUE 冲突
        new_id = f"sess_{uuid.uuid4().hex[:12]}"
        ttl = REGISTERED_TTL if user_id else GUEST_TTL
        expires_at = datetime.now(timezone.utc) + ttl
        new_session = ConsultSession(
            session_id=new_id, tenant_slug=tenant_slug,
            user_id=user_id, expires_at=expires_at,
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session, True
```

**关键修正**：过期时 `new_id` 永远是全新 UUID，不复用传入的 `session_id`。前端收到 `is_new=True` 后用新 `session_id` 覆盖本地存储。

## Route: `backend/api/routes/miniapp.py`

`/miniapp/enter` 开头加：

```python
from utils.jwt import decode_token

user_id = None
auth_header = request.headers.get("Authorization", "")
if auth_header.startswith("Bearer "):
    try:
        payload = decode_token(auth_header[7:])
        if payload:
            user_id = UUID(payload["user_id"])
    except Exception:
        pass
```

## Frontend: `mini-app/src/pages/chat/index.vue`

```
<template>
  <!-- 无有效 session：全屏入口选择 -->
  <view v-if="!hasSession" class="entry-overlay">
    <view class="entry-content">
      <text class="entry-title">AI 智能高考志愿咨询</text>
      <button @tap="handleRegister">注册 / 登录</button>
      <button @tap="handleGuest">访客模式</button>
      <text class="entry-hint">
        注册用户：对话记录保存 30 天 | 访客：保存 1 天
      </text>
    </view>
  </view>

  <!-- 有 session：正常聊天 -->
  <view v-else><!-- 现有聊天界面 --></view>

  <LoginModal :visible="showLogin" @close="showLogin=false" @success="onLoginSuccess" />
</template>
```

- `entry-overlay`: `position: fixed; z-index: 999;` 覆盖 tabBar
- `handleGuest`: 调 `/miniapp/enter`（无 Authorization）→ 保存新 `session_id` → `hasSession = true`
- `handleRegister`: 打开 `LoginModal`
- `onLoginSuccess`: 从 `userStore` 取 token → 调 `/miniapp/enter`（带 Authorization）→ 保存 session
- `onLoad`: 已有 session_id → 尝试 resume → 过期则前端清除旧 session_id 并显示入口选择

## Error Handling

| Scenario | Behavior |
|----------|----------|
| JWT 解析失败 | 按游客处理 |
| Session 过期 | 生成新 session_id，`is_new=True`，前端覆盖本地存储 |
| 过期会话 DB 残留 | 旧行保留，后续清理 job 处理 |
| DB 写入失败 | 返回 500 |
| `expires_at = NULL` | 永不过期 |

## Test Coverage

### Unit: `tests/unit/test_consult_service.py`

| Test | Expected |
|------|----------|
| `test_create_registered_session_30day_ttl` | user_id 存在 → expires_at ≈ +30d |
| `test_create_guest_session_1day_ttl` | user_id=None → expires_at ≈ +1d |
| `test_resume_valid_session_unchanged_ttl` | 未过期 → 返回原 session，expires_at 不变 |
| `test_expired_guest_session_triggers_new` | 过期 → 创建新 session，new_id ≠ old_id |
| `test_expired_session_does_not_reuse_session_id` | 过期重建 → session_id 是全新 UUID，非传入值 |
| `test_resume_does_not_extend_ttl` | resume 时 expires_at 不被修改 |

### Integration: `tests/integration/test_miniapp_pipeline.py`

| Test | Expected |
|------|----------|
| `test_enter_with_jwt_returns_30day_ttl` | POST + Bearer → expires_at ≈ +30d |
| `test_enter_without_jwt_returns_1day_ttl` | POST no auth → expires_at ≈ +1d |
| `test_expired_session_returns_new_session` | expired → is_new=True, session_id changed |

### E2E: `tests/e2e/test_student_journey.py`

| Test | Expected |
|------|----------|
| `test_entry_page_shows_when_no_session` | 首次访问 → 入口选择可见 |
| `test_guest_mode_enters_chat` | 点击"访客模式" → 聊天页面渲染 |
| `test_register_then_login_persists_session` | 注册→登录→enter→session 绑定用户 |

## Files Summary

| Layer | File | Action |
|-------|------|--------|
| Migration | `backend/migrations/versions/006_add_session_ttl.py` | **Create** |
| Model | `backend/models/consult_session.py` | Modify — +expires_at |
| Service | `backend/services/consult_service.py` | Modify — +user_id, +TTL, +expiry check, 过期强制新 ID |
| Route | `backend/api/routes/miniapp.py` | Modify — JWT optional parse |
| Frontend | `mini-app/src/pages/chat/index.vue` | Modify — entry selection overlay |
| Test | `backend/tests/unit/test_consult_service.py` | Modify — 6 TTL tests |
| Test | `backend/tests/integration/test_miniapp_pipeline.py` | Modify — 3 dual-mode tests |
| Test | `backend/tests/e2e/test_student_journey.py` | Modify — 3 entry UX tests |

**不修改**：`EnterRequest` schema、`LoginModal.vue`、`userStore`、`session.ts`、`pages.json`
