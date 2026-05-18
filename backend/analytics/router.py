"""Analytics API — module-gated endpoints returning stub data during Phase 1."""
from fastapi import APIRouter, Depends

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
async def funnel(tenant=Depends(_require(ModuleKey.FUNNEL))):
    return {
        "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-12-31T23:59:59Z"},
        "stages": {"visitors": 0, "conversations": 0, "deepConsultations": 0, "intentExpressed": 0, "enrolled": 0},
        "conversionRates": {},
        "_stub": True,
    }


@router.get("/profile-dashboard")
async def profile_dashboard(tenant=Depends(_require(ModuleKey.PROFILE_DASHBOARD))):
    return {
        "riasecDistribution": [],
        "valuesDistribution": [],
        "completenessBreakdown": [],
        "totalProfiles": 0,
        "_stub": True,
    }


@router.get("/major-heatmap")
async def major_heatmap(tenant=Depends(_require(ModuleKey.MAJOR_HEATMAP))):
    return {"majors": [], "_stub": True}


@router.get("/region-distribution")
async def region_distribution(tenant=Depends(_require(ModuleKey.REGION_DISTRIBUTION))):
    return {"regions": [], "_stub": True}


@router.get("/competitive")
async def competitive(tenant=Depends(_require(ModuleKey.COMPETITIVE_ANALYSIS))):
    return {"comparisonDimensions": [], "lossAnalysis": [], "_stub": True}


@router.get("/dialogue-quality")
async def dialogue_quality(tenant=Depends(_require(ModuleKey.DIALOGUE_QUALITY))):
    return {"metrics": {}, "_stub": True}


@router.get("/annual-report")
async def annual_report(tenant=Depends(_require(ModuleKey.ANNUAL_REPORT))):
    return {"report": {}, "_stub": True}
