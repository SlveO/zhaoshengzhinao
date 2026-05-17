# B2B 招生智脑平台 — 工程设计方案

> 状态: 设计中 | 日期: 2026-05-18 | 目标: 50+ 院校规模化 SaaS 平台

### 代码现状评估

**可复用（核心引擎）：**
- `agents/conversation/agent.py` — LangGraph 对话编排，逻辑完整
- `agents/conversation/evidence_accumulator.py` — 画像累积，业务正确
- `agents/conversation/profile_analyzer.py` — LLM 结构化提取，可用
- `agents/conversation/prompts.py` — 提示工程 + 少样本，沉淀深厚
- `knowledge_base/retriever.py` — 混合检索 + 过滤 + 去重，逻辑正确
- `knowledge_base/embeddings.py` — BGE 嵌入封装，稳定
- `services/recommendation_service.py` — 推荐流水线，核心逻辑可用
- `scrapers/` — 数据采集管道，可复用

**需修复/不稳定：**
- `api/routes/chat.py` — WebSocket 连接管理有边界 bug
- 部分 API 路由的异常处理不完善
- 前后端联调存在 schema 不一致

**需完全重做：**
- 前端（React SPA）：UI 需要重新设计，当前仅为基础原型
- 前端状态管理：Zustand store 逻辑散乱
- 小程序：完全不存在，需从零创建

### 总体策略

**核心引擎复用，外壳重建。** Conversation Agent + Profile Analyzer + Retriever + Recommendation 是已有价值的资产，将其封装为独立模块后纳入新架构。前端和 API 层按新设计重建。所有架构决策（tenant_id、多 collection、模块开关）从第一天就到位，第一个可交付里程碑是单院校全链路跑通。

---

## 1. 总体系统架构

### 1.1 服务拓扑

```
                         ┌──────────────────────┐
                         │   Nginx Reverse Proxy │
                         │   /api → backend      │
                         │   /ws  → backend:ws   │
                         │   admin → admin SPA   │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
    ┌─────────▼─────────┐  ┌───────▼───────┐  ┌─────────▼─────────┐
    │   Backend (API)   │  │  Admin SPA    │  │  Student Mini-App │
    │   FastAPI :8000   │  │  React+Vite   │  │  uni-app (per     │
    │   ws /session/    │  │  /admin/*     │  │  tenant build)    │
    └─────────┬─────────┘  └───────────────┘  └───────────────────┘
              │
    ┌─────────┼─────────┬──────────────┬──────────────┐
    │         │         │              │              │
┌───▼───┐ ┌──▼──┐ ┌────▼────┐ ┌──────▼──────┐ ┌─────▼─────┐
│PostgreSQL│Redis│ │ChromaDB │ │ File Store  │ │ LLM API   │
│(pgvector)│     │ │per-tenant│ │(logos/docs) │ │ DeepSeek  │
│all data   │cache│ │collection│ │             │ │           │
└───────────┘     │ │          │ │             │ │           │
                  │ └──────────┘ └─────────────┘ └───────────┘
```

### 1.2 关键设计决策

**1. 单体 API 而非微服务**

50 所院校的规模下，微服务运维成本远超收益。FastAPI 单体 + 模块化目录结构。

**2. 数据隔离 = 共享 PG + 独立 ChromaDB collection**

- PostgreSQL：所有租户共享，每行 `tenant_id`，Row-Level Security 兜底
- ChromaDB：每租户一个 collection，`{tenant_id}_colleges`
- 旗舰私有部署：独立 PG + 独立 ChromaDB，Docker Compose 覆盖

**3. 统一事件表驱动分析**

核心引擎产生事件时只写事件表。每个分析模块从事件表查询聚合，互不耦合。

**4. 模块开关 = tenant config JSONB + API 中间件**

前端面板按模块开关动态渲染；后端 API 通过中间件检查模块权限。

---

## 2. 模块依赖链

