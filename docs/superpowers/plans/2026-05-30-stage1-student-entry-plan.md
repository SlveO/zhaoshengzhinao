# Stage 1: Student Entry Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development (recommended) to implement task-by-task. Steps use checkbox syntax for tracking. Each Task is self-contained with TDD.

**Goal:** Implement dual-mode student entry: registered users (30-day TTL) and guests (1-day TTL) with entry selection UI.

**Architecture:** Backend adds expires_at column + JWT-optional parsing in /miniapp/enter. Frontend adds conditional entry overlay on chat page. Session TTL set at creation only (no renewal). Expired sessions get fresh session_id (UNIQUE constraint safe).

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy / Alembic / Vue 3 / uni-app / JWT (python-jose)

**Spec:** docs/superpowers/specs/2026-05-30-stage1-student-entry-design.md

---

## New Session Launch Instruction

Copy everything below to a new Claude Code session. Execute Task 1 through Task 6 sequentially. Each task uses TDD.

> **Task:** Implement Stage 1 student dual-entry (registered + guest). Spec at docs/superpowers/specs/2026-05-30-stage1-student-entry-design.md
>
> **Constraints:** Do NOT modify EnterRequest schema, LoginModal.vue, userStore, session.ts, or pages.json.
> **Tools:** Agent (backend-dev, model: sonnet) for backend, Bash for verification.
> **TDD:** Write test first, verify it fails, then implement, then verify it passes.

---

### Task 1: Unit Tests (6 TTL tests)

**File:** Modify backend/tests/unit/test_consult_service.py

Add import at top: `from datetime import datetime, timedelta, timezone`

Add new class after existing tests:

```python
class TestSessionTTL:

    @pytest.mark.asyncio
    async def test_create_registered_session_30day_ttl(self):
        captured: dict = {}
        class FakeSession:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                for k, v in kwargs.items():
                    setattr(self, k, v)

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock()

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            with patch("services.consult_service.ConsultSession", FakeSession):
                session, is_new = await get_or_create_session(
                    None, "scnu", user_id=uuid.UUID("11111111-1111-1111-1111-111111111111")
                )
                assert is_new is True
                assert captured["user_id"] == uuid.UUID("11111111-1111-1111-1111-111111111111")
                now = datetime.now(timezone.utc)
                ttl = captured["expires_at"] - now
                assert timedelta(days=29) < ttl < timedelta(days=31)

    @pytest.mark.asyncio
    async def test_create_guest_session_1day_ttl(self):
        captured: dict = {}
        class FakeSession:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                for k, v in kwargs.items():
                    setattr(self, k, v)

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock()

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            with patch("services.consult_service.ConsultSession", FakeSession):
                session, is_new = await get_or_create_session(None, "scnu")
                assert is_new is True
                assert captured["user_id"] is None
                now = datetime.now(timezone.utc)
                ttl = captured["expires_at"] - now
                assert timedelta(hours=23) < ttl < timedelta(hours=25)

    @pytest.mark.asyncio
    async def test_resume_valid_session_unchanged_ttl(self):
        now = datetime.now(timezone.utc)
        existing = MagicMock()
        existing.session_id = "sess_abc"
        existing.expires_at = now + timedelta(hours=12)
        existing.tenant_slug = "scnu"

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            session, is_new = await get_or_create_session("sess_abc", "scnu")
            assert is_new is False
            assert session.session_id == "sess_abc"
            assert session.expires_at == existing.expires_at

    @pytest.mark.asyncio
    async def test_expired_guest_session_triggers_new(self):
        now = datetime.now(timezone.utc)
        old = MagicMock()
        old.session_id = "sess_old_guest"
        old.expires_at = now - timedelta(hours=1)

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mr = MagicMock()
        mr.scalar_one_or_none.return_value = old
        mock_db.execute = AsyncMock(return_value=mr)

        captured: dict = {}
        class FakeSession:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                for k, v in kwargs.items():
                    setattr(self, k, v)

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            with patch("services.consult_service.ConsultSession", FakeSession):
                with patch("uuid.uuid4") as mu:
                    mu.return_value.hex = "abc123def456"
                    session, is_new = await get_or_create_session("sess_old_guest", "scnu")
                    assert is_new is True
                    assert captured["session_id"] == "sess_abc123def456"
                    assert captured["session_id"] != "sess_old_guest"

    @pytest.mark.asyncio
    async def test_expired_session_does_not_reuse_session_id(self):
        now = datetime.now(timezone.utc)
        old = MagicMock()
        old.session_id = "sess_will_expire"
        old.expires_at = now - timedelta(days=2)

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mr = MagicMock()
        mr.scalar_one_or_none.return_value = old
        mock_db.execute = AsyncMock(return_value=mr)

        captured: dict = {}
        class FakeSession:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                for k, v in kwargs.items():
                    setattr(self, k, v)

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            with patch("services.consult_service.ConsultSession", FakeSession):
                with patch("uuid.uuid4") as mu:
                    mu.return_value.hex = "deadbeef1234"
                    session, is_new = await get_or_create_session("sess_will_expire", "scnu")
                    assert captured["session_id"] != "sess_will_expire"
                    assert captured["session_id"] == "sess_deadbeef1234"

    @pytest.mark.asyncio
    async def test_resume_does_not_extend_ttl(self):
        now = datetime.now(timezone.utc)
        orig = now + timedelta(hours=5)
        existing = MagicMock()
        existing.session_id = "sess_no_extend"
        existing.expires_at = orig

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mr = MagicMock()
        mr.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=mr)

        with patch("services.consult_service.async_session") as mas:
            mas.return_value.__aenter__.return_value = mock_db
            session, is_new = await get_or_create_session("sess_no_extend", "scnu")
            assert is_new is False
            assert session.expires_at == orig
```

