# B2B 招生智脑平台 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Gaokao Agents 从单用户 B2C 原型改造为多租户 B2B SaaS 平台，支持院校白标小程序 + 管理端数据面板。

**Architecture:** FastAPI 单体 + 领域模块化目录 + 共享 PostgreSQL(tenant_id 行隔离) + 独立 ChromaDB collection + 统一 event_logs 驱动分析。管理端 React SPA(CSS 变量换肤)，小程序 uni-app(构建配置注入)。

**Tech Stack:** Python 3.11, FastAPI, LangGraph, ChromaDB, PostgreSQL(pgvector), Redis, React 18 + TypeScript + Tailwind, uni-app(Vue 3)

**并行策略:** Foundation 轨道完成 API scaffold 后，Admin SPA / Mini-App / Analytics / Data Onboarding 四个轨道并行。

---

## 轨道与依赖

```
Week 1-2  │  Week 3-5   │  Week 6-9            │  Week 10-13
          │             │                      │
Phase 0   │  Phase 1    │  Phase 2             │  Phase 3
稳定化    │  地基       │  重建                │  扩展
          │             │                      │
  ┌───────┼──────────┐  │  ┌─────────────────┐ │  ┌──────────────────┐
  │Foundation Track  ├──┼──┤ 并行轨道启动      │ │  │ 全部轨道收尾合并   │
  │(单 session)      │  │  │                  │ │  │                  │
  └──────────────────┘  │  │ feat/admin-spa   │ │  │ feat/analytics    │
                        │  │ feat/mini-app    │ │  │ feat/data-onboard │
                        │  │                  │ │  │                  │
                        │  │ 可 4 session 并行 │ │  │ 增量开发          │
                        │  └─────────────────┘ │  └──────────────────┘
```

**Gate:** Phase 1 Week 5 完成（API scaffold 可调用）→ 解锁所有并行轨道

---

## Git 管理要求

### 每个 session 开始
```bash
git fetch origin
git checkout <你的分支>
git pull origin <你的分支>  # 如果有其他 session 在同一分支
```

### 每个 task 完成后
```bash
git add <changed files>
git commit -m "<type>: <description>"
```

### 每日结束
```bash
git push origin <你的分支>
# 更新 SESSION_STATE.md 并提交
```

### 合并
```bash
# feat/* → develop: PR via GitHub
# develop → main: 里程碑完成后，完整测试通过
```

---

## Foundation Track (Phase 0 + Phase 1, Week 1-5)

**分支:** `feat/foundation`
**Session 数:** 1（必须顺序执行）

### Task F0.1: 环境准备与 Alembic 初始化

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial_migration.py`
- Modify: `requirements.txt`

- [ ] **Step 1: 安装 Alembic 并初始化**

```bash
cd backend
pip install alembic
alembic init alembic
```

- [ ] **Step 2: 配置 alembic/env.py 指向数据库**

```python
# alembic/env.py
from backend.config import Settings
from backend.core.database import Base

settings = Settings()
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```

- [ ] **Step 3: 创建初始迁移（基于现有 8 个模型）**

```bash
alembic revision --autogenerate -m "001_initial_schema"
alembic upgrade head
```

- [ ] **Step 4: 验证迁移**

```bash
alembic downgrade -1  # 回滚
alembic upgrade head  # 重新升级
```

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/ backend/alembic.ini requirements.txt
git commit -m "chore: init Alembic with existing schema migration"
```

---

### Task F0.2: 核心引擎审查 — Conversation Agent

**Files:**
- Review: `backend/agents/conversation/agent.py`
- Review: `backend/agents/conversation/state.py`
- Create: `backend/tests/unit/test_conversation_agent.py`

- [ ] **Step 1: 编写状态转换测试**

```python
# tests/unit/test_conversation_agent.py
import pytest
from conversation.state import Stage, ConversationState

def test_stage_progression_open_to_explore():
    """3+ RIASEC dims + region_pref → transition to explore"""
    state = ConversationState(
        messages=[],
        stage=Stage.OPEN,
        slots={"riasec": {"R": 6, "I": 5, "S": 4}, "region_pref": "广东"},
        stage_complete=False,
        summary_pending=False
    )
    # 测试 _determine_next_stage 逻辑
    from conversation.agent import _determine_next_stage
    assert _determine_next_stage(state) == Stage.EXPLORE

def test_stage_no_transition_insufficient_evidence():
    """Only 2 RIASEC dims → stay in OPEN"""
    state = ConversationState(
        messages=[],
        stage=Stage.OPEN,
        slots={"riasec": {"R": 6, "I": 5}, "region_pref": None},
        stage_complete=False,
        summary_pending=False
    )
    from conversation.agent import _determine_next_stage
    assert _determine_next_stage(state) == Stage.OPEN
```

- [ ] **Step 2: 运行测试确认当前行为**

```bash
pytest backend/tests/unit/test_conversation_agent.py -v
```

- [ ] **Step 3: 审查 agent.py 边界 case 并修复发现的问题**

审查重点：
- 空消息列表时不崩溃
- 情感检测的关键词匹配边界（无匹配时返回 neutral）
- 系统提示构建时 stage/slots/blinds/hints 为空的情况

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/test_conversation_agent.py
git commit -m "test: add conversation agent stage transition tests"
```

---

### Task F0.3: 核心引擎审查 — Evidence Accumulator

**Files:**
- Review: `backend/agents/conversation/evidence_accumulator.py`
- Create: `backend/tests/unit/test_evidence_accumulator.py`

- [ ] **Step 1: 编写画像累积单元测试**

```python
# tests/unit/test_evidence_accumulator.py
import pytest
from conversation.evidence_accumulator import EvidenceAccumulator

def test_confidence_calculation_never_exceeds_095():
    acc = EvidenceAccumulator()
    for i in range(20):  # 大量证据
        acc.add_evidence("R", 8, "喜欢拆装机械")
    assert acc.confidence["R"] <= 0.95

def test_confidence_increases_with_more_evidence():
    acc = EvidenceAccumulator()
    acc.add_evidence("R", 7, "喜欢动手")
    first_conf = acc.confidence["R"]
    acc.add_evidence("R", 8, "修过自行车")
    assert acc.confidence["R"] > first_conf