```
                        ┌─────────────────────────┐
                        │   Platform Foundation    │
                        │  多租户 · 知识库 · AI引擎 │
                        └────────────┬────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │     Data Collection      │
                        │  对话 · 画像 · 推荐 · 行为 │
                        └────────────┬────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
       ┌──────▼──────┐        ┌─────▼──────┐        ┌──────▼──────┐
       │ ① 招生漏斗   │        │ ② 画像看板  │        │ ③ 基础配置   │
       │ 对话+行为事件 │        │ 画像快照    │        │ 租户管理     │
       └──────┬──────┘        └─────┬──────┘        └─────────────┘
              │                      │
              └──────────┬───────────┘
                         │
          ┌──────────────┼──────────────┬──────────────┐
          │              │              │              │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
    │④ 专业热度 │  │⑤ 地域分布 │  │⑥ 对比+流失│  │⑦ 对话质量 │
    │对话+推荐   │  │画像+用户   │  │对话+画像   │  │对话+反馈   │
    │+画像       │  │           │  │+漏斗       │  │           │
    └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
          │              │              │              │
          └──────────────┼──────────────┘              │
                         │                             │
                  ┌──────▼──────┐                      │
                  │⑧ 年度报告   │◄─────────────────────┘
                  │聚合①②④⑤⑥  │
                  └─────────────┘
```

**横切关注点（影响所有模块）：**

```
    ┌──────────┐          ┌──────────────┐
    │⑨ 角色权限 │          │⑩ 多院系管理   │
    └──────────┘          └──────────────┘
```

### 2.1 模块定价与依赖约束

| 模块 | 类型 | 年费 | 硬依赖 | 预购条件 |
|------|------|------|--------|---------|
| ① 招生漏斗 | 基础 | 含订阅 | — | — |
| ② 画像看板 | 基础 | 含订阅 | — | — |
| ③ 基础配置 | 基础 | 含订阅 | — | — |
| ④ 专业热度 | 增值 | ¥12,000 | ① 漏斗 | 须先有基础包 |
| ⑤ 地域分布 | 增值 | ¥8,000 | — | — |
| ⑥ 对比+流失 | 增值 | ¥18,000 | ①② | 须先有漏斗+画像 |
| ⑦ 对话质量 | 增值 | ¥10,000 | — | — |
| ⑧ 年度报告 | 增值 | ¥8,000 | ①②④⑤⑥ | 须先有所有被聚合模块 |
| ⑨ 角色权限 | 增值 | ¥6,000 | — | — |
| ⑩ 多院系 | 增值 | ¥15,000 | — | — |

---

## 3. 数据模型

### 3.1 新增实体

**Tenant (组织/院校)**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| name | String | 院校全称 |
| slug | String (unique) | API 子路径标识，如 "gdufs" |
| config | JSONB | 品牌 + 模块开关 + 知识库配置 + 小程序配置 |
| subscription_tier | Enum | basic / standard / advanced / flagship |
| status | Enum | active / suspended / cancelled |
| created_at / updated_at | Timestamp | — |

config JSONB 结构：
```json
{
  "brand": {
    "name": "广东工业大学",
    "short_name": "广工",
    "primary_color": "#1a56db",
    "logo_url": "https://...",
    "welcome_text": "欢迎了解..."
  },
  "modules": {
    "funnel": true,
    "profile_dashboard": true,
    "major_heatmap": false,
    "region_distribution": false,
    "competitive_analysis": false,
    "dialogue_quality": true,
    "annual_report": false,
    "multi_department": false,
    "role_management": false
  },
  "knowledge_base": { "doc_count": 200, "last_updated": "..." },
  "mini_program": {
    "app_id": "wx...",
    "app_secret_encrypted": "..."
  }
}
```

**TenantUser (租户用户 — 管理端登录)**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| tenant_id | FK → Tenant | 所属院校 |
| user_id | FK → User | 关联账户 |
| role | Enum | admin / manager / viewer / department_head |
| created_at | Timestamp | — |

**TenantData (院校专属数据 — 知识库素材)**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| tenant_id | FK → Tenant | — |
| data_type | Enum | admission_score / curriculum / employment / campus_life |
| title | String | 文档标题 |
| content | Text/JSONB | 文档内容 |
| source_url | String | 原始来源 |
| year / province | Integer / String | 数据年份/省份 |
| metadata | JSONB | 专业名、科目要求等 |
| indexed_at | Timestamp | 是否已索引到 ChromaDB |

