# Plan 2: Data Presentation Standardization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-standardize every admin-spa page per spec §四: delete 5 pages, rewrite 2 pages (Dashboard / Consultations), fix 2 pages (ProfileDashboard / Insights), hide distribution entries, remove module gate, plus backend changes (consult_sessions 8 fields, subject_type→subjects rename, consult summary service, consultation workbench APIs, mini-app pre-chat form, profile-dashboard API enhancement).

**Architecture:** Backend-first (Tasks 1-7), then mini-app (Task 8), then admin-spa cleanup (Task 9), then admin-spa page rewrites (Tasks 10-13), finally verification (Task 14).

**Tech Stack:** FastAPI + SQLAlchemy + LangGraph (backend), Vue 3 + uni-app (mini-app), React 19 + Vite + ECharts (admin-spa)

**Spec reference:** [docs/superpowers/specs/admin_data_overhaul_spec.md](file:///d:/_Greatest_programmer/_Projects/gaokao_agents/docs/superpowers/specs/admin_data_overhaul_spec.md) §四

**Prerequisites:** Plan 1 (mock cleanup) and Plan 4 (DB admin panel) should be merged first. Plan 4 already added `users.rank` + `DEV_ADMIN_USERNAME` + `is_developer` JWT claim. Plan 2 adds `consult_sessions` fields and rewrites pages.

**Key facts discovered during planning:**
- `User` model: `region` / `subjects` / `score` already exist (Plan 4 added `rank`)
- `ConsultSession` model: has `subject_type` (will deprecate), needs 8 new fields
- `subject_type` references in backend: `consult_session.py`, `consult_service.py` (lines 68, 106-110, 136, 141), `cend_profile_analyzer.py` (lines 68, 102, 131, 169-170, 293-295, 375), `profile_bridge.py` (lines 85-86, 211, 248-249), `miniapp.py` (line 207)
- `subject_type` references in mini-app: `compare/index.vue:40,150`, `recommendations/index.vue:35,156`, `chat/index.vue:44`, `profile/index.vue:57,106,161`
- Tests with `subject_type` in benchmarks and unit tests need updating
- `analytics/profile_dashboard.py` has `get_profile_dashboard(tenant_id, days)` returning `riasecDistribution` / `valuesDistribution` / `completenessBreakdown` / `totalProfiles`
- `analytics/router.py` uses `_require(ModuleKey)` dependency for module gating — Plan 2 keeps the dep functions but they'll be no-ops after Plan removes the gate (or simply: `_require` stays, ModuleGate middleware removed)
- Admin SPA Sidebar uses `MENU_ITEMS` array with `module` field — needs cleanup + distribution hidden
- DashboardPage uses `MOCK` constant — full rewrite needed

---

## File Structure

### New files

| File | Responsibility |
|---|---|
| `backend/migrations/versions/007_consult_workbench.py` | Migration: add 8 fields to consult_sessions + backfill consult_started_at |
| `backend/services/consult_summary_service.py` | Trigger-based LLM summary generation |
| `backend/api/routes/consult_workbench.py` | 5 admin consultation workbench APIs |
| `mini-app/src/pages/chat/PreForm.vue` | Pre-chat basic info form component |

### Modified files

| File | Modification |
|---|---|
| `backend/models/consult_session.py` | Add 8 fields; keep `subject_type` (deprecated, not read) |
| `backend/services/consult_service.py` | `update_session_profile` keys: subject_type→subjects, add rank; `extract_profile_from_message` remove province/subject_type/score extraction; `build_profile_summary` use subjects; `save_message` write consult_started_at; `get_or_create_session` snapshot from users table |
| `backend/services/cend_profile_analyzer.py` | LLM prompt: remove subject_type/score/province fields; keep intent_majors/focus_points |
| `backend/services/profile_bridge.py` | Remove subject_type assignments in consult_updates |
| `backend/api/routes/miniapp.py` | Add `PUT /api/v1/miniapp/profile/basic`; session creation reads users snapshot; trigger consult summary after SSE done; subject_type→subjects in slots_text |
| `backend/analytics/profile_dashboard.py` | Add `monthlyNew`, `growthRate`, `todayNewSessions`, `pendingFollowSessions` |
| `backend/main.py` | Register `consult_workbench.router` |
| `backend/core/middleware.py` | Remove `ModuleGateMiddleware` (or make it pass-through) |
| `admin-spa/src/components/Sidebar.tsx` | Remove /leads /channels /reports /brand /modules + hide distribution 3; rename "咨询管理" to "咨询工作台" |
| `admin-spa/src/App.tsx` | Remove 5 routes (leads/channels/reports/brand/modules) |
| `admin-spa/src/pages/DashboardPage.tsx` | Full rewrite — no mock, use real APIs |
| `admin-spa/src/pages/ConsultationsPage.tsx` | Full rewrite — 7-col table + filter + drawer + follow actions |
| `admin-spa/src/pages/ProfileDashboardPage.tsx` | Remove mock fallback + hardcoded percentages + radar→Top3 cards |
| `admin-spa/src/pages/InsightsPage.tsx` | Remove emotion timeline + mock fallback (3→2 APIs) |
| `mini-app/src/pages/chat/index.vue` | subject_type→subjects; add PreForm gate before chat |
| `mini-app/src/pages/profile/index.vue` | subject_type→subjects |
| `mini-app/src/pages/recommendations/index.vue` | subject_type→subjects |
| `mini-app/src/pages/compare/index.vue` | subject_type→subjects |

### Deleted files

| File | Reason |
|---|---|
| `admin-spa/src/pages/LeadWorkbenchPage.tsx` | Merged into ConsultationsPage |
| `admin-spa/src/pages/ChannelsPage.tsx` | No backend support |
| `admin-spa/src/pages/ReportsPage.tsx` | All mock |
| `admin-spa/src/pages/ModuleSettingsPage.tsx` | Module gate removed |
| `admin-spa/src/pages/BrandSettingsPage.tsx` | Per user decision |

---

## Task 1: Backend — migration for consult_sessions 8 new fields

**Files:**
- Modify: `backend/models/consult_session.py`
- Create: `backend/migrations/versions/007_consult_workbench.py`

- [ ] **Step 1: Add 8 fields to ConsultSession model**

Edit `backend/models/consult_session.py` — after `subject_type` line add:
```python
    subjects: Mapped[str] = mapped_column(String(20), default="")
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consult_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    consult_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    follow_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    follow_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    followed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    followed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
```

Add `Text` to the sqlalchemy import line at top:
```python
from sqlalchemy import String, Integer, DateTime, Text, func
```

- [ ] **Step 2: Create migration**

Create `backend/migrations/versions/007_consult_workbench.py`:
```python
"""consult workbench: add 8 fields + backfill consult_started_at

Revision ID: 007_consult_workbench
Revises: 006_db_admin_panel
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa


revision = "007_consult_workbench"
down_revision = "006_db_admin_panel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consult_sessions", sa.Column("subjects", sa.String(20), server_default="", nullable=False))
    op.add_column("consult_sessions", sa.Column("rank", sa.Integer(), nullable=True))
    op.add_column("consult_sessions", sa.Column("consult_summary", sa.Text(), nullable=True))
    op.add_column("consult_sessions", sa.Column("consult_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consult_sessions", sa.Column("follow_status", sa.String(20), server_default="pending", nullable=False))
    op.add_column("consult_sessions", sa.Column("follow_note", sa.Text(), nullable=True))
    op.add_column("consult_sessions", sa.Column("followed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consult_sessions", sa.Column("followed_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))

    # Backfill consult_started_at from first user message
    op.execute("""
        UPDATE consult_sessions cs
        SET consult_started_at = (
          SELECT MIN(created_at) FROM chat_messages cm
          WHERE cm.session_id = cs.session_id AND cm.role = 'user'
        )
        WHERE cs.consult_started_at IS NULL
          AND EXISTS (
            SELECT 1 FROM chat_messages cm
            WHERE cm.session_id = cs.session_id AND cm.role = 'user'
          )
    """)


def downgrade() -> None:
    for col in ["followed_by", "followed_at", "follow_note", "follow_status",
                "consult_started_at", "consult_summary", "rank", "subjects"]:
        op.drop_column("consult_sessions", col)
```

- [ ] **Step 3: Apply migration**

```bash
cd backend && alembic upgrade head
```
Expected: `Running upgrade 006_db_admin_panel -> 007_consult_workbench`

- [ ] **Step 4: Verify fields exist**

```bash
cd backend && python -c "import asyncio; from models import async_session; from sqlalchemy import text; asyncio.run((lambda: (async_session()().__aenter__().then(lambda db: db.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='consult_sessions' ORDER BY ordinal_position\")))))())" 2>&1 | head
```
Simpler: just run alembic and check no error.

- [ ] **Step 5: Commit**

```bash
git add backend/models/consult_session.py backend/migrations/versions/007_consult_workbench.py
git commit -m "feat(backend): add 8 fields to consult_sessions + backfill consult_started_at"
```

---

## Task 2: Backend — subject_type → subjects rename + remove AI basic-info extraction

**Files:**
- Modify: `backend/services/consult_service.py`
- Modify: `backend/services/cend_profile_analyzer.py`
- Modify: `backend/services/profile_bridge.py`

- [ ] **Step 1: Update `consult_service.py`**

Edit `backend/services/consult_service.py`:

In `update_session_profile` change the key tuple:
```python
            for key in ("province", "subjects", "rank", "score", "intent_majors", "focus_points", "consult_stage"):
```

In `extract_profile_from_message`: **REMOVE** all province/subject_type/score extraction logic. The function should only extract `intent_majors` (and `focus_points` if desired). Replace the entire function with:
```python
async def extract_profile_from_message(user_content: str, ai_response: str, existing_profile: dict) -> dict:
    """Extract intent majors only. Province/subjects/score/rank come from student form."""
    updates = {}
    text = user_content + " " + ai_response
    if not existing_profile.get("intent_majors"):
        major_keywords = [
            "计算机", "人工智能", "软件工程", "数据科学", "网络安全", "大数据",
            "电子信息", "通信工程", "自动化", "电气工程", "微电子",
            "机械", "土木", "建筑", "材料", "环境",
            "临床医学", "口腔医学", "药学", "护理",
            "法学", "经济学", "金融", "会计", "工商管理", "国际贸易",
            "数学", "物理", "化学", "生物", "地理",
            "中文", "英语", "日语", "新闻", "历史", "哲学",
            "师范", "教育", "心理", "体育",
        ]
        found = []
        for kw in major_keywords:
            if kw in text:
                found.append(kw)
        if found:
            updates["intent_majors"] = found[:5]
    return updates
```

In `build_profile_summary` replace `subject_type` with `subjects`:
```python
def build_profile_summary(session: ConsultSession) -> dict | None:
    has_any = any([session.province, session.subjects, session.score, session.intent_majors])
    if not has_any:
        return None
    return {
        "province": session.province or None,
        "subjects": session.subjects or None,
        "score": session.score or None,
        "rank": session.rank or None,
        "intent_majors": session.intent_majors or [],
        "focus_points": session.focus_points or [],
    }
```

In `save_message` add consult_started_at write — replace function with:
```python
async def save_message(session_id: str, role: str, content: str) -> dict:
    async with async_session() as db:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        db.add(msg)
        # When user sends first message, record consult_started_at
        if role == "user":
            result = await db.execute(
                select(ConsultSession).where(ConsultSession.session_id == session_id)
            )
            session = result.scalar_one_or_none()
            if session and session.consult_started_at is None:
                session.consult_started_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(msg)
        return {"message_id": str(msg.id), "role": msg.role, "content": msg.content, "created_at": msg.created_at.isoformat()}
```

In `get_or_create_session`: when creating a new session for a registered user, snapshot basic info from users table. Replace the `new_session = ConsultSession(...)` block with:
```python
        # Snapshot basic info from users table for registered users
        province = ""
        subjects = ""
        score = 0
        rank = None
        if user_id:
            from models.user import User
            user_result = await db.execute(select(User).where(User.id == user_id))
            u = user_result.scalar_one_or_none()
            if u:
                province = u.region or ""
                subjects = u.subjects or ""
                score = u.score or 0
                rank = u.rank

        new_session = ConsultSession(
            session_id=new_id,
            tenant_slug=tenant_slug,
            user_id=user_id,
            province=province,
            subjects=subjects,
            score=score,
            rank=rank,
            expires_at=expires_at,
        )
```

Note: the `db` variable in `get_or_create_session` is from `async with async_session() as db:` — already in scope.

- [ ] **Step 2: Update `cend_profile_analyzer.py`**

Edit `backend/services/cend_profile_analyzer.py`:

In the LLM prompt template (line ~68), remove `subject_type` / `score` / `province` from the basic field spec. Replace the basic field docstring with:
```python
    "basic": "意向专业 (intent_majors list of strings), 关注点 (focus_points list of strings)",
```

In the `ProfileBasic` dataclass (line ~102), remove province/subject_type/score fields:
```python
@dataclass
class ProfileBasic:
    intent_majors: list = field(default_factory=list)
    focus_points: list = field(default_factory=list)
```

In `_has_basic` (line ~131), update:
```python
        if basic.get("intent_majors") or basic.get("focus_points"):
```

In `_build_summary` (line ~169), remove subject_type part:
```python
        if basic.get("intent_majors"):
            parts.append(f"意向: {', '.join(basic['intent_majors'])}")
```

In the extraction parser (line ~293), remove `subject_type = basic_raw.get("subject_type")` block entirely.

In the merge function (line ~375), remove `subject_type` line:
```python
    merged.basic["intent_majors"] = list(set((new_extraction.basic.get("intent_majors") or []) + (existing.basic.get("intent_majors") or [])))
    merged.basic["focus_points"] = list(set((new_extraction.basic.get("focus_points") or []) + (existing.basic.get("focus_points") or [])))
```

- [ ] **Step 3: Update `profile_bridge.py`**

Edit `backend/services/profile_bridge.py`:

In `_merge_basic` (line ~85), remove subject_type block:
```python
        # (remove lines 85-86: if basic.get("subject_type"): result.basic["subject_type"] = basic["subject_type"])
        if basic.get("intent_majors"):
            result.basic["intent_majors"] = basic["intent_majors"]
        if basic.get("focus_points"):
            result.basic["focus_points"] = basic["focus_points"]
```

In `_apply_to_session` (line ~248), remove subject_type assignment:
```python
        # (remove lines 248-249: if basic.get("subject_type"): consult_updates["subject_type"] = basic["subject_type"])
        if basic.get("intent_majors"):
            consult_updates["intent_majors"] = basic["intent_majors"]
        if basic.get("focus_points"):
            consult_updates["focus_points"] = basic["focus_points"]
```

Update the docstring at line 211 to reflect new fields.

- [ ] **Step 4: Smoke test backend startup**

Restart backend. Confirm no import errors. Test a chat message still works:
```bash
# Get a student token first by registering
$resp = Invoke-RestMethod -Uri http://localhost:8000/api/v1/auth/register -Method Post -ContentType "application/json" -Body '{"username":"test_subj_001","password":"pass123"}'
$token = $resp.access_token
# Enter session
$enter = Invoke-RestMethod -Uri http://localhost:8000/api/v1/miniapp/enter -Method Post -ContentType "application/json" -Body '{"tenant_slug":"scnu","session_id":null}' -Headers @{Authorization="Bearer $token"}
$sessionId = $enter.data.session_id
```
Expected: session created, no errors in backend log.

- [ ] **Step 5: Commit**

```bash
git add backend/services/consult_service.py backend/services/cend_profile_analyzer.py backend/services/profile_bridge.py
git commit -m "refactor(backend): subject_type->subjects, remove AI basic-info extraction"
```

---

## Task 3: Backend — consult_summary_service + trigger in miniapp

**Files:**
- Create: `backend/services/consult_summary_service.py`
- Modify: `backend/api/routes/miniapp.py`

- [ ] **Step 1: Create summary service**

Create `backend/services/consult_summary_service.py`:
```python
"""Trigger-based LLM consult summary generation."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select, func
from models import async_session
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage


async def _count_user_messages(session_id: str) -> int:
    async with async_session() as db:
        result = await db.execute(
            select(func.count()).select_from(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.role == "user")
        )
        return result.scalar() or 0


async def _get_recent_messages(session_id: str, limit: int = 8) -> list[dict]:
    async with async_session() as db:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        msgs = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in msgs]


async def generate_summary(session_id: str) -> str:
    """Generate a 30-char summary of the consult session. Falls back to first user message truncated."""
    msgs = await _get_recent_messages(session_id, limit=8)
    if not msgs:
        return ""

    user_msgs = [m for m in msgs if m["role"] == "user"]
    if not user_msgs:
        return ""

    fallback = user_msgs[0]["content"][:30]

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        from config import settings

        llm = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.3,
        )
        conversation_text = "\n".join(f"{m['role']}: {m['content']}" for m in msgs)
        sys = SystemMessage(content="你是咨询摘要助手。用30字以内总结学生本次咨询的核心问题，例如：'计算机专业就业前景与转专业政策咨询'。直接输出总结内容，不加任何前缀。")
        hum = HumanMessage(content=f"对话内容：\n{conversation_text}\n\n请总结：")
        resp = await llm.ainvoke([sys, hum])
        summary = (resp.content or "").strip()[:30]
        return summary or fallback
    except Exception as e:
        logging.warning(f"Summary LLM failed for session={session_id}: {e}")
        return fallback


async def maybe_generate_summary(session_id: str) -> None:
    """Trigger summary if: first time (≥4 user msgs and consult_summary is None) or refresh (≥2 new user msgs since last summary).

    Heuristic: we store a marker in consult_summary — if it's None and user_msgs ≥ 4, generate. If it exists and user_msgs grew by 2 since last generation, regenerate. For simplicity, we regenerate when user_msgs % 2 == 0 and user_msgs >= 4, capped at every 2 new messages.
    """
    async with async_session() as db:
        result = await db.execute(
            select(ConsultSession).where(ConsultSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return

        user_count = await _count_user_messages(session_id)
        if user_count < 4:
            return

        # Regenerate every 2 new messages after the first summary
        if session.consult_summary is None:
            should_gen = True
        elif user_count % 2 == 0:
            should_gen = True
        else:
            should_gen = False

        if not should_gen:
            return

        summary = await generate_summary(session_id)
        if summary:
            session.consult_summary = summary
            await db.commit()
            logging.info(f"Summary updated for session={session_id}: {summary}")
```

- [ ] **Step 2: Trigger summary after SSE completes**

Edit `backend/api/routes/miniapp.py` — in `send_chat_message`'s `event_stream()` generator, after the `done_data` yield (the `yield f"data: {json.dumps(done_data)}\n\n"` line), add before the event write:
```python
        # Trigger consult summary generation (async, non-blocking)
        try:
            from services.consult_summary_service import maybe_generate_summary
            asyncio.create_task(maybe_generate_summary(body.session_id))
        except Exception as e:
            logging.warning(f"Summary trigger failed for session={body.session_id}: {e}")
```

Also update `slots_text` to use `subjects` instead of `subject_type`:
```python
    slots_text = (
        f"省份: {existing_profile.get('province', '未知')}, "
        f"选科: {existing_profile.get('subjects', '未知')}, "
        f"分数: {existing_profile.get('score', '未知')}, "
        f"位次: {existing_profile.get('rank', '未知')}"
    )
```

And in the `existing_dict` fallback extraction setup, use `subjects`:
```python
        existing_dict = {
            "province": session.province or "",
            "subjects": session.subjects or "",
            "score": session.score or 0,
        }
```

- [ ] **Step 3: Smoke test summary generation**

Send 4+ user messages in a chat session. Wait ~10s. Query DB:
```bash
cd backend && python -c "import asyncio; from models import async_session; from models.consult_session import ConsultSession; from sqlalchemy import select
async def m():
    async with async_session() as db:
        r = await db.execute(select(ConsultSession).order_by(ConsultSession.created_at.desc()).limit(1))
        s = r.scalar_one_or_none()
        print(f'summary={s.consult_summary!r}, started_at={s.consult_started_at}')
asyncio.run(m())"
```
Expected: `consult_summary` is non-empty (or fallback first message), `consult_started_at` is set.

- [ ] **Step 4: Commit**

```bash
git add backend/services/consult_summary_service.py backend/api/routes/miniapp.py
git commit -m "feat(backend): trigger-based consult summary service + subjects rename in miniapp"
```

---

## Task 4: Backend — consultation workbench API (5 endpoints)

**Files:**
- Create: `backend/api/routes/consult_workbench.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create router with 5 endpoints**

Create `backend/api/routes/consult_workbench.py`:
```python
"""Admin consultation workbench — list, detail, follow status, regenerate summary."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.tenant_context import get_current_tenant, get_current_tenant_user
from models import get_db
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage
from models.user import User

router = APIRouter()


@router.get("/consultations")
async def list_consultations(
    status: Optional[str] = Query(None),
    period: Optional[str] = Query(None),  # today / 7d / 30d
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """List consultation sessions for the current tenant."""
    stmt = select(ConsultSession).where(ConsultSession.tenant_slug == tenant.slug)

    # Status filter
    if status == "pending":
        stmt = stmt.where(ConsultSession.follow_status == "pending")
    elif status == "processed":
        stmt = stmt.where(ConsultSession.follow_status == "processed")
    elif status == "ignored":
        stmt = stmt.where(ConsultSession.follow_status == "ignored")
    elif status == "no_consult":
        stmt = stmt.where(ConsultSession.consult_started_at.is_(None))

    # Period filter
    if period == "today":
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = stmt.where(ConsultSession.consult_started_at >= start)
    elif period == "7d":
        stmt = stmt.where(ConsultSession.consult_started_at >= datetime.now(timezone.utc) - timedelta(days=7))
    elif period == "30d":
        stmt = stmt.where(ConsultSession.consult_started_at >= datetime.now(timezone.utc) - timedelta(days=30))

    # Search: match username or consult_summary
    if search:
        # Join users for username search
        stmt = stmt.outerjoin(User, ConsultSession.user_id == User.id)
        stmt = stmt.where(
            or_(
                User.username.ilike(f"%{search}%"),
                ConsultSession.consult_summary.ilike(f"%{search}%"),
            )
        )

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginate
    stmt = stmt.order_by(ConsultSession.consult_started_at.desc().nullslast()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    # Fetch usernames
    user_ids = list({r.user_id for r in rows if r.user_id})
    usernames = {}
    if user_ids:
        user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in user_result.scalars().all():
            usernames[str(u.id)] = u.username

    return {
        "data": [
            {
                "session_id": str(r.id),
                "session_string": r.session_id,
                "student_name": usernames.get(str(r.user_id), "游客") if r.user_id else "游客",
                "province": r.province or "",
                "subjects": r.subjects or "",
                "score": r.score or 0,
                "rank": r.rank,
                "intent_majors": r.intent_majors or [],
                "consult_summary": r.consult_summary or "",
                "consult_started_at": r.consult_started_at.isoformat() if r.consult_started_at else None,
                "follow_status": r.follow_status,
                "follow_note": r.follow_note or "",
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/consultations/{session_id}")
async def get_consultation_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """Get consultation detail with chat messages."""
    result = await db.execute(
        select(ConsultSession).where(
            ConsultSession.id == uuid.UUID(session_id),
            ConsultSession.tenant_slug == tenant.slug,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch username
    username = "游客"
    if session.user_id:
        u_result = await db.execute(select(User).where(User.id == session.user_id))
        u = u_result.scalar_one_or_none()
        if u:
            username = u.username

    # Fetch messages
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in msg_result.scalars().all()
    ]

    return {
        "session": {
            "session_id": str(session.id),
            "session_string": session.session_id,
            "student_name": username,
            "province": session.province or "",
            "subjects": session.subjects or "",
            "score": session.score or 0,
            "rank": session.rank,
            "intent_majors": session.intent_majors or [],
            "focus_points": session.focus_points or [],
            "consult_summary": session.consult_summary or "",
            "consult_started_at": session.consult_started_at.isoformat() if session.consult_started_at else None,
            "follow_status": session.follow_status,
            "follow_note": session.follow_note or "",
            "followed_at": session.followed_at.isoformat() if session.followed_at else None,
        },
        "messages": messages,
    }


class FollowStatusUpdate(BaseModel):
    status: str  # pending / processed / ignored
    note: str = ""


@router.patch("/consultations/{session_id}/follow-status")
async def update_follow_status(
    session_id: str,
    body: FollowStatusUpdate,
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    user=Depends(get_current_tenant_user),
):
    """Update follow-up status of a consultation."""
    if body.status not in ("pending", "processed", "ignored"):
        raise HTTPException(status_code=400, detail="Invalid status")
    result = await db.execute(
        select(ConsultSession).where(
            ConsultSession.id == uuid.UUID(session_id),
            ConsultSession.tenant_slug == tenant.slug,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.follow_status = body.status
    session.follow_note = body.note or None
    if body.status == "processed":
        session.followed_at = datetime.now(timezone.utc)
        session.followed_by = user.user_id
    await db.commit()
    return {"ok": True, "follow_status": session.follow_status}


@router.post("/consultations/{session_id}/regenerate-summary")
async def regenerate_summary(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """Manually trigger summary regeneration."""
    result = await db.execute(
        select(ConsultSession).where(
            ConsultSession.id == uuid.UUID(session_id),
            ConsultSession.tenant_slug == tenant.slug,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    from services.consult_summary_service import generate_summary
    summary = await generate_summary(session.session_id)
    session.consult_summary = summary
    await db.commit()
    return {"consult_summary": summary}


@router.get("/consultations/stats/summary")
async def consultations_stats(
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    """Quick stats for consultation workbench header."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = (await db.execute(
        select(func.count()).select_from(ConsultSession)
        .where(ConsultSession.tenant_slug == tenant.slug)
    )).scalar() or 0
    today_new = (await db.execute(
        select(func.count()).select_from(ConsultSession)
        .where(ConsultSession.tenant_slug == tenant.slug, ConsultSession.consult_started_at >= today_start)
    )).scalar() or 0
    pending = (await db.execute(
        select(func.count()).select_from(ConsultSession)
        .where(ConsultSession.tenant_slug == tenant.slug, ConsultSession.follow_status == "pending")
    )).scalar() or 0
    processed = (await db.execute(
        select(func.count()).select_from(ConsultSession)
        .where(ConsultSession.tenant_slug == tenant.slug, ConsultSession.follow_status == "processed")
    )).scalar() or 0
    return {"total": total, "today_new": today_new, "pending": pending, "processed": processed}
