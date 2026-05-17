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
            "funnel": True,
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

PILOT_TENANTS = [
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000001"),
        "name": "广东工业大学",
        "slug": "gdufs",
        "subscription_tier": "advanced",
        "status": "active",
        "config": {
            "brand": {
                "name": "广东工业大学",
                "short_name": "广工",
                "primary_color": "#1a56db",
                "secondary_color": "#f59e0b",
                "logo_url": "",
                "welcome_text": "欢迎了解广东工业大学！我是你的专属AI招生顾问，有什么想了解的？",
            },
            "modules": {
                "funnel": True,
                "profile_dashboard": True,
                "major_heatmap": True,
                "region_distribution": False,
                "competitive_analysis": False,
                "dialogue_quality": True,
                "annual_report": False,
                "multi_department": False,
                "role_management": False,
            },
            "knowledge_base": {"doc_count": 0, "last_updated": None},
            "mini_program": {"app_id": "", "app_secret_encrypted": ""},
        },
    },
]