**Department (院系子组织 — 增值模块)**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| tenant_id | FK → Tenant | — |
| name | String | "计算机学院" |
| config | JSONB | 院系级模块配置覆盖 |
| parent_id | FK → self | 支持二级层级 |

**event_logs (统一事件表)**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| tenant_id | FK → Tenant | — |
| event_type | VARCHAR(64) | 事件类型枚举，见下表 |
| user_id | UUID (nullable) | 可为 null（匿名浏览） |
| session_id | UUID | 对话会话 |
| payload | JSONB | 事件负载，结构随 event_type 变化 |
| created_at | TIMESTAMPTZ | 默认 now() |

索引设计：
```sql
CREATE INDEX idx_events_tenant_time ON event_logs (tenant_id, created_at DESC);
CREATE INDEX idx_events_type_tenant ON event_logs (event_type, tenant_id, created_at DESC);
CREATE INDEX idx_events_session ON event_logs (session_id, created_at);
-- 按月 RANGE 分区，保留 36 个月后自动清理
PARTITION BY RANGE (created_at);
```

事件类型与负载规范：

| event_type | payload 关键字段 |
|-----------|-----------------|
| `chat.message_sent` | stage, turn, message_length, emotion |
| `chat.stage_changed` | from_stage, to_stage, turn |
| `profile.updated` | completeness(L1/L2/L3), riasec_dims[], values[], confidence |
| `profile.blindspot_hit` | dimension, turn |
| `recommendation.generated` | profile_level, candidates_count, output_count, latency_ms |
| `recommendation.feedback` | college_name, major_name, feedback(useful/not_relevant) |
| `page.viewed` | page_path, source |
| `page.intent_expressed` | colleges_of_interest[], majors_of_interest[] |

### 3.2 现有模型改造

所有现有模型新增 `tenant_id` 字段：

```python
tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False, index=True)
```

| 模型 | 改造内容 | 说明 |
|------|---------|------|
| User | +tenant_id | 学生通过哪所院校的小程序注册 |
| College | +tenant_id (nullable) | NULL = 全局共享；非 NULL = 某院校专属数据 |
| AdmissionData | +tenant_id | 每条录取数据归属 |
| UserProfile | +tenant_id | 画像归属 |
| Recommendation | +tenant_id | 推荐结果归属 |
| RecommendationFeedback | +tenant_id | 反馈归属 |
| IndustryAnalysis | 不改造 | 全局共享（行业数据非院校专属） |
| MajorIndustryMapping | 不改造 | 全局共享 |

### 3.3 ChromaDB 多租户设计

```
ChromaDB (PersistentClient)
├── collection: "global_industries"        # 全局共享：行业知识库
├── collection: "global_major_mapping"     # 全局共享：专业→行业映射
├── collection: "{tenant_slug}_colleges"   # 租户专属：院校+专业+录取数据
├── collection: "{tenant_slug}_custom"     # 租户专属：该院校自己的补充文档
└── ... (per tenant)
```

---

## 4. 后端目录结构与分层

### 4.1 领域模块化结构

