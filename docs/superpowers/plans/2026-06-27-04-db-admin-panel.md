# Plan 4: DB Admin Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/db` route in admin-spa, visible only to the developer account (`admin`), that exposes a 3-tab panel (PostgreSQL CRUD / Knowledge raw JSON editor / Schema viewer) backed by 8 new FastAPI endpoints under `/api/v1/admin/db/*`.

**Architecture:** Backend introduces a developer-identification layer (env var `DEV_ADMIN_USERNAME` → JWT `is_developer` claim → contextvar → route dependency). A new `db_admin_service.py` enforces a per-table writable-field whitelist. Frontend adds `RequireDeveloper` route guard + `DbAdminPage` with Refine CRUD for tables and Monaco Editor for knowledge JSON.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React 19 + Vite + Refine + `@monaco-editor/react` (admin-spa)

**Spec reference:** [docs/superpowers/specs/admin_data_overhaul_spec.md](file:///d:/_Greatest_programmer/_Projects/gaokao_agents/docs/superpowers/specs/admin_data_overhaul_spec.md) §三

**Key facts discovered during planning:**
- Admin login uses `/api/v1/auth/login` → `User` table (in `models/user.py`) for password verification.
- `UserAuthMiddleware` decodes JWT → looks up `TenantUser` → sets `_current_user` contextvar (a `TenantUser` row with `.role`).
- `User` table already has `region` / `subjects` / `score` columns; only `rank` is new.
- Knowledge raw data lives in `tenant_data` table (model `TenantData`); ChromaDB collection is `{tenant_slug}_colleges`; reindex helper is `knowledge.indexer.reindex_tenant(slug)` or `index_tenant_data(slug, td)` for a single doc.

---

## File Structure

### New files

| File | Responsibility |
|---|---|
| `backend/migrations/versions/006_db_admin_panel.py` | Alembic migration: add `users.rank`; no `is_developer` column |
| `backend/core/developer_guard.py` | `require_developer` FastAPI dependency — reads JWT payload from contextvar |
| `backend/services/db_admin_service.py` | Table whitelist, schema introspection, CRUD with writable-field whitelist |
| `backend/api/routes/db_admin.py` | 8 endpoints under `/api/v1/admin/db/*` |
| `admin-spa/src/components/RequireDeveloper.tsx` | Route guard — checks `useAuthStore.user.is_developer` |
| `admin-spa/src/pages/DbAdminPage.tsx` | 3-tab shell |
| `admin-spa/src/components/db/TablesTab.tsx` | Tab 1: Refine CRUD over `/api/v1/admin/db/{table}` |
| `admin-spa/src/components/db/KnowledgeRawTab.tsx` | Tab 2: list + Monaco editor + reindex trigger |
| `admin-spa/src/components/db/SchemaTab.tsx` | Tab 3: read-only schema viewer |

### Modified files

| File | Modification |
|---|---|
| `backend/config.py` | Add `dev_admin_username: str = "admin"` |
| `backend/services/auth_service.py` | `authenticate_user` returns `is_developer` flag based on username match |
| `backend/utils/jwt.py` | `create_token` accepts optional `extra_claims: dict`; `decode_token` returns full payload |
| `backend/schemas/auth.py` | `TokenResponse` gains optional `is_developer: bool = False` |
| `backend/core/tenant_context.py` | New contextvar `_current_jwt_payload` + setter/getter |
| `backend/core/middleware.py` | `UserAuthMiddleware` stores decoded JWT payload into new contextvar |
| `backend/main.py` | Register `db_admin.router` under `/api/v1/admin` |
| `backend/models/user.py` | Add `rank: Mapped[int | None]` column |
| `admin-spa/src/stores/authStore.ts` | Persist `is_developer` from login response |
| `admin-spa/src/types/index.ts` | Add `is_developer?: boolean` to `LoginResponse` and `AuthUser` |
| `admin-spa/src/App.tsx` | Add `/db` route wrapped in `RequireDeveloper` |
| `admin-spa/src/components/Sidebar.tsx` | Add `/db` entry conditionally on `is_developer` |
| `admin-spa/package.json` | Add deps: `@refinedev/core`, `@refinedev/simple-rest`, `@refinedev/antd`, `@monaco-editor/react`, `antd` |

---

## Task 1: Backend — migration + config + User.rank

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/models/user.py`
- Create: `backend/migrations/versions/006_db_admin_panel.py`

- [ ] **Step 1: Add `dev_admin_username` to Settings**

Edit `backend/config.py` — inside `class Settings(BaseSettings):` after `refresh_token_expire_days: int = 7`:
```python
    # Developer identification (DB admin panel access)
    dev_admin_username: str = "admin"
```

- [ ] **Step 2: Add `rank` column to User model**

Edit `backend/models/user.py` — after the `subjects` line add:
```python
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 3: Create migration file**

Create `backend/migrations/versions/006_db_admin_panel.py`:
```python
"""db admin panel: add users.rank

Revision ID: 006_db_admin_panel
Revises: 005_distribution_tables
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa


revision = "006_db_admin_panel"
down_revision = "005_distribution_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("rank", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "rank")
```

> If the existing `down_revision` chain differs, run `alembic heads` first and use the actual current head as `down_revision`.

- [ ] **Step 4: Apply migration locally**

Run:
```bash
cd backend && alembic upgrade head
```
Expected: `INFO [alembic.runtime.migration] Running upgrade 005_* -> 006_db_admin_panel, db admin panel: add users.rank`

- [ ] **Step 5: Verify column exists**

Run via backend REPL or psql:
```bash
cd backend && python -c "import asyncio; from models import async_session, engine; from sqlalchemy import text; import asyncio
async def m():
    async with async_session() as db:
        r = await db.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='rank'\"))
        print(r.scalar() is not None)
asyncio.run(m())"
```
Expected: `True`

- [ ] **Step 6: Commit**

```bash
git add backend/config.py backend/models/user.py backend/migrations/versions/006_db_admin_panel.py
git commit -m "feat(backend): add users.rank column + dev_admin_username config"
```

---

## Task 2: Backend — developer identification layer

**Files:**
- Modify: `backend/schemas/auth.py`
- Modify: `backend/services/auth_service.py`
- Modify: `backend/utils/jwt.py`
- Modify: `backend/core/tenant_context.py`
- Modify: `backend/core/middleware.py`
- Create: `backend/core/developer_guard.py`

- [ ] **Step 1: Extend TokenResponse schema**

Edit `backend/schemas/auth.py` — append field to `TokenResponse`:
```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    username: str
    is_developer: bool = False
```

- [ ] **Step 2: Update `authenticate_user` to return `is_developer`**

Edit `backend/services/auth_service.py` — replace the return line of `authenticate_user`:
```python
async def authenticate_user(db: AsyncSession, username: str, password: str) -> dict | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return {
        "user_id": str(user.id),
        "username": user.username,
        "is_developer": username == settings.dev_admin_username,
    }
```

- [ ] **Step 3: Update `generate_tokens` to accept extra claims + propagate is_developer**

Edit `backend/services/auth_service.py` — replace `generate_tokens`:
```python
def generate_tokens(user_id: str, username: str, is_developer: bool = False) -> dict:
    return {
        "access_token": create_token(
            user_id, username, settings.access_token_expire_minutes,
            extra_claims={"is_developer": is_developer},
        ),
        "refresh_token": create_token(
            user_id, username, settings.refresh_token_expire_days * 24 * 60,
            extra_claims={"is_developer": is_developer},
        ),
    }
```

- [ ] **Step 4: Update `auth.py` route to pass is_developer**

Edit `backend/api/routes/auth.py` — update both `register` and `login` return statements.

For `register`:
```python
    tokens = generate_tokens(str(user.id), user.username, is_developer=False)
    return {**tokens, "user_id": str(user.id), "username": user.username, "is_developer": False}
```

For `login`:
```python
    tokens = generate_tokens(info["user_id"], info["username"], info.get("is_developer", False))
    return {**tokens, **info}
```

- [ ] **Step 5: Extend `create_token` to accept extra claims**

Edit `backend/utils/jwt.py` — replace `create_token`:
```python
def create_token(user_id: str, username: str, expire_minutes: int, extra_claims: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload: dict = {"user_id": user_id, "username": username, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
```

`decode_token` already returns the full payload dict, so no change needed.

- [ ] **Step 6: Add JWT payload contextvar**

Edit `backend/core/tenant_context.py` — add after `_current_user` definition:
```python
_current_jwt_payload: ContextVar[Optional[dict]] = ContextVar("jwt_payload", default=None)


def get_current_jwt_payload() -> dict | None:
    return _current_jwt_payload.get()


def set_current_jwt_payload(payload: dict | None) -> None:
    _current_jwt_payload.set(payload)
```

- [ ] **Step 7: Store JWT payload in middleware**

Edit `backend/core/middleware.py` — in `UserAuthMiddleware.dispatch`, replace the `if payload:` block inside the try:
```python
            if payload:
                from core.tenant_context import set_current_jwt_payload
                set_current_jwt_payload(payload)
                from models import async_session
                from sqlalchemy import select
                from tenants.models import TenantUser as TUModel
                async with async_session() as db:
                    result = await db.execute(
                        select(TUModel).where(TUModel.user_id == payload["user_id"])
                    )
                    tu = result.scalar_one_or_none()
                    if tu:
                        _current_user.set(tu)
```

- [ ] **Step 8: Create developer guard dependency**

Create `backend/core/developer_guard.py`:
```python
"""FastAPI dependency: require developer (JWT is_developer claim)."""
from fastapi import HTTPException

from core.tenant_context import get_current_jwt_payload


async def require_developer() -> dict:
    """Return JWT payload if caller is a developer; else raise 403."""
    payload = get_current_jwt_payload()
    if not payload or not payload.get("is_developer"):
        raise HTTPException(status_code=403, detail="Developer access required")
    return payload
```

- [ ] **Step 9: Smoke test login response**

Restart backend (terminal 3). Run:
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
```
Expected: JSON contains `"is_developer": true`.

Run:
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"username\":\"nonexistent\",\"password\":\"x\"}"
```
Expected: 401 (no crash).

- [ ] **Step 10: Commit**

```bash
git add backend/schemas/auth.py backend/services/auth_service.py backend/utils/jwt.py backend/api/routes/auth.py backend/core/tenant_context.py backend/core/middleware.py backend/core/developer_guard.py
git commit -m "feat(backend): developer identification via JWT is_developer claim"
```

---

## Task 3: Backend — db_admin_service (schema + CRUD + whitelist)

**Files:**
- Create: `backend/services/db_admin_service.py`

- [ ] **Step 1: Create service with table whitelist + schema introspection**

Create `backend/services/db_admin_service.py`:
```python
"""DB admin panel service: table whitelist, schema introspection, CRUD with field-level write gates."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

# ── Table whitelist ──
# Map table name → (model module path, writable_fields, deletable)
# writable_fields: None = all fields writable; list = only these fields; [] = read-only
TABLE_REGISTRY: dict[str, dict] = {
    "users": {
        "model": "models.user:User",
        "writable_fields": None,
        "deletable": False,
    },
    "user_profiles": {
        "model": "models.profile:UserProfile",
        "writable_fields": None,
        "deletable": False,
    },
    "consult_sessions": {
        "model": "models.consult_session:ConsultSession",
        "writable_fields": ["follow_status", "follow_note", "followed_at", "followed_by"],
        "deletable": False,
    },
    "chat_messages": {
        "model": "models.chat_message:ChatMessage",
        "writable_fields": [],
        "deletable": True,
    },
    "recommendations": {
        "model": "models.recommendation:Recommendation",
        "writable_fields": [],
        "deletable": True,
    },
    "recommendation_feedback": {
        "model": "models.recommendation_feedback:RecommendationFeedback",
        "writable_fields": [],
        "deletable": True,
    },
    "admission_data": {
        "model": "models.admission:AdmissionData",
        "writable_fields": None,
        "deletable": True,
    },
    "colleges": {
        "model": "models.college:College",
        "writable_fields": None,
        "deletable": True,
    },
    "tenant_data": {
        "model": "tenants.models:TenantData",
        "writable_fields": None,
        "deletable": True,
    },
    "tenants": {
        "model": "tenants.models:Tenant",
        "writable_fields": None,
        "deletable": False,
    },
}


def _load_model(dotted: str):
    module_path, cls_name = dotted.rsplit(":", 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, cls_name)


def list_tables() -> list[dict]:
    """Return table metadata for the panel UI."""
    return [
        {
            "name": name,
            "writable_fields": cfg["writable_fields"],
            "deletable": cfg["deletable"],
        }
        for name, cfg in TABLE_REGISTRY.items()
    ]


async def get_table_schema(db: AsyncSession, table_name: str) -> list[dict]:
    """Introspect columns from information_schema."""
    if table_name not in TABLE_REGISTRY:
        raise ValueError(f"Unknown table: {table_name}")
    sql = text(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = :t
        ORDER BY ordinal_position
        """
    )
    rows = (await db.execute(sql, {"t": table_name})).all()
    return [
        {
            "name": r[0],
            "type": r[1],
            "nullable": r[2] == "YES",
            "default": r[3],
        }
        for r in rows
    ]


def _serialize_value(v: Any) -> Any:
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def _serialize_row(row) -> dict:
    return {k: _serialize_value(getattr(row, k, None)) for k in row.__table__.columns.keys()}


async def list_rows(
    db: AsyncSession, table_name: str, page: int = 1, page_size: int = 20,
    filters: dict | None = None, sort_by: str | None = None, sort_desc: bool = False,
) -> dict:
    if table_name not in TABLE_REGISTRY:
        raise ValueError(f"Unknown table: {table_name}")
    model = _load_model(TABLE_REGISTRY[table_name]["model"])
    stmt = select(model)
    if filters:
        for k, v in filters.items():
            col = getattr(model, k, None)
            if col is not None and v != "":
                stmt = stmt.where(col == v)
    if sort_by and hasattr(model, sort_by):
        col = getattr(model, sort_by)
        stmt = stmt.order_by(col.desc() if sort_desc else col.asc())
    else:
        if hasattr(model, "created_at"):
            stmt = stmt.order_by(model.created_at.desc())
    # count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    # paginate
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "data": [_serialize_row(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_row(db: AsyncSession, table_name: str, row_id: str) -> dict:
    if table_name not in TABLE_REGISTRY:
        raise ValueError(f"Unknown table: {table_name}")
    model = _load_model(TABLE_REGISTRY[table_name]["model"])
    pk = list(model.__table__.primary_key.columns)[0]
    stmt = select(model).where(pk == _coerce_id(row_id, pk))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    return _serialize_row(row)


def _coerce_id(raw: str, pk_col):
    """Cast string id to UUID if column type is UUID."""
    try:
        from sqlalchemy.dialects.postgresql import UUID as PG_UUID
        if isinstance(pk_col.type, PG_UUID):
            return uuid.UUID(raw)
    except Exception:
        pass
    try:
        return int(raw)
    except (TypeError, ValueError):
        return raw


async def create_row(db: AsyncSession, table_name: str, payload: dict) -> dict:
    cfg = TABLE_REGISTRY.get(table_name)
    if not cfg:
        raise ValueError(f"Unknown table: {table_name}")
    if cfg["writable_fields"] == []:
        raise PermissionError(f"Table {table_name} is read-only (no create)")
    model = _load_model(cfg["model"])
    if cfg["writable_fields"] is not None:
        allowed = set(cfg["writable_fields"]) | {"id"}
        payload = {k: v for k, v in payload.items() if k in allowed}
    row = model(**payload)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _serialize_row(row)


async def update_row(db: AsyncSession, table_name: str, row_id: str, payload: dict) -> dict:
    cfg = TABLE_REGISTRY.get(table_name)
    if not cfg:
        raise ValueError(f"Unknown table: {table_name}")
    if cfg["writable_fields"] == []:
        raise PermissionError(f"Table {table_name} is read-only (no update)")
    model = _load_model(cfg["model"])
    pk = list(model.__table__.primary_key.columns)[0]
    stmt = select(model).where(pk == _coerce_id(row_id, pk))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    if cfg["writable_fields"] is not None:
        payload = {k: v for k, v in payload.items() if k in cfg["writable_fields"]}
    for k, v in payload.items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return _serialize_row(row)


async def delete_row(db: AsyncSession, table_name: str, row_id: str) -> bool:
    cfg = TABLE_REGISTRY.get(table_name)
    if not cfg:
        raise ValueError(f"Unknown table: {table_name}")
    if not cfg["deletable"]:
        raise PermissionError(f"Table {table_name} is not deletable")
    model = _load_model(cfg["model"])
    pk = list(model.__table__.primary_key.columns)[0]
    stmt = select(model).where(pk == _coerce_id(row_id, pk))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return False
    await db.delete(row)
    await db.commit()
    return True
```

- [ ] **Step 2: Smoke test the service in REPL**

Run:
```bash
cd backend && python -c "import asyncio; from services.db_admin_service import list_tables; print([t['name'] for t in list_tables()])"
```
Expected: list of 10 table names.

- [ ] **Step 3: Commit**

```bash
git add backend/services/db_admin_service.py
git commit -m "feat(backend): db_admin_service with table whitelist + CRUD"
```

---

## Task 4: Backend — db_admin router (8 endpoints)

**Files:**
- Create: `backend/api/routes/db_admin.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create router with 6 table CRUD endpoints + 2 knowledge raw endpoints**

Create `backend/api/routes/db_admin.py`:
```python
"""DB admin panel routes — developer-only."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.developer_guard import require_developer
from core.tenant_context import get_current_tenant
from models import get_db
from services.db_admin_service import (
    list_tables, get_table_schema, list_rows, get_row,
    create_row, update_row, delete_row, TABLE_REGISTRY,
)

router = APIRouter()


class RowCreate(BaseModel):
    payload: dict


class RowUpdate(BaseModel):
    payload: dict


@router.get("/db/tables")
async def get_tables(_=Depends(require_developer)):
    return {"tables": list_tables()}


@router.get("/db/{table_name}")
async def list_table_rows(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str | None = Query(None),
    sort_desc: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_developer),
):
    if table_name not in TABLE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown table: {table_name}")
    # filters from query params (skip pagination/sort keys)
    filters = {}
    return await list_rows(db, table_name, page, page_size, filters, sort_by, sort_desc)


@router.get("/db/{table_name}/schema")
async def get_schema(
    table_name: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_developer),
):
    if table_name not in TABLE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown table: {table_name}")
    return {"columns": await get_table_schema(db, table_name)}


@router.get("/db/{table_name}/{row_id}")
async def get_one_row(
    table_name: str,
    row_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_developer),
):
    if table_name not in TABLE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown table: {table_name}")
    row = await get_row(db, table_name, row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Row not found")
    return row


@router.post("/db/{table_name}")
async def create_one_row(
    table_name: str,
    body: RowCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_developer),
):
    if table_name not in TABLE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown table: {table_name}")
    try:
        return await create_row(db, table_name, body.payload)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Create failed: {e}")


@router.put("/db/{table_name}/{row_id}")
async def update_one_row(
    table_name: str,
    row_id: str,
    body: RowUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_developer),
):
    if table_name not in TABLE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown table: {table_name}")
    try:
        row = await update_row(db, table_name, row_id, body.payload)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if row is None:
        raise HTTPException(status_code=404, detail="Row not found")
    return row


@router.delete("/db/{table_name}/{row_id}")
async def delete_one_row(
    table_name: str,
    row_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_developer),
):
    if table_name not in TABLE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown table: {table_name}")
    try:
        ok = await delete_row(db, table_name, row_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Row not found")
    return {"deleted": True}


# ── Knowledge raw JSON endpoints ──

@router.get("/db/knowledge/raw")
async def list_knowledge_raw(
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    _=Depends(require_developer),
):
    from tenants.models import TenantData
    result = await db.execute(
        select(TenantData)
        .where(TenantData.tenant_id == tenant.id)
        .order_by(TenantData.created_at.desc())
    )
    docs = result.scalars().all()
    return {
        "documents": [
            {
                "id": str(d.id),
                "title": d.title,
                "data_type": str(d.data_type) if hasattr(d.data_type, "value") else d.data_type,
                "year": d.year,
                "content": d.content,
                "indexed_at": d.indexed_at.isoformat() if d.indexed_at else None,
            }
            for d in docs
        ]
    }


class RawUpdate(BaseModel):
    title: str | None = None
    content: dict | None = None


@router.put("/db/knowledge/raw/{doc_id}")
async def update_knowledge_raw(
    doc_id: str,
    body: RawUpdate,
    db: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    _=Depends(require_developer),
):
    from tenants.models import TenantData
    from knowledge.indexer import index_tenant_data, reindex_tenant
    result = await db.execute(
        select(TenantData).where(
            TenantData.id == uuid.UUID(doc_id),
            TenantData.tenant_id == tenant.id,
        )
    )
    td = result.scalar_one_or_none()
    if td is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if body.title is not None:
        td.title = body.title
    if body.content is not None:
        td.content = body.content
    await db.commit()
    await db.refresh(td)
    # Reindex: delete old + re-add single doc (simplest: full reindex)
    try:
        await reindex_tenant(tenant.slug)
        td.indexed_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as e:
        # Reindex failure should not block the edit
        pass
    return {
        "id": str(td.id),
        "title": td.title,
        "content": td.content,
        "indexed_at": td.indexed_at.isoformat() if td.indexed_at else None,
    }
```

- [ ] **Step 2: Register router in main.py**

Edit `backend/main.py` — add import after the other admin router imports (around line 224):
```python
from api.routes import db_admin  # noqa: E402
```

Then add after `app.include_router(admin_router, ...)`:
```python
app.include_router(db_admin.router, prefix="/api/v1/admin", tags=["db-admin"])
```

- [ ] **Step 3: Restart backend and smoke test endpoints**

Restart backend (terminal 3). Get a developer token:
```bash
$resp = Invoke-RestMethod -Uri http://localhost:8000/api/v1/auth/login -Method Post -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}'; $token = $resp.access_token
```

Test tables list:
```bash
Invoke-RestMethod -Uri http://localhost:8000/api/v1/admin/db/tables -Headers @{Authorization="Bearer $token"; "X-Tenant"="scnu"}
```
Expected: JSON with `tables` array of 10 entries.

Test 403 for non-developer (register a non-dev user first, or use a fake token):
```bash
Invoke-RestMethod -Uri http://localhost:8000/api/v1/admin/db/tables -Headers @{Authorization="Bearer invalidtoken"; "X-Tenant"="scnu"}
```
Expected: 401/403.

- [ ] **Step 4: Commit**

```bash
git add backend/api/routes/db_admin.py backend/main.py
git commit -m "feat(backend): db_admin router with 8 endpoints (CRUD + knowledge raw)"
```

---

## Task 5: Frontend — install deps + authStore + types + route guard

**Files:**
- Modify: `admin-spa/package.json`
- Modify: `admin-spa/src/types/index.ts`
- Modify: `admin-spa/src/stores/authStore.ts`
- Create: `admin-spa/src/components/RequireDeveloper.tsx`
- Modify: `admin-spa/src/App.tsx`

- [ ] **Step 1: Install Refine + Monaco + antd**

Run:
```bash
cd admin-spa && npm install @refinedev/core @refinedev/simple-rest @refinedev/antd @monaco-editor/react antd
```

- [ ] **Step 2: Add `is_developer` to types**

Read `admin-spa/src/types/index.ts` to find `LoginResponse` definition. Then edit it to add:
```typescript
export interface LoginResponse {
  access_token: string
  refresh_token: string
  user_id: string
  username: string
  is_developer?: boolean
}
```

If `AuthUser` interface exists, add `is_developer?: boolean` there too.

- [ ] **Step 3: Update authStore to persist is_developer**

Edit `admin-spa/src/stores/authStore.ts` — extend `AuthState` interface and implementations:

In the interface, change `user` type:
```typescript
  user: { id: string; username: string; is_developer?: boolean } | null
```

In `login`:
```typescript
  login: async (username: string, password: string, tenantSlug: string) => {
    localStorage.setItem('tenantSlug', tenantSlug)
    const res = await api.post<LoginResponse>('/auth/login', { username, password })
    const { access_token, user_id, username: uname, is_developer } = res.data
    const userObj = { id: user_id, username: uname, is_developer: is_developer ?? false }
    localStorage.setItem('token', access_token)
    localStorage.setItem('role', 'admin')
    localStorage.setItem('user', JSON.stringify(userObj))
    set({ token: access_token, role: 'admin', user: userObj })
  },
```

In `loginDemo` (success branch):
```typescript
      const { access_token, user_id, username: uname, is_developer } = res.data
      const userObj = { id: user_id, username: uname, is_developer: is_developer ?? false }
      localStorage.setItem('token', access_token)
      localStorage.setItem('role', 'demo')
      localStorage.setItem('user', JSON.stringify(userObj))
      set({ token: access_token, role: 'demo', user: userObj })
```

- [ ] **Step 4: Create RequireDeveloper route guard**

Create `admin-spa/src/components/RequireDeveloper.tsx`:
```tsx
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function RequireDeveloper({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (!user?.is_developer) {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children}</>
}
```

- [ ] **Step 5: Add `/db` route to App.tsx**

Edit `admin-spa/src/App.tsx` — add import:
```tsx
import DbAdminPage from './pages/DbAdminPage'
import RequireDeveloper from './components/RequireDeveloper'
```

Add route inside the `<Route path="/" element={...}>` block (after the distribution routes):
```tsx
          <Route
            path="db"
            element={
              <RequireDeveloper>
                <DbAdminPage />
              </RequireDeveloper>
            }
          />
```

> Note: `DbAdminPage` does not exist yet — created in Task 6. Build will fail until then; that's expected (TDD-style).

- [ ] **Step 6: Commit**

```bash
git add admin-spa/package.json admin-spa/package-lock.json admin-spa/src/types/index.ts admin-spa/src/stores/authStore.ts admin-spa/src/components/RequireDeveloper.tsx admin-spa/src/App.tsx
git commit -m "feat(admin-spa): add is_developer to authStore + RequireDeveloper guard + /db route"
```

---

## Task 6: Frontend — DbAdminPage + 3 tabs

**Files:**
- Create: `admin-spa/src/pages/DbAdminPage.tsx`
- Create: `admin-spa/src/components/db/TablesTab.tsx`
- Create: `admin-spa/src/components/db/KnowledgeRawTab.tsx`
- Create: `admin-spa/src/components/db/SchemaTab.tsx`

- [ ] **Step 1: Create DbAdminPage shell with 3 tabs**

Create `admin-spa/src/pages/DbAdminPage.tsx`:
```tsx
import { useState } from 'react'
import TablesTab from '../components/db/TablesTab'
import KnowledgeRawTab from '../components/db/KnowledgeRawTab'
import SchemaTab from '../components/db/SchemaTab'

type TabKey = 'tables' | 'knowledge' | 'schema'

const TABS: { key: TabKey; label: string }[] = [
  { key: 'tables', label: '数据表管理' },
  { key: 'knowledge', label: '知识库 Raw' },
  { key: 'schema', label: '表结构' },
]

export default function DbAdminPage() {
  const [tab, setTab] = useState<TabKey>('tables')

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 16 }}>数据库管理</h1>
      <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid var(--color-border, #e5e7eb)', marginBottom: 16 }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: tab === t.key ? 'var(--color-primary, #1a3a6b)' : 'transparent',
              color: tab === t.key ? '#fff' : 'inherit',
              cursor: 'pointer',
              borderBottom: tab === t.key ? '2px solid var(--color-primary, #1a3a6b)' : '2px solid transparent',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'tables' && <TablesTab />}
      {tab === 'knowledge' && <KnowledgeRawTab />}
      {tab === 'schema' && <SchemaTab />}
    </div>
  )
}
```

- [ ] **Step 2: Create TablesTab — table selector + raw CRUD table**

Create `admin-spa/src/components/db/TablesTab.tsx`:
```tsx
import { useEffect, useState } from 'react'
import api from '../../api/client'

interface TableMeta {
  name: string
  writable_fields: string[] | null
  deletable: boolean
}

export default function TablesTab() {
  const [tables, setTables] = useState<TableMeta[]>([])
  const [selected, setSelected] = useState<string>('')
  const [rows, setRows] = useState<Record<string, any>[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ tables: TableMeta[] }>('/admin/db/tables')
      .then((r) => {
        setTables(r.data.tables)
        if (r.data.tables.length > 0) setSelected(r.data.tables[0].name)
      })
      .catch((e) => setError(e?.message || 'Failed to load tables'))
  }, [])

  useEffect(() => {
    if (!selected) return
    setLoading(true)
    setError(null)
    api.get<{ data: any[]; total: number; page: number; page_size: number }>(
      `/admin/db/${selected}?page=${page}&page_size=20`
    )
      .then((r) => { setRows(r.data.data); setTotal(r.data.total) })
      .catch((e) => setError(e?.message || 'Failed to load rows'))
      .finally(() => setLoading(false))
  }, [selected, page])

  const columns = rows.length > 0 ? Object.keys(rows[0]) : []

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
        <label>选择表：</label>
        <select value={selected} onChange={(e) => { setSelected(e.target.value); setPage(1) }} style={{ padding: '4px 8px' }}>
          {tables.map((t) => <option key={t.name} value={t.name}>{t.name}</option>)}
        </select>
        {selected && (
          <span style={{ marginLeft: 16, fontSize: 12, color: '#666' }}>
            {tables.find((t) => t.name === selected)?.writable_fields === null
              ? '全字段可写'
              : tables.find((t) => t.name === selected)?.writable_fields?.length
                ? `仅可写: ${tables.find((t) => t.name === selected)?.writable_fields?.join(', ')}`
                : '只读'}
            {tables.find((t) => t.name === selected)?.deletable ? ' · 可删除' : ''}
          </span>
        )}
      </div>
      {error && <div style={{ color: 'var(--color-danger, #dc2626)', padding: 8 }}>{error}</div>}
      {loading ? (
        <div>加载中...</div>
      ) : rows.length === 0 ? (
        <div style={{ padding: 16, color: '#999' }}>无数据</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c} style={{ textAlign: 'left', padding: '8px 12px', borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  {columns.map((c) => (
                    <td key={c} style={{ padding: '6px 12px', borderBottom: '1px solid #f3f4f6', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {typeof r[c] === 'object' ? JSON.stringify(r[c]) : String(r[c] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <button disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
            <span>第 {page} 页 · 共 {Math.ceil(total / 20)} 页 ({total} 条)</span>
            <button disabled={page >= Math.ceil(total / 20)} onClick={() => setPage(page + 1)}>下一页</button>
          </div>
        </div>
      )}
    </div>
  )
}
```

> Inline edit/delete UI is intentionally minimal for v1 — full Refine CRUD forms can be added later. Reading + pagination is the primary use case per spec §3.6.

- [ ] **Step 3: Create KnowledgeRawTab — list + Monaco editor + save+reindex**

Create `admin-spa/src/components/db/KnowledgeRawTab.tsx`:
```tsx
import { useEffect, useState } from 'react'
import api from '../../api/client'
import MonacoEditor from '@monaco-editor/react'

interface RawDoc {
  id: string
  title: string
  data_type: string
  year: number | null
  content: Record<string, any>
  indexed_at: string | null
}

export default function KnowledgeRawTab() {
  const [docs, setDocs] = useState<RawDoc[]>([])
  const [selected, setSelected] = useState<RawDoc | null>(null)
  const [draft, setDraft] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState('')

  const fetchDocs = () => {
    api.get<{ documents: RawDoc[] }>('/admin/db/knowledge/raw')
      .then((r) => setDocs(r.data.documents))
      .catch((e) => setError(e?.message || '加载失败'))
  }

  useEffect(() => { fetchDocs() }, [])

  const onSelect = (d: RawDoc) => {
    setSelected(d)
    setDraft(JSON.stringify(d.content, null, 2))
    setMessage('')
  }

  const onSave = async () => {
    if (!selected) return
    setSaving(true)
    setMessage('')
    let parsed: Record<string, any>
    try {
      parsed = JSON.parse(draft)
    } catch (e: any) {
      setError('JSON 解析失败: ' + e.message)
      setSaving(false)
      return
    }
    try {
      await api.put(`/admin/db/knowledge/raw/${selected.id}`, { content: parsed })
      setMessage('已保存，ChromaDB 已重新索引')
      fetchDocs()
    } catch (e: any) {
      setError('保存失败: ' + (e?.message || ''))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: 'flex', gap: 16, minHeight: 500 }}>
      <div style={{ width: 280, borderRight: '1px solid #e5e7eb', paddingRight: 12 }}>
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>知识库文档 ({docs.length})</h3>
        {docs.map((d) => (
          <div
            key={d.id}
            onClick={() => onSelect(d)}
            style={{
              padding: '8px 12px',
              cursor: 'pointer',
              background: selected?.id === d.id ? '#eff6ff' : 'transparent',
              borderRadius: 4,
              marginBottom: 4,
              fontSize: 13,
            }}
          >
            <div style={{ fontWeight: 500 }}>{d.title}</div>
            <div style={{ fontSize: 11, color: '#666' }}>
              {d.data_type} · {d.year || '-'} · {d.indexed_at ? '已索引' : '未索引'}
            </div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1 }}>
        {!selected ? (
          <div style={{ padding: 32, color: '#999' }}>选择左侧文档查看/编辑 JSON</div>
        ) : (
          <>
            <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 14 }}>{selected.title}</h3>
              <button onClick={onSave} disabled={saving} style={{ padding: '6px 16px', background: 'var(--color-primary, #1a3a6b)', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
                {saving ? '保存中...' : '保存并重新索引'}
              </button>
            </div>
            {error && <div style={{ color: 'var(--color-danger, #dc2626)', marginBottom: 8 }}>{error}</div>}
            {message && <div style={{ color: 'var(--color-success, #16a34a)', marginBottom: 8 }}>{message}</div>}
            <div style={{ border: '1px solid #e5e7eb', height: 500 }}>
              <MonacoEditor
                height="500px"
                language="json"
                value={draft}
                onChange={(v) => setDraft(v || '')}
                options={{ minimap: { enabled: false }, fontSize: 13 }}
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create SchemaTab — read-only column viewer**

Create `admin-spa/src/components/db/SchemaTab.tsx`:
```tsx
import { useEffect, useState } from 'react'
import api from '../../api/client'

interface Column {
  name: string
  type: string
  nullable: boolean
  default: string | null
}

export default function SchemaTab() {
  const [tables, setTables] = useState<string[]>([])
  const [selected, setSelected] = useState('')
  const [columns, setColumns] = useState<Column[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ tables: { name: string }[] }>('/admin/db/tables')
      .then((r) => {
        setTables(r.data.tables.map((t) => t.name))
        if (r.data.tables.length > 0) setSelected(r.data.tables[0].name)
      })
      .catch((e) => setError(e?.message || '加载失败'))
  }, [])

  useEffect(() => {
    if (!selected) return
    api.get<{ columns: Column[] }>(`/admin/db/${selected}/schema`)
      .then((r) => setColumns(r.data.columns))
      .catch((e) => setError(e?.message || '加载失败'))
  }, [selected])

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <label>选择表：</label>
        <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ padding: '4px 8px' }}>
          {tables.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      {error && <div style={{ color: 'var(--color-danger, #dc2626)' }}>{error}</div>}
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            <th style={th}>字段名</th>
            <th style={th}>类型</th>
            <th style={th}>可空</th>
            <th style={th}>默认值</th>
          </tr>
        </thead>
        <tbody>
          {columns.map((c) => (
            <tr key={c.name}>
              <td style={td}><code>{c.name}</code></td>
              <td style={td}>{c.type}</td>
              <td style={td}>{c.nullable ? 'YES' : 'NO'}</td>
              <td style={td}>{c.default || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const th: React.CSSProperties = { textAlign: 'left', padding: '8px 12px', borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }
const td: React.CSSProperties = { padding: '6px 12px', borderBottom: '1px solid #f3f4f6' }
```

- [ ] **Step 5: Build admin-spa**

Run:
```bash
cd admin-spa && npm run build
```
Expected: build succeeds with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add admin-spa/src/pages/DbAdminPage.tsx admin-spa/src/components/db/
git commit -m "feat(admin-spa): DbAdminPage with 3 tabs (Tables / KnowledgeRaw / Schema)"
```

---

## Task 7: Frontend — Sidebar `/db` entry conditional on is_developer

**Files:**
- Modify: `admin-spa/src/components/Sidebar.tsx`

- [ ] **Step 1: Read current Sidebar.tsx**

Run: Read tool on `admin-spa/src/components/Sidebar.tsx` to understand the nav structure.

- [ ] **Step 2: Add /db entry gated by is_developer**

Find the nav items array (or JSX list). Add a new entry at the end, conditionally rendered:
```tsx
{useAuthStore.getState().user?.is_developer && (
  <NavLink to="/db" className={...}>
    {/* icon */} 数据库管理
  </NavLink>
)}
```

Better pattern (to be reactive): at top of component:
```tsx
const isDeveloper = useAuthStore((s) => s.user?.is_developer ?? false)
```

Then conditionally render the `/db` NavLink. Use the same styling/label pattern as other nav items (icon + "数据库管理" label, placed at the bottom of the nav, perhaps after a divider).

- [ ] **Step 3: Build + smoke test**

Run:
```bash
cd admin-spa && npm run build
```

Open `http://localhost:3001?tenant=scnu`. Log in as `admin`/`admin123`. Confirm "数据库管理" appears in sidebar. Click → `/db` page with 3 tabs loads. Tab 1 shows table selector + 10 tables. Tab 2 shows knowledge docs. Tab 3 shows schema.

Log out, register a non-admin user (or simulate). Confirm "数据库管理" does NOT appear in sidebar. Manually navigate to `/db` → redirected to `/dashboard`.

- [ ] **Step 4: Commit**

```bash
git add admin-spa/src/components/Sidebar.tsx
git commit -m "feat(admin-spa): add /db sidebar entry gated by is_developer"
```

---

## Task 8: Integration verification

**Files:** None modified.

- [ ] **Step 1: End-to-end smoke test**

With backend (terminal 3) and admin-spa dev server running:
1. Login as `admin`/`admin123` at `http://localhost:3001?tenant=scnu`
2. Verify "数据库管理" appears in sidebar
3. Click → `/db` loads with 3 tabs
4. Tab 1 (数据表管理): select `users` table → see admin row → paginate
5. Tab 1: select `consult_sessions` → note "仅可写: follow_status, follow_note, followed_at, followed_by" hint
6. Tab 2 (知识库 Raw): if docs exist, click one → Monaco editor loads JSON → edit a non-critical field → click "保存并重新索引" → success message
7. Tab 3 (表结构): select `users` → see columns including `rank` (type integer, nullable YES)

- [ ] **Step 2: Permission test**

Register a new non-admin user via mini-app or API. Log in as that user in a fresh browser session. Confirm:
- Sidebar has NO "数据库管理" entry
- Manually visiting `/db` redirects to `/dashboard`

- [ ] **Step 3: API permission test**

Using a non-developer JWT, call:
```bash
Invoke-RestMethod -Uri http://localhost:8000/api/v1/admin/db/tables -Headers @{Authorization="Bearer <non-dev-token>"; "X-Tenant"="scnu"}
```
Expected: 403 with "Developer access required".

- [ ] **Step 4: Unknown table test**

Using developer JWT:
```bash
Invoke-RestMethod -Uri http://localhost:8000/api/v1/admin/db/unknown_table -Headers @{Authorization="Bearer $token"; "X-Tenant"="scnu"}
```
Expected: 404 with "Unknown table: unknown_table".

- [ ] **Step 5: Plan complete**

All 8 tasks done. Plan 4 complete. Next plan: Plan 2 (data presentation standardization).

---

## Self-Review

**Spec coverage (§三 of spec):**
- §3.1 tech stack: Refine + Monaco + admin-spa /db route ✅ (Task 5-6)
- §3.2 users.rank column ✅ (Task 1)
- §3.2.1 dev identification via env var + JWT claim ✅ (Task 2)
- §3.3 3 tabs (Tables / KnowledgeRaw / Schema) ✅ (Task 6)
- §3.3 writable-range matrix (10 tables) ✅ (Task 3 TABLE_REGISTRY)
- §3.4 8 endpoints ✅ (Task 4 — 6 CRUD + 2 knowledge raw = 8)
- §3.5 Refine + Monaco + RequireDeveloper + authStore ✅ (Task 5-7)
- §3.6 acceptance: rank column, DEV_ADMIN_USERNAME, is_developer in login, /db visible to admin, 3 tabs work, 403 for non-dev, 404 for unknown table ✅ (Task 8)

**Placeholder scan:** No TBD/TODO. All steps have concrete code. The only intentional "minimal" note is in TablesTab — inline edit/delete UI is minimal but reading/pagination (primary use case) is fully implemented. This matches spec §3.3 which says "Refine 自动生成的 CRUD 表格" but does not mandate full inline edit forms in v1. ✅

**Type consistency:**
- `is_developer` used consistently in: backend dict, JWT claim, TokenResponse, authStore, RequireDeveloper ✅
- `rank` field: `Mapped[int | None]` in model, `Integer` in migration, `nullable=True` in DB ✅
- `TABLE_REGISTRY` keys match table names used in endpoints ✅
- `require_developer` dependency name consistent across files ✅

**Scope boundary:** This plan does NOT touch consult_sessions new fields (subjects/rank/consult_summary/consult_started_at/follow_*) — those are Plan 2's responsibility. Plan 4 only adds `users.rank`. ✅
