from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db
from schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from services.auth_service import register_user, authenticate_user, generate_tokens
from utils.jwt import decode_token

router = APIRouter()

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await register_user(db, req.username, req.password, req.region, req.score, req.subjects, req.rank)
    if user is None:
        raise HTTPException(status_code=400, detail="Username already exists")
    tokens = generate_tokens(str(user.id), user.username, is_developer=False, role=None)
    return {**tokens, "user_id": str(user.id), "username": user.username,
            "is_developer": False, "role": None}

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    info = await authenticate_user(db, req.username, req.password)
    if info is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    tokens = generate_tokens(
        info["user_id"], info["username"],
        is_developer=info.get("is_developer", False),
        role=info.get("role"),
    )
    return {**tokens, **info}

@router.post("/refresh")
async def refresh(req: Request):
    auth = req.headers.get("authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    is_developer = bool(payload.get("is_developer", False))
    role = payload.get("role")
    tokens = generate_tokens(
        payload["user_id"], payload["username"],
        is_developer=is_developer, role=role,
    )
    return {**tokens, "user_id": payload["user_id"], "username": payload["username"],
            "is_developer": is_developer, "role": role}