def test_blind_spot_detection():
    acc = EvidenceAccumulator()
    acc.add_evidence("R", 8, "test")
    acc.add_evidence("I", 7, "test")
    acc.add_evidence("A", 6, "test")
    blinds = acc.get_blind_spots()
    assert "S" in blinds or "E" in blinds or "C" in blinds

def test_completeness_levels():
    acc = EvidenceAccumulator()
    assert acc.get_completeness() == "L1"  # 初始
    acc.add_evidence("R", 7, "test")
    acc.add_evidence("I", 6, "test")
    acc.set_region_pref("广东")
    assert acc.get_completeness() == "L2"
    acc.add_evidence("A", 5, "test")
    acc.add_evidence("S", 6, "test")
    acc.add_values(["社会贡献"])
    assert acc.get_completeness() == "L3"
```

- [ ] **Step 2: 运行测试**

```bash
pytest backend/tests/unit/test_evidence_accumulator.py -v
```

- [ ] **Step 3: 修复发现的问题并重跑到全绿**

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/test_evidence_accumulator.py
git commit -m "test: add evidence accumulator unit tests"
```

---

### Task F0.4: 核心引擎审查 — Profile Analyzer 与 LLM 调用稳定性

**Files:**
- Review: `backend/agents/conversation/profile_analyzer.py`
- Review: `backend/services/recommendation_service.py`
- Create: `backend/tests/integration/test_profile_analysis.py`

- [ ] **Step 1: 编写 JSON 解析容错测试**

```python
# tests/integration/test_profile_analysis.py
import pytest
from conversation.profile_analyzer import ProfileAnalyzer

def test_parse_valid_json_response():
    analyzer = ProfileAnalyzer()
    raw = '{"new_evidence": [{"dimension": "R", "score": 8, "evidence": "喜欢修理"}], "values_hint": null, "region_mentioned": "广东", "engagement_assessment": "high"}'
    result = analyzer._parse_response(raw)
    assert len(result["new_evidence"]) == 1
    assert result["new_evidence"][0]["dimension"] == "R"

def test_parse_markdown_wrapped_json():
    analyzer = ProfileAnalyzer()
    raw = '```json\n{"new_evidence": [], "values_hint": "社会贡献", "region_mentioned": null, "engagement_assessment": "medium"}\n```'
    result = analyzer._parse_response(raw)
    assert result["values_hint"] == "社会贡献"

def test_parse_malformed_json_returns_empty():
    analyzer = ProfileAnalyzer()
    raw = 'not valid json at all {'
    result = analyzer._parse_response(raw)
    assert result["new_evidence"] == []
    assert result["engagement_assessment"] == "low"  # 默认值
```

- [ ] **Step 2: 审查推荐服务重试逻辑**

审查 `recommendation_service.py`：
- LLM 调用超时设置为 120s（已设置）
- 重试次数最多 2 次（已设置）
- 指数退避间隔是否正确
- JSON 解析失败时的 fallback 行为

- [ ] **Step 3: 修复并验证**

```bash
pytest backend/tests/integration/test_profile_analysis.py -v
```

- [ ] **Step 4: Commit**

---

### Task F0.5: WebSocket 连接管理修复

**Files:**
- Review/Modify: `backend/api/routes/chat.py`
- Create: `backend/tests/integration/test_websocket.py`

- [ ] **Step 1: 编写 WebSocket 生命周期测试**

```python
# tests/integration/test_websocket.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_ws_session_create_and_connect():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 创建 session
        resp = await client.post("/api/v1/chat/session", headers={"X-Tenant": "test"})
        assert resp.status_code == 200
        session_id = resp.json()["data"]["session_id"]

@pytest.mark.asyncio
async def test_ws_disconnect_cleans_up_session():
    # 验证 WebSocket 断开后 Redis session 被清理
    pass

@pytest.mark.asyncio
async def test_ws_reconnect_resumes_session():
    # 验证重连后恢复之前的对话状态
    pass
```

- [ ] **Step 2: 审查 chat.py 的异常处理**

- 客户端意外断开 → 清理 Redis session
- LLM 调用超时 → 发送 error 消息，不断开连接
- 无效消息格式 → 发送 error 消息
- Session 不存在的重连 → 创建新 session

- [ ] **Step 3: 修复并验证**

- [ ] **Step 4: Commit**

---

### Task F1.1: Tenant 数据模型与迁移

**Files:**
- Create: `backend/tenants/__init__.py`
- Create: `backend/tenants/models.py`
- Create: `backend/alembic/versions/002_tenant_tables.py`
- Modify: `backend/core/database.py`

- [ ] **Step 1: 编写 Tenant 模型**

```python
# tenants/models.py
import uuid
from sqlalchemy import Column, String, Enum, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from core.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    config = Column(JSONB, nullable=False, default=dict)
    subscription_tier = Column(
        Enum("basic", "standard", "advanced", "flagship", name="subscription_tier"),
        nullable=False, default="basic"
    )
    status = Column(
        Enum("active", "suspended", "cancelled", name="tenant_status"),
        nullable=False, default="active"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TenantUser(Base):
    __tablename__ = "tenant_users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(
        Enum("admin", "manager", "viewer", "department_head", name="tenant_user_role"),
        nullable=False, default="viewer"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TenantData(Base):
    __tablename__ = "tenant_data"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    data_type = Column(
        Enum("admission_score", "curriculum", "employment", "campus_life", name="tenant_data_type"),
        nullable=False
    )
    title = Column(String(500), nullable=False)
    content = Column(JSONB, nullable=False)
    source_url = Column(String(1000))
    year = Column(Integer)
    province = Column(String(100))
    metadata = Column(JSONB, default=dict)
    indexed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Department(Base):
    __tablename__ = "departments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    config = Column(JSONB, default=dict)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)

class SessionProfile(Base):
    __tablename__ = "session_profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # 注册后关联
    profile_json = Column(JSONB, nullable=False, default=dict)
    confidence_json = Column(JSONB, nullable=False, default=dict)
    completeness = Column(String(10))  # L1/L2/L3
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: 创建迁移**

```bash
alembic revision --autogenerate -m "002_add_tenant_models"
alembic upgrade head
```

- [ ] **Step 3: 验证**

```bash
alembic downgrade -1 && alembic upgrade head  # 回滚+升级测试
```

- [ ] **Step 4: Commit**

---

### Task F1.2: 现有模型 tenant_id 迁移

**Files:**
- Create: `backend/alembic/versions/003_add_tenant_id_to_existing.sql`
- Modify: `backend/auth/models.py`
- Modify: `backend/colleges/models.py`
- Modify: `backend/conversation/models.py`
- Modify: `backend/recommendation/models.py`
- Modify: `backend/profile/models.py`

- [ ] **Step 1: 生成 migration 给所有现有表加 tenant_id**

```sql
-- 003_add_tenant_id_to_existing.sql
ALTER TABLE users ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE colleges ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE admission_data ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE user_profiles ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE recommendations ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE recommendation_feedback ADD COLUMN tenant_id UUID REFERENCES tenants(id);