```
backend/
├── main.py                         # FastAPI app factory + lifespan
├── config.py                       # Settings
│
├── core/                           # 跨领域共享基础设施
│   ├── database.py                 # DB 连接池
│   ├── security.py                 # JWT + 密码哈希
│   ├── tenant_context.py           # 租户解析中间件 + contextvar
│   ├── module_registry.py          # 模块开关 + 依赖校验
│   └── event_writer.py             # 统一事件写入
│
├── tenants/                        # 🔴 多租户域
│   ├── models.py                   # Tenant, TenantUser, TenantData
│   ├── schemas.py
│   ├── router.py                   # /api/v1/admin/tenants/*
│   ├── service.py
│   └── dependencies.py             # get_current_tenant()
│
├── auth/                           # 认证域（改造）
│   ├── models.py                   # User (+tenant_id)
│   ├── schemas.py
│   ├── router.py                   # /api/v1/auth/*
│   └── service.py
│
├── conversation/                   # 🟡 对话域（重组原 agents/ + chat route）
│   ├── models.py                   # Session (+tenant_id)
│   ├── schemas.py
│   ├── router.py                   # /api/v1/chat/* (WS + REST)
│   ├── service.py                  # 会话管理 + 事件写入
│   ├── agent.py                    # LangGraph 编排
│   ├── prompts.py                  # 系统提示 + 少样本
│   ├── evidence_accumulator.py     # 画像证据累积
│   ├── profile_analyzer.py         # LLM 画像分析
│   └── slot_filler.py              # 兼容包装
│
├── recommendation/                 # 🟡 推荐域
│   ├── models.py                   # Recommendation, Feedback (+tenant_id)
│   ├── schemas.py
│   ├── router.py                   # /api/v1/recommendations/*
│   ├── service.py                  # 推荐流水线 + 事件写入
│   └── cache.py                    # Redis 缓存
│
├── profile/                        # 🟡 画像域
│   ├── models.py                   # UserProfile (+tenant_id)
│   ├── schemas.py
│   ├── router.py                   # /api/v1/profiles/*
│   └── service.py
│
├── knowledge/                      # 🟡 知识库域（重组原 knowledge_base/）
│   ├── client.py                   # ChromaDB 客户端（多 collection）
│   ├── embeddings.py               # BGE 嵌入
│   ├── retriever.py                # 混合检索（tenant-scoped）
│   └── indexer.py                  # 🔴 按租户索引文档
│
├── analytics/                      # 🔴 分析域（管理端数据查询层）
│   ├── router.py                   # /api/v1/admin/analytics/*
│   ├── funnel.py                   # 招生漏斗
│   ├── profile_dashboard.py        # 画像聚合
│   ├── major_heatmap.py            # 专业热度
│   ├── region_distribution.py      # 生源地域
│   ├── competitive_analysis.py     # 对比+流失
│   ├── dialogue_quality.py         # 对话质量
│   └── annual_report.py            # 年度报告
│
├── admin/                          # 🔴 管理端域
│   ├── router.py                   # /api/v1/admin/* 聚合
│   ├── brand_config.py             # 品牌设置 CRUD
│   ├── knowledge_config.py         # 知识库管理
│   ├── department_mgmt.py          # 院系管理（增值）
│   └── role_mgmt.py               # 角色权限（增值）
│
├── colleges/                       # 院校信息域（改造）
│   ├── models.py                   # College (+tenant_id nullable)
│   ├── schemas.py
│   ├── router.py
│   └── service.py
│
├── industry/                       # 行业数据域（不变）
│   ├── models.py
│   ├── schemas.py
│   ├── router.py
│   └── service.py
│
└── data/                           # 🔴 院校专属数据管道
    ├── seed/                       # 全局种子数据
    ├── onboarding/                 # Onboarding 导入
    │   ├── excel_importer.py
    │   ├── api_importer.py
    │   └── validator.py
    └── fixtures/                   # 开发用租户配置
```

### 4.2 分层规则

```
router.py   →  schemas 校验  →  dependencies 注入
    │
    ▼
service.py  →  业务逻辑  →  event_writer (写事件)
    │
    ▼
models.py   →  SQLAlchemy  →  PostgreSQL
```

- `analytics/` 可读其他任何域的 models，不可写
- `admin/` 可调用 `tenants/service.py`、`knowledge/indexer.py`
- `conversation/`、`recommendation/`、`profile/` 只写 event_logs，不互通
- 所有模块通过 `core/tenant_context.py` 获取当前租户

---

## 5. 租户中间件与 API 鉴权

### 5.1 租户解析链

```
HTTP Request
    │
    ▼
┌─────────────────────────────┐
│ Step 1: 提取 Tenant         │  ← Starlette Middleware
│  学生端:                     │
│    X-Tenant 请求头 (小程序硬编码)│
│  管理端:                     │
│    X-Tenant 请求头             │
│    OR JWT payload.tenant_id │
│  如果都缺失 → 401            │
├─────────────────────────────┤
│ Step 2: 验证 Tenant         │
│  查 DB: status == active    │
│  config 加载到 Redis 缓存    │
│  存入 contextvar            │
├─────────────────────────────┤
│ Step 3: JWT 认证 (仅管理端)  │
│  验证 token → 提取 user_id  │
│  查 TenantUser → 确定 role  │
│  存入 contextvar            │
├─────────────────────────────┤
│ Step 4: 模块开关检查         │
│  请求路径匹配到模块 →        │
│  查 tenant.config.modules   │
│  未开通 → 403               │
└─────────────────────────────┘
    │
    ▼
  Route Handler
```

