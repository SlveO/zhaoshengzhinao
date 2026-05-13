# 高考志愿填报系统 MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 5-day MVP: registration → psychology-guided dialogue → user profile → gaokao recommendations with RAG.

**Architecture:** FastAPI backend with LangGraph conversation state machine, Chroma vector search, DeepSeek API for LLM. Vite + React frontend over REST + WebSocket. PostgreSQL + Redis.

**Tech Stack:** FastAPI, LangChain + LangGraph, DeepSeek API, Chroma, PostgreSQL, Redis, Vite + React 18 + TypeScript + Tailwind CSS

---

## File Structure

```
backend/
├── main.py, config.py, requirements.txt, Dockerfile
├── api/
│   ├── deps.py
│   └── routes/ (auth.py, chat.py, profile.py, recommendation.py, college.py)
├── models/ (user.py, profile.py, college.py, admission.py, recommendation.py)
├── schemas/ (auth.py, chat.py, profile.py, recommendation.py)
├── services/ (auth_service.py, chat_service.py, recommendation_service.py, profile_service.py)
├── agents/conversation/ (agent.py, state.py, slot_filler.py, prompts.py)
├── knowledge_base/ (embeddings.py, chroma_client.py, retriever.py)
├── utils/ (security.py, jwt.py)
└── migrations/

frontend/
├── package.json, vite.config.ts, tailwind.config.js, index.html
└── src/
    ├── App.tsx, main.tsx, index.css
    ├── pages/ (Landing.tsx, Login.tsx, Register.tsx, Chat.tsx, Recommendations.tsx)
    ├── components/
    │   ├── chat/ (ChatBubble.tsx, ChatInput.tsx, StageIndicator.tsx, SlotProgress.tsx, SummaryModal.tsx)
    │   ├── recommendation/ (RecommendationCard.tsx, ProfileSummaryBar.tsx, FilterBar.tsx)
    │   └── common/ (Layout.tsx, ProtectedRoute.tsx)
    ├── hooks/ (useChat.ts, useWebSocket.ts, useAuth.ts)
    ├── services/ (api.ts, auth.ts, recommendation.ts)
    ├── stores/ (authStore.ts, chatStore.ts, recommendationStore.ts)
    └── types/index.ts

data/seed/ (schools.json, scores.json)
docker/ (Dockerfile.backend, Dockerfile.frontend, nginx.conf)
.env.example, docker-compose.yml
```

---

## Session 1: Infrastructure (Day 1-2) — Blocker for S2/S3

### Task 1: Project scaffolding

**Files:**
- Create: `backend/requirements.txt`, `backend/config.py`, `backend/main.py` (skeleton)
- Create: `.env.example`, `docker-compose.yml`
- Create: `docker/Dockerfile.backend`, `docker/Dockerfile.frontend`, `docker/nginx.conf`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.1
redis==5.2.1
langchain==0.3.15
langgraph==0.2.61
langchain-openai==0.3.2
chromadb==0.5.23
sentence-transformers==3.3.1
pydantic==2.10.5
pydantic-settings==2.7.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.19
websockets==14.1
httpx==0.28.1
```

- [ ] **Step 2: Create config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gaokao:gaokao@localhost:5432/gaokao"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    chroma_persist_dir: str = "./chroma_data"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: Create backend main.py skeleton**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Gaokao Advisor API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Create docker-compose.yml**

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: gaokao
      POSTGRES_PASSWORD: gaokao
      POSTGRES_DB: gaokao
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  backend:
    build: { context: ., dockerfile: docker/Dockerfile.backend }
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [db, redis]
    volumes: [./backend:/app, ./data:/app/data]

  frontend:
    build: { context: ., dockerfile: docker/Dockerfile.frontend }
    ports: ["3000:80"]
    depends_on: [backend]

volumes:
  pgdata:
```

- [ ] **Step 5: Create Dockerfiles and nginx.conf**