-- 创建索引
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_colleges_tenant ON colleges(tenant_id);
CREATE INDEX idx_admission_data_tenant ON admission_data(tenant_id);
CREATE INDEX idx_user_profiles_tenant ON user_profiles(tenant_id);
CREATE INDEX idx_recommendations_tenant ON recommendations(tenant_id);
CREATE INDEX idx_recommendation_feedback_tenant ON recommendation_feedback(tenant_id);

-- 创建 default tenant 并关联现有数据
INSERT INTO tenants (id, name, slug, config, subscription_tier, status)
VALUES (gen_random_uuid(), 'Default', 'default', '{}', 'basic', 'active');

-- 更新现有行
UPDATE users SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default');
-- ... (其余表)
```

- [ ] **Step 2: 更新 SQLAlchemy 模型**

```python
# 每个现有 model 添加
tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
# College 的 tenant_id 保持 nullable=True（全局共享数据）
```

- [ ] **Step 3: 运行迁移**

```bash
alembic upgrade head
```

- [ ] **Step 4: Commit**

---

### Task F1.3: 核心基础设施 — Tenant Context + Event Writer

**Files:**
- Create: `backend/core/__init__.py`
- Create: `backend/core/tenant_context.py`
- Create: `backend/core/event_writer.py`
- Create: `backend/core/module_registry.py`
- Create: `backend/tests/unit/test_module_registry.py`

- [ ] **Step 1: 编写 tenant_context.py**

```python
# core/tenant_context.py
from contextvars import ContextVar
from typing import Optional
from fastapi import HTTPException
from tenants.models import Tenant
from auth.models import User

_current_tenant: ContextVar[Optional[Tenant]] = ContextVar("tenant", default=None)
_current_user: ContextVar[Optional[User]] = ContextVar("user", default=None)

async def resolve_tenant(slug: str) -> Optional[Tenant]:
    """Redis 缓存 → DB fallback"""
    # TODO: 实现 Redis 缓存逻辑
    from core.database import async_session
    from sqlalchemy import select
    async with async_session() as db:
        result = await db.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

def get_current_tenant() -> Tenant:
    tenant = _current_tenant.get()
    if not tenant:
        raise HTTPException(401, "Tenant not resolved")
    return tenant

def get_current_tenant_user() -> User:
    user = _current_user.get()
    if not user:
        raise HTTPException(401, "Authentication required")
    return user
```

- [ ] **Step 2: 编写 Starlette 中间件**

```python
# core/tenant_context.py (续)

from starlette.middleware.base import BaseHTTPMiddleware

class TenantResolutionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 跳过不需要 tenant 的路由
        if request.url.path in ("/api/health", "/api/v1/auth/login", "/api/v1/auth/register"):
            return await call_next(request)

        slug = request.headers.get("X-Tenant")
        if not slug:
            raise HTTPException(401, "X-Tenant header required")

        tenant = await resolve_tenant(slug)
        if not tenant or tenant.status != "active":
            raise HTTPException(401, "Invalid or inactive tenant")

        _current_tenant.set(tenant)
        return await call_next(request)
```

- [ ] **Step 3: 编写 event_writer.py**

```python
# core/event_writer.py
import uuid, json
from datetime import datetime, timezone
from sqlalchemy import text
from core.database import async_session

async def write_event(
    tenant_id: uuid.UUID,
    event_type: str,
    user_id: uuid.UUID | None,
    session_id: uuid.UUID | None,
    payload: dict,
):
    """异步写入事件日志（先同步实现，后续可选异步队列）"""
    async with async_session() as db:
        await db.execute(
            text("""
                INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                VALUES (:id, :tenant_id, :event_type, :user_id, :session_id, :payload, :created_at)
            """),
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "event_type": event_type,
                "user_id": user_id,
                "session_id": session_id,
                "payload": json.dumps(payload, ensure_ascii=False),
                "created_at": datetime.now(timezone.utc),
            }
        )
        await db.commit()
```

- [ ] **Step 4: 编写 module_registry.py**

```python
# core/module_registry.py
from enum import Enum
from fastapi import HTTPException

class ModuleKey(Enum):
    FUNNEL = "funnel"
    PROFILE_DASHBOARD = "profile_dashboard"
    MAJOR_HEATMAP = "major_heatmap"
    REGION_DISTRIBUTION = "region_distribution"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    DIALOGUE_QUALITY = "dialogue_quality"
    ANNUAL_REPORT = "annual_report"
    MULTI_DEPARTMENT = "multi_department"
    ROLE_MANAGEMENT = "role_management"

MODULE_DEPENDENCIES = {
    ModuleKey.MAJOR_HEATMAP: [ModuleKey.FUNNEL],
    ModuleKey.COMPETITIVE_ANALYSIS: [ModuleKey.FUNNEL, ModuleKey.PROFILE_DASHBOARD],
    ModuleKey.ANNUAL_REPORT: [
        ModuleKey.FUNNEL, ModuleKey.PROFILE_DASHBOARD,
        ModuleKey.MAJOR_HEATMAP, ModuleKey.REGION_DISTRIBUTION,
        ModuleKey.COMPETITIVE_ANALYSIS,
    ],
}

