"""Tenant management API — admin-only endpoints."""
from fastapi import APIRouter, Depends
from core.tenant_context import get_current_tenant, get_current_tenant_user
from tenants.schemas import TenantResponse, TenantConfigUpdate
from tenants.service import update_tenant_config

router = APIRouter()


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(tenant=Depends(get_current_tenant)):
    return TenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        subscription_tier=tenant.subscription_tier,
        status=tenant.status,
    )


@router.get("/me/config")
async def get_my_config(tenant=Depends(get_current_tenant)):
    return tenant.config or {}


@router.put("/me/config")
async def update_my_config(
    update: TenantConfigUpdate,
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    merged = await update_tenant_config(tenant, update.model_dump(exclude_none=True))
    return merged.config