`docker/Dockerfile.backend`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`docker/Dockerfile.frontend`:
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
```

`docker/nginx.conf`:
```nginx
server {
    listen 80;
    location / { root /usr/share/nginx/html; try_files $uri /index.html; }
    location /api/ { proxy_pass http://backend:8000/api/; }
    location /ws/ { proxy_pass http://backend:8000/ws/; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; }
}
```

- [ ] **Step 6: Create .env.example**

```
DATABASE_URL=postgresql+asyncpg://gaokao:gaokao@localhost:5432/gaokao
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your-secret-here
DEEPSEEK_API_KEY=sk-your-key
```

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/config.py backend/main.py docker/ docker-compose.yml .env.example
git commit -m "feat: project scaffolding with Docker Compose"
```

---

### Task 2: Database models + engine

**Files:**
- Create: `backend/models/__init__.py`, `backend/models/user.py`, `backend/models/profile.py`
- Create: `backend/models/college.py`, `backend/models/admission.py`, `backend/models/recommendation.py`
- Create: `backend/api/deps.py`

- [ ] **Step 1: Create engine + base in models/__init__.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: Create models**

`backend/models/user.py`:
```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(50), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    subjects: Mapped[str] = mapped_column(String(100), default="")
    batch: Mapped[str] = mapped_column(String(20), default="本科批")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

`backend/models/profile.py`:
```python
import uuid
from datetime import datetime
from sqlalchemy import Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    profile_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

`backend/models/college.py`:
```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class College(Base):
    __tablename__ = "colleges"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    type: Mapped[str] = mapped_column(String(20))
    level: Mapped[str] = mapped_column(String(50))
    province: Mapped[str] = mapped_column(String(50))
    city: Mapped[str] = mapped_column(String(50))
    is_985: Mapped[bool] = mapped_column(Boolean, default=False)
    is_211: Mapped[bool] = mapped_column(Boolean, default=False)
    is_double_first: Mapped[bool] = mapped_column(Boolean, default=False)
    intro: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

`backend/models/admission.py`:
```python
import uuid
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class AdmissionData(Base):
    __tablename__ = "admission_data"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    major_name: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    batch: Mapped[str] = mapped_column(String(20))
    min_score: Mapped[int] = mapped_column(Integer)
    min_rank: Mapped[int] = mapped_column(Integer)
    subject_requirements: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

`backend/models/recommendation.py`:
```python
import uuid
from datetime import datetime
from sqlalchemy import Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    result_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 3: Create deps.py**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db
from utils.jwt import decode_token

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload
```

- [ ] **Step 4: Commit**

```bash
git add backend/models/ backend/api/deps.py
git commit -m "feat: add SQLAlchemy models and auth dependency"
```

---

### Task 3: Auth utilities + service + routes

**Files:**
- Create: `backend/utils/__init__.py`, `backend/utils/security.py`, `backend/utils/jwt.py`
- Create: `backend/schemas/__init__.py`, `backend/schemas/auth.py`
- Create: `backend/services/__init__.py`, `backend/services/auth_service.py`
- Create: `backend/api/routes/__init__.py`, `backend/api/routes/auth.py`

- [ ] **Step 1: Create utils**

`backend/utils/security.py`:
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

`backend/utils/jwt.py`:
```python
from datetime import datetime, timedelta, timezone
from jose import jwt
from config import settings

def create_token(user_id: str, username: str, expire_minutes: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    return jwt.encode({"user_id": user_id, "username": username, "exp": expire}, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except Exception:
        return None
```

- [ ] **Step 2: Create auth schema**

`backend/schemas/auth.py`:
```python
from pydantic import BaseModel, Field

class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    region: str = ""
    score: int = 0
    subjects: str = ""

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    username: str
```

- [ ] **Step 3: Create auth service**

`backend/services/auth_service.py`:
```python
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
```

- [ ] **Step 4: Create auth routes**

`backend/api/routes/auth.py`:
```python
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
    # For MVP: accept existing access token and issue new one if valid
    pass
```

- [ ] **Step 5: Wire routes into main.py**

Add to `backend/main.py`:
```python
from api.routes import auth
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
```

- [ ] **Step 6: Commit**

```bash
git add backend/utils/ backend/schemas/ backend/services/ backend/api/routes/
git commit -m "feat: add auth module with register, login, JWT"
```

---

### Task 4: Seed data + indexing script

**Files:**
- Create: `data/seed/schools.json`, `data/seed/scores.json`
- Create: `scripts/seed_db.py`, `scripts/index_chroma.py`

- [ ] **Step 1: Create schools.json — 20 Guangdong colleges**

```json
[
  {"name":"中山大学","code":"10558","type":"综合","level":"985","province":"广东","city":"广州","is_985":true,"is_211":true,"is_double_first":true,"intro":"教育部直属综合性全国重点大学"},
  {"name":"华南理工大学","code":"10561","type":"理工","level":"985","province":"广东","city":"广州","is_985":true,"is_211":true,"is_double_first":true,"intro":"以工见长，理工结合"},
  {"name":"暨南大学","code":"10559","type":"综合","level":"211","province":"广东","city":"广州","is_985":false,"is_211":true,"is_double_first":true,"intro":"华侨最高学府"},
  {"name":"华南师范大学","code":"10574","type":"师范","level":"211","province":"广东","city":"广州","is_985":false,"is_211":true,"is_double_first":true,"intro":"师范教育为特色"},
  {"name":"深圳大学","code":"10590","type":"综合","level":"省重点","province":"广东","city":"深圳","is_985":false,"is_211":false,"is_double_first":false,"intro":"特区大学"},
  {"name":"华南农业大学","code":"10564","type":"农林","level":"双一流","province":"广东","city":"广州","is_985":false,"is_211":false,"is_double_first":true,"intro":"农业科学为优势"},
  {"name":"南方医科大学","code":"12121","type":"医药","level":"省重点","province":"广东","city":"广州","is_985":false,"is_211":false,"is_double_first":false,"intro":"原第一军医大学"},
  {"name":"广东工业大学","code":"11845","type":"理工","level":"省重点","province":"广东","city":"广州","is_985":false,"is_211":false,"is_double_first":false,"intro":"工科优势突出"},
  {"name":"广州大学","code":"11078","type":"综合","level":"省重点","province":"广东","city":"广州","is_985":false,"is_211":false,"is_double_first":false,"intro":"综合性大学"},
  {"name":"汕头大学","code":"10560","type":"综合","level":"省重点","province":"广东","city":"汕头","is_985":false,"is_211":false,"is_double_first":false,"intro":"李嘉诚基金会资助"},
  {"name":"南方科技大学","code":"14325","type":"理工","level":"双一流","province":"广东","city":"深圳","is_985":false,"is_211":false,"is_double_first":true,"intro":"新型研究型大学"},
  {"name":"广州医科大学","code":"10570","type":"医药","level":"双一流","province":"广东","city":"广州","is_985":false,"is_211":false,"is_double_first":true,"intro":"呼吸疾病研究为特色"},
  {"name":"广东外语外贸大学","code":"11846","type":"语言","level":"省重点","province":"广东","city":"广州","is_985":false,"is_211":false,"is_double_first":false,"intro":"外语外贸为特色"},
  {"name":"广州中医药大学","code":"10572","type":"医药","level":"双一流","province":"广东","city":"广州","is_985":false,"is_211":false,"is_double_first":true,"intro":"中医药研究为特色"},
  {"name":"东莞理工学院","code":"11819","type":"理工","level":"省重点","province":"广东","city":"东莞","is_985":false,"is_211":false,"is_double_first":false,"intro":"应用型理工科大学"},
  {"name":"佛山科学技术学院","code":"11847","type":"理工","level":"省重点","province":"广东","city":"佛山","is_985":false,"is_211":false,"is_double_first":false,"intro":"服务地方产业"},
  {"name":"广东财经大学","code":"10592","type":"财经","level":"省重点","province":"广东","city":"广州","is_985":false,"is_211":false,"is_double_first":false,"intro":"财经类为特色"},
  {"name":"广东海洋大学","code":"10566","type":"农林","level":"省重点","province":"广东","city":"湛江","is_985":false,"is_211":false,"is_double_first":false,"intro":"海洋科学为特色"},
  {"name":"五邑大学","code":"11349","type":"综合","level":"省重点","province":"广东","city":"江门","is_985":false,"is_211":false,"is_double_first":false,"intro":"侨乡高校"},
  {"name":"仲恺农业工程学院","code":"11347","type":"农林","level":"省重点","province":"广东","city":"广州","is_985":false,"is_211":false,"is_double_first":false,"intro":"纪念廖仲恺先生"}
]
```

- [ ] **Step 2: Create scores.json — 3-5 majors per school, ~70 entries total**

```json
[
  {"college_name":"中山大学","major_name":"临床医学（5+3一体化）","year":2024,"batch":"本科批","min_score":658,"min_rank":3500,"subject_requirements":"物理+化学+生物","source_url":"https://eea.gd.gov.cn/"},
  {"college_name":"中山大学","major_name":"计算机科学与技术","year":2024,"batch":"本科批","min_score":655,"min_rank":4200,"subject_requirements":"物理+化学","source_url":"https://eea.gd.gov.cn/"},
  {"college_name":"中山大学","major_name":"生物科学","year":2024,"batch":"本科批","min_score":648,"min_rank":5500,"subject_requirements":"物理+化学+生物","source_url":"https://eea.gd.gov.cn/"},
  {"college_name":"中山大学","major_name":"工商管理","year":2024,"batch":"本科批","min_score":642,"min_rank":6800,"subject_requirements":"不限","source_url":"https://eea.gd.gov.cn/"},
  {"college_name":"中山大学","major_name":"法学","year":2024,"batch":"本科批","min_score":645,"min_rank":6000,"subject_requirements":"不限","source_url":"https://eea.gd.gov.cn/"},
  {"college_name":"华南理工大学","major_name":"计算机科学与技术","year":2024,"batch":"本科批","min_score":642,"min_rank":6800,"subject_requirements":"物理+化学","source_url":"https://eea.gd.gov.cn/"},
  {"college_name":"华南理工大学","major_name":"生物医学工程","year":2024,"batch":"本科批","min_score":630,"min_rank":10200,"subject_requirements":"物理+化学","source_url":"https://eea.gd.gov.cn/"},
  {"college_name":"华南理工大学","major_name":"建筑学","year":2024,"batch":"本科批","min_score":638,"min_rank":8200,"subject_requirements":"物理","source_url":"https://eea.gd.gov.cn/"},
  {"college_name":"华南理工大学","major_name":"化学工程与工艺","year":2024,"batch":"本科批","min_score":618,"min_rank":15000,"subject_requirements":"物理+化学","source_url":"https://eea.gd.gov.cn/"},
  {"college_name":"华南理工大学","major_name":"食品科学与工程","year":2024,"batch":"本科批","min_score":615,"min_rank":16200,"subject_requirements":"物理+化学","source_url":"https://eea.gd.gov.cn/"}
]
```

**The engineer must expand scores.json to cover all 20 schools.** Rank ranges by tier: 985 → 3000-8000, 211/双一流 → 6000-25000, 省重点 → 15000-50000. Each school gets 3-5 majors.

- [ ] **Step 3: Create seed_db.py**

```python
"""Run once to load seed data into PostgreSQL."""
import asyncio, json, uuid
from sqlalchemy import select
from backend.models import engine, async_session, init_db
from backend.models.college import College
from backend.models.admission import AdmissionData

async def seed():
    await init_db()
    async with async_session() as db:
        existing = await db.execute(select(College).limit(1))
        if existing.scalar_one_or_none():
            print("Already seeded, skipping.")
            return
        with open("data/seed/schools.json", encoding="utf-8") as f:
            schools = json.load(f)
        with open("data/seed/scores.json", encoding="utf-8") as f:
            scores = json.load(f)
        name_to_id = {}
        for s in schools:
            c = College(id=uuid.uuid4(), **s)
            db.add(c)
            name_to_id[s["name"]] = c.id
        for r in scores:
            cn = r.pop("college_name")
            db.add(AdmissionData(id=uuid.uuid4(), college_id=name_to_id[cn], **r))
        await db.commit()
        print(f"Seeded {len(schools)} colleges, {len(scores)} admission records.")

if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 4: Create embedding + Chroma infrastructure**

`backend/knowledge_base/embeddings.py`:
```python
from langchain_community.embeddings import HuggingFaceEmbeddings
from config import settings

embedding_model = HuggingFaceEmbeddings(
    model_name=settings.embedding_model,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)
```

`backend/knowledge_base/chroma_client.py`:
```python
import chromadb
from config import settings
from knowledge_base.embeddings import embedding_model

client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
collection = client.get_or_create_collection(name="colleges_majors")

def index_documents(docs: list[str], metadatas: list[dict], ids: list[str]):
    embeddings = embedding_model.embed_documents(docs)
    collection.add(ids=ids, embeddings=embeddings, documents=docs, metadatas=metadatas)

def search_similar(query: str, k: int = 30) -> list[dict]:
    q_emb = embedding_model.embed_query(query)
    results = collection.query(query_embeddings=[q_emb], n_results=k)
    items = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            items.append({
                "id": doc_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
            })
    return items
```

- [ ] **Step 5: Create index_chroma.py**

```python
"""Index seed data into Chroma for RAG."""
import asyncio
from sqlalchemy import select
from backend.models import async_session
from backend.models.college import College
from backend.models.admission import AdmissionData
from backend.knowledge_base.chroma_client import index_documents

async def index():
    async with async_session() as db:
        colleges = {str(c.id): c for c in (await db.execute(select(College))).scalars().all()}
        admissions = (await db.execute(select(AdmissionData))).scalars().all()
        docs, metas, ids = [], [], []
        for a in admissions:
            c = colleges.get(str(a.college_id))
            if not c:
                continue
            doc = f"{c.name} {a.major_name} {c.level} {c.province}{c.city} 录取位次{a.min_rank} 分数{a.min_score} {a.subject_requirements} 985:{c.is_985} 211:{c.is_211} {c.intro}"
            docs.append(doc)
            metas.append({"college_id": str(a.college_id), "college_name": c.name, "major_name": a.major_name, "level": c.level, "province": c.province, "city": c.city, "min_rank": a.min_rank, "min_score": a.min_score, "subjects": a.subject_requirements, "source_url": a.source_url})
            ids.append(str(a.id))
        if docs:
            index_documents(docs, metas, ids)
            print(f"Indexed {len(docs)} documents into Chroma.")

if __name__ == "__main__":
    asyncio.run(index())
```

- [ ] **Step 6: Commit**

```bash
git add data/seed/ scripts/ backend/knowledge_base/
git commit -m "feat: add seed data and Chroma indexing"
```

---

## Session 2: Conversation Agent (Day 2-3) — Depends on Task 1-3

### Task 5: Conversation state machine + prompts

**Files:**
- Create: `backend/agents/__init__.py`, `backend/agents/conversation/__init__.py`
- Create: `backend/agents/conversation/state.py`, `backend/agents/conversation/prompts.py`

- [ ] **Step 1: Create state definitions**

`backend/agents/conversation/state.py`:
```python
from enum import Enum
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class Stage(str, Enum):
    OPEN = "open"
    EXPLORE = "explore"
    FOCUS = "focus"
    CONFIRM = "confirm"
    DONE = "done"

STAGE_ORDER = [Stage.OPEN, Stage.EXPLORE, Stage.FOCUS, Stage.CONFIRM, Stage.DONE]

class ConversationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    stage: Stage
    slots: dict       # {"score": 610, "subjects": "物理+化学+生物", "riasec": {"R":3,"I":8,...}, "values": [...], "region_pref": [...], "career_vision": "", "family_influence": ""}
    stage_complete: bool
    summary_pending: bool
```

- [ ] **Step 2: Create system prompts**

`backend/agents/conversation/prompts.py`:
```python
SYSTEM_PROMPT = """你是一位经验丰富的高考志愿填报心理咨询师。你的任务是通过对话引导学生深入认识自己的兴趣、价值观和偏好，而不是直接给出志愿建议。

## 核心原则
1. 保持中立和共情——不要评判学生的任何选择
2. 引导而非灌输——通过提问帮助学生自己发现答案
3. 永远不要说"你应该选XX专业"——你的角色是帮助学生了解自己
4. 关注学生的情绪状态，及时调整对话节奏

## 对话阶段
你当前处于 {stage} 阶段。各阶段目标和话术要求：

### 建立信任 (open)
- 目标：破冰，了解学生基本情况（分数、选科、批次）
- 话术：温暖、开放、非评判
- 示例："不管这次考试结果怎么样，我们先聊聊你对未来的想法吧"

### 深度探索 (explore)
- 目标：挖掘兴趣倾向(RIASEC)、价值观、地域偏好、家庭影响
- 话术：引导性提问，避免暗示性提问
- 关键信息：喜欢什么学科？课外做什么？对什么好奇？理想的生活状态？

### 聚焦澄清 (focus)
- 目标：在矛盾或模糊处深入澄清，确定优先级
- 话术：结构化对比，"如果必须在A和B之间选一个..."
- 方法：两难情境、权重排序、假设性提问

### 画像确认 (confirm)
- 目标：输出用户画像让学生确认或修正
- 话术：总结性，可视化反馈
- 说明各项画像维度的含义，询问是否准确

## 已收集的学生信息
{slots_summary}

## 注意事项
- 每次回复控制在2-4句话
- 一次只问一个问题
- 如果学生表达困惑或焦虑，先共情再提问
- 当学生在当前阶段的信息已经足够时，自然过渡到下一阶段
"""

STAGE_TRANSITION_PROMPT = """基于当前对话，判断是否应该进入下一个对话阶段。

当前阶段：{current_stage}
对话内容：{conversation}

判断标准：
- open → explore: 已收集到分数、选科、批次
- explore → focus: 至少收集到兴趣倾向(RIASEC)、价值观排序、地域偏好中的两项
- focus → confirm: 已完成至少一次矛盾澄清或优先级确认
- confirm → done: 用户已确认画像

请只回复 JSON: {{"should_transition": true/false, "reason": "简短理由"}}"""

SLOT_EXTRACTION_PROMPT = """从学生的最新回复中提取以下信息。只提取明确提到的内容，不要推测。

学生信息：{conversation}
当前已有信息：{current_slots}

请回复 JSON（未提到的不需要包含）:
{{
  "score": 数字或null,
  "subjects": "选科组合或null",
  "riasec_update": {{任意RIASEC维度: 1-10评分}},
  "values_hint": "提到的价值观关键词或null",
  "region_pref": ["偏好地区"],
  "career_vision": "职业憧憬或null",
  "family_influence": "low/medium/high或null"
}}

注意：
- RIASEC解读：R=动手操作 I=研究思考 A=艺术创造 S=帮助他人 E=领导说服 C=规范有序
- 价值观关键词映射：提到"帮助别人""有意义" → S型；提到"创新""探索" → I型；提到"稳定""安全" → C型
"""

FEW_SHOT_EXAMPLES = [
    {"type": "迷茫型", "user": "我也不知道喜欢什么，感觉什么都差不多", "response": "没关系的，很多同学在这个阶段都会有类似的感受。我们换个角度：你平时空闲的时候，做什么事情会让你感觉时间过得特别快？"},
    {"type": "主见型", "user": "我就是想学医，其他的不考虑", "response": "对医学有这么明确的方向很好。能跟我分享一下，是什么让你对医学产生兴趣的？是某个经历、某个榜样，还是别的什么？"},
    {"type": "焦虑型", "user": "我爸妈让我学金融，但我数学不太好，好烦", "response": "我能感受到你有些纠结。父母的期望和自己的实际情况之间确实需要平衡。除了数学方面的顾虑，你对金融本身感兴趣吗？"},
]
```

- [ ] **Step 3: Commit**

```bash
git add backend/agents/
git commit -m "feat: add conversation state machine and prompt templates"
```

---

### Task 6: Conversation agent + slot filler

**Files:**
- Create: `backend/agents/conversation/slot_filler.py`, `backend/agents/conversation/agent.py`
- Create: `backend/schemas/chat.py`

- [ ] **Step 1: Create slot filler**

`backend/agents/conversation/slot_filler.py`:
```python
"""Extract structured profile information from conversation text."""
import json
from langchain_openai import ChatOpenAI
from config import settings
from agents.conversation.prompts import SLOT_EXTRACTION_PROMPT

llm = ChatOpenAI(
    model=settings.deepseek_model,
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    temperature=0.1,
)

def merge_slots(existing: dict, update: dict) -> dict:
    """Merge new slot values into existing, preserving confidence scoring."""
    merged = dict(existing)
    # Simple numeric values: take if not None
    for key in ["score", "subjects", "career_vision", "family_influence"]:
        if update.get(key):
            merged[key] = update[key]
    # RIASEC: merge dimension scores
    riasec = merged.get("riasec", {})
    riasec_update = update.get("riasec_update", {})
    for dim, val in riasec_update.items():
        if val is not None:
            riasec[dim] = round((riasec.get(dim, 5) + val) / 2, 1) if dim in riasec else val
    merged["riasec"] = riasec
    # Values: append new keywords
    if update.get("values_hint"):
        vals = merged.get("values", [])
        if update["values_hint"] not in vals:
            vals.append(update["values_hint"])
        merged["values"] = vals
    # Region: merge lists
    if update.get("region_pref"):
        existing_regions = set(merged.get("region_pref", []))
        existing_regions.update(update["region_pref"])
        merged["region_pref"] = list(existing_regions)
    return merged

async def extract_slots(conversation: str, current_slots: dict) -> dict:
    """Use LLM to extract slot values from the latest student message."""
    prompt = SLOT_EXTRACTION_PROMPT.format(conversation=conversation, current_slots=json.dumps(current_slots, ensure_ascii=False))
    response = await llm.ainvoke(prompt)
    try:
        update = json.loads(response.content)
        return merge_slots(current_slots, update)
    except json.JSONDecodeError:
        return current_slots

def slots_summary(slots: dict) -> str:
    """Human-readable summary of current slots."""
    lines = []
    if slots.get("score"):
        lines.append(f"分数: {slots['score']}")
    if slots.get("subjects"):
        lines.append(f"选科: {slots['subjects']}")
    riasec = slots.get("riasec", {})
    if riasec:
        dim_names = {"R": "动手操作", "I": "研究思考", "A": "艺术创造", "S": "帮助他人", "E": "领导说服", "C": "规范有序"}
        top = sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:2]
        lines.append("兴趣倾向: " + ", ".join(f"{dim_names.get(k, k)}({v})" for k, v in top))
    if slots.get("values"):
        lines.append(f"价值观: {' > '.join(slots['values'])}")
    if slots.get("region_pref"):
        lines.append(f"地域偏好: {', '.join(slots['region_pref'])}")
    return "\n".join(lines) if lines else "尚无信息"
```

- [ ] **Step 2: Create conversation agent**

`backend/agents/conversation/agent.py`:
```python
"""LangGraph-based conversation agent with 4-stage state machine."""
import json
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from config import settings
from agents.conversation.state import ConversationState, Stage, STAGE_ORDER
from agents.conversation.prompts import SYSTEM_PROMPT, STAGE_TRANSITION_PROMPT
from agents.conversation.slot_filler import extract_slots, slots_summary

llm = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url, temperature=0.7)