### 5.2 核心代码骨架

```python
# core/tenant_context.py
from contextvars import ContextVar

_current_tenant: ContextVar[Optional[Tenant]] = ContextVar("tenant", default=None)
_current_user: ContextVar[Optional[User]] = ContextVar("user", default=None)

def get_current_tenant() -> Tenant:
    tenant = _current_tenant.get()
    if not tenant:
        raise HTTPException(401, "Tenant not resolved")
    return tenant

def get_current_tenant_user() -> TenantUser:
    tu = _current_user.get()
    if not tu:
        raise HTTPException(401, "Authentication required")
    return tu
```

```python
# core/tenant_context.py - 解析中间件
class TenantResolutionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        slug = request.headers.get("X-Tenant") or extract_subdomain(request)
        tenant = await resolve_tenant(slug)  # Redis 缓存 5 分钟 → DB fallback
        _current_tenant.set(tenant)
        return await call_next(request)
```

### 5.3 模块开关中间件

```python
# core/module_registry.py

MODULE_ROUTE_MAP = {
    "/api/v1/admin/analytics/funnel":              ModuleKey.FUNNEL,
    "/api/v1/admin/analytics/profile-dashboard":   ModuleKey.PROFILE_DASHBOARD,
    "/api/v1/admin/analytics/major-heatmap":       ModuleKey.MAJOR_HEATMAP,
    "/api/v1/admin/analytics/region-distribution": ModuleKey.REGION_DISTRIBUTION,
    "/api/v1/admin/analytics/competitive":         ModuleKey.COMPETITIVE_ANALYSIS,
    "/api/v1/admin/analytics/dialogue-quality":    ModuleKey.DIALOGUE_QUALITY,
    "/api/v1/admin/analytics/annual-report":       ModuleKey.ANNUAL_REPORT,
    "/api/v1/admin/departments":                   ModuleKey.MULTI_DEPARTMENT,
    "/api/v1/admin/roles":                         ModuleKey.ROLE_MANAGEMENT,
}

MODULE_DEPENDENCIES = {
    ModuleKey.MAJOR_HEATMAP:         [ModuleKey.FUNNEL],
    ModuleKey.COMPETITIVE_ANALYSIS:  [ModuleKey.FUNNEL, ModuleKey.PROFILE_DASHBOARD],
    ModuleKey.ANNUAL_REPORT:         [ModuleKey.FUNNEL, ModuleKey.PROFILE_DASHBOARD,
                                      ModuleKey.MAJOR_HEATMAP, ModuleKey.REGION_DISTRIBUTION,
                                      ModuleKey.COMPETITIVE_ANALYSIS],
}


class ModuleGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        module = match_route_to_module(request.url.path)
        if module:
            tenant = _current_tenant.get()
            modules = tenant.config.get("modules", {})
            if not modules.get(module.value, False):
                raise HTTPException(403, f"Module '{module.value}' not enabled")
            for dep in MODULE_DEPENDENCIES.get(module, []):
                if not modules.get(dep.value, False):
                    raise HTTPException(403,
                        f"Module '{module.value}' requires '{dep.value}' not enabled")
        return await call_next(request)
```

### 5.4 两种认证路径

| 端 | 认证方式 | 租户解析 | 使用场景 |
|----|---------|---------|---------|
| 学生小程序 | 可选 JWT（注册后携带） | X-Tenant 头（硬编码在构建中） | AI 对话、查看推荐 |
| 管理后台 Web | 强制 JWT（必须登录） | JWT payload.tenant_id | 招生办管理面板 |

### 5.5 User 表设计：区分院校人员与学生