Verify: `docker compose exec backend python -m pytest tests/unit/test_consult_service.py::TestSessionTTL -v --tb=short`
Expected: 6 FAILED (TypeError: user_id param not accepted yet)

---

### Task 2: Migration + Model + Service

#### 2.1 Create migration: backend/migrations/versions/006_add_session_ttl.py

```python
"""add session TTL

Revision ID: 006
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"

def upgrade():
    op.add_column("consult_sessions", sa.Column(
        "expires_at", sa.DateTime(timezone=True), nullable=True,
        comment="Session expiry: 1 day for guests, 30 days for registered, null = never expires"
    ))
    op.execute("""
        UPDATE consult_sessions
        SET expires_at = created_at + INTERVAL '1 day'
        WHERE user_id IS NULL AND expires_at IS NULL
    """)

def downgrade():
    op.drop_column("consult_sessions", "expires_at")
```

#### 2.2 Modify backend/models/consult_session.py

Add after the updated_at column (line 21):

```python
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Session expiry: null = never expires"
    )
```

#### 2.3 Replace backend/services/consult_service.py lines 1-33

```python
"""
C session consult service layer.
"""
import uuid
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from models import async_session
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage

GUEST_TTL = timedelta(days=1)
REGISTERED_TTL = timedelta(days=30)


async def get_or_create_session(
    session_id: str | None, tenant_slug: str, user_id: uuid.UUID | None = None
) -> tuple[ConsultSession, bool]:
    """Return (session, is_new). Expired sessions get a fresh session_id."""
    async with async_session() as db:
        if session_id:
            result = await db.execute(
                select(ConsultSession).where(ConsultSession.session_id == session_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                now = datetime.now(timezone.utc)
                if existing.expires_at is None or existing.expires_at > now:
                    await db.commit()
                    return existing, False

        # Always generate fresh ID to avoid UNIQUE constraint on expired rows
        new_id = f"sess_{uuid.uuid4().hex[:12]}"
        ttl = REGISTERED_TTL if user_id else GUEST_TTL
        expires_at = datetime.now(timezone.utc) + ttl
        new_session = ConsultSession(
            session_id=new_id,
            tenant_slug=tenant_slug,
            user_id=user_id,
            expires_at=expires_at,
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session, True


# Keep ALL functions below this line unchanged:
# get_session, update_session_profile, get_chat_history,
# save_message, extract_profile_from_message, build_profile_summary
```

Keep lines 36-113 (all other functions) unchanged.

#### 2.4 Verify

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m pytest tests/unit/test_consult_service.py::TestSessionTTL -v --tb=short
```
Expected: 6 PASSED

```bash
docker compose exec backend python -m pytest tests/unit/test_consult_service.py -q
```
Expected: all existing tests still pass

---

### Task 3: Route JWT Parsing

**File:** Modify backend/api/routes/miniapp.py

Add import after line 28 (`from core.event_writer import write_event`):
```python
from utils.jwt import decode_token
```

Replace lines 52-55:
```python
# BEFORE
    session, is_new = await get_or_create_session(body.session_id, tenant_slug)
    if is_new and tenant:
        try:
            await write_event(tenant.id, "chat_session_started", session_id=session.id)