def _system_message(state: ConversationState) -> SystemMessage:
    summary = slots_summary(state["slots"])
    return SystemMessage(content=SYSTEM_PROMPT.format(stage=state["stage"].value, slots_summary=summary))

async def _should_transition(state: ConversationState) -> bool:
    """Ask LLM whether current stage is complete."""
    if len(state["messages"]) < 2:
        return False
    recent = "\n".join(m.content for m in state["messages"][-4:])
    prompt = STAGE_TRANSITION_PROMPT.format(current_stage=state["stage"].value, conversation=recent)
    resp = await llm.ainvoke(prompt)
    try:
        result = json.loads(resp.content)
        return result.get("should_transition", False)
    except json.JSONDecodeError:
        return False

async def conversation_node(state: ConversationState) -> ConversationState:
    """Generate the next AI message."""
    msgs = [_system_message(state)] + state["messages"]
    response = await llm.ainvoke(msgs)
    return {"messages": [response], "stage": state["stage"], "slots": state["slots"], "stage_complete": state["stage_complete"], "summary_pending": False}

async def extract_slots_node(state: ConversationState) -> ConversationState:
    """Extract slots from the latest user message."""
    if state["messages"] and isinstance(state["messages"][-1], HumanMessage):
        conv = "\n".join(m.content for m in state["messages"][-6:])
        new_slots = await extract_slots(conv, state["slots"])
        return {"messages": [], "stage": state["stage"], "slots": new_slots, "stage_complete": state["stage_complete"], "summary_pending": False}
    return {}

async def check_transition(state: ConversationState) -> ConversationState:
    """Check if stage should advance."""
    transitioned = await _should_transition(state)
    if transitioned:
        idx = STAGE_ORDER.index(state["stage"])
        if idx < len(STAGE_ORDER) - 1:
            new_stage = STAGE_ORDER[idx + 1]
            return {"messages": [], "stage": new_stage, "slots": state["slots"], "stage_complete": True, "summary_pending": True}
    return {"messages": [], "stage": state["stage"], "slots": state["slots"], "stage_complete": False, "summary_pending": False}

