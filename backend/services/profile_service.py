import uuid
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from models.profile import UserProfile

async def save_profile(db: AsyncSession, user_id: str, slots: dict) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id).order_by(desc(UserProfile.version)).limit(1))
    latest = result.scalar_one_or_none()
    version = (latest.version + 1) if latest else 1

    confidence = {}
    if slots.get("score"):
        confidence["score"] = 1.0
    if slots.get("riasec"):
        conf = min(0.5 + len(slots["riasec"]) * 0.08, 0.9)
        confidence["riasec"] = round(conf, 2)
    if slots.get("values"):
        confidence["values"] = 0.7

    profile = UserProfile(id=uuid.uuid4(), user_id=uuid.UUID(user_id), version=version, profile_json=slots, confidence_json=confidence)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

async def get_latest_profile(db: AsyncSession, user_id: str) -> dict | None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id).order_by(desc(UserProfile.version)).limit(1))
    p = result.scalar_one_or_none()
    return {"profile": p.profile_json, "confidence": p.confidence_json, "version": p.version} if p else None
