import json
import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from config import settings
from models import init_db, async_session
from models.college import College
from models.admission import AdmissionData

logger = logging.getLogger(__name__)


# ── Seed / Index helpers (unchanged) ──

def _load_json(path: str) -> list:
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


# ── Auto-import knowledge data on first boot ──

async def _auto_import_knowledge():
    """If TenantData is empty and knowledge JSON exists, import it."""
    from pathlib import Path

    knowledge_file = Path("/app/data/approved/scnu_ibc_rag_knowledge_base.json")
    if not knowledge_file.exists():
        logger.info("Knowledge data file not found, skipping auto-import.")
        return

    from models import async_session as _as
    from sqlalchemy import select, func
    from tenants.models import TenantData

    async with _as() as db:
        count = await db.execute(select(func.count()).select_from(TenantData))
        rows = count.scalar()
        if rows and rows > 0:
            logger.info(f"TenantData already has {rows} rows, skipping auto-import.")
            return

    logger.info("TenantData empty — running knowledge auto-import...")
    try:
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "/app/scripts/import_scnu_knowledge.py"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            logger.info("Knowledge auto-import complete.")
        else:
            logger.warning(f"Knowledge auto-import failed: {result.stderr}")
    except Exception as e:
        logger.warning(f"Knowledge auto-import failed: {e}")


# ── Lifespan ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("Database tables created.")

    from core.startup_seed import _ensure_tenant_and_admin
    await _ensure_tenant_and_admin()

    await _auto_import_knowledge()

    if await _seed_if_empty():
        try:
            await _run_seed()
            await _run_index()
        except FileNotFoundError:
            print("Seed data files not found, skipping seed (production mode).")
    else:
        print("Skipping seed and index (already seeded).")

    # 预热 embedding 模型（消除首次调用冷启动延迟）
    try:
        from knowledge_base.embeddings import embedding_model
        _ = embedding_model.embed_query("预热")
        logger.info("Embedding model warmed up")
    except Exception as e:
        logger.warning(f"Embedding model warmup failed: {e}")

    # 检查 scnu_colleges 集合是否有数据，空则触发索引
    try:
        from knowledge_base.chroma_client import client as chroma_client
        try:
            col = chroma_client.get_collection("scnu_colleges")
            count = col.count()
            if count == 0:
                logger.warning("scnu_colleges collection is empty, running index...")
                from knowledge.indexer import reindex_tenant
                await reindex_tenant("scnu")
                logger.info("scnu_colleges indexed successfully")
            else:
                logger.info(f"scnu_colleges collection has {count} documents")
        except Exception:
            logger.warning("scnu_colleges collection not found, running index...")
            from knowledge.indexer import reindex_tenant
            await reindex_tenant("scnu")
            logger.info("scnu_colleges indexed successfully")
    except Exception as e:
        logger.warning(f"ChromaDB index check failed: {e}")

    from distribution.scheduler import start_scheduler, shutdown_scheduler
    start_scheduler()
    print("Distribution scheduler started.")

    # 提示词启动一致性检查：CODE_DEFAULTS 与 PROMPT_FILE_MAP 一致 + 关键占位符存在
    try:
        from services.prompt_service import CODE_DEFAULTS, PROMPT_FILE_MAP
        missing_keys = set(CODE_DEFAULTS.keys()) - set(PROMPT_FILE_MAP.keys())
        if missing_keys:
            logger.warning(f"PROMPT_FILE_MAP missing keys: {missing_keys}")
        # 验证 B2B prompt 含 consult_context 和 knowledge_context 占位符
        from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT
        for placeholder in ("{consult_context}", "{knowledge_context}"):
            if placeholder not in B2B_SYSTEM_PROMPT:
                logger.warning(f"B2B_SYSTEM_PROMPT missing {placeholder} placeholder")
        else:
            logger.info(
                "Prompt consistency check passed: %d keys, B2B placeholders OK",
                len(CODE_DEFAULTS),
            )
    except Exception as e:
        logger.warning(f"Prompt consistency check failed: {e}")

    yield

    shutdown_scheduler()
    print("Distribution scheduler stopped.")


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
from api.routes import auth, chat, profile, recommendation, college, industry, compare, knowledge, miniapp  # noqa: E402
from api.routes import consult, prompt_admin  # noqa: E402

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
app.include_router(recommendation.router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(college.router, prefix="/api/v1/colleges", tags=["colleges"])
app.include_router(compare.router, prefix="/api/v1/compare", tags=["compare"])
app.include_router(industry.router, prefix="/api/v1", tags=["industry"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])

# ── C端小程序 Routes ──
app.include_router(miniapp.router)

# ── C端咨询模块 Routes（SSE 流式） ──
app.include_router(consult.router)

# ── New B2B Routes ──
from tenants.router import router as tenant_router  # noqa: E402
from analytics.router import router as analytics_router  # noqa: E402
from admin.router import router as admin_router  # noqa: E402
from api.routes import db_admin  # noqa: E402
from api.routes import consult_workbench  # noqa: E402

app.include_router(tenant_router, prefix="/api/v1/admin/tenants", tags=["tenants"])
app.include_router(analytics_router, prefix="/api/v1/admin/analytics", tags=["analytics"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(db_admin.router, prefix="/api/v1/admin", tags=["db-admin"])
app.include_router(consult_workbench.router, prefix="/api/v1/admin", tags=["consult-workbench"])

# ── 提示词管理 Routes（admin） ──
app.include_router(prompt_admin.router, prefix="/api/v1/admin", tags=["prompt-admin"])

# Distribution Routes
from distribution.router import router as distribution_router  # noqa: E402

app.include_router(distribution_router, prefix="/api/v1/distribution", tags=["distribution"])

app.mount("/uploads", StaticFiles(directory=os.path.abspath(settings.uploads_dir)), name="uploads")

@app.get("/api/health")
async def health():
    return {"status": "ok"}
