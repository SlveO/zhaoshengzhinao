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


# ── Knowledge raw JSON endpoints (must be before /db/{table_name} routes) ──

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
    from knowledge.indexer import reindex_tenant
    from knowledge.index_lock import is_running
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
    # 异步触发 reindex — 不阻塞 HTTP 响应
    # 如果已有 reindex 在跑，跳过（避免并发冲突，已有任务会覆盖最新数据）
    reindex_started = False
    if not is_running(tenant.slug):
        import asyncio
        asyncio.create_task(reindex_tenant(tenant.slug, triggered_by="raw_edit"))
        reindex_started = True
    return {
        "id": str(td.id),
        "title": td.title,
        "content": td.content,
        "indexed_at": td.indexed_at.isoformat() if td.indexed_at else None,
        "reindex_started": reindex_started,
        "reindex_status": "running" if reindex_started else "skipped_existing",
    }


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
    filters: dict = {}
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
