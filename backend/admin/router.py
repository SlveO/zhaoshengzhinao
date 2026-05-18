"""Admin management endpoints — brand config, knowledge base, departments, roles."""
from fastapi import APIRouter, Depends, UploadFile, File, Form

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


@router.post("/brand-config/logo")
async def upload_logo(
    file: UploadFile = File(...),
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    # Stub: save to file store (Phase 2)
    return {"logo_url": f"/uploads/{tenant.slug}/logo.png", "_stub": True}


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