```

- [ ] **Step 2: Register router**

Edit `backend/main.py` — add import after the other route imports:
```python
from api.routes import consult_workbench  # noqa: E402
```

After the admin router registration:
```python
app.include_router(consult_workbench.router, prefix="/api/v1/admin", tags=["consult-workbench"])
```

- [ ] **Step 3: Smoke test**

Restart backend. With admin token:
```bash
Invoke-RestMethod -Uri http://localhost:8000/api/v1/admin/consultations?page=1 -Headers @{Authorization="Bearer $token"; "X-Tenant"="scnu"}
```
Expected: `{"data": [...], "total": N, ...}`

- [ ] **Step 4: Commit**

```bash
git add backend/api/routes/consult_workbench.py backend/main.py
git commit -m "feat(backend): 5 consultation workbench admin endpoints"
```

---

## Task 5: Backend — mini-app profile/basic API + profile-dashboard enhancement

**Files:**
- Modify: `backend/api/routes/miniapp.py`
- Modify: `backend/analytics/profile_dashboard.py`

- [ ] **Step 1: Add `PUT /api/v1/miniapp/profile/basic` endpoint**

Edit `backend/api/routes/miniapp.py` — add at the end of the file (after all existing routes):
```python
# ─── API: Student basic info form (pre-chat) ───