# AFTER
    # Optional JWT parse: guest if absent or invalid
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            if payload:
                user_id = uuid.UUID(payload["user_id"])
        except Exception:
            pass

    session, is_new = await get_or_create_session(body.session_id, tenant_slug, user_id)
    if is_new and tenant:
        try:
            await write_event(
                tenant.id, "chat_session_started",
                session_id=session.id,
                payload={"user_id": str(user_id)} if user_id else None,
            )
```

Verify: `docker compose exec backend python -m pytest tests/integration/test_miniapp_pipeline.py -v --tb=short`

---

### Task 4: Integration Tests (3 dual-mode TTL tests)

**File:** Modify backend/tests/integration/test_miniapp_pipeline.py

Add at end:

```python
class TestDualModeSessionTTL:

    @pytest.mark.asyncio
    async def test_enter_without_jwt_creates_1day_ttl(self, async_client):
        resp = await async_client.post("/api/v1/miniapp/enter", json={"tenant_slug": "scnu"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_new_session"] is True
        assert data["session_id"].startswith("sess_")

        from services.consult_service import get_session
        from datetime import datetime, timedelta, timezone
        session = await get_session(data["session_id"])
        assert session is not None
        assert session.user_id is None
        now = datetime.now(timezone.utc)
        ttl = session.expires_at - now
        assert timedelta(hours=23) < ttl < timedelta(hours=25)

    @pytest.mark.asyncio
    async def test_enter_with_jwt_creates_30day_ttl(self, async_client):
        from utils.jwt import create_token
        token = create_token("11111111-1111-1111-1111-111111111111", "testuser", 60)

        resp = await async_client.post(
            "/api/v1/miniapp/enter",
            json={"tenant_slug": "scnu"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_new_session"] is True

        from services.consult_service import get_session
        from datetime import datetime, timedelta, timezone
        session = await get_session(data["session_id"])
        assert session is not None
        assert session.user_id is not None
        now = datetime.now(timezone.utc)
        ttl = session.expires_at - now
        assert timedelta(days=29) < ttl < timedelta(days=31)

    @pytest.mark.asyncio
    async def test_expired_session_returns_new(self, async_client):
        resp1 = await async_client.post("/api/v1/miniapp/enter", json={"tenant_slug": "scnu"})
        old_id = resp1.json()["data"]["session_id"]

        from services.consult_service import get_session
        from datetime import datetime, timedelta, timezone
        from models import async_session as dbs
        from sqlalchemy import update
        from models.consult_session import ConsultSession

        async with dbs() as db:
            await db.execute(
                update(ConsultSession)
                .where(ConsultSession.session_id == old_id)
                .values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
            )
            await db.commit()

        resp2 = await async_client.post("/api/v1/miniapp/enter", json={
            "session_id": old_id, "tenant_slug": "scnu",
        })
        data2 = resp2.json()["data"]
        assert data2["is_new_session"] is True
        assert data2["session_id"] != old_id
```

Verify: `docker compose exec backend python -m pytest tests/integration/test_miniapp_pipeline.py::TestDualModeSessionTTL -v --tb=short`
Expected: 3 PASSED

---

### Task 5: Frontend Entry Overlay

**File:** Modify mini-app/src/pages/chat/index.vue

#### 5.1 Add import at top of script

```typescript
import { getToken } from "@/utils/api"
```

#### 5.2 Replace the onLoad function

Replace the existing `onLoad` function (approximately lines 143-166) with the version that checks for stored session first, falls back to showing entry overlay. Add these state variables and functions:

```typescript
const hasSession = ref(false)
const showLogin = ref(false)
const showEntry = ref(true)

onLoad(async () => {
  const token = getToken()
  const stored = getStoredSessionId()

  if (stored) {
    try {
      const headers: Record<string, string> = {}
      if (token) headers["Authorization"] = `Bearer ${token}`

      const res = await api.post<any>("/miniapp/enter", {
        session_id: stored,
        tenant_slug: TENANT_SLUG,
      }, { headers })

      if (res.data) {
        sessionId.value = res.data.session_id
        saveSessionId(res.data.session_id)
        hasSession.value = true
        showEntry.value = false
        if (res.data.chat_history && res.data.chat_history.length) {
          messages.value = res.data.chat_history.map((m: any) => ({
            id: m.message_id || m.id,
            role: m.role,
            content: m.content,
            timestamp: new Date(m.created_at).getTime(),
          }))
        }
        return
      }
    } catch {
      clearStoredSessionId()
    }
  }
  showEntry.value = true
})

async function handleRegister(): Promise<void> {
  showLogin.value = true
}

async function handleGuest(): Promise<void> {
  try {
    const res = await api.post<any>("/miniapp/enter", {
      session_id: null,
      tenant_slug: TENANT_SLUG,
    })
    if (res.data) {
      sessionId.value = res.data.session_id
      saveSessionId(res.data.session_id)
      hasSession.value = true
      showEntry.value = false
    }
  } catch {
    showEntry.value = false
    hasSession.value = true
  }
}

async function onLoginSuccess(): Promise<void> {
  showLogin.value = false
  const token = getToken()
  try {
    const headers: Record<string, string> = {}
    if (token) headers["Authorization"] = `Bearer ${token}`

    const res = await api.post<any>("/miniapp/enter", {
      session_id: null,
      tenant_slug: TENANT_SLUG,
    }, { headers })

    if (res.data) {
      sessionId.value = res.data.session_id
      saveSessionId(res.data.session_id)
      hasSession.value = true
      showEntry.value = false
    }
  } catch {
    showEntry.value = false
    hasSession.value = true
  }
}
```

#### 5.3 Add entry overlay in template

Wrap existing template. The root `<template>` becomes:

```html
<template>
  <view v-if="showEntry" class="entry-overlay">
    <view class="entry-card">
      <text class="entry-title">招生智脑</text>
      <text class="entry-subtitle">AI 智能高考志愿咨询</text>
      <view class="entry-buttons">
        <button class="entry-btn entry-btn-primary" @tap="handleRegister">
          注册 / 登录
        </button>
        <button class="entry-btn entry-btn-secondary" @tap="handleGuest">
          访客模式
        </button>
      </view>
      <text class="entry-hint">注册用户：对话记录保存 30 天 | 访客：保存 1 天</text>
    </view>
  </view>

  <view v-else class="chat-page">
    <!-- ALL existing chat template content goes here, unchanged -->
  </view>

  <LoginModal :visible="showLogin" @close="showLogin = false" @success="onLoginSuccess" />
</template>
```

Important: Move ALL existing template content inside `<view v-else class="chat-page">`.

#### 5.4 Add overlay CSS at end of style block

```css
.entry-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.entry-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px 32px;
  margin: 0 32px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.entry-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  display: block;
  margin-bottom: 8px;
}

.entry-subtitle {
  font-size: 16px;
  color: #666;
  display: block;
  margin-bottom: 32px;
}

.entry-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.entry-btn {
  width: 100%;
  height: 48px;
  border-radius: 24px;
  font-size: 16px;
  font-weight: 600;
  line-height: 48px;
  border: none;
}

.entry-btn-primary {
  background: #667eea;
  color: #fff;
}

.entry-btn-secondary {
  background: #f0f0f5;
  color: #333;
}

.entry-hint {
  font-size: 12px;
  color: #999;
  margin-top: 24px;
  display: block;
}
```

---

### Task 6: E2E Test (3 entry UX tests)

**File:** Modify backend/tests/e2e/test_student_journey.py

Add at end:

```python
class TestEntryFlow:

    def test_entry_page_shows_when_no_session(self, page: Page):
        page.goto("http://nginx/", wait_until="networkidle", timeout=15000)
        assert page.locator(".entry-title").is_visible(timeout=5000)
        assert page.locator("text=访客模式").is_visible()

    def test_guest_mode_enters_chat(self, page: Page):
        page.goto("http://nginx/", wait_until="networkidle", timeout=15000)
        page.locator("text=访客模式").click(timeout=5000)
        page.wait_for_timeout(3000)
        assert not page.locator(".entry-overlay").is_visible()

    def test_register_login_shows_modal(self, page: Page):
        page.goto("http://nginx/", wait_until="networkidle", timeout=15000)
        page.locator("text=注册").click(timeout=5000)
        page.wait_for_timeout(2000)
        assert page.locator("input[placeholder*='手机'], input[placeholder*='用户']").is_visible(timeout=3000)
```

Verify: `docker compose exec backend python -m pytest tests/e2e/test_student_journey.py::TestEntryFlow -v --tb=short`

---

## Full Regression

```bash
docker compose exec backend python -m pytest tests/unit/test_consult_service.py -q
docker compose exec backend python -m pytest tests/integration/test_miniapp_pipeline.py -q
docker compose exec backend python -m pytest tests/ -q
```

Expected: all tests pass.