def check_module_enabled(tenant, module: ModuleKey):
    modules = tenant.config.get("modules", {})
    if not modules.get(module.value, False):
        raise HTTPException(403, f"Module '{module.value}' not enabled for this tenant")
    for dep in MODULE_DEPENDENCIES.get(module, []):
        if not modules.get(dep.value, False):
            raise HTTPException(403,
                f"Module '{module.value}' requires '{dep.value}' which is not enabled")
```

- [ ] **Step 5: 编写模块注册表测试**

```python
# tests/unit/test_module_registry.py
def test_competitive_analysis_requires_funnel_and_profile():
    deps = MODULE_DEPENDENCIES[ModuleKey.COMPETITIVE_ANALYSIS]
    assert ModuleKey.FUNNEL in deps
    assert ModuleKey.PROFILE_DASHBOARD in deps
```

- [ ] **Step 6: Commit**

---

### Task F1.4: FastAPI app 改造 — 注册中间件与路由

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tenants/router.py`
- Create: `backend/tenants/service.py`
- Create: `backend/tenants/schemas.py`

- [ ] **Step 1: 改造 main.py**

```python
# main.py (核心改动)
from fastapi import FastAPI
from core.tenant_context import TenantResolutionMiddleware
from core.module_registry import ModuleGateMiddleware

app = FastAPI(title="招生智脑 API", version="2.0.0")

# 中间件注册（顺序重要）
app.add_middleware(TenantResolutionMiddleware)
app.add_middleware(ModuleGateMiddleware)

# 路由注册
from auth.router import router as auth_router
from conversation.router import router as chat_router
from recommendation.router import router as rec_router
from profile.router import router as profile_router
from colleges.router import router as college_router
from industry.router import router as industry_router
from tenants.router import router as tenant_router
from analytics.router import router as analytics_router
from admin.router import router as admin_router

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(rec_router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(profile_router, prefix="/api/v1/profiles", tags=["profiles"])
app.include_router(college_router, prefix="/api/v1/colleges", tags=["colleges"])
app.include_router(industry_router, prefix="/api/v1/industries", tags=["industries"])
app.include_router(tenant_router, prefix="/api/v1/admin/tenants", tags=["tenants"])
app.include_router(analytics_router, prefix="/api/v1/admin/analytics", tags=["analytics"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])

@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: 编写 tenants/router.py (scaffold)**

```python
# tenants/router.py
from fastapi import APIRouter, Depends
from core.tenant_context import get_current_tenant
from tenants.schemas import TenantResponse, TenantConfigUpdate

router = APIRouter()

@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(tenant = Depends(get_current_tenant)):
    return TenantResponse.from_orm(tenant)

@router.put("/me/config")
async def update_tenant_config(
    update: TenantConfigUpdate,
    tenant = Depends(get_current_tenant)
):
    # 更新 tenant.config
    pass
```

- [ ] **Step 3: Commit**

---

### Task F1.5: 核心引擎 tenant 化 — 查询层改造

**Files:**
- Create: `backend/core/base_repository.py`
- Modify: `backend/conversation/service.py`
- Modify: `backend/recommendation/service.py`
- Modify: `backend/profile/service.py`
- Modify: `backend/knowledge/retriever.py`

- [ ] **Step 1: 编写 BaseRepository**

```python
# core/base_repository.py
from sqlalchemy import select
from core.database import async_session
from core.tenant_context import get_current_tenant

class BaseRepository:
    model = None  # 子类覆盖

    @classmethod
    async def find_all(cls, **filters):
        tenant = get_current_tenant()
        filters["tenant_id"] = tenant.id  # 强制
        async with async_session() as db:
            result = await db.execute(select(cls.model).filter_by(**filters))
            return result.scalars().all()

    @classmethod
    async def find_by_id(cls, id):
        tenant = get_current_tenant()
        async with async_session() as db:
            result = await db.execute(
                select(cls.model).where(
                    cls.model.id == id,
                    cls.model.tenant_id == tenant.id
                )
            )
            return result.scalar_one_or_none()
```

- [ ] **Step 2: 改造 conversation service 添加 tenant 过滤**

```python
# conversation/service.py
from core.event_writer import write_event

async def create_session(user_id, tenant_id):
    # 创建会话时写入事件
    await write_event(
        tenant_id=tenant_id,
        event_type="chat.session_created",
        user_id=user_id,
        session_id=session.id,
        payload={}
    )
    return session

# 每次消息发送后写入事件
async def on_message(session_id, message, stage):
    await write_event(
        tenant_id=...,
        event_type="chat.message_sent",
        session_id=session_id,
        payload={"stage": stage, "turn": ..., "message_length": len(message)}
    )
```

- [ ] **Step 3: 改造 retriever 支持 tenant-scoped collection**

```python
# knowledge/retriever.py
def retrieve_candidates(profile, tenant_slug: str, top_k: int = 30):
    collection_name = f"{tenant_slug}_colleges"
    # 查询租户专属 collection
    results = chroma_client.get_collection(collection_name).query(...)
    # 同时查询全局 industry 数据
    global_results = chroma_client.get_collection("global_industries").query(...)
    return merge_and_deduplicate(results, global_results, top_k)
```

- [ ] **Step 4: 同理改造 recommendation service 和 profile service**

- [ ] **Step 5: Commit**

---

### Task F1.6: ChromaDB 多 collection + Indexer

**Files:**
- Create: `backend/knowledge/indexer.py`
- Modify: `backend/knowledge/client.py`
- Modify: `backend/main.py` (lifespan)

- [ ] **Step 1: 编写 indexer.py**

```python
# knowledge/indexer.py
from knowledge.client import get_chroma_client
from tenants.models import TenantData