def build_conversation_graph():
    graph = StateGraph(ConversationState)
    graph.add_node("extract_slots", extract_slots_node)
    graph.add_node("check_transition", check_transition)
    graph.add_node("conversation", conversation_node)

    graph.set_entry_point("extract_slots")
    graph.add_edge("extract_slots", "check_transition")
    graph.add_edge("check_transition", "conversation")
    graph.add_edge("conversation", END)

    return graph.compile(checkpointer=MemorySaver())

agent = build_conversation_graph()
```

- [ ] **Step 3: Create chat schemas**

`backend/schemas/chat.py`:
```python
from pydantic import BaseModel

class ChatMessage(BaseModel):
    type: str          # "message" | "thinking" | "stage_change" | "profile_update" | "summary"
    role: str | None = None
    content: str | None = None
    stage: str | None = None
    field: str | None = None
    value: dict | None = None
    confidence: float | None = None
    profile_snapshot: dict | None = None

class WSMessage(BaseModel):
    type: str
    content: str
    session_id: str
```

- [ ] **Step 4: Commit**

```bash
git add backend/agents/conversation/slot_filler.py backend/agents/conversation/agent.py backend/schemas/chat.py
git commit -m "feat: add LangGraph conversation agent with slot filling"
```

---

### Task 7: Chat WebSocket + session management

**Files:**
- Create: `backend/services/chat_service.py`, `backend/services/profile_service.py`
- Create: `backend/schemas/profile.py`, `backend/api/routes/profile.py`
- Create: `backend/api/routes/chat.py`

- [ ] **Step 1: Create chat service**

`backend/services/chat_service.py`:
```python
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
```

- [ ] **Step 2: Create profile service**

`backend/services/profile_service.py`:
```python
import uuid, json
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
```

- [ ] **Step 3: Create chat WebSocket endpoint**

`backend/api/routes/chat.py`:
```python
import json, uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db
from api.deps import get_current_user
from services.chat_service import get_dialog_state, save_dialog_state, create_session, delete_dialog_state
from agents.conversation.state import ConversationState, Stage
from agents.conversation.agent import agent as conv_agent
from langchain_core.messages import HumanMessage, AIMessage
from agents.conversation.slot_filler import slots_summary

router = APIRouter()

@router.websocket("/session/{session_id}")
async def chat_websocket(ws: WebSocket, session_id: str):
    await ws.accept()
    state_data = await get_dialog_state(session_id)
    if not state_data:
        await ws.send_json({"type": "error", "content": "Session not found"})
        await ws.close()
        return

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            user_content = msg.get("content", "")

            await ws.send_json({"type": "thinking", "message": "正在分析你的回答..."})

            # Build LangGraph state
            history = []
            for m in state_data.get("messages", []):
                if m["role"] == "user":
                    history.append(HumanMessage(content=m["content"]))
                else:
                    history.append(AIMessage(content=m["content"]))
            history.append(HumanMessage(content=user_content))

            initial_state: ConversationState = {
                "messages": history,
                "stage": Stage(state_data.get("stage", "open")),
                "slots": state_data.get("slots", {}),
                "stage_complete": False,
                "summary_pending": False,
            }

            result = await conv_agent.ainvoke(initial_state, config={"configurable": {"thread_id": session_id}})

            ai_msg = result["messages"][-1].content if result["messages"] else ""
            new_stage = result["stage"].value if isinstance(result["stage"], Stage) else str(result["stage"])
            new_slots = result.get("slots", {})

            # Update state
            state_data["messages"].append({"role": "user", "content": user_content})
            state_data["messages"].append({"role": "assistant", "content": ai_msg})
            state_data["stage"] = new_stage
            state_data["slots"] = new_slots

            await save_dialog_state(session_id, state_data)

            # Send AI response
            await ws.send_json({"type": "message", "role": "assistant", "content": ai_msg, "stage": new_stage})

            # If stage changed, send summary
            if result.get("summary_pending"):
                summary = f"阶段小结：{slots_summary(new_slots)}"
                await ws.send_json({"type": "summary", "stage": new_stage, "content": summary, "profile_snapshot": new_slots})

            if result.get("stage") == Stage.DONE:
                await ws.send_json({"type": "stage_change", "from": new_stage, "to": "done"})

    except WebSocketDisconnect:
        pass

@router.post("/session")
async def new_session(user: dict = Depends(get_current_user)):
    sid = await create_session(user["user_id"])
    return {"session_id": sid}

@router.get("/session/{session_id}")
async def get_session(session_id: str):
    state = await get_dialog_state(session_id)
    if not state:
        return {"error": "not found"}
    return {"session_id": session_id, "stage": state.get("stage"), "slots": state.get("slots"), "messages": state.get("messages", [])}

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    await delete_dialog_state(session_id)
    return {"status": "deleted"}
```

- [ ] **Step 4: Create profile route**

`backend/api/routes/profile.py`:
```python
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
```

- [ ] **Step 5: Wire routes in main.py**

```python
from api.routes import auth, chat, profile
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/chat_service.py backend/services/profile_service.py backend/api/routes/chat.py backend/api/routes/profile.py
git commit -m "feat: add WebSocket chat and profile management"
```

---

## Session 3: Recommendation System (Day 2-3) — Depends on Task 1-4

### Task 8: RAG retriever + recommendation service

**Files:**
- Create: `backend/knowledge_base/retriever.py`
- Create: `backend/services/recommendation_service.py`
- Create: `backend/schemas/recommendation.py`

- [ ] **Step 1: Create retriever**

`backend/knowledge_base/retriever.py`:
```python
"""Hybrid retrieval: semantic (Chroma) + rule-based filtering (PostgreSQL)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from knowledge_base.chroma_client import search_similar
from models.admission import AdmissionData

def build_query_text(profile: dict) -> str:
    """Build a search query from user profile for semantic matching."""
    parts = []
    riasec = profile.get("riasec", {})
    if riasec:
        top_dims = sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:3]
        dim_keywords = {"R": "动手操作 工程 技术 实验", "I": "研究 科学 分析 探索", "A": "设计 创意 艺术 表达", "S": "帮助 教育 医疗 服务 社会", "E": "管理 领导 商业 金融", "C": "规范 数据 会计 行政 组织"}
        kw = " ".join(dim_keywords.get(d, "") for d, _ in top_dims)
        parts.append(kw)
    if profile.get("career_vision"):
        parts.append(profile["career_vision"])
    if profile.get("values"):
        parts.append(" ".join(profile["values"]))
    return " ".join(parts) if parts else "综合 大学 本科"

async def retrieve_candidates(profile: dict, db: AsyncSession, k: int = 30) -> list[dict]:
    """Semantic search + rule filter returning top-k candidates."""
    query = build_query_text(profile)
    candidates = search_similar(query, k=k)

    # Rule filter: subject requirements
    user_subjects = set((profile.get("subjects", "") or "").replace("+", " ").split())
    filtered = []
    for item in candidates:
        meta = item["metadata"]
        req = set((meta.get("subjects", "") or "").replace("+", " ").split())
        if not user_subjects or not req or req == {"不限"} or user_subjects & req:
            filtered.append(item)
        elif user_subjects:
            continue  # subject mismatch, skip
        else:
            filtered.append(item)

    return filtered[:k]
```

- [ ] **Step 2: Create recommendation service**

`backend/services/recommendation_service.py`:
```python
import json, uuid
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from config import settings
from knowledge_base.retriever import retrieve_candidates
from models.recommendation import Recommendation

llm = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url, temperature=0.3)

RANKING_PROMPT = """你是高考志愿填报专家。基于学生画像和候选院校数据，对以下候选进行精排并生成推荐理由。

## 学生画像
{profile}

## 候选院校列表
{candidates}

## 要求
1. 按综合匹配度排序，选出 Top-10
2. 每个推荐标注：冲刺/稳妥/保底（基于学生位次 vs 录取位次：学生位次明显低于录取位次=冲刺，接近=稳妥，明显高于=保底）
3. 每条推荐生成 2-3 条理由：分数匹配、兴趣匹配、就业前景
4. 每条理由附带数据来源引用

