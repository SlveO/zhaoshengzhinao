"""FastAPI dependency: require developer (JWT is_developer claim)."""
from fastapi import HTTPException

from core.tenant_context import get_current_jwt_payload


async def require_developer() -> dict:
    """Return JWT payload if caller is a developer; else raise 403."""
    payload = get_current_jwt_payload()
    if not payload or not payload.get("is_developer"):
        raise HTTPException(status_code=403, detail="Developer access required")
    return payload