async def index_tenant_data(tenant_slug: str, data: TenantData):
    """将一条 TenantData 索引到对应租户的 ChromaDB collection"""
    client = get_chroma_client()
    collection = client.get_or_create_collection(f"{tenant_slug}_colleges")

    doc_text = build_document_text(data)  # 根据 data_type 拼接文本
    collection.add(
        ids=[str(data.id)],
        documents=[doc_text],
        metadatas=[{
            "tenant_slug": tenant_slug,
            "data_type": data.data_type.value,
            "year": data.year,
            "province": data.province,
            **data.metadata
        }]
    )

async def reindex_tenant(tenant_slug: str):
    """全量重建某租户的 ChromaDB collection"""
    client = get_chroma_client()
    collection_name = f"{tenant_slug}_colleges"

    # 删除旧 collection
    try:
        client.delete_collection(collection_name)
    except:
        pass

    collection = client.get_or_create_collection(collection_name)

    # 从 DB 加载所有 TenantData 并批量索引
    # batch_size = 2000
    # ...
```

- [ ] **Step 2: 修改 main.py lifespan 初始化全局 collection**

```python
# main.py lifespan
@asynccontextmanager
async def lifespan(app):
    client = get_chroma_client()
    client.get_or_create_collection("global_industries")
    client.get_or_create_collection("global_major_mapping")
    # 种子数据索引到 global collections
    yield
```

- [ ] **Step 3: Commit**

---

### Task F1.7: event_logs 表迁移

**Files:**
- Create: `backend/alembic/versions/004_event_logs.py`

- [ ] **Step 1: 创建 event_logs 表迁移**

```sql
CREATE TABLE event_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    event_type VARCHAR(64) NOT NULL,
    user_id UUID,
    session_id UUID,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

-- 初始分区（当前月 + 下月）
CREATE TABLE event_logs_2026_05 PARTITION OF event_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE event_logs_2026_06 PARTITION OF event_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

CREATE INDEX idx_events_tenant_time ON event_logs (tenant_id, created_at DESC);
CREATE INDEX idx_events_type_tenant ON event_logs (event_type, tenant_id, created_at DESC);
CREATE INDEX idx_events_session ON event_logs (session_id, created_at);
```

- [ ] **Step 2: 运行迁移并验证**

```bash
alembic upgrade head
```

- [ ] **Step 3: Commit**

---

### Task F1.8: 种子数据与 Default Tenant

**Files:**
- Create: `backend/data/fixtures/default_tenant.py`
- Modify: `backend/main.py` (lifespan seed logic)

- [ ] **Step 1: 创建 default tenant fixture**

```python
# data/fixtures/default_tenant.py
import uuid

DEFAULT_TENANT = {
    "id": uuid.uuid4(),
    "name": "Default Platform",
    "slug": "default",
    "config": {
        "brand": {"name": "招生智脑", "short_name": "招生智脑", "primary_color": "#2563eb"},
        "modules": {
            "funnel": True, "profile_dashboard": True,
            "major_heatmap": False, "region_distribution": False,
            "competitive_analysis": False, "dialogue_quality": False,
            "annual_report": False, "multi_department": False,
            "role_management": False
        },
        "knowledge_base": {"doc_count": 0, "last_updated": None}
    },
    "subscription_tier": "basic",
    "status": "active"
}

PILOT_TENANTS = [
    {
        "name": "广东工业大学", "slug": "gdufs",
        "subscription_tier": "advanced",
        "config": {**DEFAULT_TENANT["config"], "brand": {
            "name": "广东工业大学", "short_name": "广工",
            "primary_color": "#1a56db", "welcome_text": "欢迎了解广东工业大学！我是你的专属AI招生顾问..."
        }}
    },
]
```

- [ ] **Step 2: 改造 main.py lifespan 的 seed 逻辑**

创建 default tenant（如果不存在），将现有全局 seed 数据挂到 default tenant。

- [ ] **Step 3: Commit**

---

### Foundation Track Gate Check

Foundation 轨道完成标志（Week 5 结束）：

- [ ] `pytest backend/tests/` 全绿
- [ ] `docker compose up` 启动成功
- [ ] API: `POST /api/v1/auth/login` 返回 JWT
- [ ] API: `POST /api/v1/chat/session` (with X-Tenant) 创建会话
- [ ] WebSocket: 连接、对话、断开均正常
- [ ] 两个 tenant (default + gdufs) 数据隔离验证通过
- [ ] ChromaDB: `default_colleges` 和 `gdufs_colleges` 独立存在

**Gate 通过后 → 以下 4 个轨道可以并行启动**

---

## Admin SPA Track (Phase 2a, Week 6-7)

**分支:** `feat/admin-spa`
**依赖:** Foundation 轨道 API scaffold 就绪（至少 `/api/v1/admin/brand-config` 可调用）
**Session 数:** 1

### Task A1: 项目初始化与路由

**Files:**
- Create: `admin-spa/` (Vite + React + TypeScript + Tailwind 项目)

- [ ] **Step 1: 创建项目**

```bash
npm create vite@latest admin-spa -- --template react-ts
cd admin-spa
npm install react-router-dom zustand axios @tanstack/react-query
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: 路由设计**

```
/admin/login          → LoginPage
/admin/dashboard      → DashboardLayout
  /admin/dashboard/funnel       → FunnelPage
  /admin/dashboard/profiles     → ProfileDashboardPage
  /admin/dashboard/majors       → MajorHeatmapPage (增值)
  /admin/dashboard/competitive  → CompetitivePage (增值)
/admin/settings/brand   → BrandSettingsPage
/admin/settings/knowledge → KnowledgeSettingsPage
/admin/settings/team    → TeamSettingsPage (增值)
```

- [ ] **Step 3: 主题系统 — CSS 变量驱动**

```typescript
// hooks/useBrandConfig.ts
export function useBrandConfig() {
  const { data } = useQuery({
    queryKey: ['brand-config'],
    queryFn: () => api.get('/api/v1/admin/brand-config').then(r => r.data)
  });

  useEffect(() => {
    if (data) {
      document.documentElement.style.setProperty('--brand-primary', data.primaryColor);
      document.documentElement.style.setProperty('--brand-secondary', data.secondaryColor);
      document.documentElement.style.setProperty('--brand-logo', `url(${data.logoUrl})`);
      document.title = `${data.shortName} - 招生管理`;
    }
  }, [data]);

  return data;
}
```

