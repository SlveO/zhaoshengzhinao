"""Analytics API — module-gated endpoints backed by real SQL aggregation queries."""
from fastapi import APIRouter, Depends, Query

from core.module_registry import ModuleKey, check_module_enabled
from core.tenant_context import get_current_tenant, get_current_tenant_user

router = APIRouter()


def _require(module: ModuleKey):
    """FastAPI dependency that gates on module + auth."""
    async def gate(tenant=Depends(get_current_tenant), _user=Depends(get_current_tenant_user)):
        check_module_enabled(tenant, module)
        return tenant
    return gate


@router.get("/funnel")
async def funnel(
    tenant=Depends(_require(ModuleKey.FUNNEL)),
    days: int = Query(default=365, ge=1, le=1095),
):
    from analytics.funnel import get_funnel
    return await get_funnel(str(tenant.id), days=days)


@router.get("/profile-dashboard")
async def profile_dashboard(
    tenant=Depends(_require(ModuleKey.PROFILE_DASHBOARD)),
    days: int = Query(default=365, ge=1, le=1095),
):
    from analytics.profile_dashboard import get_profile_dashboard
    return await get_profile_dashboard(str(tenant.id), days=days)


@router.get("/major-heatmap")
async def major_heatmap(
    tenant=Depends(_require(ModuleKey.MAJOR_HEATMAP)),
    days: int = Query(default=365, ge=1, le=1095),
):
    from analytics.major_heatmap import get_major_heatmap
    return await get_major_heatmap(str(tenant.id), days=days)


@router.get("/region-distribution")
async def region_distribution(
    tenant=Depends(_require(ModuleKey.REGION_DISTRIBUTION)),
    days: int = Query(default=365, ge=1, le=1095),
):
    from analytics.region_distribution import get_region_distribution
    return await get_region_distribution(str(tenant.id), days=days)


@router.get("/competitive")
async def competitive(
    tenant=Depends(_require(ModuleKey.COMPETITIVE_ANALYSIS)),
    days: int = Query(default=365, ge=1, le=1095),
):
    from analytics.competitive_analysis import get_competitive_analysis
    return await get_competitive_analysis(str(tenant.id), days=days)


@router.get("/dialogue-quality")
async def dialogue_quality(
    tenant=Depends(_require(ModuleKey.DIALOGUE_QUALITY)),
    days: int = Query(default=365, ge=1, le=1095),
):
    from analytics.dialogue_quality import get_dialogue_quality
    return await get_dialogue_quality(str(tenant.id), days=days)


@router.get("/annual-report")
async def annual_report(
    tenant=Depends(_require(ModuleKey.ANNUAL_REPORT)),
    days: int = Query(default=365, ge=1, le=1095),
):
    from analytics.annual_report import get_annual_report
    return await get_annual_report(str(tenant.id), days=days)
