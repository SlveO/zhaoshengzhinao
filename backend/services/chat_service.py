import json, uuid
import redis.asyncio as aioredis
from config import settings

redis = aioredis.from_url(settings.redis_url)

async def get_dialog_state(session_id: str) -> dict | None:
    data = await redis.get(f"dialog:{session_id}")
    return json.loads(data) if data else None

async def save_dialog_state(session_id: str, state: dict, ttl: int = 1800):
    await redis.setex(f"dialog:{session_id}", ttl, json.dumps(state, ensure_ascii=False, default=str))

async def delete_dialog_state(session_id: str):
    await redis.delete(f"dialog:{session_id}")

async def create_session(user_id: str) -> str:
    session_id = str(uuid.uuid4())
    state = {
        "session_id": session_id,
        "user_id": user_id,
        "stage": "open",
        "slots": {},
        "messages": [],
    }
    await save_dialog_state(session_id, state)
    return session_id
