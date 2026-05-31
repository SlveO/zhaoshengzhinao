"""Create SCNU (华南师范大学) tenant in the database."""
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
# Inside Docker the backend code lives at /app directly, not /app/backend
if not Path(_backend_dir).is_dir():
    _backend_dir = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _backend_dir)
if Path(_backend_dir).is_dir():
    os.chdir(_backend_dir)

from sqlalchemy import text  # noqa: E402
from models import async_session  # noqa: E402

SCNU_TENANT = {
    "id": "20000000-0000-0000-0000-000000000002",
    "name": "华南师范大学",
    "slug": "scnu",
    "subscription_tier": "advanced",
    "status": "active",
    "config": {
        "brand": {
            "name": "华南师范大学",
            "short_name": "华南师大",
            "primary_color": "#1a3a6b",
            "secondary_color": "#c41230",
            "logo_url": "",
            "welcome_text": "欢迎了解华南师范大学！艰苦奋斗、严谨治学、求实创新、为人师表。我是你的专属AI招生顾问~",
        },
        "modules": {
            "funnel": True,
            "profile_dashboard": True,
            "major_heatmap": True,
            "region_distribution": True,
            "competitive_analysis": True,
            "dialogue_quality": True,
            "topic_cloud": True,
            "emotion_timeline": True,
            "hot_questions": True,
            "annual_report": False,
            "multi_department": False,
            "role_management": False,
        },
        "knowledge_base": {"doc_count": 0, "last_updated": None},
        "mini_program": {"app_id": "", "app_secret_encrypted": ""},
    },
}


async def create():
    async with async_session() as db:
        await db.execute(
            text("""
                INSERT INTO tenants (id, name, slug, config, subscription_tier, status)
                VALUES (:id, :name, :slug, :config, :subscription_tier, :status)
                ON CONFLICT (slug) DO UPDATE SET config = :config
            """),
            {
                **SCNU_TENANT,
                "config": json.dumps(SCNU_TENANT["config"], ensure_ascii=False),
            },
        )
        await db.commit()

    # Verify
    async with async_session() as db:
        result = await db.execute(
            text("SELECT id, name, slug, config, subscription_tier FROM tenants WHERE slug = 'scnu'")
        )
        row = result.fetchone()
        if row:
            print(f"SCNU tenant created/updated: {row[1]} (slug={row[2]}, tier={row[4]})")
            config = row[3] if isinstance(row[3], dict) else json.loads(row[3])
            print(f"  Brand: {config['brand']['name']} | Color: {config['brand']['primary_color']}")
            print(f"  Modules enabled: {[k for k, v in config['modules'].items() if v]}")
        else:
            print("ERROR: Tenant not found after insert")


if __name__ == "__main__":
    asyncio.run(create())
