from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import auth, chat, profile, recommendation, college
from models import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Gaokao Advisor API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
app.include_router(recommendation.router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(college.router, prefix="/api/v1/colleges", tags=["colleges"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
