import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from utils.security import hash_password, verify_password
from utils.jwt import create_token
from config import settings

async def register_user(db: AsyncSession, username: str, password: str, region: str, score: int, subjects: str) -> User | None:
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        return None
    user = User(id=uuid.uuid4(), username=username, password_hash=hash_password(password), region=region, score=score, subjects=subjects)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(db: AsyncSession, username: str, password: str) -> dict | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return {"user_id": str(user.id), "username": user.username}

def generate_tokens(user_id: str, username: str) -> dict:
    return {
        "access_token": create_token(user_id, username, settings.access_token_expire_minutes),
        "refresh_token": create_token(user_id, username, settings.refresh_token_expire_days * 24 * 60),
    }
