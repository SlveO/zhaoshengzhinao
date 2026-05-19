import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import get_db, async_session
from models.user import User
from api.deps import get_current_user, get_optional_user
from services.profile_service import get_latest_profile
from recommendation.cross_college import cross_college_recommendations
from tenants.models import Tenant

router = APIRouter()


@router.get("/recommendations")
async def get_compare_recommendations(
    user: dict | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
    profile_snapshot: str | None = Query(None),
):
    profile = {}

    if user:
        profile_data = await get_latest_profile(db, user["user_id"])
        profile = profile_data["profile"] if profile_data else {}

        # Fallback: merge user registration data into profile
        async with async_session() as db2:
            result = await db2.execute(select(User).where(User.id == user["user_id"]))
            u = result.scalar_one_or_none()
            if u:
                if not profile.get("score") and u.score:
                    profile["score"] = u.score
                if not profile.get("subjects") and u.subjects:
                    profile["subjects"] = u.subjects
                if not profile.get("region_pref") and u.region:
                    profile["region_pref"] = [u.region]
    elif profile_snapshot:
        try:
            profile = json.loads(profile_snapshot)
        except json.JSONDecodeError:
            profile = {}
    else:
        return {"recommendations": [], "error": "No profile available", "profile_snapshot": {}, "tenants_compared": 0}

    # Get all active tenant slugs
    async with async_session() as db2:
        result = await db2.execute(
            select(Tenant.slug, Tenant.name).where(Tenant.status == "active")
        )
        tenants = result.all()

    slug_name_map = {t.slug: t.name for t in tenants}
    slugs = list(slug_name_map.keys())

    results = await cross_college_recommendations(profile, slugs)

    # Enrich with tenant names
    for r in results:
        r["tenant_name"] = slug_name_map.get(r["tenant_slug"], r["tenant_slug"])

    return {
        "recommendations": results,
        "profile_snapshot": profile,
        "tenants_compared": len(slugs),
    }
