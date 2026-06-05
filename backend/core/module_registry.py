"""Module feature-flag system.

Each analytics/admin module can be independently toggled per tenant
via tenant.config.modules. Dependencies are enforced — e.g. you
cannot enable competitive_analysis without funnel + profile_dashboard.
"""
from enum import Enum

from fastapi import HTTPException


class ModuleKey(Enum):
    FUNNEL = "funnel"
    PROFILE_DASHBOARD = "profile_dashboard"
    MAJOR_HEATMAP = "major_heatmap"
    REGION_DISTRIBUTION = "region_distribution"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    DIALOGUE_QUALITY = "dialogue_quality"
    ANNUAL_REPORT = "annual_report"
    MULTI_DEPARTMENT = "multi_department"
    ROLE_MANAGEMENT = "role_management"
    TOPIC_CLOUD = "topic_cloud"
    EMOTION_TIMELINE = "emotion_timeline"
    HOT_QUESTIONS = "hot_questions"
    DISTRIBUTION = "distribution"


# Modules that require other modules to be enabled first
MODULE_DEPENDENCIES: dict[ModuleKey, list[ModuleKey]] = {
    ModuleKey.MAJOR_HEATMAP: [ModuleKey.FUNNEL],
    ModuleKey.COMPETITIVE_ANALYSIS: [ModuleKey.FUNNEL, ModuleKey.PROFILE_DASHBOARD],
    ModuleKey.ANNUAL_REPORT: [
        ModuleKey.FUNNEL,
        ModuleKey.PROFILE_DASHBOARD,
        ModuleKey.MAJOR_HEATMAP,
        ModuleKey.REGION_DISTRIBUTION,
        ModuleKey.COMPETITIVE_ANALYSIS,
    ],
}


# Route prefix → ModuleKey mapping for automatic gating
MODULE_ROUTE_MAP: dict[str, ModuleKey] = {
    "/api/v1/admin/analytics/funnel": ModuleKey.FUNNEL,
    "/api/v1/admin/analytics/profile-dashboard": ModuleKey.PROFILE_DASHBOARD,
    "/api/v1/admin/analytics/major-heatmap": ModuleKey.MAJOR_HEATMAP,
    "/api/v1/admin/analytics/region-distribution": ModuleKey.REGION_DISTRIBUTION,
    "/api/v1/admin/analytics/competitive": ModuleKey.COMPETITIVE_ANALYSIS,
    "/api/v1/admin/analytics/dialogue-quality": ModuleKey.DIALOGUE_QUALITY,
    "/api/v1/admin/analytics/annual-report": ModuleKey.ANNUAL_REPORT,
    "/api/v1/admin/analytics/topic-cloud": ModuleKey.TOPIC_CLOUD,
    "/api/v1/admin/analytics/emotion-timeline": ModuleKey.EMOTION_TIMELINE,
    "/api/v1/admin/analytics/hot-questions": ModuleKey.HOT_QUESTIONS,
    "/api/v1/admin/departments": ModuleKey.MULTI_DEPARTMENT,
    "/api/v1/admin/roles": ModuleKey.ROLE_MANAGEMENT,
    "/api/v1/distribution": ModuleKey.DISTRIBUTION,
}


def check_module_enabled(tenant, module: ModuleKey):
    """Raise 403 if *module* (or any of its dependencies) is not enabled for *tenant*."""
    modules = (tenant.config or {}).get("modules", {})

    if not modules.get(module.value, False):
        raise HTTPException(
            status_code=403,
            detail=f"Module '{module.value}' is not enabled for this tenant",
        )

    for dep in MODULE_DEPENDENCIES.get(module, []):
        if not modules.get(dep.value, False):
            raise HTTPException(
                status_code=403,
                detail=f"Module '{module.value}' requires '{dep.value}' which is not enabled",
            )
