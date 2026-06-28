from datetime import datetime, timedelta, timezone
from jose import jwt
from config import settings

def create_token(user_id: str, username: str, expire_minutes: int, extra_claims: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload: dict = {"user_id": user_id, "username": username, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except Exception:
        return None