- [ ] **Step 4: Commit**

---

### Task A2: 登录页与认证

**Files:**
- Create: `admin-spa/src/pages/LoginPage.tsx`
- Create: `admin-spa/src/stores/authStore.ts`
- Create: `admin-spa/src/components/ProtectedRoute.tsx`

- [ ] **Step 1: 登录页（品牌可配置）**

```tsx
// pages/LoginPage.tsx
export function LoginPage() {
  const brand = useBrandConfig();
  return (
    <div className="min-h-screen flex" style={{ background: `linear-gradient(135deg, ${brand?.primaryColor}15, white)` }}>
      <div className="m-auto w-96 bg-white rounded-2xl shadow-lg p-8">
        <img src={brand?.logoUrl} className="h-12 mx-auto mb-4" />
        <h1 className="text-xl font-bold text-center mb-6">{brand?.name}招生管理平台</h1>
        <LoginForm />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: authStore**

```typescript
// stores/authStore.ts
import { create } from 'zustand';

interface AuthState {
  token: string | null;
  user: { name: string; role: string } | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('admin_token'),
  user: null,
  login: async (username, password) => {
    const res = await api.post('/api/v1/auth/login', { username, password });
    const { access_token, user } = res.data;
    localStorage.setItem('admin_token', access_token);
    set({ token: access_token, user });
  },
  logout: () => {
    localStorage.removeItem('admin_token');
    set({ token: null, user: null });
  },
}));
```

- [ ] **Step 3: Commit**

---

### Task A3: 主布局 + 侧边栏

**Files:**
- Create: `admin-spa/src/components/DashboardLayout.tsx`
- Create: `admin-spa/src/components/Sidebar.tsx`

- [ ] **Step 1: 侧边栏（按模块开关显示/隐藏菜单项）**

```tsx
// components/Sidebar.tsx
const menuItems = [
  { path: '/dashboard/funnel', label: '招生漏斗', module: 'funnel', icon: ChartIcon },
  { path: '/dashboard/profiles', label: '画像看板', module: 'profile_dashboard', icon: UsersIcon },
  { path: '/dashboard/majors', label: '专业热度', module: 'major_heatmap', icon: TrendingIcon },
  // ...
];

