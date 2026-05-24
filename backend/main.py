import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from config import settings
from models import init_db, async_session
from models.college import College
from models.admission import AdmissionData


# ── Seed / Index helpers (unchanged) ──

def _load_json(path: str) -> list:
    import os

    base = os.environ.get("DATA_DIR", "data/seed")
    filepath = os.path.join(base, path)
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


async def _seed_if_empty():
    async with async_session() as db:
        existing = await db.execute(select(College).limit(1))
        if existing.scalar_one_or_none():
            print("Database already has data, skipping seed.")
            return False
    return True


async def _run_seed():
    async with async_session() as db:
        schools = _load_json("schools.json")
        scores = _load_json("scores.json")
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


async def _run_index():
    from knowledge_base.chroma_client import index_documents

    async with async_session() as db:
        colleges = {str(c.id): c for c in (await db.execute(select(College))).scalars().all()}
        admissions = (await db.execute(select(AdmissionData))).scalars().all()
        docs, metas, ids_list = [], [], []
        for a in admissions:
            c = colleges.get(str(a.college_id))
            if not c:
                continue
            doc = (
                f"{c.name} {a.major_name} {c.level} {c.province}{c.city} "
                f"录取位次{a.min_rank} 分数{a.min_score} {a.subject_requirements} "
                f"985:{c.is_985} 211:{c.is_211} {c.intro}"
            )
            docs.append(doc)
            metas.append({
                "college_id": str(a.college_id),
                "college_name": c.name,
                "major_name": a.major_name,
                "level": c.level,
                "province": c.province,
                "city": c.city,
                "min_rank": a.min_rank,
                "min_score": a.min_score,
                "subjects": a.subject_requirements,
                "source_url": a.source_url,
            })
            ids_list.append(str(a.id))
        if docs:
            index_documents(docs, metas, ids_list)
            print(f"Indexed {len(docs)} documents into Chroma.")


# ── Lifespan ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("Database tables created.")

    if await _seed_if_empty():
        try:
            await _run_seed()
            await _run_index()
        except FileNotFoundError:
            print("Seed data files not found, skipping seed (production mode).")
    else:
        print("Skipping seed and index (already seeded).")

    yield


# ── App ──

app = FastAPI(title="招生智脑 API", version="2.0.0", lifespan=lifespan)

# CORS (allow local dev + Cloudflare Pages production origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── B2B Middleware (order matters!) ──
from core.middleware import TenantResolutionMiddleware, UserAuthMiddleware, ModuleGateMiddleware  # noqa: E402

app.add_middleware(TenantResolutionMiddleware)
app.add_middleware(UserAuthMiddleware)
app.add_middleware(ModuleGateMiddleware)

# ── Existing Routes (api/routes) ──
from api.routes import auth, chat, profile, recommendation, college, industry, compare, miniapp  # noqa: E402

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
app.include_router(recommendation.router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(college.router, prefix="/api/v1/colleges", tags=["colleges"])
app.include_router(compare.router, prefix="/api/v1/compare", tags=["compare"])
app.include_router(industry.router, prefix="/api/v1", tags=["industry"])

# ── C端小程序 Routes ──
app.include_router(miniapp.router)

# ── New B2B Routes ──
from tenants.router import router as tenant_router  # noqa: E402
from analytics.router import router as analytics_router  # noqa: E402
from admin.router import router as admin_router  # noqa: E402

app.include_router(tenant_router, prefix="/api/v1/admin/tenants", tags=["tenants"])
app.include_router(analytics_router, prefix="/api/v1/admin/analytics", tags=["analytics"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
