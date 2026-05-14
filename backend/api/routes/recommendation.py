import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db, async_session
from api.deps import get_current_user
from models.user import User
from services.profile_service import get_latest_profile
from services.recommendation_service import generate_recommendations
from models.recommendation import Recommendation
from models.recommendation_feedback import RecommendationFeedback
from schemas.recommendation import RecommendationResponse
import json as json_module
import redis.asyncio as aioredis
from config import settings

router = APIRouter()


async def _get_cached_recommendations(user_id: str) -> dict | None:
    try:
        r = aioredis.from_url(settings.redis_url)
        data = await r.get(f"recs_cache:{user_id}")
        if data:
            return json_module.loads(data)
    except Exception:
        pass
    return None


async def _cache_recommendations(user_id: str, data: dict, ttl: int = 600):
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.setex(f"recs_cache:{user_id}", ttl, json_module.dumps(data, ensure_ascii=False))
    except Exception:
        pass


@router.get("", response_model=RecommendationResponse)
async def get_recommendations(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    # Check cache first
    cached = await _get_cached_recommendations(user["user_id"])
    if cached:
        return cached

    # Get profile from conversation (may be empty)
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

    recs = await generate_recommendations(user["user_id"], profile, db)
    result = {"recommendations": recs, "profile_snapshot": profile}

    # Cache result (fire-and-forget, don't block on cache write failure)
    await _cache_recommendations(user["user_id"], result)

    return result


@router.post("/feedback")
async def submit_feedback(
    body: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fb = RecommendationFeedback(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user["user_id"]),
        college_name=body.get("college_name", ""),
        major_name=body.get("major_name", ""),
        feedback_type=body.get("feedback_type", "useful"),
    )
    db.add(fb)
    await db.commit()
    return {"status": "ok"}


@router.get("/{rec_id}")
async def get_recommendation_detail(
    rec_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Recommendation).where(
            Recommendation.id == rec_id, Recommendation.user_id == user["user_id"]
        )
    )
    rec = result.scalar_one_or_none()
    return rec.result_json if rec else {}