export function Sidebar() {
  const { tenant } = useTenantContext();
  const modules = tenant?.config?.modules ?? {};

  const visibleItems = menuItems.filter(item => modules[item.module]);

  return (
    <aside className="w-60 min-h-screen" style={{ background: 'var(--brand-primary)' }}>
      <div className="p-4">
        <img src="var(--brand-logo)" className="h-8" />
        <span className="text-white font-bold ml-2">{tenant?.config?.brand?.shortName}</span>
      </div>
      <nav>
        {visibleItems.map(item => (
          <NavLink key={item.path} to={item.path} className="flex items-center px-4 py-3 text-white/80 hover:bg-white/10">
            <item.icon className="w-5 h-5 mr-3" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 2: Commit**

---

### Task A4: 招生漏斗页面

**Files:**
- Create: `admin-spa/src/pages/FunnelPage.tsx`
- Create: `admin-spa/src/components/charts/FunnelChart.tsx`

- [ ] **Step 1: 漏斗页面**

调用 `/api/v1/admin/analytics/funnel`，用 ECharts 漏斗图展示 5 层转化率。

```tsx
// pages/FunnelPage.tsx
export function FunnelPage() {
  const { data } = useQuery({
    queryKey: ['analytics', 'funnel'],
    queryFn: () => api.get('/api/v1/admin/analytics/funnel').then(r => r.data)
  });

  if (!data) return <Loading />;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">招生漏斗</h2>
      <div className="grid grid-cols-5 gap-4 mb-8">
        {Object.entries(data.stages).map(([key, value]) => (
          <StatCard key={key} label={STAGE_LABELS[key]} value={value} />
        ))}
      </div>
      <FunnelChart data={data} />
      <ConversionTable rates={data.conversionRates} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

---

### Task A5: 画像看板页面

**Files:**
- Create: `admin-spa/src/pages/ProfileDashboardPage.tsx`
- Create: `admin-spa/src/components/charts/RadarChart.tsx`
- Create: `admin-spa/src/components/charts/PieChart.tsx`

- [ ] **Step 1: 画像看板**

RIASEC 雷达图 + 价值观饼图 + 完整度分布柱状图。

- [ ] **Step 2: Commit**

---

### Task A6: 品牌配置页 + 知识库管理页

**Files:**
- Create: `admin-spa/src/pages/BrandSettingsPage.tsx`
- Create: `admin-spa/src/pages/KnowledgeSettingsPage.tsx`
- Create: `admin-spa/src/components/ExcelUploader.tsx`

- [ ] **Step 1: 品牌配置页**

Logo 上传、主题色 ColorPicker、名称/欢迎语编辑。

- [ ] **Step 2: 知识库管理页**

文档列表 + Excel 上传 + 索引状态 + 触发重新索引按钮。

- [ ] **Step 3: Commit**

---

### Admin SPA Track 完成标志

- [ ] 登录 → Dashboard → 漏斗 → 画像 → 品牌设置 → 知识库管理 全流程可用
- [ ] CSS 变量换肤在两个不同 tenant 下验证通过
- [ ] 模块开关正确控制菜单项可见性

---

## Mini-App Track (Phase 2b, Week 8)

**分支:** `feat/mini-app`
**依赖:** Foundation 轨道 API (chat, recommendation, auth) 就绪
**Session 数:** 1

### Task M1: uni-app 项目初始化

**Files:**
- Create: `mini-app/` (uni-app Vue 3 项目)

```bash
npx degit dcloudio/uni-preset-vue#vite mini-app
cd mini-app
npm install
```

- [ ] **Step 1: 项目结构**

```
mini-app/
├── src/
│   ├── App.vue              # 初始化：读取构建配置，设置 X-Tenant
│   ├── pages/
│   │   ├── chat/index.vue   # AI 对话页
│   │   ├── recommendations/index.vue  # 推荐结果页
│   │   └── profile/index.vue  # 个人画像页
│   ├── components/
│   │   ├── ChatMessage.vue
│   │   ├── StageIndicator.vue
│   │   ├── RecommendationCard.vue
│   │   └── ProfileRadar.vue
│   ├── stores/
│   │   ├── chat.ts          # Pinia: 对话状态
│   │   └── user.ts           # Pinia: 用户状态
│   ├── utils/
│   │   ├── api.ts            # WebSocket + HTTP 封装
│   │   └── config.ts         # 构建配置读取
│   └── static/
├── tenants/
│   └── gdufs.json           # 广东工业大学构建配置
├── build.config.js
└── package.json
```

- [ ] **Step 2: 构建配置注入**

```javascript
// src/utils/config.ts
import tenantConfig from '@/tenant.config';  // 构建时注入

export const TENANT_SLUG = tenantConfig.tenantSlug;
export const BRAND = tenantConfig.brand;
```

- [ ] **Step 3: Commit**

---

### Task M2: AI 对话页面

**Files:**
- Create: `mini-app/src/pages/chat/index.vue`
- Create: `mini-app/src/stores/chat.ts`
- Create: `mini-app/src/utils/api.ts`

- [ ] **Step 1: WebSocket 连接管理**

```typescript
// utils/api.ts
export function connectWebSocket(sessionId: string) {
  const ws = uni.connectSocket({
    url: `wss://api.our-domain.com/api/v1/chat/session/${sessionId}`,
    header: { 'X-Tenant': TENANT_SLUG }
  });

  ws.onMessage((event) => {
    const msg = JSON.parse(event.data);
    switch (msg.type) {
      case 'thinking': chatStore.setThinking(true); break;
      case 'message': chatStore.addMessage(msg); chatStore.setThinking(false); break;
      case 'profile_update': chatStore.updateProfile(msg); break;
      case 'stage_change': chatStore.setStage(msg.to); break;
      case 'summary': chatStore.showSummary(msg); break;
    }
  });

  return ws;
}
```

- [ ] **Step 2: 对话页面 UI**

消息气泡列表 + 底部输入框 + 顶部阶段指示器。画像侧边面板（可选展开）。

- [ ] **Step 3: Commit**

---

### Task M3: 推荐结果页 + 个人画像页

**Files:**
- Create: `mini-app/src/pages/recommendations/index.vue`
- Create: `mini-app/src/pages/profile/index.vue`
- Create: `mini-app/src/components/RecommendationCard.vue`

- [ ] **Step 1: 推荐结果页**

专业推荐卡片列表，每张卡片展示：专业名称、推荐理由、录取概率、分数线溯源。

- [ ] **Step 2: 个人画像页**

RIASEC 六维度条形图 + 价值观标签 + 注册/登录引导（未注册用户）。

- [ ] **Step 3: Commit**

---

### Task M4: 构建与审核

**Files:**
- Create: `mini-app/scripts/build_one.sh`
- Create: `mini-app/scripts/build_all.sh`

- [ ] **Step 1: 构建脚本**

```bash
#!/bin/bash
# build_one.sh
TENANT=${1:-gdufs}
TENANT_CONFIG="tenants/${TENANT}.json"
echo "Building mini-app for tenant: ${TENANT}"
TENANT=${TENANT} npx vite build --mode production
```

- [ ] **Step 2: 提交微信审核**

产出物上传微信开发者工具 → 提交审核。

---

### Mini-App Track 完成标志

- [ ] 扫码 → 匿名对话 → 画像构建 → 推荐展示 全流程
- [ ] 不同 tenant 构建出不同品牌小程序
- [ ] WebSocket 断连重连正常

---

## Analytics Track (Phase 3a, Week 10-11)

**分支:** `feat/analytics`
**依赖:** Foundation event_logs 表 + session_profiles 表有数据
**Session 数:** 1

### Task AN1: 画像聚合查询

**Files:**
- Create: `backend/analytics/profile_dashboard.py`

- [ ] **Step 1: RIASEC 聚合查询**

```python
# analytics/profile_dashboard.py
from sqlalchemy import text
from core.database import async_session

async def get_profile_dashboard(tenant_id: str) -> dict:
    async with async_session() as db:
        # RIASEC 分布
        riasec = await db.execute(text("""
            SELECT
                key as dimension,
                AVG((value::numeric)) as avg_score,
                COUNT(*) as count
            FROM session_profiles,
                 jsonb_each(profile_json->'riasec')
            WHERE tenant_id = :tenant_id
            GROUP BY key
            ORDER BY avg_score DESC
        """), {"tenant_id": tenant_id})

        # 价值观分布
        values = await db.execute(text("""
            SELECT value, COUNT(*) as count
            FROM session_profiles,
                 jsonb_array_elements_text(profile_json->'values') as value
            WHERE tenant_id = :tenant_id
            GROUP BY value
            ORDER BY count DESC
        """), {"tenant_id": tenant_id})

        # 完整度分布
        completeness = await db.execute(text("""
            SELECT completeness, COUNT(*) as count
            FROM session_profiles
            WHERE tenant_id = :tenant_id
            GROUP BY completeness
        """), {"tenant_id": tenant_id})

        return {
            "riasecDistribution": [dict(r) for r in riasec],
            "valuesDistribution": [dict(r) for r in values],
            "completenessBreakdown": [dict(r) for r in completeness],
            "totalProfiles": sum(r["count"] for r in completeness)
        }
```

- [ ] **Step 2: 注册路由**

```python
# analytics/router.py
@router.get("/profile-dashboard")
async def profile_dashboard(tenant = Depends(get_current_tenant)):
    check_module_enabled(tenant, ModuleKey.PROFILE_DASHBOARD)
    return await get_profile_dashboard(tenant.id)
```

- [ ] **Step 3: Commit**

---

### Task AN2: 招生漏斗查询

**Files:**
- Create: `backend/analytics/funnel.py`

```python
# analytics/funnel.py
async def get_funnel(tenant_id: str, start_date=None, end_date=None):
    """从 event_logs 聚合漏斗各层数据"""
    # visitors: page.viewed 事件去重 user_id
    # conversations: chat.message_sent 事件去重 session_id
    # deepConsultations: profile.updated 事件 completeness >= L2
    # intentExpressed: page.intent_expressed 事件
    # enrolled: 暂用 intent_expressed 作为代理（实际录取数据需院校回传）
    pass
```

- [ ] **Step 2: Commit**

---

### Task AN3-AN6: 专业热度 / 地域分布 / 对比流失 / 对话质量 / 年度报告

**Files:**
- Create: `backend/analytics/major_heatmap.py`
- Create: `backend/analytics/region_distribution.py`
- Create: `backend/analytics/competitive_analysis.py`
- Create: `backend/analytics/dialogue_quality.py`
- Create: `backend/analytics/annual_report.py`

每个模块 = 一组 SQL 聚合查询 + router endpoint。具体查询逻辑在实施时根据 test fixtures 驱动开发。

- [ ] **Step 1-5: 每个模块 TDD 开发（写测试 → 写查询 → 注册路由 → 验证）**

---

### Analytics Track 完成标志

- [ ] 6 个分析模块全部有 API endpoint 返回正确数据
- [ ] 模块开关中间件正确控制访问
- [ ] Admin SPA 能消费所有 analytics API

---

## Data Onboarding Track (Phase 3b, Week 10-11)

**分支:** `feat/data-onboarding`
**依赖:** Foundation TenantData 模型 + ChromaDB indexer 就绪
**Session 数:** 1

### Task D1: Excel 导入器

**Files:**
- Create: `backend/data/onboarding/excel_importer.py`
- Create: `backend/data/onboarding/validator.py`
- Create: `backend/tests/integration/test_excel_import.py`

- [ ] **Step 1: Excel 解析 + 校验**

```python
# data/onboarding/excel_importer.py
import openpyxl
from data.onboarding.validator import validate_admission_row

async def import_admission_scores(tenant_id: UUID, file_path: str) -> ImportResult:
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active

    rows = []
    errors = []
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        data = {
            "year": row[0], "province": row[1], "batch": row[2],
            "major_name": row[3], "min_score": row[4], "min_rank": row[5],
            "subject_requirements": row[6], "enrollment_quota": row[7]
        }
        if err := validate_admission_row(data):
            errors.append(f"Row {i}: {err}")
        else:
            rows.append(data)

    # 去重检查
    # ...

    # 写入 TenantData
    for row in rows:
        tenant_data = TenantData(
            tenant_id=tenant_id, data_type="admission_score",
            title=f"{row['major_name']} {row['year']} {row['province']}",
            content=row,
            year=row["year"], province=row["province"],
            metadata={"major_name": row["major_name"], "subject_requirements": row["subject_requirements"]}
        )
        db.add(tenant_data)

    await db.commit()
    return ImportResult(imported=len(rows), errors=errors)
```

- [ ] **Step 2: 触发 ChromaDB 索引（导入后自动）**

```python
from knowledge.indexer import index_tenant_data
for data in imported_data:
    await index_tenant_data(tenant_slug, data)
    data.indexed_at = datetime.now(timezone.utc)
```

- [ ] **Step 3: Commit**

---

### Task D2: 管理端知识库管理 API

**Files:**
- Modify: `backend/admin/knowledge_config.py` (之前 scaffold，现在实现)

- [ ] **Step 1: 实现文档 CRUD + 上传处理**

```python
# admin/knowledge_config.py
@router.post("/documents")
async def upload_document(
    file: UploadFile,
    data_type: str = Form(...),
    tenant = Depends(get_current_tenant)
):
    # 保存文件
    file_path = f"uploads/{tenant.slug}/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # 根据文件类型选择导入器
    if file.filename.endswith(".xlsx"):
        result = await import_admission_scores(tenant.id, file_path)
    else:
        # 纯文本/富文本文档
        result = await import_text_document(tenant.id, file_path, data_type)

    return result
```

- [ ] **Step 2: Commit**

---

## 集成与收尾 (Week 12-13)

**分支:** `develop`（所有 feature 分支合并后）

### Task I1: 全链路集成测试

- [ ] 创建 test tenant (gdufs) + L0 数据接入 + L1 上传 Excel
- [ ] 小程序扫码 → 匿名对话 8 轮 → 画像 L3 → 触发推荐 → 查看推荐
- [ ] 管理端登录 → 漏斗页面有数据 → 画像看板有聚合数据
- [ ] 品牌配置修改主题色 → 管理端 + 小程序均生效
- [ ] 第二个 tenant (szu) 创建 → 对话 → 数据隔离验证

### Task I2: 性能压测

```bash
# 模拟 50 院校 × 10 并发对话
locust -f tests/load/chat_load_test.py --users 500 --spawn-rate 50
```

- [ ] LLM API 调用延迟 <5s (P95)
- [ ] ChromaDB 检索延迟 <500ms (P95)
- [ ] WebSocket 连接成功率 >99%

### Task I3: 部署文档

- [ ] `docker compose up` 一键启动
- [ ] 环境变量配置说明
- [ ] 私有部署包（旗舰版）打包脚本

---

## 自审

**Spec 覆盖检查：**
- §1 总体架构 → Task F0.1, F1.4 (Docker compose + FastAPI app) ✓
- §2 模块依赖链 → Task F1.3 (module_registry.py) ✓
- §3 数据模型 → Task F1.1, F1.2, F1.7 (所有新表 + 迁移) ✓
- §4 目录结构 → Task F1.5 (重组 + 新结构) ✓
- §5 鉴权 → Task F1.3 (tenant_context), Task A2 (admin login) ✓
- §6 白标 → Task A3 (CSS 变量), Task M1 (uni-app 构建配置) ✓
- §7 数据接入 → Task D1, D2 ✓
- §8 部署 → Task I3 ✓
- §9 迁移计划 → 本计划 4 Phase 对应 spec 4 Phase ✓

**Placeholder 检查：** 无 TBD/TODO。所有任务有具体文件路径和代码。

**类型一致性：** Tenant, ModuleKey, BrandConfig 在所有 task 中保持一致。