```python
class User(Base):
    __tablename__ = "users"
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    user_type = Column(Enum("student", "staff"), nullable=False, default="student")

    # 学生专属字段（staff 为 NULL）
    region = Column(String, nullable=True)
    score = Column(Integer, nullable=True)
    subjects = Column(String, nullable=True)
    batch = Column(String, nullable=True)
    created_at, updated_at = ...

class TenantUser(Base):  # 仅 staff 有
    __tablename__ = "tenant_users"
    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    user_id = Column(UUID, ForeignKey("users.id"))
    role = Column(Enum("admin", "manager", "viewer", "department_head"))
```

### 5.6 学生匿名对话与画像双归属模型

**学生无需注册即可对话。** 注册门槛每增加一步就筛掉一批学生。B2B 场景下，触达率优先。

```
匿名对话流程:
  session_id: abc-123, tenant_id: gdufs

  Turn 1 → evidence: { R: 6, 置信度: 0.58 }
  Turn 3 → evidence: { R: 7, I: 5, 置信度: 0.70 }
  Turn 5 → evidence: { R: 7, I: 5, S: 4, values: ["社会贡献"], 置信度: 0.78 }
  Turn 7 → 到达 CONFIRM → 写入 session_profiles 快照
```

**两种画像归属：**

| | 院校群像 | 学生个体画像 |
|---|---|---|
| 存储表 | session_profiles (tenant_id) | student_profiles (user_id) |
| 用途 | 院校看"想报我校的学生群体特征" | 学生做"我适合哪些院校"的跨校匹配 |
| 是否需注册 | 否 | 是 |
| 谁拥有 | 院校（自身 tenant 内） | 学生自己 |
| 跨院校可见 | 否 | 是（学生主动触发多校对比时） |

**学生体验完整链路：**

```
扫广工小程序码
  → 匿名对话 8 轮（无需注册）
  → AI: "我理解你了，推荐广工这几个专业..."
  → 学生看完
  → AI: "你的画像已生成。想看看它匹配其他院校的哪些专业吗？注册解锁多校对比"
  → 学生注册 → 同一份画像匹配深大、华农、广大...
  → 流失分析数据反哺给广工管理端（聚合统计，非个体数据）
```

---

## 6. 白标系统（管理端 + 小程序）

### 6.1 管理端白标：品牌 API + CSS 变量

管理端是统一 React SPA，品牌差异化通过"品牌 API + 动态 CSS 变量"实现，一套代码服务所有院校。

```
招生办老师打开 admin.our-domain.com
  → 登录（JWT 含 tenant_id）
  → 前端调 GET /api/v1/admin/brand-config
  → 返回:
    {
      "name": "广东工业大学",
      "short_name": "广工",
      "logo_url": "https://cdn.../gdufs-logo.png",
      "primary_color": "#1a56db",
      "secondary_color": "#f59e0b",
      "favicon_url": "...",
      "login_bg_url": "..."
    }
  → 前端动态设置 CSS 变量和页面标题
```

```css
:root {
  --brand-primary: #1a56db;
  --brand-secondary: #f59e0b;
  --brand-logo: url('https://cdn.../gdufs-logo.png');
}
.sidebar { background: var(--brand-primary); }
```

### 6.2 小程序白标：uni-app + 构建配置注入

一套 uni-app 源码，每院校独立构建产出独立小程序包，各自提交微信审核。

```
mini-app/
├── src/                          # 一套源码
│   ├── App.vue
│   ├── pages/
│   └── components/
├── tenants/                      # 每院校构建配置
│   ├── gdufs.json                # 广东工业大学
│   ├── szu.json                  # 深圳大学
│   └── ...
├── build.config.js               # 读取 TENANT 环境变量
└── scripts/
    ├── build_one.sh              # TENANT=gdufs npm run build
    └── build_all.sh              # 批量构建
```

**构建配置（gdufs.json）：**
```json
{
  "appId": "wx_gdufs_app_id",
  "tenantSlug": "gdufs",
  "brand": {
    "name": "广东工业大学", "shortName": "广工",
    "primaryColor": "#1a56db", "welcomeText": "欢迎了解广工！..."
  },
  "features": { "guestMode": true, "crossCollegeCompare": true }
}
```

### 6.3 定制层级