请直接回复 JSON 数组：
[
  {{
    "rank": 1,
    "college_name": "大学名",
    "major_name": "专业名",
    "level": "985/211/双一流/省重点",
    "category": "冲刺/稳妥/保底",
    "match_score": 85,
    "reasons": [
      {{"type": "score_match", "content": "...", "source": "广东省教育考试院2024年录取数据", "source_url": "..."}},
      {{"type": "interest_match", "content": "...", "source": "霍兰德职业兴趣理论", "confidence": 0.88}}
    ],
    "scores": {{"admission_probability": 58, "interest_match": 92, "career_prospect": 85}}
  }}
]
"""

async def generate_recommendations(user_id: str, profile: dict, db: AsyncSession) -> list[dict]:
    # Phase 1: retrieve candidates
    candidates = await retrieve_candidates(profile, db, k=30)

    # Phase 2: build candidate summary for LLM
    candidate_text = "\n".join(
        f"- {c['metadata']['college_name']} | {c['metadata']['major_name']} | {c['metadata']['level']} | 最低位次: {c['metadata']['min_rank']} | 最低分数: {c['metadata']['min_score']} | 选科: {c['metadata']['subjects']}"
        for c in candidates
    )
    profile_text = json.dumps(profile, ensure_ascii=False)
    prompt = RANKING_PROMPT.format(profile=profile_text, candidates=candidate_text)

    response = await llm.ainvoke(prompt)
    try:
        recommendations = json.loads(response.content)
    except json.JSONDecodeError:
        recommendations = []

    # Save to DB
    rec = Recommendation(id=uuid.uuid4(), user_id=uuid.UUID(user_id), profile_version=1, result_json=recommendations)
    db.add(rec)
    await db.commit()

    return recommendations
```

- [ ] **Step 3: Create recommendation schema + route**

`backend/schemas/recommendation.py`:
```python
from pydantic import BaseModel

class ProfileSnapshot(BaseModel):
    score: int | None = None
    subjects: str | None = None
    riasec: dict = {}
    values: list[str] = []
    region_pref: list[str] = []
```

class RecommendationResponse(BaseModel):
    recommendations: list[dict]
    profile_snapshot: dict
```

`backend/api/routes/recommendation.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db
from api.deps import get_current_user
from services.profile_service import get_latest_profile
from services.recommendation_service import generate_recommendations
from schemas.recommendation import RecommendationResponse

router = APIRouter()

@router.get("", response_model=RecommendationResponse)
async def get_recommendations(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile_data = await get_latest_profile(db, user["user_id"])
    profile = profile_data["profile"] if profile_data else {}
    recs = await generate_recommendations(user["user_id"], profile, db)
    return {"recommendations": recs, "profile_snapshot": profile}

@router.get("/{rec_id}")
async def get_recommendation_detail(rec_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # For MVP: return from saved result_json
    from sqlalchemy import select
    from models.recommendation import Recommendation
    result = await db.execute(select(Recommendation).where(Recommendation.id == rec_id, Recommendation.user_id == user["user_id"]))
    rec = result.scalar_one_or_none()
    return rec.result_json if rec else {}
```

- [ ] **Step 4: Create college reference route**

`backend/api/routes/college.py`:
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import get_db
from models.college import College

router = APIRouter()

@router.get("")
async def list_colleges(db: AsyncSession = Depends(get_db), page: int = 1, page_size: int = 20, level: str = Query(None), province: str = Query(None)):
    q = select(College)
    if level:
        q = q.where(College.level == level)
    if province:
        q = q.where(College.province == province)
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    colleges = result.scalars().all()
    return [{"id": str(c.id), "name": c.name, "code": c.code, "type": c.type, "level": c.level, "province": c.province, "city": c.city, "is_985": c.is_985, "is_211": c.is_211, "is_double_first": c.is_double_first, "intro": c.intro} for c in colleges]

@router.get("/{college_id}")
async def get_college(college_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(College).where(College.id == college_id))
    c = result.scalar_one_or_none()
    if not c:
        return {"error": "not found"}
    return {"id": str(c.id), "name": c.name, "code": c.code, "type": c.type, "level": c.level, "province": c.province, "city": c.city, "is_985": c.is_985, "is_211": c.is_211, "is_double_first": c.is_double_first, "intro": c.intro}
```

- [ ] **Step 5: Wire routes in main.py**

```python
from api.routes import auth, chat, profile, recommendation, college
app.include_router(recommendation.router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(college.router, prefix="/api/v1/colleges", tags=["colleges"])
```

- [ ] **Step 6: Commit**

```bash
git add backend/knowledge_base/retriever.py backend/services/recommendation_service.py backend/schemas/recommendation.py backend/api/routes/recommendation.py backend/api/routes/college.py
git commit -m "feat: add RAG retrieval and recommendation service"
```

---

## Session 4: Frontend (Day 2-3) — Independent, uses mock API

### Task 9: Vite + React + Tailwind setup

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`
- Create: `frontend/src/types/index.ts`

- [ ] **Step 1: package.json**

```json
{
  "name": "gaokao-advisor-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "zustand": "^5.0.2",
    "axios": "^1.7.9"
  },
  "devDependencies": {
    "@types/react": "^18.3.14",
    "@types/react-dom": "^18.3.5",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.7.3",
    "vite": "^6.0.7"
  }
}
```

- [ ] **Step 2: Config files**

`frontend/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000', '/ws': { target: 'ws://localhost:8000', ws: true } } },
})
```

`frontend/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: { colors: { primary: '#4f8cf7', primaryDark: '#3b6fd4', warm: '#ff8c42', success: '#4caf50', warning: '#f5a623', danger: '#e74c3c', bg: '#f5f6f8', card: '#ffffff', text: '#1a1a2e', muted: '#8b919e', border: '#e2e4e9' } } },
  plugins: [],
}
```

`frontend/postcss.config.js`:
```js
export default { plugins: { tailwindcss: {}, autoprefixer: {} } }
```

`frontend/tsconfig.json`:
```json
{ "compilerOptions": { "target": "ES2020", "useDefineForClassFields": true, "lib": ["ES2020", "DOM", "DOM.Iterable"], "module": "ESNext", "skipLibCheck": true, "moduleResolution": "bundler", "allowImportingTsExtensions": true, "isolatedModules": true, "moduleDetection": "force", "noEmit": true, "jsx": "react-jsx", "strict": true, "noUnusedLocals": false, "noUnusedParameters": false, "noFallthroughCasesInSwitch": true }, "include": ["src"] }
```

`frontend/index.html`:
```html
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><title>高考志愿填报助手</title></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>
```

- [ ] **Step 3: Entry files**

`frontend/src/index.css`:
```css
@tailwind base; @tailwind components; @tailwind utilities;
body { font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; background: #f5f6f8; color: #1a1a2e; }
```

`frontend/src/main.tsx`:
```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
```

`frontend/src/App.tsx`:
```tsx
import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Chat from './pages/Chat'
import Recommendations from './pages/Recommendations'
import Layout from './components/common/Layout'
import ProtectedRoute from './components/common/ProtectedRoute'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/chat" element={<Chat />} />
          <Route path="/recommendations" element={<Recommendations />} />
        </Route>
      </Route>
    </Routes>
  )
}
```

- [ ] **Step 4: Types**

`frontend/src/types/index.ts`:
```ts
export interface User { user_id: string; username: string }

export interface AuthState { user: User | null; accessToken: string | null; refreshToken: string | null; login: (username: string, password: string) => Promise<void>; register: (username: string, password: string, region: string, score: number, subjects: string) => Promise<void>; logout: () => void }

export interface ChatMessage { type: string; role?: string; content?: string; stage?: string; field?: string; value?: any; confidence?: number; profile_snapshot?: any }

export interface ProfileSlot { score?: number; subjects?: string; riasec?: Record<string, number>; values?: string[]; region_pref?: string[]; career_vision?: string; family_influence?: string }

export interface Recommendation { rank: number; college_name: string; major_name: string; level: string; category: string; match_score: number; reasons: Reason[]; scores: { admission_probability: number; interest_match: number; career_prospect: number } }

export interface Reason { type: string; content: string; source: string; source_url?: string; confidence?: number }
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Vite + React + Tailwind frontend"
```

---

### Task 10: Auth stores + services + pages

**Files:**
- Create: `frontend/src/services/api.ts`, `frontend/src/services/auth.ts`
- Create: `frontend/src/stores/authStore.ts`
- Create: `frontend/src/pages/Landing.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/pages/Register.tsx`
- Create: `frontend/src/components/common/ProtectedRoute.tsx`

- [ ] **Step 1: API client**

`frontend/src/services/api.ts`:
```ts
import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use((r) => r, async (error) => {
  if (error.response?.status === 401) {
    const refresh = localStorage.getItem('refresh_token')
    if (refresh) {
      try {
        const { data } = await axios.post('/api/v1/auth/refresh', {}, { headers: { Authorization: `Bearer ${refresh}` } })
        localStorage.setItem('access_token', data.access_token)
        error.config.headers.Authorization = `Bearer ${data.access_token}`
        return api(error.config)
      } catch { localStorage.clear(); window.location.href = '/login' }
    }
  }
  return Promise.reject(error)
})

export default api
```

`frontend/src/services/auth.ts`:
```ts
import api from './api'

export const authApi = {
  login: (username: string, password: string) => api.post('/auth/login', { username, password }),
  register: (username: string, password: string, region: string, score: number, subjects: string) => api.post('/auth/register', { username, password, region, score, subjects }),
}
```

- [ ] **Step 2: Auth store**

`frontend/src/stores/authStore.ts`:
```ts
import { create } from 'zustand'
import { authApi } from '../services/auth'

interface AuthState {
  user: { user_id: string; username: string } | null
  accessToken: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string, region: string, score: number, subjects: string) => Promise<void>
  logout: () => void
  setTokens: (access: string, refresh: string) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: localStorage.getItem('access_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),
  login: async (username, password) => {
    const { data } = await authApi.login(username, password)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    set({ user: { user_id: data.user_id, username: data.username }, accessToken: data.access_token, isAuthenticated: true })
  },
  register: async (username, password, region, score, subjects) => {
    const { data } = await authApi.register(username, password, region, score, subjects)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    set({ user: { user_id: data.user_id, username: data.username }, accessToken: data.access_token, isAuthenticated: true })
  },
  logout: () => {
    localStorage.clear()
    set({ user: null, accessToken: null, isAuthenticated: false })
  },
  setTokens: (access, refresh) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    set({ accessToken: access, isAuthenticated: true })
  },
}))
```

- [ ] **Step 3: Pages**

`frontend/src/pages/Landing.tsx`:
```tsx
import { Link } from 'react-router-dom'

export default function Landing() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-blue-50 to-white">
      <div className="text-center max-w-lg px-6">
        <h1 className="text-4xl font-bold text-text mb-4">高考志愿填报助手</h1>
        <p className="text-lg text-muted mb-8">通过智能对话了解你的兴趣和价值观，为你推荐最匹配的大学专业</p>
        <div className="flex gap-4 justify-center">
          <Link to="/register" className="px-8 py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition">开始使用</Link>
          <Link to="/login" className="px-8 py-3 border border-border text-text rounded-lg font-semibold hover:bg-gray-50 transition">登录</Link>
        </div>
      </div>
    </div>
  )
}
```

`frontend/src/pages/Login.tsx`:
```tsx
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const login = useAuthStore((s) => s.login)
  const nav = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try { await login(username, password); nav('/chat') }
    catch { setError('用户名或密码错误') }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-xl shadow-sm border border-border w-full max-w-sm">
        <h2 className="text-2xl font-bold text-text mb-6 text-center">登录</h2>
        {error && <div className="bg-red-50 text-danger text-sm p-3 rounded-lg mb-4">{error}</div>}
        <input className="w-full px-4 py-3 border border-border rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-primary" placeholder="用户名" value={username} onChange={(e) => setUsername(e.target.value)} required />
        <input className="w-full px-4 py-3 border border-border rounded-lg mb-6 focus:outline-none focus:ring-2 focus:ring-primary" type="password" placeholder="密码" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button type="submit" className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition">登录</button>
        <p className="text-center text-muted text-sm mt-4">还没有账号？<Link to="/register" className="text-primary hover:underline">注册</Link></p>
      </form>
    </div>
  )
}
```

`frontend/src/pages/Register.tsx`:
```tsx
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function Register() {
  const [form, setForm] = useState({ username: '', password: '', region: '广东', score: '', subjects: '' })
  const [error, setError] = useState('')
  const register = useAuthStore((s) => s.register)
  const nav = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try { await register(form.username, form.password, form.region, Number(form.score), form.subjects); nav('/chat') }
    catch { setError('注册失败，请重试') }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-xl shadow-sm border border-border w-full max-w-sm">
        <h2 className="text-2xl font-bold text-text mb-6 text-center">注册</h2>
        {error && <div className="bg-red-50 text-danger text-sm p-3 rounded-lg mb-4">{error}</div>}
        <input className="w-full px-4 py-3 border border-border rounded-lg mb-3 focus:outline-none focus:ring-2 focus:ring-primary" placeholder="用户名" value={form.username} onChange={(e) => setForm({...form, username: e.target.value})} required />
        <input className="w-full px-4 py-3 border border-border rounded-lg mb-3 focus:outline-none focus:ring-2 focus:ring-primary" type="password" placeholder="密码" value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} required />
        <select className="w-full px-4 py-3 border border-border rounded-lg mb-3 focus:outline-none focus:ring-2 focus:ring-primary bg-white" value={form.region} onChange={(e) => setForm({...form, region: e.target.value})}>
          <option>广东</option><option>北京</option><option>上海</option>
        </select>
        <input className="w-full px-4 py-3 border border-border rounded-lg mb-3 focus:outline-none focus:ring-2 focus:ring-primary" placeholder="预估分数（如 610）" type="number" value={form.score} onChange={(e) => setForm({...form, score: e.target.value})} required />
        <input className="w-full px-4 py-3 border border-border rounded-lg mb-6 focus:outline-none focus:ring-2 focus:ring-primary" placeholder="选科（如 物理+化学+生物）" value={form.subjects} onChange={(e) => setForm({...form, subjects: e.target.value})} required />
        <button type="submit" className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition">注册</button>
        <p className="text-center text-muted text-sm mt-4">已有账号？<Link to="/login" className="text-primary hover:underline">登录</Link></p>
      </form>
    </div>
  )
}
```

`frontend/src/components/common/ProtectedRoute.tsx`:
```tsx
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

export default function ProtectedRoute() {
  return useAuthStore((s) => s.isAuthenticated) ? <Outlet /> : <Navigate to="/login" />
}
```

`frontend/src/components/common/Layout.tsx`:
```tsx
import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

export default function Layout() {
  const logout = useAuthStore((s) => s.logout)
  const nav = useNavigate()
  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-border px-6 py-3 flex items-center justify-between">
        <Link to="/chat" className="font-bold text-lg text-text">高考志愿助手</Link>
        <button onClick={() => { logout(); nav('/') }} className="text-sm text-muted hover:text-text">退出</button>
      </header>
      <Outlet />
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/ frontend/src/stores/ frontend/src/pages/ frontend/src/components/
git commit -m "feat: add auth pages, stores, and API client"
```

---

### Task 11: Chat page — WebSocket hook + components

**Files:**
- Create: `frontend/src/hooks/useWebSocket.ts`, `frontend/src/hooks/useChat.ts`
- Create: `frontend/src/stores/chatStore.ts`
- Create: `frontend/src/components/chat/ChatBubble.tsx`, `ChatInput.tsx`, `StageIndicator.tsx`, `SlotProgress.tsx`, `SummaryModal.tsx`
- Create: `frontend/src/pages/Chat.tsx`

- [ ] **Step 1: WebSocket hook**

`frontend/src/hooks/useWebSocket.ts`:
```ts
import { useEffect, useRef, useCallback } from 'react'

export function useWebSocket(sessionId: string | null, onMessage: (msg: any) => void) {
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!sessionId) return
    const token = localStorage.getItem('access_token')
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/chat/session/${sessionId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      onMessage(msg)
    }
    ws.onerror = () => console.error('WebSocket error')
    return () => { ws.close() }
  }, [sessionId])

  const send = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', content, session_id: sessionId }))
    }
  }, [sessionId])

  return { send }
}
```

- [ ] **Step 2: Chat store**

`frontend/src/stores/chatStore.ts`:
```ts
import { create } from 'zustand'
import type { ChatMessage, ProfileSlot } from '../types'

interface ChatState {
  sessionId: string | null
  stage: string
  messages: ChatMessage[]
  slots: ProfileSlot
  summaryPending: boolean
  summaryData: { stage: string; content: string; profile: any } | null
  setSessionId: (id: string) => void
  addMessage: (msg: ChatMessage) => void
  setStage: (stage: string) => void
  updateSlots: (slots: ProfileSlot) => void
  showSummary: (data: any) => void
  dismissSummary: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  sessionId: null,
  stage: 'open',
  messages: [],
  slots: {},
  summaryPending: false,
  summaryData: null,
  setSessionId: (id) => set({ sessionId: id }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setStage: (stage) => set({ stage }),
  updateSlots: (slots) => set({ slots }),
  showSummary: (data) => set({ summaryPending: true, summaryData: data }),
  dismissSummary: () => set({ summaryPending: false, summaryData: null }),
}))
```

- [ ] **Step 3: useChat hook**

`frontend/src/hooks/useChat.ts`:
```ts
import { useEffect, useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useWebSocket } from './useWebSocket'
import api from '../services/api'
import type { ChatMessage } from '../types'

export function useChat() {
  const { sessionId, setSessionId, addMessage, setStage, updateSlots, showSummary } = useChatStore()

  const handleMessage = useCallback((msg: ChatMessage) => {
    if (msg.type === 'thinking') { addMessage(msg); return }
    if (msg.type === 'message' && msg.role === 'assistant') { addMessage(msg) }
    if (msg.type === 'stage_change') { setStage(msg.content || '') }
    if (msg.type === 'profile_update') { updateSlots(msg.value || {}) }
    if (msg.type === 'summary') { showSummary({ stage: msg.stage || '', content: msg.content || '', profile: msg.profile_snapshot || {} }) }
  }, [])

  const { send } = useWebSocket(sessionId, handleMessage)

  useEffect(() => {
    if (!sessionId) {
      api.post('/chat/session').then((r) => { setSessionId(r.data.session_id) })
        .catch(() => { setSessionId('mock-session') })
    }
  }, [sessionId])

  return { send, sessionId }
}
```

- [ ] **Step 4: Chat components**

`frontend/src/components/chat/StageIndicator.tsx`:
```tsx
const stages = [{ key: 'open', label: '建立信任' }, { key: 'explore', label: '深度探索' }, { key: 'focus', label: '聚焦澄清' }, { key: 'confirm', label: '画像确认' }]
const order = ['open', 'explore', 'focus', 'confirm']

export default function StageIndicator({ current }: { current: string }) {
  const idx = order.indexOf(current)
  return (
    <div className="space-y-1">
      <div className="text-xs uppercase text-muted tracking-wider mb-2">对话阶段</div>
      {stages.map((s, i) => {
        const done = i < idx, active = i === idx
        return (
          <div key={s.key} className={`flex items-center gap-2 px-2 py-1.5 rounded-md ${active ? 'bg-blue-50' : done ? 'opacity-50' : 'opacity-30'}`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-white ${active ? 'bg-warning' : done ? 'bg-primary' : 'bg-gray-300'}`}>{done ? '✓' : i + 1}</span>
            <span className={`text-xs font-medium ${active ? 'text-warning' : 'text-text'}`}>{s.label}</span>
          </div>
        )
      })}
    </div>
  )
}
```

`frontend/src/components/chat/SlotProgress.tsx`:
```tsx
import type { ProfileSlot } from '../../types'

export default function SlotProgress({ slots }: { slots: ProfileSlot }) {
  const items = [
    { key: 'score', label: '分数 / 选科', done: !!slots.score },
    { key: 'batch', label: '目标批次', done: true },
    { key: 'riasec', label: '兴趣倾向', done: Object.keys(slots.riasec || {}).length > 0 },
    { key: 'values', label: '价值观排序', done: (slots.values || []).length > 0 },
    { key: 'region_pref', label: '地域偏好', done: (slots.region_pref || []).length > 0 },
  ]
  const done = items.filter((i) => i.done).length
  const pct = Math.round((done / items.length) * 100)

  return (
    <div>
      <div className="text-xs uppercase text-muted tracking-wider mb-2">已收集信息</div>
      <div className="space-y-1.5">
        {items.map((i) => (
          <div key={i.key} className={`flex items-center gap-2 text-xs ${i.done ? '' : 'opacity-40'}`}>
            <span className={i.done ? 'text-success' : ''}>{i.done ? '✓' : '○'}</span>
            <span>{i.label}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 bg-border rounded h-1"><div className="bg-primary h-1 rounded transition-all" style={{ width: `${pct}%` }} /></div>
      <div className="text-xs text-muted mt-1 text-right">完成度 {pct}%</div>
    </div>
  )
}
```

`frontend/src/components/chat/ChatBubble.tsx`:
```tsx
import type { ChatMessage } from '../../types'

export default function ChatBubble({ msg }: { msg: ChatMessage }) {
  if (msg.type === 'thinking') {
    return (
      <div className="flex gap-3 max-w-[80%]">
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs flex-shrink-0">AI</div>
        <div className="bg-card rounded-xl px-4 py-3 flex gap-1.5 items-center">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-300 animate-bounce" />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: '0.15s' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: '0.3s' }} />
          <span className="text-muted ml-1 text-sm">{msg.message || '正在分析...'}</span>
        </div>
      </div>
    )
  }
  const isAI = msg.role === 'assistant'
  return (
    <div className={`flex gap-3 max-w-[80%] ${isAI ? '' : 'self-end flex-row-reverse'}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs flex-shrink-0 ${isAI ? 'bg-primary' : 'bg-warm'}`}>{isAI ? 'AI' : '我'}</div>
      <div>
        <div className={`rounded-xl px-4 py-3 leading-relaxed ${isAI ? 'bg-card text-text' : 'bg-primary text-white'}`}>{msg.content}</div>
        {msg.stage && <div className="text-xs text-muted mt-1 px-1">{msg.stage === 'open' ? '建立信任' : msg.stage === 'explore' ? '深度探索' : msg.stage === 'focus' ? '聚焦澄清' : msg.stage === 'confirm' ? '画像确认' : msg.stage}</div>}
      </div>
    </div>
  )
}
```

`frontend/src/components/chat/ChatInput.tsx`:
```tsx
import { useState } from 'react'

export default function ChatInput({ onSend, disabled }: { onSend: (text: string) => void; disabled?: boolean }) {
  const [text, setText] = useState('')
  const handle = () => { if (text.trim()) { onSend(text.trim()); setText('') } }
  return (
    <div className="flex gap-3">
      <input className="flex-1 px-5 py-3 border border-border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary" placeholder="输入你的想法..." value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handle()} disabled={disabled} />
      <button onClick={handle} disabled={disabled} className="w-11 h-11 rounded-full bg-primary text-white flex items-center justify-center hover:bg-primaryDark transition disabled:opacity-50">{'➤'}</button>
    </div>
  )
}
```

`frontend/src/components/chat/SummaryModal.tsx`:
```tsx
import { useState } from 'react'
import type { ProfileSlot } from '../../types'

interface Props { stage: string; profile: any; onConfirm: () => void; onModify: (field: string, value: any) => void; onDismiss: () => void }

function slotToRows(profile: any): { key: string; icon: string; label: string; value: string; complex: boolean }[] {
  const rows: any[] = []
  if (profile.score) rows.push({ key: 'score', icon: '📊', label: '分数', value: String(profile.score), complex: false })
  if (profile.riasec && Object.keys(profile.riasec).length > 0) {
    const n: Record<string, string> = { R: '动手', I: '研究', A: '创造', S: '助人', E: '领导', C: '规范' }
    const top = Object.entries(profile.riasec as Record<string, number>).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([k]) => n[k] || k).join(' + ')
    rows.push({ key: 'riasec', icon: '🔬', label: '兴趣类型', value: top, complex: true })
  }
  if (profile.values?.length) rows.push({ key: 'values', icon: '🎯', label: '价值观', value: profile.values.join(' > '), complex: false })
  if (profile.region_pref?.length) rows.push({ key: 'region_pref', icon: '🌍', label: '地域偏好', value: profile.region_pref.join(', '), complex: false })
  return rows
}

export default function SummaryModal({ stage, profile, onConfirm, onModify, onDismiss }: Props) {
  const rows = slotToRows(profile)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onDismiss} />
      <div className="relative bg-white rounded-2xl p-6 w-[440px] max-w-[90vw] shadow-xl">
        <div className="flex items-center gap-3 mb-5">
          <span className="text-2xl">{'📋'}</span>
          <div>
            <div className="font-bold text-lg text-text">阶段小结：{stage === 'open' ? '建立信任' : stage === 'explore' ? '深度探索' : stage === 'focus' ? '聚焦澄清' : '画像确认'}完成</div>
            <div className="text-sm text-muted">请确认或修改以下信息</div>
          </div>
        </div>
        <div className="space-y-2 mb-5">
          {rows.map((r) => (
            <div key={r.key} className="bg-blue-50/50 rounded-xl p-3 flex gap-3 items-center">
              <span className="text-xl">{r.icon}</span>
              <div className="flex-1"><div className="text-xs text-muted">{r.label}</div><div className="font-semibold text-text">{r.value}</div></div>
              <button onClick={() => onModify(r.key, profile[r.key])} className="text-primary text-xs hover:underline">修改</button>
            </div>
          ))}
        </div>
        <div className="flex gap-3">
          <button onClick={onDismiss} className="flex-1 py-2.5 border border-border rounded-lg text-text hover:bg-gray-50 transition text-sm">我再看一下对话</button>
          <button onClick={onConfirm} className="flex-[2] py-2.5 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition text-sm">确认，进入下一阶段</button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Chat page**

`frontend/src/pages/Chat.tsx`:
```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useChatStore } from '../stores/chatStore'
import { useChat } from '../hooks/useChat'
import StageIndicator from '../components/chat/StageIndicator'
import SlotProgress from '../components/chat/SlotProgress'
import ChatBubble from '../components/chat/ChatBubble'
import ChatInput from '../components/chat/ChatInput'
import SummaryModal from '../components/chat/SummaryModal'

export default function Chat() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { send } = useChat()
  const { stage, messages, slots, summaryPending, summaryData, dismissSummary, updateSlots, setStage } = useChatStore()
  const nav = useNavigate()

  const handleSend = (text: string) => {
    send(text)
  }

  const handleConfirm = () => {
    dismissSummary()
    if (stage === 'confirm') nav('/recommendations')
  }

  const handleModify = (field: string, value: any) => {
    dismissSummary()
    // For simple fields, we can do inline edit. For complex ones, close modal and let AI re-ask.
    if (field === 'region_pref' || field === 'values') {
      updateSlots({ [field]: undefined })
    }
  }

  return (
    <div className="flex h-[calc(100vh-53px)]">
      {/* Sidebar */}
      {sidebarOpen && (
        <div className="w-[260px] bg-gray-50/80 border-r border-border p-4 flex flex-col gap-6 flex-shrink-0">
          <StageIndicator current={stage} />
          <SlotProgress slots={slots} />
          <button onClick={() => setSidebarOpen(false)} className="text-xs text-muted hover:text-text mt-auto">收起侧栏 {'»'}</button>
        </div>
      )}

      {/* Main chat */}
      <div className="flex-1 flex flex-col bg-white">
        {!sidebarOpen && <button onClick={() => setSidebarOpen(true)} className="text-xs text-muted p-2 hover:text-text">{'«'} 展开侧栏</button>}
        <div className="px-4 py-2 border-b border-gray-100 text-xs text-muted">
          正在进行：<span className="text-warning font-semibold ml-1">{stage === 'open' ? '建立信任' : stage === 'explore' ? '深度探索' : stage === 'focus' ? '聚焦澄清' : stage === 'confirm' ? '画像确认' : stage}</span>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4">
          {messages.map((msg, i) => <ChatBubble key={i} msg={msg} />)}
        </div>

        <div className="p-4 border-t border-gray-100">
          <ChatInput onSend={handleSend} />
        </div>
      </div>

      {/* Summary modal */}
      {summaryPending && summaryData && (
        <SummaryModal stage={summaryData.stage} profile={summaryData.profile} onConfirm={handleConfirm} onModify={handleModify} onDismiss={dismissSummary} />
      )}
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/ frontend/src/stores/chatStore.ts frontend/src/components/chat/ frontend/src/pages/Chat.tsx
git commit -m "feat: add chat page with WebSocket, stage indicator, and summary modal"
```

---

### Task 12: Recommendations page

**Files:**
- Create: `frontend/src/services/recommendation.ts`
- Create: `frontend/src/stores/recommendationStore.ts`
- Create: `frontend/src/components/recommendation/ProfileSummaryBar.tsx`, `FilterBar.tsx`, `RecommendationCard.tsx`
- Create: `frontend/src/pages/Recommendations.tsx`

- [ ] **Step 1: Recommendation API + store**

`frontend/src/services/recommendation.ts`:
```ts
import api from './api'
export const recApi = { getRecommendations: () => api.get('/recommendations') }
```

`frontend/src/stores/recommendationStore.ts`:
```ts
import { create } from 'zustand'
import type { Recommendation } from '../types'
import { recApi } from '../services/recommendation'

interface RecState {
  recommendations: Recommendation[]
  profileSnapshot: any
  filters: { level: string; city: string; category: string }
  loading: boolean
  load: () => Promise<void>
  setFilter: (key: string, value: string) => void
}

export const useRecStore = create<RecState>((set, get) => ({
  recommendations: [], profileSnapshot: null, filters: { level: '', city: '', category: '' }, loading: false,
  load: async () => {
    set({ loading: true })
    try {
      const { data } = await recApi.getRecommendations()
      set({ recommendations: data.recommendations || [], profileSnapshot: data.profile_snapshot, loading: false })
    } catch { set({ loading: false }) }
  },
  setFilter: (key, value) => set({ filters: { ...get().filters, [key]: value } }),
}))
```

- [ ] **Step 2: Components**

`frontend/src/components/recommendation/ProfileSummaryBar.tsx`:
```tsx
import { Link } from 'react-router-dom'

export default function ProfileSummaryBar({ profile }: { profile: any }) {
  const items = [
    { icon: '👤', label: '分数 / 位次', value: profile?.score ? `${profile.score} ± 10` : '未设置' },
    { icon: '🔬', label: '兴趣类型', value: profile?.riasec ? Object.entries(profile.riasec as Record<string,number>).sort((a,b) => b[1]-a[1]).slice(0,1).map(([k]) => ({R:'动手',I:'研究',A:'创造',S:'助人',E:'领导',C:'规范'}[k])).join('') : '未分析' },
    { icon: '🌍', label: '地域偏好', value: profile?.region_pref?.length ? profile.region_pref.join(', ') : '未设置' },
  ]
  return (
    <div className="bg-white rounded-xl p-4 border border-border flex items-center gap-6 flex-wrap">
      {items.map((i) => (
        <div key={i.label} className="flex items-center gap-2">
          <span className="text-xl">{i.icon}</span>
          <div><div className="text-xs text-muted">{i.label}</div><div className="font-semibold text-text text-sm">{i.value}</div></div>
        </div>
      ))}
      <Link to="/chat" className="ml-auto text-primary text-xs hover:underline">修改画像 &rarr;</Link>
    </div>
  )
}
```

`frontend/src/components/recommendation/FilterBar.tsx`:
```tsx
export default function FilterBar({ filters, onChange, count }: { filters: any; onChange: (k: string, v: string) => void; count: number }) {
  return (
    <div className="flex gap-3 items-center flex-wrap">
      <span className="text-xs text-muted">筛选：</span>
      <select value={filters.level} onChange={(e) => onChange('level', e.target.value)} className="px-3 py-1.5 border border-border rounded-md text-xs bg-white">
        <option value="">全部层次</option><option value="985">985</option><option value="211">211</option><option value="双一流">双一流</option><option value="省重点">省重点</option>
      </select>
      <select value={filters.city} onChange={(e) => onChange('city', e.target.value)} className="px-3 py-1.5 border border-border rounded-md text-xs bg-white">
        <option value="">全部地区</option><option>广州</option><option>深圳</option><option>珠海</option><option>汕头</option><option>东莞</option>
      </select>
      <span className="ml-auto text-xs text-muted">共 <strong>{count}</strong> 条推荐</span>
    </div>
  )
}
```

`frontend/src/components/recommendation/RecommendationCard.tsx`:
```tsx
import { useState } from 'react'
import type { Recommendation } from '../../types'

const barColors: Record<string, string> = { 'admission_probability': 'bg-warning', 'interest_match': 'bg-success', 'career_prospect': 'bg-primary' }
const categoryStyle: Record<string, { bar: string; bg: string; text: string }> = {
  '冲刺': { bar: 'bg-danger', bg: 'bg-red-50', text: 'text-danger' },
  '稳妥': { bar: 'bg-success', bg: 'bg-green-50', text: 'text-[#2e7d32]' },
  '保底': { bar: 'bg-primary', bg: 'bg-blue-50', text: 'text-primary' },
}

export default function RecommendationCard({ rec }: { rec: Recommendation }) {
  const [open, setOpen] = useState(false)
  const cs = categoryStyle[rec.category] || categoryStyle['稳妥']
  return (
    <div className="bg-white rounded-xl border border-border overflow-hidden">
      <div className="flex">
        <div className={`w-1 flex-shrink-0 ${cs.bar}`} />
        <div className="flex-1 p-5">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex gap-2 items-center flex-wrap">
                <h3 className="font-bold text-text">{rec.college_name}</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${cs.bg} ${cs.text}`}>{rec.category}</span>
                <span className="text-xs bg-blue-50 text-primary px-2 py-0.5 rounded-full">{rec.level}</span>
              </div>
              <div className="font-semibold text-text mt-1.5">{rec.major_name}</div>
            </div>
            <div className="text-right">
              <div className={`text-2xl font-extrabold ${cs.text}`}>{rec.match_score}%</div>
              <div className="text-xs text-muted">综合匹配</div>
            </div>
          </div>

          <div className="flex gap-4 mt-4">
            {Object.entries(rec.scores).map(([k, v]) => (
              <div key={k} className="flex-1">
                <div className="flex justify-between text-xs text-muted mb-1">
                  <span>{k === 'admission_probability' ? '录取概率' : k === 'interest_match' ? '兴趣匹配' : '前景评分'}</span>
                  <span>{v}%</span>
                </div>
                <div className="h-1 bg-border rounded-full"><div className={`h-1 rounded-full ${barColors[k] || 'bg-primary'}`} style={{ width: `${v}%` }} /></div>
              </div>
            ))}
          </div>

          <button onClick={() => setOpen(!open)} className="mt-3 text-primary text-xs hover:underline">{open ? '收起' : '展开'}详细理由</button>

          {open && (
            <div className="mt-3 bg-gray-50 rounded-lg p-4">
              <div className="text-xs text-muted mb-2">推荐理由 &amp; 数据来源</div>
              <div className="space-y-3">
                {rec.reasons.map((r, i) => (
                  <div key={i} className="flex gap-2 text-sm">
                    <span className="flex-shrink-0">{r.type === 'score_match' ? '🎯' : r.type === 'interest_match' ? '🔬' : '📈'}</span>
                    <div>
                      <p className="text-text leading-relaxed">{r.content}</p>
                      <p className="text-xs text-muted mt-0.5">来源：{r.source}{r.source_url ? ` (${r.source_url})` : ''}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Recommendations page**

`frontend/src/pages/Recommendations.tsx`:
```tsx
import { useEffect } from 'react'
import { useRecStore } from '../stores/recommendationStore'
import ProfileSummaryBar from '../components/recommendation/ProfileSummaryBar'
import FilterBar from '../components/recommendation/FilterBar'
import RecommendationCard from '../components/recommendation/RecommendationCard'

export default function Recommendations() {
  const { recommendations, profileSnapshot, filters, loading, load, setFilter } = useRecStore()

  useEffect(() => { load() }, [])

  const filtered = recommendations.filter((r) => {
    if (filters.level && r.level !== filters.level) return false
    if (filters.city && !r.college_name.includes(filters.city) && !r.college_name.includes(filters.city.replace('市',''))) return false
    if (filters.category && r.category !== filters.category) return false
    return true
  })

  if (loading) return <div className="flex items-center justify-center h-64 text-muted">加载中...</div>

  return (
    <div className="max-w-[900px] mx-auto p-5">
      <ProfileSummaryBar profile={profileSnapshot} />
      <div className="mt-4"><FilterBar filters={filters} onChange={setFilter} count={filtered.length} /></div>
      <div className="mt-4 space-y-3">
        {filtered.map((r) => <RecommendationCard key={r.rank} rec={r} />)}
        {filtered.length === 0 && <div className="text-center text-muted py-12">没有匹配的推荐结果</div>}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/recommendation.ts frontend/src/stores/recommendationStore.ts frontend/src/components/recommendation/ frontend/src/pages/Recommendations.tsx
git commit -m "feat: add recommendations page with cards and filtering"
```

---

## Session Integration (Day 4-5)

### Task 13: End-to-end integration + deployment

**Files:**
- Modify: `backend/main.py` — ensure all routes wired
- Modify: `docker-compose.yml` — finalize for cloud deployment

- [ ] **Step 1: Verify all routes in main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import auth, chat, profile, recommendation, college
from models import init_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Gaokao Advisor API", version="0.1.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
app.include_router(recommendation.router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(college.router, prefix="/api/v1/colleges", tags=["colleges"])

@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Seed data on startup**

Add to `backend/main.py` after `init_db()`:
```python
# Check if empty and seed
from sqlalchemy import select
from models.college import College
async with async_session() as db:
    result = await db.execute(select(College).limit(1))
    if not result.scalar_one_or_none():
        print("Database empty — run: python scripts/seed_db.py && python scripts/index_chroma.py")
```

- [ ] **Step 3: Test full flow locally**

```bash
# Terminal 1: start services
docker compose up db redis -d

# Terminal 2: start backend
cd backend && pip install -r requirements.txt && python -c "from models import init_db; import asyncio; asyncio.run(init_db())" && python scripts/seed_db.py && python scripts/index_chroma.py && uvicorn main:app --reload

# Terminal 3: start frontend
cd frontend && npm install && npm run dev

# Test flow:
# 1. POST /api/v1/auth/register { username, password, region, score, subjects }
# 2. POST /api/v1/chat/session → session_id
# 3. Connect WebSocket /api/v1/chat/session/{session_id}
# 4. Complete 4-stage conversation
# 5. GET /api/v1/recommendations → verify recommendations
```

- [ ] **Step 4: Deploy to cloud server**

```bash
# On cloud server
git clone <repo>
cd gaokao_agents
cp .env.example .env
# Edit .env with real DEEPSEEK_API_KEY and generated JWT_SECRET
docker compose up -d --build
```

- [ ] **Step 5: Commit**

```bash
git add backend/main.py
git commit -m "feat: finalize integration with lifespan and health check"
git add .
git commit -m "chore: final integration, ready for deployment"
```

---

## Summary: Execution Order

```
Day 1: Task 1 (Scaffolding) → Task 2 (Models) → Task 3 (Auth) → Task 4 (Seeds)
Day 2-3 (parallel):
  Session 2: Task 5 (State+Prompts) → Task 6 (Agent+Slots) → Task 7 (WebSocket)
  Session 3: Task 8 (RAG+Recommendation)
  Session 4: Task 9 (Frontend setup) → Task 10 (Auth pages) → Task 11 (Chat page) → Task 12 (Recommendations page)
Day 4: Task 13 (Integration + deploy)
Day 5: End-to-end testing with real students
```
