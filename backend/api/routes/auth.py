from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db
from schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from services.auth_service import register_user, authenticate_user, generate_tokens

router = APIRouter()

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await register_user(db, req.username, req.password, req.region, req.score, req.subjects)
    if user is None:
        raise HTTPException(status_code=400, detail="Username already exists")
    tokens = generate_tokens(str(user.id), user.username)
    return {**tokens, "user_id": str(user.id), "username": user.username}

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    info = await authenticate_user(db, req.username, req.password)
    if info is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    tokens = generate_tokens(info["user_id"], info["username"])
    return {**tokens, **info}

@router.post("/refresh")
async def refresh():
    pass
