from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db
from api.deps import get_current_user
from services.profile_service import get_latest_profile
from services.recommendation_service import generate_recommendations
from models.recommendation import Recommendation
from schemas.recommendation import RecommendationResponse

router = APIRouter()


@router.get("", response_model=RecommendationResponse)
async def get_recommendations(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    profile_data = await get_latest_profile(db, user["user_id"])
    profile = profile_data["profile"] if profile_data else {}
    recs = await generate_recommendations(user["user_id"], profile, db)
    return {"recommendations": recs, "profile_snapshot": profile}


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
