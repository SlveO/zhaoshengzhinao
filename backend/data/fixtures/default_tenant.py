"""Seed data for the default platform tenant and pilot tenants."""
import uuid

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

DEFAULT_TENANT = {
    "id": DEFAULT_TENANT_ID,
    "name": "招生智脑 Platform",
    "slug": "default",
    "subscription_tier": "basic",
    "status": "active",
    "config": {
        "brand": {
            "name": "招生智脑",
            "short_name": "招生智脑",
            "primary_color": "#2563eb",
            "secondary_color": "#f59e0b",
            "logo_url": "",
            "welcome_text": "欢迎使用招生智脑！我是你的AI招生顾问。",
        },
        "modules": {
            "profile_dashboard": True,
            "major_heatmap": False,
            "region_distribution": False,
            "competitive_analysis": False,
            "dialogue_quality": False,
            "annual_report": False,
            "multi_department": False,
            "role_management": False,
        },
        "knowledge_base": {"doc_count": 0, "last_updated": None},
        "mini_program": {"app_id": "", "app_secret_encrypted": ""},
    },
}

# SCNU is the active pilot tenant, created by backend/core/startup_seed.py
# (id=20000000-0000-0000-0000-000000000002). Other pilot tenants removed
# during SCNU-only consolidation.
PILOT_TENANTS = []