| 层级 | 内容 | 方式 |
|------|------|------|
| 自动 | 名称、Logo、主题色、appId、欢迎语 | tenants/*.json |
| 半自动 | 功能开关、知识库、推荐偏好 | 管理端配置面板 |
| 人工 | 深度 UI 定制、特殊功能 | 旗舰版私有部署分支 |

前两层覆盖 90% 院校需求。第三层对应 ¥398,000 旗舰版。

---

## 7. 院校数据接入标准化

### 7.1 六级接入方案（L0-L5）

| 级别 | 方式 | 院校配合度 | 数据覆盖率 | 适用场景 |
|------|------|-----------|-----------|---------|
| L0 | 公开数据自动采集 | 零配合 | ~60% | 签约即刻可用，冷启动 |
| L1 | Excel/CSV 模板上传 | 招生办自助 | +30% | 标准版及以上 |
| L2 | 管理后台手动录入 | 招生办自助 | 补充零散数据 | 所有版本 |
| L3 | 数据库直连/导出 | IT 部门配合 | +10% 深度数据 | 高级版及以上 |
| L4 | API 对接（标准协议） | IT 部门开发 | 实时同步 | 高级版/旗舰版 |
| L5 | 教育局/考试院统一通道 | 政府合作 | 批量覆盖辖区院校 | 教育局合同 |

### 7.2 L0: 公开数据自动采集

```
各省教育考试院公开 API → 爬虫采集 → 公共数据池
学信网公开数据 → 爬虫 → 公共数据池
```

院校签约后自动从公共池提取基础录取数据。零配合即用。

### 7.3 L1: Excel 模板上传

**模板一：历年录取分数线** — year, province, batch, major_name, min_score, min_rank, subject_requirements, enrollment_quota

**模板二：专业培养计划** — major_name, college(学院), duration, core_courses, objective, degree

**模板三：毕业生就业去向** — major_name, year, employment_rate, avg_salary, main_industries, typical_companies, further_study_rate

**模板四：校园信息** — 自由文本，学院介绍、住宿条件、社团活动、奖助学金政策

### 7.4 L3: 数据库直连（对接主流教务系统）

为正方教务（800+高校）、青果教务（400+高校）、强智科技（300+高校）预写导出脚本。

### 7.5 L4: API 对接

支持 REST API pull 和 Webhook push。对接时通过 field_mapping 自动转换字段，无需手写解析代码。

### 7.6 校验与索引流水线

```
上传 → 格式校验 → 数据校验(范围/去重) → 入库 TenantData → ChromaDB 索引
```

### 7.7 数据质量评分

| 来源 | 质量分 |
|------|--------|
| public_crawl | 0.6 |
| excel_upload | 0.85 |
| manual_entry | 0.8 |
| database_export | 0.9 |
| api_sync | 0.95 |
| education_bureau | 1.0 |

AI 推荐优先使用高质量数据源。管理端展示数据来源和可信度。

---

## 8. 部署与 CI/CD

### 8.1 部署架构

SaaS 生产环境：Docker Compose Stack + 独立小程序构建管线。旗舰版提供独立私有部署包（docker-compose.prod.yml + .env.example）。

### 8.2 CI/CD 管线

```
Git Push (main)
  ├── Backend: pytest → docker build → alembic upgrade → deploy
  ├── Admin SPA: npm build → docker build → deploy
  └── 小程序: 检测 tenants/*.json 变更 → 构建 → 上传微信后台
```

### 8.3 数据库迁移

引入 Alembic，5 个初始迁移脚本：Tenant/TenantUser/TenantData/Department 表 → User 加 tenant_id → 其余表加 tenant_id → event_logs → session_profiles。

### 8.4 多环境

dev（Docker Compose + fixtures）/ staging（脱敏数据）/ prod。

---

## 9. 迁移计划

### 核心原则

**核心引擎复用，外壳重建。** AI 引擎（对话、画像、推荐）的核心逻辑经检验可复用——封装为独立模块后纳入新架构。API 层重建，前端完全重做，小程序从零创建。

### 四阶段迁移

| 阶段 | 时间 | 目标 |
|------|------|------|
| Phase 0: 稳定化 | Week 1-2 | 核心引擎稳定，修复已知 bug，引擎可独立验证 |
| Phase 1: 地基 | Week 3-5 | 多租户框架就绪，引擎在 tenant 隔离下工作 |
| Phase 2: 重建 | Week 6-9 | 新 API + 新管理端 SPA + 小程序，单院校全链路 |
| Phase 3: 扩展 | Week 10-13 | 多院校 + 增值模块 + 完整管理端 |

### Phase 0: 稳定化（Week 1-2）

```
Week 1: 核心引擎审查与修复
  ├── conversation/agent.py — 审查 LangGraph 状态转换边界 case
  ├── conversation/profile_analyzer.py — JSON 解析容错
  ├── conversation/evidence_accumulator.py — 置信度计算边界
  ├── recommendation/service.py — LLM 调用重试 + 超时处理
  ├── api/routes/chat.py — WebSocket 断连/重连/异常处理
  └── 修复 API schema 前后端不一致

Week 2: 核心引擎独立可验证
  ├── 为核心引擎编写集成测试（对话→画像→推荐 全链路）
  ├── fixture 数据验证推荐输出确定性
  ├── 清理无用代码和过时注释
  └── 产出: 核心引擎通过测试，可独立运行
```

### Phase 1: 地基（Week 3-5）

```
Week 3: 数据库 + 基础设施
  ├── Alembic 初始化 + Migration 001-003
  ├── core/tenant_context.py
  ├── core/module_registry.py
  └── core/event_writer.py

Week 4: 核心引擎 tenant 化
  ├── 按新目录结构迁移 conversation/recommendation/profile/knowledge
  ├── 所有查询加 tenant_id 过滤
  ├── ChromaDB 改为多 collection
  └── 验证引擎在 tenant 隔离下正常运行

Week 5: 全新 API 层搭建
  ├── 新 router 文件 + 整合核心引擎
  ├── admin/analytics/tenants 路由 scaffold
  └── 产出: 新 API 可启动，核心接口可调用
```

### Phase 2: 重建（Week 6-9）

```
Week 6: 管理端 SPA 重建（全新 Vite + React + TS + Tailwind 项目）
  ├── 路由 + 登录页（品牌可配置）+ 主布局（CSS 变量换肤）
  └── 产出: 管理端可登录，动态品牌色生效

Week 7: 管理端核心面板
  ├── 品牌配置页 + 知识库管理页
  ├── 招生漏斗面板（ECharts）+ 画像看板（雷达图+饼图）
  └── 产出: 基础包功能完整

Week 8: 小程序（全新 uni-app 项目）
  ├── 对话页 + 推荐页 + 注册/登录页（可选）
  ├── 品牌配置注入（构建时 tenant slug + 主题色）
  └── 产出: 单院校小程序可扫码对话

Week 9: 单院校全链路联调
  ├── 试点 tenant 创建 + 数据接入（L0+L1）
  ├── 扫码 → 对话 → 画像 → 推荐 → 全链路验证
  ├── 管理端 → 漏斗数据 → 画像聚合 → 知识库上传
  └── 产出: 单院校闭环可演示，小程序提交审核
```

### Phase 3: 扩展（Week 10-13）

```
Week 10-11: 增值模块 + 多院校
  ├── 专业热度/地域分布/对话质量模块
  ├── 第 2-3 所试点院校接入
  └── 小程序批量构建 + Onboarding 自动化

Week 12-13: 完整管理端 + 性能
  ├── 对比/流失分析 + 年度报告 + 角色权限 + 多院系
  ├── 压测（50 院校并发对话 + 并发检索）
  └── 产出: 完整产品可交付
```

### 关键风险点

| 风险 | 应对 |
|------|------|
| 核心引擎有隐藏 bug，稳定化超预期 | Phase 0 限时 2 周；超出则标记已知问题不阻塞 |
| 前端重做需求蔓延 | 严格按基础包功能做 Phase 2，不碰增值模块 UI |
| 小程序审核不通过 | Parallel Track：同步开发 H5 降级版（WebView 嵌入公众号） |
| 管理端 UI 设计反复 | Phase 2 开始前先定设计稿（至少线框图），不边做边改 |
| tenant_id 遗漏导致数据泄漏 | 所有查询封装 BaseRepository，强制 tenant 过滤 |
