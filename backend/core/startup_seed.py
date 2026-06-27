"""Startup seed: ensure scnu tenant and admin user exist on first boot."""
import hashlib
import logging
import os
import uuid

from sqlalchemy import select, text

logger = logging.getLogger(__name__)

SCNU_TENANT_CONFIG = {
    "brand": {
        "name": "华南师范大学",
        "short_name": "华南师大",
        "primary_color": "#1a3a6b",
        "secondary_color": "#c41230",
        "logo_url": "",
        "welcome_text": "欢迎了解华南师范大学！艰苦奋斗、严谨治学、求实创新、为人师表。我是你的专属AI招生顾问~",
    },
    "modules": {
        "profile_dashboard": True,
        "major_heatmap": True,
        "region_distribution": True,
        "competitive_analysis": True,
        "dialogue_quality": True,
        "annual_report": True,
        "multi_department": True,
        "role_management": True,
        "topic_cloud": True,
        "emotion_timeline": True,
        "hot_questions": True,
        "distribution": True,
    },
    "knowledge_base": {"doc_count": 0, "last_updated": None},
    "mini_program": {"app_id": "", "app_secret_encrypted": ""},
}


async def _ensure_tenant_and_admin():
    """Ensure scnu tenant and admin user exist (idempotent).

    Seeds two accounts:
      - admin / admin123  → developer account (is_developer=True, full menu + DB panel)
      - scnu / 2026scnu   → college admin account (is_developer=False, restricted menu)
    """
    try:
        from models import async_session
        from tenants.models import Tenant, TenantUser
        from models.user import User

        async with async_session() as db:
            # Ensure is_developer column exists (hotfix for prod DBs without migration)
            await db.execute(text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_developer BOOLEAN DEFAULT FALSE"
            ))

            result = await db.execute(select(Tenant).where(Tenant.slug == "scnu"))
            tenant = result.scalar_one_or_none()

            if not tenant:
                tenant = Tenant(
                    id=uuid.UUID("20000000-0000-0000-0000-000000000002"),
                    name="华南师范大学",
                    slug="scnu",
                    config=SCNU_TENANT_CONFIG,
                    subscription_tier="advanced",
                    status="active",
                )
                db.add(tenant)
            else:
                # Merge missing modules into existing tenant config (hotfix for 403 on analytics)
                existing_config = dict(tenant.config or {})
                existing_modules = existing_config.get("modules", {})
                default_modules = SCNU_TENANT_CONFIG.get("modules", {})
                if any(k not in existing_modules for k in default_modules):
                    merged = {**default_modules, **existing_modules}
                    existing_config["modules"] = merged
                    tenant.config = existing_config
                    logger.info(f"Patched tenant config: added {[k for k in default_modules if k not in existing_modules]} modules")

            # ── admin 账号（开发者）──
            result = await db.execute(select(User).where(User.username == "admin"))
            admin_user = result.scalar_one_or_none()

            if not admin_user:
                salt = os.urandom(16).hex()
                password_hash = salt + ":" + hashlib.sha256(
                    (salt + "admin123").encode()
                ).hexdigest()
                admin_user = User(
                    username="admin",
                    password_hash=password_hash,
                    is_developer=True,
                )
                db.add(admin_user)
            else:
                # 升级老库：把 admin 标记为开发者
                admin_user.is_developer = True

            result = await db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == tenant.id,
                    TenantUser.user_id == admin_user.id,
                )
            )
            link = result.scalar_one_or_none()

            if not link:
                link = TenantUser(
                    tenant_id=tenant.id,
                    user_id=admin_user.id,
                    role="admin",
                )
                db.add(link)

            # ── scnu 账号（院校管理员，非开发者）──
            result = await db.execute(select(User).where(User.username == "scnu"))
            scnu_user = result.scalar_one_or_none()

            if not scnu_user:
                salt = os.urandom(16).hex()
                password_hash = salt + ":" + hashlib.sha256(
                    (salt + "2026scnu").encode()
                ).hexdigest()
                scnu_user = User(
                    username="scnu",
                    password_hash=password_hash,
                    is_developer=False,
                )
                db.add(scnu_user)
            else:
                scnu_user.is_developer = False

            result = await db.execute(
                select(TenantUser).where(
                    TenantUser.tenant_id == tenant.id,
                    TenantUser.user_id == scnu_user.id,
                )
            )
            scnu_link = result.scalar_one_or_none()

            if not scnu_link:
                scnu_link = TenantUser(
                    tenant_id=tenant.id,
                    user_id=scnu_user.id,
                    role="admin",
                )
                db.add(scnu_link)

            await db.commit()
            logger.info("Tenant and users ensured (admin=developer, scnu=college admin).")
    except Exception as e:
        logger.error(f"Startup seed failed: {e}")
