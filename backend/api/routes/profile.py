from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db
from api.deps import get_current_user
from services.profile_service import save_profile, get_latest_profile

router = APIRouter()

@router.get("")
async def get_profile(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    p = await get_latest_profile(db, user["user_id"])
    return p or {"profile": {}, "confidence": {}, "version": 0}

@router.post("/feedback")
async def update_profile(slots: dict, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await save_profile(db, user["user_id"], slots)
    return {"version": profile.version, "profile": profile.profile_json}
