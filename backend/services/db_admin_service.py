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


async def get_row(db: AsyncSession, table_name: str, row_id: str) -> dict | None:
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


async def update_row(db: AsyncSession, table_name: str, row_id: str, payload: dict) -> dict | None:
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