class BasicInfoRequest(BaseModel):
    region: str
    subjects: str
    score: int
    rank: int


@router.put("/miniapp/profile/basic")
async def update_basic_info(body: BasicInfoRequest, request: Request):
    """Update student basic info (province/subjects/score/rank) before chat."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return err("AUTH_REQUIRED", "登录后才能填写基本信息")
    try:
        payload = decode_token(auth_header[7:])
        if not payload:
            return err("AUTH_REQUIRED", "无效的登录凭证")
        user_id = uuid.UUID(payload["user_id"])
    except Exception:
        return err("AUTH_REQUIRED", "无效的登录凭证")

    # Validate
    if not body.region or not body.subjects:
        return err("INVALID_INPUT", "省份和选科为必填")
    if not (0 <= body.score <= 750):
        return err("INVALID_INPUT", "分数必须在 0-750 之间")
    if body.rank <= 0:
        return err("INVALID_INPUT", "位次必须为正整数")

    from models.user import User
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return err("USER_NOT_FOUND", "用户不存在")
        user.region = body.region
        user.subjects = body.subjects
        user.score = body.score
        user.rank = body.rank
        await db.commit()
    return ok({"updated": True})
```

Add the necessary imports at the top of the file:
```python
from pydantic import BaseModel
from sqlalchemy import select as sa_select  # avoid name clash if any
```

Also: in `miniapp_enter`, after creating a new session for a registered user, the snapshot is already taken in `get_or_create_session` (Task 2). No additional change needed.

- [ ] **Step 2: Add 4 new fields to profile-dashboard response**

Edit `backend/analytics/profile_dashboard.py` — in `get_profile_dashboard`, before the final `return`, add queries:
```python
        # New stats: monthlyNew, growthRate, todayNewSessions, pendingFollowSessions
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (month_start.replace(month=month_start.month - 1) if month_start.month > 1
                            else month_start.replace(year=month_start.year - 1, month=12))
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        monthly_new_result = await db.execute(text("""
            SELECT COUNT(*) FROM consult_sessions
            WHERE tenant_slug = (SELECT slug FROM tenants WHERE id = :tid)
              AND consult_started_at >= :ms
        """), {"tid": tenant_id, "ms": month_start})
        monthly_new = monthly_new_result.scalar() or 0

        last_month_new_result = await db.execute(text("""
            SELECT COUNT(*) FROM consult_sessions
            WHERE tenant_slug = (SELECT slug FROM tenants WHERE id = :tid)
              AND consult_started_at >= :lms AND consult_started_at < :ms
        """), {"tid": tenant_id, "lms": last_month_start, "ms": month_start})
        last_month_new = last_month_new_result.scalar() or 0
        growth_rate = round((monthly_new - last_month_new) / last_month_new, 2) if last_month_new else None

        today_new_result = await db.execute(text("""
            SELECT COUNT(*) FROM consult_sessions
            WHERE tenant_slug = (SELECT slug FROM tenants WHERE id = :tid)
              AND consult_started_at >= :ts
        """), {"tid": tenant_id, "ts": today_start})
        today_new_sessions = today_new_result.scalar() or 0

        pending_result = await db.execute(text("""
            SELECT COUNT(*) FROM consult_sessions
            WHERE tenant_slug = (SELECT slug FROM tenants WHERE id = :tid)
              AND follow_status = 'pending'
        """), {"tid": tenant_id})
        pending_follow_sessions = pending_result.scalar() or 0
```

Then add to the return dict:
```python
    return {
        "riasecDistribution": riasec_distribution,
        "valuesDistribution": values_distribution,
        "completenessBreakdown": completeness_breakdown,
        "totalProfiles": total_profiles,
        "monthlyNew": monthly_new,
        "growthRate": growth_rate,
        "todayNewSessions": today_new_sessions,
        "pendingFollowSessions": pending_follow_sessions,
    }
```

- [ ] **Step 3: Smoke test**

```bash
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/analytics/profile-dashboard?days=365" -Headers @{Authorization="Bearer $token"; "X-Tenant"="scnu"}
```
Expected: response includes `monthlyNew`, `growthRate`, `todayNewSessions`, `pendingFollowSessions`.

- [ ] **Step 4: Commit**

```bash
git add backend/api/routes/miniapp.py backend/analytics/profile_dashboard.py
git commit -m "feat(backend): miniapp profile/basic API + profile-dashboard 4 new stats"
```

---

## Task 6: Backend — remove ModuleGate middleware

**Files:**
- Modify: `backend/core/middleware.py`

- [ ] **Step 1: Make ModuleGateMiddleware pass-through**

Edit `backend/core/middleware.py` — replace `ModuleGateMiddleware.dispatch` body with a simple pass-through:
```python
class ModuleGateMiddleware(BaseHTTPMiddleware):
    """Module gate disabled per admin data overhaul spec §4.9. All modules always enabled."""

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)
```

(Keep the class so existing imports don't break. The `MODULE_ROUTE_MAP` and `MODULE_DEPENDENCIES` imports are no longer used but harmless.)

- [ ] **Step 2: Smoke test**

Restart backend. Confirm no errors. Hit an analytics endpoint that was previously gated — should now always succeed (given valid auth):
```bash
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/analytics/topic-cloud?days=7" -Headers @{Authorization="Bearer $token"; "X-Tenant"="scnu"}
```
Expected: 200 (data may be empty, but no 403 MODULE_DISABLED).

- [ ] **Step 3: Commit**

```bash
git add backend/core/middleware.py
git commit -m "refactor(backend): disable ModuleGate middleware (spec §4.9)"
```

---

## Task 7: Backend — update tests referencing subject_type

**Files:**
- Modify: `backend/tests/unit/test_consult_service.py`
- Modify: `backend/tests/unit/test_cend_profile_analyzer.py`
- Modify: `backend/tests/unit/test_lead_extraction.py`
- Modify: `backend/tests/unit/test_profile_extraction.py`

- [ ] **Step 1: Update test_consult_service.py**

Read `backend/tests/unit/test_consult_service.py`. For each test that sets `session.subject_type = "物理类"`, change to `session.subjects = "物化生"`. For assertions on `subject_type`, change to `subjects`. For tests that exercise `extract_profile_from_message` expecting `subject_type`/`province`/`score` extraction, **remove those assertions** (extraction no longer handles those fields).

Specifically:
- Line 124: `session_mock.subject_type = ""` → `session_mock.subjects = ""`
- Line 229: `session.subject_type = ""` → `session.subjects = ""`
- Line 240: `session.subject_type = "物理类"` → `session.subjects = "物化生"`
- Anywhere `extract_profile_from_message` is called with expected `province`/`subject_type`/`score` keys in result — remove those keys from expected dict, keep only `intent_majors`.

- [ ] **Step 2: Update test_cend_profile_analyzer.py**

Read `backend/tests/unit/test_cend_profile_analyzer.py`. Update fixtures:
- Line 44: `basic={"province": "广东", "subject_type": "物理", "score": 600}` → `basic={"intent_majors": ["计算机"], "focus_points": ["就业"]}`
- Line 90: similar update to expected output

- [ ] **Step 3: Update test_lead_extraction.py**

Read `backend/tests/unit/test_lead_extraction.py`. Update:
- Line 23: `cs.subject_type` → `cs.subjects`
- Line 45: `"subject_type": row.subject_type` → `"subjects": row.subjects`
- Line 82: `mock_row.subject_type = "物理类"` → `mock_row.subjects = "物化生"`
- Line 103: `assert lead["subject_type"] == "物理类"` → `assert lead["subjects"] == "物化生"`
- Line 114: `mock_row.subject_type = ""` → `mock_row.subjects = ""`
- Line 143: `mock_row.subject_type = "历史类"` → `mock_row.subjects = "历政地"`

- [ ] **Step 4: Update test_profile_extraction.py**

Read `backend/tests/unit/test_profile_extraction.py`. This file tests regex extraction of province/subject_type/score. Since that extraction is removed, **mark all tests as skipped**.

Simplest approach: add at top of file:
```python
import pytest
pytestmark = pytest.mark.skip(reason="Province/subject_type/score extraction removed in Plan 2 — basic info now from student form")
```

- [ ] **Step 5: Run unit tests**

```bash
cd backend && python -m pytest tests/unit/test_consult_service.py tests/unit/test_cend_profile_analyzer.py tests/unit/test_lead_extraction.py tests/unit/test_profile_extraction.py -v
```
Expected: All tests pass (or skipped for test_profile_extraction.py).

- [ ] **Step 6: Commit**

```bash
git add backend/tests/unit/test_consult_service.py backend/tests/unit/test_cend_profile_analyzer.py backend/tests/unit/test_lead_extraction.py backend/tests/unit/test_profile_extraction.py
git commit -m "test(backend): update unit tests for subject_type->subjects rename"
```

---

## Task 8: Mini-app — pre-chat form + subject_type→subjects rename

**Files:**
- Create: `mini-app/src/pages/chat/PreForm.vue`
- Modify: `mini-app/src/pages/chat/index.vue`
- Modify: `mini-app/src/pages/profile/index.vue`
- Modify: `mini-app/src/pages/recommendations/index.vue`
- Modify: `mini-app/src/pages/compare/index.vue`

- [ ] **Step 1: Create PreForm.vue component**

Create `mini-app/src/pages/chat/PreForm.vue`:
```vue
<template>
  <view class="pre-form">
    <view class="form-title">填写基本信息</view>
    <view class="form-desc">为了给你更准确的咨询，请先填写以下信息</view>

    <view class="form-item">
      <text class="label">省份</text>
      <picker mode="selector" :range="provinces" @change="onProvinceChange">
        <view class="picker-value">{{ form.region || '请选择省份' }}</view>
      </picker>
    </view>

    <view class="form-item">
      <text class="label">选科</text>
      <picker mode="selector" :range="subjectCombos" @change="onSubjectsChange">
        <view class="picker-value">{{ form.subjects || '请选择选科组合' }}</view>
      </picker>
    </view>

    <view class="form-item">
      <text class="label">分数</text>
      <input type="number" v-model="form.score" placeholder="0-750" class="input" />
    </view>

    <view class="form-item">
      <text class="label">位次</text>
      <input type="number" v-model="form.rank" placeholder="全省排名" class="input" />
    </view>

    <button class="submit-btn" :disabled="!canSubmit" @click="submit">开始咨询</button>
  </view>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue'

const provinces = ['北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江', '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州', '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆']

const subjectCombos = [
  '物化生', '物化地', '物化政', '物生地', '物生政', '物政地',
  '历化生', '历化地', '历化政', '历生地', '历生政', '历政地',
]

const emit = defineEmits<{ (e: 'submit', data: { region: string; subjects: string; score: number; rank: number }): void }>()

const form = reactive({
  region: '',
  subjects: '',
  score: '',
  rank: '',
})

const onProvinceChange = (e: any) => { form.region = provinces[e.detail.value] }
const onSubjectsChange = (e: any) => { form.subjects = subjectCombos[e.detail.value] }

const canSubmit = computed(() =>
  form.region && form.subjects &&
  Number(form.score) > 0 && Number(form.score) <= 750 &&
  Number(form.rank) > 0
)

const submit = () => {
  if (!canSubmit.value) return
  emit('submit', {
    region: form.region,
    subjects: form.subjects,
    score: Number(form.score),
    rank: Number(form.rank),
  })
}
</script>

<style scoped>
.pre-form { padding: 40rpx 32rpx; background: #fff; min-height: 100vh; }
.form-title { font-size: 40rpx; font-weight: 600; color: #1f2937; margin-bottom: 12rpx; }
.form-desc { font-size: 26rpx; color: #6b7280; margin-bottom: 48rpx; }
.form-item { margin-bottom: 32rpx; }
.label { display: block; font-size: 28rpx; color: #374151; margin-bottom: 12rpx; }
.picker-value { padding: 20rpx; background: #f3f4f6; border-radius: 8rpx; font-size: 28rpx; color: #1f2937; }
.input { padding: 20rpx; background: #f3f4f6; border-radius: 8rpx; font-size: 28rpx; }
.submit-btn { margin-top: 48rpx; background: #1a3a6b; color: #fff; border: none; border-radius: 8rpx; padding: 24rpx; font-size: 30rpx; }
.submit-btn[disabled] { background: #d1d5db; }
</style>
```

- [ ] **Step 2: Integrate PreForm into chat/index.vue**

Read `mini-app/src/pages/chat/index.vue`. Modifications:
1. Replace all `subject_type` references with `subjects` (line 44: `profileSummary.subject_type` → `profileSummary.subjects`; update label "科类" to "选科").
2. Add `showPreForm` ref, default false.
3. On page mount (after fetching profile), if `studentInfo.value.subjects` is empty AND user is logged in (not guest), set `showPreForm = true`.
4. Render `<PreForm v-if="showPreForm" @submit="onPreFormSubmit" />` as a full-screen overlay.
5. `onPreFormSubmit` calls `PUT /api/v1/miniapp/profile/basic` then sets `showPreForm = false` and re-fetches session.

Concretely, add to script:
```typescript
import PreForm from './PreForm.vue'

const showPreForm = ref(false)

const checkPreForm = async () => {
  const token = uni.getStorageSync('token')
  if (!token) return  // guest users skip
  try {
    const res = await uni.request({
      url: `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/student/profile`,
      method: 'GET',
      header: { Authorization: `Bearer ${token}` },
    })
    const profile = (res.data as any)?.data
    if (profile && !profile.subjects) {
      showPreForm.value = true
    }
  } catch (e) {
    // fail silently — don't block chat
  }
}

const onPreFormSubmit = async (data: { region: string; subjects: string; score: number; rank: number }) => {
  const token = uni.getStorageSync('token')
  try {
    await uni.request({
      url: `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/miniapp/profile/basic`,
      method: 'PUT',
      header: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data,
    })
    showPreForm.value = false
    // Re-enter session to refresh snapshot
    await initSession()
  } catch (e) {
    uni.showToast({ title: '保存失败', icon: 'none' })
  }
}

onMounted(() => { checkPreForm() })
```

In template, add at the top:
```vue
<PreForm v-if="showPreForm" @submit="onPreFormSubmit" />
```

- [ ] **Step 3: Rename subject_type→subjects in 3 other mini-app pages**

Edit `mini-app/src/pages/profile/index.vue`:
- Line 57: `{{ studentInfo.subject_type }}` → `{{ studentInfo.subjects }}`
- Line 106: `subject_type: ""` → `subjects: ""`
- Line 161: `subject_type: ""` → `subjects: ""`
- Update label "科类" → "选科" if present

Edit `mini-app/src/pages/recommendations/index.vue`:
- Line 35: `{{ studentInfo.subject_type }}` → `{{ studentInfo.subjects }}`
- Line 156: `subject_type: ""` → `subjects: ""`
- Update label "科类" → "选科"

Edit `mini-app/src/pages/compare/index.vue`:
- Line 40: `{{ studentInfo.subject_type }}` → `{{ studentInfo.subjects }}`
- Line 150: `subject_type: ""` → `subjects: ""`
- Update label "科类" → "选科"

- [ ] **Step 4: Build mini-app**

```bash
cd mini-app && npm run build:h5
```
Expected: Build succeeds.

- [ ] **Step 5: Smoke test**

Start mini-app dev server:
```bash
cd mini-app && npm run dev:h5 -- --port 3002
```
Open `http://localhost:3002`. Register a new student. Enter chat page. Confirm:
- PreForm appears (since `users.subjects` is empty)
- Fill form → submit → form disappears → chat available
- Profile page shows "选科" label with the value

- [ ] **Step 6: Commit**

```bash
git add mini-app/src/pages/chat/PreForm.vue mini-app/src/pages/chat/index.vue mini-app/src/pages/profile/index.vue mini-app/src/pages/recommendations/index.vue mini-app/src/pages/compare/index.vue
git commit -m "feat(mini-app): pre-chat basic info form + subject_type->subjects rename"
```

---

## Task 9: Admin-spa — Sidebar + App cleanup (delete 5 pages, hide distribution)

**Files:**
- Modify: `admin-spa/src/components/Sidebar.tsx`
- Modify: `admin-spa/src/App.tsx`
- Delete: `admin-spa/src/pages/LeadWorkbenchPage.tsx`
- Delete: `admin-spa/src/pages/ChannelsPage.tsx`
- Delete: `admin-spa/src/pages/ReportsPage.tsx`
- Delete: `admin-spa/src/pages/ModuleSettingsPage.tsx`
- Delete: `admin-spa/src/pages/BrandSettingsPage.tsx`

- [ ] **Step 1: Update Sidebar MENU_ITEMS**

Edit `admin-spa/src/components/Sidebar.tsx` — replace the `MENU_ITEMS` array:
```typescript
const MENU_ITEMS: MenuItem[] = [
  { path: '/dashboard', label: '工作台', icon: <LayoutDashboard size={18} />, module: null, section: '导航' },
  { path: '/consultations', label: '咨询工作台', icon: <MessageSquare size={18} />, module: null, section: '导航' },
  { path: '/profile', label: '画像看板', icon: <User size={18} />, module: 'profile_dashboard', section: '导航' },
  { path: '/insights', label: '洞察分析', icon: <BarChart3 size={18} />, module: 'topic_cloud', section: '导航' },
  { path: '/knowledge', label: '知识库', icon: <BookOpen size={18} />, module: null, section: '管理' },
  { path: '/agent-settings', label: 'Agent 设置', icon: <Bot size={18} />, module: null, section: '管理' },
]
```

(Removed: /leads, /reports, /channels, /brand, /modules, /distribution/tasks, /distribution/channels, /distribution/logs. Renamed: "咨询管理" → "咨询工作台".)

Also remove unused imports (FileText, Radio, Palette, Blocks, Send) from the lucide-react import.

Add `/db` entry conditionally on `is_developer` — append to MENU_ITEMS or render separately. Add before the footer:
```typescript
{isDeveloper && (
  <NavLink to="/db" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
    <span className="nav-icon"><Database size={18} /></span>
    <span>数据库管理</span>
  </NavLink>
)}
```

Add imports:
```typescript
import { Database } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
```

And inside component:
```typescript
const isDeveloper = useAuthStore((s) => s.user?.is_developer ?? false)
```

- [ ] **Step 2: Update App.tsx routes**

Edit `admin-spa/src/App.tsx` — remove imports for LeadWorkbenchPage, ChannelsPage, ReportsPage, BrandSettingsPage, ModuleSettingsPage.

Remove the corresponding `<Route>` lines for `/leads`, `/channels`, `/reports`, `/brand`, `/modules`.

> Distribution 3 routes are kept (spec §4.8: "路由和页面代码保留不动"). Only remove them from Sidebar.

Final routes block (after Plan 4's /db route):
```tsx
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="consultations" element={<ConsultationsPage />} />
          <Route path="profile" element={<ProfileDashboardPage />} />
          <Route path="insights" element={<InsightsPage />} />
          <Route path="knowledge" element={<KnowledgeSettingsPage />} />
          <Route path="agent-settings" element={<AgentSettingsPage />} />
          <Route
            path="db"
            element={
              <RequireDeveloper>
                <DbAdminPage />
              </RequireDeveloper>
            }
          />
          {/* Distribution routes kept per spec §4.8 */}
          <Route path="distribution/tasks" element={<DistributionTasksPage />} />
          <Route path="distribution/channels" element={<DistributionChannelsPage />} />
          <Route path="distribution/logs" element={<DistributionLogsPage />} />
        </Route>
```

- [ ] **Step 3: Delete 5 page files**

Use DeleteFile tool with paths:
- `admin-spa/src/pages/LeadWorkbenchPage.tsx`
- `admin-spa/src/pages/ChannelsPage.tsx`
- `admin-spa/src/pages/ReportsPage.tsx`
- `admin-spa/src/pages/ModuleSettingsPage.tsx`
- `admin-spa/src/pages/BrandSettingsPage.tsx`

- [ ] **Step 4: Build + smoke test**

```bash
cd admin-spa && npm run build
```
Expected: Build succeeds. If "Cannot find module" errors appear, find and remove the leftover imports.

Smoke test: open `http://localhost:3001?tenant=scnu`. Sidebar shows only 6 items + /db (if developer). Navigate around — no broken links.

- [ ] **Step 5: Commit**

```bash
git add admin-spa/src/components/Sidebar.tsx admin-spa/src/App.tsx admin-spa/src/pages/
git commit -m "refactor(admin-spa): delete 5 pages, hide distribution entries, rename consultations"
```

---

## Task 10: Admin-spa — DashboardPage rewrite (no mock)

**Files:**
- Modify: `admin-spa/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Rewrite DashboardPage**

Replace entire content of `admin-spa/src/pages/DashboardPage.tsx`:
```tsx
import { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import api from '../api/client'
import StatusCard from '../components/StatusCard'
import { useMobileStore } from '../stores/mobileStore'

interface ProfileDashboard {
  totalProfiles: number
  monthlyNew: number
  growthRate: number | null
  todayNewSessions: number
  pendingFollowSessions: number
  riasecDistribution: { dimension: string; avgScore: number; count: number }[]
  valuesDistribution: { value: string; percentage: number }[]
  completenessBreakdown: { level: string; count: number }[]
}

interface HotQuestion { topic: string; count: number }

const RIASEC_NAMES: Record<string, string> = {
  R: '实用型', I: '研究型', A: '艺术型', S: '社会型', E: '企业型', C: '常规型',
}

const RIASEC_MAJORS: Record<string, string> = {
  R: '机械/电气/土木',
  I: '计算机/人工智能/数据科学',
  A: '设计/传媒/中文',
  S: '师范/心理学/社会工作',
  E: '工商管理/市场营销/金融',
  C: '会计/统计学/档案学',
}

export default function DashboardPage() {
  const isMobile = useMobileStore((s) => s.isMobile)
  const [data, setData] = useState<ProfileDashboard | null>(null)
  const [hotQuestions, setHotQuestions] = useState<HotQuestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const valuesRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    Promise.allSettled([
      api.get<ProfileDashboard>('/admin/analytics/profile-dashboard?days=365'),
      api.get<HotQuestion[]>('/admin/analytics/hot-questions?days=7'),
    ]).then(([pd, hq]) => {
      if (pd.status === 'fulfilled') setData(pd.value.data)
      if (hq.status === 'fulfilled') setHotQuestions(hq.value.data)
      if (pd.status === 'rejected' && hq.status === 'rejected') {
        setError('获取数据失败')
      }
    }).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!valuesRef.current || !data?.valuesDistribution?.length) return
    const chart = echarts.init(valuesRef.current)
    chart.setOption({
      grid: { left: 80, right: 40, top: 10, bottom: 20 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: data.valuesDistribution.map((v) => v.value).reverse(), axisLabel: { fontSize: 12 } },
      series: [{
        type: 'bar',
        data: data.valuesDistribution.map((v) => v.percentage).reverse(),
        itemStyle: { color: '#1a3a6b', borderRadius: [0, 4, 4, 0] },
        barMaxWidth: 24,
      }],
    })
    return () => chart.dispose()
  }, [data])

  const top3Riasec = (data?.riasecDistribution || [])
    .slice()
    .sort((a, b) => b.avgScore - a.avgScore)
    .slice(0, 3)

  const fullCount = data?.completenessBreakdown?.find((c) => c.level === 'L3')?.count ?? 0
  const partialCount = data?.completenessBreakdown?.find((c) => c.level === 'L2')?.count ?? 0
  const initialCount = data?.completenessBreakdown?.find((c) => c.level === 'L1')?.count ?? 0

  return (
    <div>
      <StatusCard loading={loading} error={error}>
        {data && (
          <>
            {/* 4 stat cards */}
            <div className="stat-grid" style={{ gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(4,1fr)' }}>
              <div className="stat-card">
                <span className="stat-label">累计咨询学生数</span>
                <span className="stat-value">{data.totalProfiles}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">今日新增会话数</span>
                <span className="stat-value">{data.todayNewSessions}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">待跟进会话数</span>
                <span className="stat-value">{data.pendingFollowSessions}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">本月新增画像数</span>
                <span className="stat-value">{data.monthlyNew}</span>
                {data.growthRate !== null && (
                  <span style={{ fontSize: 11, color: data.growthRate >= 0 ? 'var(--color-success)' : 'var(--color-danger)', fontWeight: 500 }}>
                    {data.growthRate >= 0 ? '+' : ''}{(data.growthRate * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            </div>

            {/* Top 3 RIASEC interest cards */}
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-header"><h3>咨询学生画像 Top 3 兴趣</h3></div>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3,1fr)', gap: 12, padding: 16 }}>
                {top3Riasec.length === 0 ? (
                  <div style={{ color: '#999', padding: 16 }}>暂无画像数据</div>
                ) : top3Riasec.map((r) => (
                  <div key={r.dimension} style={{ padding: 16, background: '#f9fafb', borderRadius: 8, border: '1px solid #f3f4f6' }}>
                    <div style={{ fontSize: 16, fontWeight: 600, color: '#1a3a6b' }}>
                      {r.dimension} {RIASEC_NAMES[r.dimension] || ''}
                    </div>
                    <div style={{ fontSize: 12, color: '#666', margin: '4px 0' }}>学生数 {r.count}</div>
                    <div style={{ fontSize: 11, color: '#999' }}>推荐匹配: {RIASEC_MAJORS[r.dimension] || '-'}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Values distribution + Hot questions */}
            <div className="chart-grid even" style={{ marginTop: 16 }}>
              <div className="card">
                <div className="card-header"><h3>价值观分布</h3></div>
                <div ref={valuesRef} style={{ height: isMobile ? 260 : 340 }} />
              </div>
              <div className="card">
                <div className="card-header"><h3>咨询热点 Top 10</h3></div>
                {hotQuestions.length > 0 ? (
                  <div style={{ padding: 16 }}>
                    {hotQuestions.slice(0, 10).map((q, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f3f4f6', fontSize: 13 }}>
                        <span>{i + 1}. {q.topic}</span>
                        <span style={{ color: '#666' }}>{q.count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: 32, color: '#999', textAlign: 'center' }}>暂无数据</div>
                )}
              </div>
            </div>

            {/* Completeness breakdown */}
            <div className="stat-grid" style={{ gridTemplateColumns: isMobile ? '1fr' : 'repeat(3,1fr)', marginTop: 16 }}>
              <div className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--color-success)' }}>{fullCount}</div>
                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>完整画像（L3）</div>
              </div>
              <div className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--color-warning)' }}>{partialCount}</div>
                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>部分画像（L2）</div>
              </div>
              <div className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: '#999' }}>{initialCount}</div>
                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>初始画像（L1）</div>
              </div>
            </div>
          </>
        )}
      </StatusCard>
    </div>
  )
}
```

- [ ] **Step 2: Build + smoke test**

```bash
cd admin-spa && npm run build
```
Open `/dashboard`. Confirm: no mock data, 4 stat cards from API, Top 3 RIASEC cards, values bar chart, hot questions list, completeness cards. Error state shows if backend unavailable.

- [ ] **Step 3: Commit**

```bash
git add admin-spa/src/pages/DashboardPage.tsx
git commit -m "feat(admin-spa): rewrite DashboardPage with real API data (no mock)"
```

---

## Task 11: Admin-spa — ConsultationsPage rewrite (consultation workbench)

**Files:**
- Modify: `admin-spa/src/pages/ConsultationsPage.tsx`

- [ ] **Step 1: Rewrite ConsultationsPage**

Replace entire content of `admin-spa/src/pages/ConsultationsPage.tsx`:
```tsx
import { useEffect, useState } from 'react'
import api from '../api/client'
import StatusCard from '../components/StatusCard'
import { useMobileStore } from '../stores/mobileStore'

interface ConsultationRow {
  session_id: string
  session_string: string
  student_name: string
  province: string
  subjects: string
  score: number
  rank: number | null
  intent_majors: string[]
  consult_summary: string
  consult_started_at: string | null
  follow_status: 'pending' | 'processed' | 'ignored'
  follow_note: string
}

interface ConsultationDetail {
  session: ConsultationRow & { focus_points: string[]; followed_at: string | null }
  messages: { id: string; role: string; content: string; created_at: string }[]
}

const STATUS_LABELS: Record<string, string> = {
  pending: '待跟进', processed: '已处理', ignored: '已忽略',
}

export default function ConsultationsPage() {
  const isMobile = useMobileStore((s) => s.isMobile)
  const [rows, setRows] = useState<ConsultationRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState<{ status: string; period: string; search: string }>({ status: '', period: '', search: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detail, setDetail] = useState<ConsultationDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const fetchList = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '20' })
      if (filter.status) params.set('status', filter.status)
      if (filter.period) params.set('period', filter.period)
      if (filter.search) params.set('search', filter.search)
      const r = await api.get<{ data: ConsultationRow[]; total: number }>(`/admin/consultations?${params}`)
      setRows(r.data.data)
      setTotal(r.data.total)
    } catch (e: any) {
      setError(e?.message || '获取咨询列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchList() }, [page, filter])

  const openDetail = async (sessionId: string) => {
    setDetailLoading(true)
    try {
      const r = await api.get<ConsultationDetail>(`/admin/consultations/${sessionId}`)
      setDetail(r.data)
    } catch (e) {
      // ignore
    } finally {
      setDetailLoading(false)
    }
  }

  const updateFollow = async (sessionId: string, status: string, note: string = '') => {
    try {
      await api.patch(`/admin/consultations/${sessionId}/follow-status`, { status, note })
      setRows((prev) => prev.map((r) => r.session_id === sessionId ? { ...r, follow_status: status as any, follow_note: note } : r))
      if (detail?.session.session_id === sessionId) {
        setDetail({ ...detail, session: { ...detail.session, follow_status: status as any, follow_note: note } })
      }
    } catch (e) {
      // ignore
    }
  }

  const regenerateSummary = async (sessionId: string) => {
    try {
      const r = await api.post<{ consult_summary: string }>(`/admin/consultations/${sessionId}/regenerate-summary`)
      setRows((prev) => prev.map((row) => row.session_id === sessionId ? { ...row, consult_summary: r.data.consult_summary } : row))
      if (detail?.session.session_id === sessionId) {
        setDetail({ ...detail, session: { ...detail.session, consult_summary: r.data.consult_summary } })
      }
    } catch (e) {
      // ignore
    }
  }

  return (
    <div>
      <StatusCard loading={loading} error={error}>
        {/* Filter bar */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <select value={filter.status} onChange={(e) => { setFilter({ ...filter, status: e.target.value }); setPage(1) }} style={{ padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13 }}>
            <option value="">全部状态</option>
            <option value="pending">待跟进</option>
            <option value="processed">已处理</option>
            <option value="ignored">已忽略</option>
            <option value="no_consult">未咨询</option>
          </select>
          <select value={filter.period} onChange={(e) => { setFilter({ ...filter, period: e.target.value }); setPage(1) }} style={{ padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13 }}>
            <option value="">全部时间</option>
            <option value="today">今日</option>
            <option value="7d">近7天</option>
            <option value="30d">近30天</option>
          </select>
          <input
            value={filter.search}
            onChange={(e) => setFilter({ ...filter, search: e.target.value })}
            placeholder="搜索学生名/咨询摘要"
            style={{ padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, flex: 1, minWidth: 200 }}
          />
        </div>

        {/* Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)', textAlign: 'left' }}>
                <th style={{ padding: '8px' }}>学生</th>
                <th style={{ padding: '8px' }}>基本信息</th>
                <th style={{ padding: '8px' }}>意向专业</th>
                <th style={{ padding: '8px' }}>咨询摘要</th>
                <th style={{ padding: '8px' }}>咨询时间</th>
                <th style={{ padding: '8px' }}>跟进状态</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.session_id} style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }} onClick={() => openDetail(r.session_id)}>
                  <td style={{ padding: '8px' }}>{r.student_name}</td>
                  <td style={{ padding: '8px' }}>{r.province} · {r.subjects} · {r.score}分{r.rank ? ` · ${r.rank}名` : ''}</td>
                  <td style={{ padding: '8px' }}>{(r.intent_majors || []).join('、') || '-'}</td>
                  <td style={{ padding: '8px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.consult_summary || '-'}</td>
                  <td style={{ padding: '8px' }}>{r.consult_started_at ? new Date(r.consult_started_at).toLocaleString('zh-CN') : '-'}</td>
                  <td style={{ padding: '8px' }}>{STATUS_LABELS[r.follow_status] || r.follow_status}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={6} style={{ padding: 32, textAlign: 'center', color: '#999' }}>暂无数据</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16, fontSize: 13, color: 'var(--muted)' }}>
          <span>共 {total} 条</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} style={{ padding: '4px 12px', border: '1px solid var(--border)', borderRadius: 4, cursor: page <= 1 ? 'not-allowed' : 'pointer' }}>上一页</button>
            <span style={{ padding: '4px 12px' }}>第 {page} 页</span>
            <button disabled={page * 20 >= total} onClick={() => setPage(page + 1)} style={{ padding: '4px 12px', border: '1px solid var(--border)', borderRadius: 4, cursor: page * 20 >= total ? 'not-allowed' : 'pointer' }}>下一页</button>
          </div>
        </div>
      </StatusCard>

      {/* Detail Drawer */}
      {detail && (
        <div style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: isMobile ? '100%' : 480, background: 'var(--surface)', boxShadow: '-4px 0 16px rgba(0,0,0,0.08)', zIndex: 100, overflow: 'auto', padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 style={{ margin: 0 }}>咨询详情</h3>
            <button onClick={() => setDetail(null)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 18 }}>×</button>
          </div>

          <div style={{ marginBottom: 16, fontSize: 13 }}>
            <div><strong>学生:</strong> {detail.session.student_name}</div>
            <div><strong>基本信息:</strong> {detail.session.province} · {detail.session.subjects} · {detail.session.score}分{detail.session.rank ? ` · ${detail.session.rank}名` : ''}</div>
            <div><strong>意向专业:</strong> {(detail.session.intent_majors || []).join('、') || '-'}</div>
            <div><strong>关注点:</strong> {(detail.session.focus_points || []).join('、') || '-'}</div>
            <div><strong>咨询时间:</strong> {detail.session.consult_started_at ? new Date(detail.session.consult_started_at).toLocaleString('zh-CN') : '-'}</div>
            <div style={{ marginTop: 8 }}>
              <strong>咨询摘要:</strong>
              <div style={{ background: 'var(--bg)', padding: 8, borderRadius: 6, marginTop: 4 }}>{detail.session.consult_summary || '暂无'}</div>
              <button onClick={() => regenerateSummary(detail.session.session_id)} style={{ marginTop: 4, padding: '2px 8px', fontSize: 12, border: '1px solid var(--border)', borderRadius: 4, background: 'transparent', cursor: 'pointer' }}>重新生成摘要</button>
            </div>
          </div>

          {/* Chat messages */}
          <div style={{ marginBottom: 16 }}>
            <strong>对话记录</strong>
            <div style={{ marginTop: 8, maxHeight: 300, overflow: 'auto', border: '1px solid var(--border)', borderRadius: 6, padding: 8 }}>
              {detail.messages.map((m) => (
                <div key={m.id} style={{ marginBottom: 8, fontSize: 13 }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>{m.role === 'user' ? '学生' : 'AI'} · {new Date(m.created_at).toLocaleTimeString('zh-CN')}</div>
                  <div style={{ padding: '4px 8px', background: m.role === 'user' ? '#eef2ff' : '#f0fdf4', borderRadius: 4 }}>{m.content}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Follow actions */}
          <div>
            <strong>跟进操作</strong>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button onClick={() => updateFollow(detail.session.session_id, 'processed', detail.session.follow_note)} style={{ padding: '6px 12px', background: 'var(--color-success)', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>标记已处理</button>
              <button onClick={() => updateFollow(detail.session.session_id, 'pending', detail.session.follow_note)} style={{ padding: '6px 12px', background: 'var(--color-warning)', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>标记待跟进</button>
              <button onClick={() => updateFollow(detail.session.session_id, 'ignored', detail.session.follow_note)} style={{ padding: '6px 12px', background: 'var(--color-danger)', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>忽略</button>
            </div>
            <textarea
              defaultValue={detail.session.follow_note}
              placeholder="跟进备注"
              style={{ width: '100%', marginTop: 8, padding: 8, border: '1px solid var(--border)', borderRadius: 4, minHeight: 60, fontFamily: 'inherit' }}
              onBlur={(e) => updateFollow(detail.session.session_id, detail.session.follow_status, e.target.value)}
            />
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Build + smoke test**

```bash
cd admin-spa && npm run build
```
Open `/consultations`. Confirm: 6-col table renders, filter bar works, clicking a row opens right drawer with messages + follow actions, regenerate summary button calls API.

- [ ] **Step 3: Commit**

```bash
git add admin-spa/src/pages/ConsultationsPage.tsx
git commit -m "feat(admin-spa): rewrite ConsultationsPage as consultation workbench"
```

---

## Task 12: Admin-spa — ProfileDashboardPage fix (radar→Top3 + remove mock/hardcoded)

**Files:**
- Modify: `admin-spa/src/pages/ProfileDashboardPage.tsx`

**Context:** Per user decision in spec, the radar chart showing "national avg" was confusing and has been replaced on DashboardPage (Task 10). ProfileDashboardPage still needs to:
1. Remove any remaining mock import (Plan 1 may have already removed this — verify)
2. Remove hardcoded `nationalAvg` field if present
3. Replace radar chart with Top 3 RIASEC interest cards (same as DashboardPage but with more detail)
4. Keep values distribution + completeness breakdown

- [ ] **Step 1: Read current state**

Read `admin-spa/src/pages/ProfileDashboardPage.tsx` end-to-end. Identify:
- Mock import line (should already be removed by Plan 1, verify)
- `nationalAvg` / radar chart option block
- API response interface

- [ ] **Step 2: Replace radar chart with Top 3 cards**

In `ProfileDashboardPage.tsx`, remove the entire radar chart `<ReactECharts option={radarOption} ... />` block and its `radarOption` config.

Replace with Top 3 RIASEC cards section (reuse the same `RIASEC_NAMES` / `RIASEC_MAJORS` constants from DashboardPage, or extract to a shared module):
```tsx
{/* Top 3 RIASEC interest cards (replaces radar) */}
<div className="card" style={{ marginTop: 16 }}>
  <div className="card-header"><h3>咨询学生画像 Top 3 兴趣</h3></div>
  <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3,1fr)', gap: 12, padding: 16 }}>
    {top3Riasec.length === 0 ? (
      <div style={{ color: '#999', padding: 16 }}>暂无画像数据</div>
    ) : top3Riasec.map((r) => (
      <div key={r.dimension} style={{ padding: 16, background: '#f9fafb', borderRadius: 8, border: '1px solid #f3f4f6' }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: '#1a3a6b' }}>
          {r.dimension} {RIASEC_NAMES[r.dimension] || ''}
        </div>
        <div style={{ fontSize: 12, color: '#666', margin: '4px 0' }}>学生数 {r.count}</div>
        <div style={{ fontSize: 11, color: '#999' }}>推荐匹配: {RIASEC_MAJORS[r.dimension] || '-'}</div>
      </div>
    ))}
  </div>
</div>
```

Add the constants + computed value near the top of the component:
```typescript
const RIASEC_NAMES: Record<string, string> = {
  R: '实用型', I: '研究型', A: '艺术型', S: '社会型', E: '企业型', C: '常规型',
}
const RIASEC_MAJORS: Record<string, string> = {
  R: '机械/电气/土木', I: '计算机/人工智能/数据科学', A: '设计/传媒/中文',
  S: '师范/心理学/社会工作', E: '工商管理/市场营销/金融', C: '会计/统计学/档案学',
}

const top3Riasec = (data?.riasecDistribution || [])
  .slice()
  .sort((a, b) => b.avgScore - a.avgScore)
  .slice(0, 3)
```

- [ ] **Step 3: Remove `nationalAvg` references**

Search the file for any `nationalAvg` or `全国均值` references. Remove the corresponding series from any chart option, the field from the TypeScript interface, and the corresponding label in JSX.

- [ ] **Step 4: Build + smoke test**

```bash
cd admin-spa && npm run build
```
Open `/profile`. Confirm: Top 3 RIASEC cards render (no radar), values distribution + completeness breakdown still work, no mock fallback on error.

- [ ] **Step 5: Commit**

```bash
git add admin-spa/src/pages/ProfileDashboardPage.tsx
git commit -m "fix(admin-spa): ProfileDashboardPage — replace radar with Top3 RIASEC cards"
```

---

## Task 13: Admin-spa — InsightsPage remove emotion timeline + mock fallback

**Files:**
- Modify: `admin-spa/src/pages/InsightsPage.tsx`

- [ ] **Step 1: Remove emotion timeline + mock fallback**

Edit `admin-spa/src/pages/InsightsPage.tsx`:

1. Remove the mock import line (Plan 1 already did this — verify):
```typescript
// Remove if present:
import { mockTopicCloud, mockHotQuestions, mockEmotionTimeline } from '../mock/insights'
```

2. Remove all 3 mock fallback calls (Plan 1 should have done this — verify):
```typescript
// These lines should NOT exist (Plan 1 removed them):
setTopicCloud(mockTopicCloud)
setHotQuestions(mockHotQuestions)
setEmotionTimeline(mockEmotionTimeline(days))
```

3. Remove emotion-related state and code entirely:
   - Remove `EMOTION_COLORS` constant
   - Remove `emotionTimeline` state: `const [emotionTimeline, setEmotionTimeline] = useState<...>(null)`
   - In `Promise.allSettled`, remove the emotion-timeline API call (reduce from 3 to 2):
     ```typescript
     Promise.allSettled([
       api.get<TopicCloudItem[]>(`/admin/analytics/topic-cloud?days=${days}`),
       api.get<HotQuestionItem[]>(`/admin/analytics/hot-questions?days=${days}`),
     ]).then(([tc, hq]) => {
       const rejected = [tc, hq].filter((r) => r.status === 'rejected')
       if (rejected.length === 2) {
         const firstErr = (rejected[0] as PromiseRejectedResult).reason
         setError(firstErr?.message || '获取分析数据失败')
         return
       }
       if (tc.status === 'fulfilled') setTopicCloud(tc.value.data)
       if (hq.status === 'fulfilled') setHotQuestions(hq.value.data)
     }).finally(() => setLoading(false))
     ```
   - Remove `emotionOption` config block
   - Remove `EmotionTimelineData` from type import
   - Remove the emotion timeline card JSX:
     ```tsx
     {/* Remove this entire block: */}
     <div className="card">
       <div className="card-header"><h3>情绪时间线</h3></div>
       {emotionTimeline && emotionTimeline.timeline.length > 0 ? (
         <ReactECharts option={emotionOption} style={{ height: isMobile ? 240 : 300 }} />
       ) : (
         <div className="view-status empty"><span>暂无情绪数据</span></div>
       )}
     </div>
     ```

- [ ] **Step 2: Build + smoke test**

```bash
cd admin-spa && npm run build
```
Open `/insights`. Confirm: only 2 cards render (Top-10 bar + word cloud), no emotion timeline section, no mock fallback on error.

- [ ] **Step 3: Commit**

```bash
git add admin-spa/src/pages/InsightsPage.tsx
git commit -m "fix(admin-spa): remove emotion timeline + mock fallback from InsightsPage"
```

---

## Task 14: Final verification

- [ ] **Step 1: Backend full test suite**

```bash
cd backend && python -m pytest tests/unit/ -v --tb=short 2>&1 | tail -50
```
Expected: All unit tests pass (with test_profile_extraction.py skipped).

- [ ] **Step 2: Backend startup smoke test**

```bash
cd backend && uvicorn main:app --reload --port 8000
```
Wait for "Application startup complete". No errors in console.

- [ ] **Step 3: Admin-spa build**

```bash
cd admin-spa && npm run build
```
Expected: Build succeeds, no TypeScript errors.

- [ ] **Step 4: Mini-app build**

```bash
cd mini-app && npm run build:h5
```
Expected: Build succeeds.

- [ ] **Step 5: Manual E2E walkthrough (10 min)**

Start all three services:
```bash
# Terminal 1
cd backend && uvicorn main:app --reload --port 8000
# Terminal 2
cd admin-spa && npm run dev -- --port 3001
# Terminal 3
cd mini-app && npm run dev:h5 -- --port 3002
```

**Admin SPA (`http://localhost:3001?tenant=scnu`):**
1. Login as `admin` / `admin123`
2. Verify Sidebar shows: 工作台 / 咨询工作台 / 画像看板 / 洞察分析 / 知识库 / Agent 设置 / (数据库管理 if developer)
3. Verify no /leads /channels /reports /brand /modules entries
4. Verify no /distribution/* entries
5. Open 工作台 — verify 4 stat cards, Top 3 RIASEC, values chart, hot questions, completeness cards render (no mock numbers)
6. Open 咨询工作台 — verify table renders, filter works, click a row → drawer with messages + follow actions works
7. Open 画像看板 — verify Top 3 RIASEC cards (no radar), values distribution, completeness
8. Open 洞察分析 — verify only Top-10 + word cloud (no emotion timeline)

**Mini-app (`http://localhost:3002`):**
1. Register new student
2. Enter chat — verify PreForm appears (since `users.subjects` is empty)
3. Fill form (省份 / 选科 / 分数 / 位次) → submit → form disappears
4. Send 4+ chat messages
5. Open 个人中心 — verify "选科" label shows value (not "科类")
6. Wait 10s — backend should have generated `consult_summary`

**Backend DB verification:**
```bash
cd backend && python -c "import asyncio; from models import async_session; from models.consult_session import ConsultSession; from models.user import User; from sqlalchemy import select
async def m():
    async with async_session() as db:
        u = (await db.execute(select(User).order_by(User.created_at.desc()).limit(1))).scalar_one_or_none()
        print(f'User: region={u.region}, subjects={u.subjects}, score={u.score}, rank={u.rank}')
        s = (await db.execute(select(ConsultSession).order_by(ConsultSession.created_at.desc()).limit(1))).scalar_one_or_none()
        print(f'Session: subjects={s.subjects}, rank={s.rank}, consult_summary={s.consult_summary!r}, consult_started_at={s.consult_started_at}, follow_status={s.follow_status}')
asyncio.run(m())"
```
Expected:
- `User` row has all 4 fields populated from form
- `ConsultSession` row has `subjects` (not `subject_type`) populated, `consult_summary` non-empty, `consult_started_at` non-null, `follow_status='pending'`

- [ ] **Step 6: Final commit (if any cleanup)**

If all checks pass, no further commits needed. If issues found, fix and commit per-issue.

---

## Plan Complete Checklist

- [ ] Task 1: consult_sessions 8 fields migration
- [ ] Task 2: subject_type → subjects rename + AI extraction removal
- [ ] Task 3: consult_summary_service + trigger
- [ ] Task 4: 5 consultation workbench APIs
- [ ] Task 5: mini-app profile/basic API + profile-dashboard enhancement
- [ ] Task 6: ModuleGate disabled
- [ ] Task 7: Unit tests updated
- [ ] Task 8: Mini-app PreForm + subject_type → subjects rename
- [ ] Task 9: Admin-spa Sidebar + App cleanup (5 pages deleted)
- [ ] Task 10: DashboardPage rewrite (no mock)
- [ ] Task 11: ConsultationsPage rewrite (workbench)
- [ ] Task 12: ProfileDashboardPage fix (radar → Top3)
- [ ] Task 13: InsightsPage fix (remove emotion + mock)
- [ ] Task 14: Final verification

**Estimated scope:** 14 tasks, ~40 file modifications, 5 file deletions, 4 new files.

---

## Self-Review

**Spec coverage (§四 of spec):**
- §4.1 "删除 5 个页面": Tasks 9 deletes LeadWorkbench/Channels/Reports/ModuleSettings/Brand ✅
- §4.2 "重写 2 个页面": Task 10 (DashboardPage) + Task 11 (ConsultationsPage) ✅
- §4.3 "修复 2 个页面": Task 12 (ProfileDashboardPage radar → Top3) + Task 13 (InsightsPage remove emotion + mock) ✅
- §4.4 "隐藏 Distribution 入口": Task 9 hides 3 entries in Sidebar (distribution.ts kept — distribution.ts cleanup deferred per §4.8) ✅
- §4.5 "后端取消模块门控": Task 6 removes ModuleGate middleware ✅
- §4.6 "subject_type → subjects 重命名 + 删除 AI 基本信息提取": Task 2 ✅
- §4.7 "选科组合与高考位次由学生填入 + mini-app 表单": Task 8 adds PreForm + Task 5 adds `/api/v1/miniapp/profile/basic` ✅
- §4.8 "Distribution 3 页不做任何修改": confirmed — distribution.ts mock file preserved, only Sidebar entries hidden ✅
- §4.9 "DB 是否显示根据账号区分": delegated to Plan 4 (`DEV_ADMIN_USERNAME` + `is_developer` JWT claim) ✅
- §4.10 "咨询摘要字段 + 咨询时间字段": Task 3 (consult_summary_service) + Task 1 (consult_started_at field + backfill) ✅

**Placeholder scan:** No TBD/TODO. Only HTML `placeholder=` attributes (intentional form hints). ✅

**Type consistency / API signature alignment:**
- `subject_type` deprecated but kept in `ConsultSession` model (Task 1 Step 1 note: "keep `subject_type` (deprecated, not read)") — avoids breaking existing rows during migration. ✅
- `users.subjects` is `String(100)` (verified in `backend/models/user.py:11`) — `consult_sessions.subjects` uses `String(20)` (Task 1 Step 1). Length mismatch acceptable — consult snapshot is short notation like "物化生". ✅
- `users.rank` (Integer nullable) added by Plan 4 Task 1 — `consult_sessions.rank` (Integer nullable) added here. Types match. ✅
- `consult_started_at` backfilled from `MIN(chat_messages.created_at WHERE role='user')` — references existing `chat_messages` table and `role` column (verified in `models/chat_message.py`). ✅
- `extract_profile_from_message` new signature only extracts `intent_majors` — Plan 3 Checkpoint 3 verifies this. ✅
- `get_or_create_session` snapshots from users table when `user_id` provided — Plan 3 Checkpoint 2 verifies snapshot fields. ✅

**Migration chain verified:**
- Migration 006 (`users.rank`) from Plan 4 → Migration 007 (`consult_sessions` 8 fields) here. `down_revision = "006_db_admin_panel"` correctly chains. ✅
- Migration 007 backfills `consult_started_at` from `chat_messages` — uses subquery with `EXISTS` guard to avoid NULL-only updates. ✅

**Prerequisite chain:**
- Plan 2 Prerequisites: "Plan 1 (mock cleanup) and Plan 4 (DB admin panel) should be merged first." ✅
- Plan 1 removes mock fallback from ProfileDashboardPage / InsightsPage / KnowledgeSettingsPage — Plan 2 Tasks 12/13 rewrite ProfileDashboardPage / InsightsPage (KnowledgeSettingsPage untouched after Plan 1). ✅
- Plan 4 adds `users.rank` — Plan 2 Task 1 references `session.rank` from snapshot of `u.rank`. ✅

**Scope boundary:**
- Distribution module (3 pages + distribution.ts) NOT modified here — only Sidebar entries hidden (Task 9). Matches §4.8. ✅
- DB admin panel NOT implemented here — delegated to Plan 4. ✅
- E2E tests NOT written here — delegated to Plan 3. ✅
- Agent 设置页面 explicitly NOT modified (per user instruction "Agent设置页面暂时不做任何改动") — confirmed absent from File Structure. ✅
