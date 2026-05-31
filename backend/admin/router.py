"""Admin management endpoints — brand config, knowledge base, departments, roles."""
import os
import tempfile
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from core.tenant_context import get_current_tenant, get_current_tenant_user
from core.module_registry import ModuleKey, check_module_enabled

router = APIRouter()


# ── Brand Config ──


@router.get("/brand-config")
async def get_brand_config(tenant=Depends(get_current_tenant)):
    return tenant.config.get("brand", {}) if tenant.config else {}


@router.put("/brand-config")
async def update_brand_config(
    body: dict,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    from tenants.service import update_tenant_config
    merged = await update_tenant_config(tenant, {"brand": body})
    return merged.config.get("brand", {})


UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/app/uploads")

@router.post("/brand-config/logo")
async def upload_logo(
    file: UploadFile = File(...),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    tenant_dir = os.path.join(UPLOAD_DIR, tenant.slug)
    if not os.path.exists(tenant_dir):
        os.makedirs(tenant_dir)
    ext = os.path.splitext(file.filename or ".png")[1] or ".png"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(tenant_dir, filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())
    return {"logo_url": f"/uploads/{tenant.slug}/{filename}"}


# ── Knowledge Base ──


@router.get("/knowledge/documents")
async def list_documents(tenant=Depends(get_current_tenant)):
    from models import async_session
    from sqlalchemy import select
    from tenants.models import TenantData

    async with async_session() as db:
        result = await db.execute(
            select(TenantData).where(TenantData.tenant_id == tenant.id).order_by(TenantData.created_at.desc())
        )
        docs = result.scalars().all()
        return {
            "documents": [
                {
                    "id": str(d.id),
                    "title": d.title,
                    "data_type": str(d.data_type) if hasattr(d.data_type, "value") else d.data_type,
                    "year": d.year,
                    "indexed_at": d.indexed_at.isoformat() if d.indexed_at else None,
                }
                for d in docs
            ]
        }


@router.post("/knowledge/documents")
async def upload_document(
    file: UploadFile = File(...),
    data_type: str = Form(...),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    from models import async_session
    from tenants.models import TenantData
    from knowledge.indexer import index_tenant_data

    suffix = os.path.splitext(file.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        if suffix in (".xlsx", ".xls"):
            from data.onboarding.excel_importer import import_excel
            result = await import_excel(
                str(tenant.id), tenant.slug, tmp_path, data_type
            )
        else:
            content_text = open(tmp_path, encoding="utf-8").read()
            async with async_session() as db:
                td = TenantData(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    data_type=data_type,
                    title=file.filename or "未命名文档",
                    content={"text": content_text},
                )
                db.add(td)
                await db.commit()
                try:
                    await index_tenant_data(tenant.slug, td)
                    td.indexed_at = datetime.now(timezone.utc)
                    await db.commit()
                except Exception:
                    pass
            result = {"success": True, "imported": 1, "errors": [], "total_rows": 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    finally:
        os.unlink(tmp_path)

    return result


@router.delete("/knowledge/documents/{document_id}")
async def delete_document(
    document_id: str,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    from models import async_session
    from sqlalchemy import select, delete
    from tenants.models import TenantData
    from knowledge.client import get_chroma_client

    async with async_session() as db:
        result = await db.execute(
            select(TenantData).where(
                TenantData.id == document_id,
                TenantData.tenant_id == tenant.id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        await db.delete(doc)
        await db.commit()

        try:
            coll = get_chroma_client().get_collection(f"{tenant.slug}_colleges")
            coll.delete(ids=[document_id])
        except Exception:
            pass

    return {"detail": "deleted"}


@router.post("/knowledge/reindex")
async def trigger_reindex(
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    from knowledge.indexer import reindex_tenant
    import asyncio
    asyncio.create_task(reindex_tenant(tenant.slug))
    return {"status": "started"}


@router.get("/knowledge/index-status")
async def index_status(tenant=Depends(get_current_tenant)):
    from models import async_session
    from sqlalchemy import select, func
    from tenants.models import TenantData

    async with async_session() as db:
        total_result = await db.execute(
            select(func.count()).select_from(TenantData).where(
                TenantData.tenant_id == tenant.id
            )
        )
        total_docs = total_result.scalar() or 0

        indexed_result = await db.execute(
            select(func.count()).select_from(TenantData).where(
                TenantData.tenant_id == tenant.id,
                TenantData.indexed_at.isnot(None),
            )
        )
        indexed_docs = indexed_result.scalar() or 0

    return {
        "total_docs": total_docs,
        "indexed_docs": indexed_docs,
        "pending_docs": total_docs - indexed_docs,
    }


# ── Departments (增值模块) ──


@router.get("/departments")
async def list_departments(
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    check_module_enabled(tenant, ModuleKey.MULTI_DEPARTMENT)
    return {"departments": [], "_stub": True}


# ── Roles (增值模块) ──


@router.get("/roles")
async def list_roles(
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    check_module_enabled(tenant, ModuleKey.ROLE_MANAGEMENT)
    return {"roles": [], "_stub": True}


# ── AI Persona ──


@router.get("/ai-persona")
async def get_persona(tenant=Depends(get_current_tenant)):
    return (tenant.config or {}).get("ai_persona", {})


@router.put("/ai-persona")
async def update_persona(
    body: dict,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    from tenants.service import update_tenant_config
    merged = await update_tenant_config(tenant, {"ai_persona": body})
    return merged.config.get("ai_persona", {})
