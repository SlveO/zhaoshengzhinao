# Role D: 数据 + 基础设施 — 技术参考文档

> 编写日期: 2026-05-24 | 负责人: Role D (数据+基础设施) | 状态: 核心功能就绪，CI/CD 和文档待补

---

## 快速使用指南（给 A / B / C 轨道同学）

### 知识库搜索 API（RAG）

D 轨道维护的知识库搜索接口，供聊天 Agent 和管理后台使用。

**端点**: `GET /api/v1/knowledge/search`

**权限**: 需要携带租户标识（`X-Tenant` header 或 `?tenant=` 查询参数）

**请求示例**:

```bash
curl -G 'http://localhost:8000/api/v1/knowledge/search' \
  -H 'X-Tenant: scnu' \
  --data-urlencode 'q=计算机科学与技术就业前景' \
  --data-urlencode 'k=5'
```

**响应格式**:

```json
{
  "query": "计算机科学与技术就业前景",
  "tenant": "scnu",
  "results": [
    {
      "id": "a617677b-...",
      "text": "文档文本内容...",
      "metadata": {
        "category": "专业与学院",
        "data_type": "campus_life",
        "tenant_slug": "scnu",
        "source_title": "华南师范大学学院及专业简介",
        "source_url": "https://zsb.scnu.edu.cn/zyjj/",
        "year": 2025,
        "province": "广东"
      },
      "score": 0.9905,
      "source_url": "https://zsb.scnu.edu.cn/zyjj/",
      "source_title": "华南师范大学学院及专业简介"
    }
  ]
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `q` | string | 是 | 搜索查询，1-500 字符 |
| `k` | int | 否 | 返回结果数，1-20，默认 5 |
| `data_type` | string | 否 | 按数据类型过滤（如 `campus_life`、`admission_score`） |

**Role A 使用场景**: 在 `chat.py` WebSocket 消息处理中，调用此接口获取知识库内容注入 System Prompt，实现 RAG 对话。tenant_slug 可从 WebSocket query params 获取。

**Role B 使用场景**: 管理后台知识库搜索框直接调用此接口，展示搜索结果及来源链接。

**Role C 使用场景**: 小程序端如果未来需要展示知识库内容，可调用此接口。

---

### 租户数据索引

当你通过管理后台或脚本导入新数据到 `tenant_data` 表后，需要触发索引重建才能让知识库搜索到。

**方法 1 — Python 代码**:

```python
from knowledge.indexer import reindex_tenant

await reindex_tenant("scnu")  # 删除旧索引 → 从 PG 读取 → 批量写入 ChromaDB
```

**方法 2 — Shell 脚本**:

```bash
cd backend
python -c "import asyncio; from knowledge.indexer import reindex_tenant; asyncio.run(reindex_tenant('scnu'))"
```

**方法 3 — 逐条索引**（导入单条数据时）:

```python
from knowledge.indexer import index_tenant_data
from tenants.models import TenantData

# td 为已 commit 的 TenantData 实例
await index_tenant_data("scnu", td)
td.indexed_at = datetime.now(timezone.utc)
await db.commit()
```

**注意事项**:
- `reindex_tenant()` 会删除整个 ChromaDB 集合并重建，操作期间该租户的搜索会返回空
- 索引使用 BAAI/bge-large-zh-v1.5 中文向量模型，首次加载约需 5 秒
- 数据量 < 10K 条时，reindex 通常在 30 秒内完成

---

### 运行测试

```bash
# 进入后端目录
cd backend

# 全量测试（单元 + 集成）
python -m pytest tests/ -v

# 仅单元测试
python -m pytest tests/unit/ -v

# 仅集成测试
python -m pytest tests/integration/ -v

# 单个测试文件
python -m pytest tests/unit/test_guard.py -v

# 带覆盖率
python -m pytest tests/ --cov=. --cov-report=html
```

**测试数据库**: 测试自动使用 `gaokao_test` 数据库，不会影响生产数据。`conftest.py` 强制设置 `DATABASE_URL` 指向测试库，每个测试后自动清理数据。

**Docker 中运行**: `docker exec zhaoshengzhinao-backend-1 sh -c "cd /app && python -m pytest tests/ -v"`

---

## 1. 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Role D 负责模块                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ 数据采集  │───→│ 数据验证  │───→│ 数据导入  │───→│ 向量索引  │   │
│  │ scrapers/ │    │ storage/ │    │ scripts/ │    │knowledge/│   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    基础设施层                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │   │
│  │  │ 测试体系  │  │ CI/CD   │  │  Docker  │  │  文档    │  │   │
│  │  │  tests/  │  │.github/  │  │ docker/  │  │  docs/   │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 数据流全景

```
外部数据源 (阳光高考/EOL API/院校官网)
    │
    ▼
BaseScraper (异步采集 + 重试 + 限速)
    │
    ▼
data/raw/ (原始 JSON)
    │
    ▼
Validator (Pydantic 校验 + 去重)
    │
    ├──→ data/approved/ (清洗后完整数据)
    │
    ▼
seed_db.py / import_scnu_knowledge.py (导入 PostgreSQL)
    │
    ▼
PostgreSQL (tenant_data 表 + 业务表)
    │
    ▼
indexer.py (BGE 中文向量化 + 写入 ChromaDB)
    │
    ▼
ChromaDB (bge-large-zh-v1.5 嵌入, 1024 维)
    │
    ▼
/api/v1/knowledge/search → LLM (RAG 问答)
```

---

## 2. 知识库与向量检索 (Knowledge Base & RAG)

### 2.1 模块架构

```
backend/knowledge_base/        # 核心向量检索
├── chroma_client.py           # ChromaDB 客户端 + search_similar()
├── embeddings.py              # bge-large-zh-v1.5 嵌入模型封装
└── retriever.py               # 混合检索器 (语义 + 规则)

backend/knowledge/             # 租户级索引
├── client.py                  # ChromaDB 客户端代理
└── indexer.py                 # 租户数据索引 + 重建

backend/api/routes/
└── knowledge.py               # /api/v1/knowledge/search 端点
```

### 2.2 ChromaDB 集合设计

| 集合 | 用途 | 租户 | 文档数 |
|------|------|------|--------|
| `colleges_majors` | 全国院校专业检索 | 全局 | ~182K |
| `scnu_colleges` | SCNU 租户深度数据（录取 + 培养 + 就业 + 校园知识） | scnu | 16 (campus_life) |

**集合命名规则**: `{tenant_slug}_colleges`

**元数据结构** (每条文档):

```json
{
  "tenant_slug": "scnu",
  "data_type": "campus_life",
  "year": 2025,
  "province": "广东",
  "category": "学科实力",
  "topic": "双一流学科",
  "dataset": "scnu_comprehensive_knowledge_v2026_05_23",
  "source_title": "华南师范大学学校简介",
  "source_url": "https://www.scnu.edu.cn/a/20161025/1.html"
}
```

### 2.3 嵌入模型

| 属性 | 值 |
|------|-----|
| 模型名称 | `BAAI/bge-large-zh-v1.5` |
| 下载渠道 | ModelScope（国内镜像）→ HuggingFace（fallback） |
| 缓存路径 | `/app/.cache/modelscope/BAAI/bge-large-zh-v1___5/` |
| 向量维度 | 1024 |
| 模型大小 | ~1.3GB |
| 归一化 | `normalize_embeddings=True` |
| 设备 | CPU |
| Docker 卷 | `modelscope_cache`（持久化，避免每次重启下载） |

**Docker 环境变量**:

```bash
MODELSCOPE_CACHE=/app/.cache/modelscope
```

**代码中获取嵌入**:

```python
from knowledge_base.embeddings import embedding_model

vec = embedding_model.embed_query("计算机科学与技术")        # → list[float] (1024维)
vecs = embedding_model.embed_documents(["文本1", "文本2"])    # → list[list[float]]
```

### 2.4 知识库搜索 API

**路由文件**: `backend/api/routes/knowledge.py`

```python
@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=1, max_length=500),
    k: int = Query(default=5, ge=1, le=20),
    data_type: str | None = Query(default=None),
    tenant=Depends(get_current_tenant),
):
```

**实现流程**:
1. 解析租户 → 确定集合名 `{slug}_colleges`
2. `embedding_model.embed_query(q)` → 1024 维向量
3. `collection.query(query_embeddings=[...], n_results=k)` → ChromaDB 语义搜索
4. 组装结果（id, text, metadata, score, source_url, source_title）

**score 说明**: `score = 1 - cosine_distance`，范围约 [-1, 1]，越接近 1 越相关。

---

## 3. 数据库设计（D 轨道维护部分）

### 3.1 tenant_data 表

通用租户数据存储表，存放录取分数、培养计划、就业数据、校园知识等。

```sql
CREATE TABLE tenant_data (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    data_type VARCHAR(64) NOT NULL,    -- 'admission_score' | 'curriculum' | 'employment' | 'campus_life'
    title VARCHAR(512),
    content JSONB NOT NULL,
    source_url VARCHAR(2048),
    year INTEGER,
    province VARCHAR(64),
    extra_meta JSONB NOT NULL DEFAULT '{}',
    indexed_at TIMESTAMPTZ,            -- 最后索引时间，NULL 表示未索引
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**data_type 枚举**:

| 类型 | 说明 | 导入脚本 |
|------|------|----------|
| `admission_score` | 历年录取分数 | `import_scnu_data.py` |
| `curriculum` | 培养计划/课程 | `import_scnu_data.py` |
| `employment` | 就业报告 | `import_scnu_data.py` |
| `campus_life` | 校园知识百科 | `import_scnu_knowledge.py` |

### 3.2 extra_meta 字段约定

`extra_meta` 是 JSONB 字段，用于存储额外的结构化元数据。ChromaDB 索引时，extra_meta 中的键值会展开到文档 metadata 中。

**campus_life 类型的 extra_meta**:

```json
{
  "dataset": "scnu_comprehensive_knowledge_v2026_05_23",
  "category": "学科实力",
  "topic": "双一流学科",
  "source_title": "华南师范大学学校简介",
  "source_url": "https://www.scnu.edu.cn/a/20161025/1.html"
}
```

**重要**: `source_url` 和 `source_title` 必须同时在 `extra_meta` 和 `content` 中设置，以确保搜索引擎前端能正确展示来源链接。

---

## 4. 租户数据索引器

### 4.1 indexer.py

**文件**: `backend/knowledge/indexer.py`

**核心函数**:

```python
async def index_tenant_data(tenant_slug: str, data: TenantData) -> None:
    """索引单条 TenantData → {tenant_slug}_colleges 集合"""

async def reindex_tenant(tenant_slug: str) -> None:
    """删除并重建租户的全部 ChromaDB 索引

    流程:
    1. 删除旧集合 {tenant_slug}_colleges
    2. 从 PostgreSQL 读取该租户的全部 TenantData
    3. 通过 BGE 中文向量模型逐条编码
    4. 批量写入 ChromaDB（500 条/批）
    """
```

**文档文本构建** (`_build_document_text`):

| data_type | 文档格式 |
|-----------|----------|
| `admission_score` | `{专业名} {年份}年 {省份} 最低分{min_score} 最低位次{min_rank} 选科要求{subject_requirements}` |
| `curriculum` | `{核心课程列表} {培养目标}` |
| `employment` | `就业率{rate} 月薪{salary} 行业: {top5行业(占比)}` |
| `campus_life` | `{类别} {主题} {摘要} {正文} {QA对} {关键词} {来源标题} {来源URL}` |

### 4.2 es_meta 覆盖规则

ChromaDB metadata 构造时，`extra_meta` 展开放置在**最前面**，后续显式键（`tenant_slug`, `data_type`, `year`, `province`, `source_title`, `source_url`）会覆盖 extra_meta 中的同名键，确保关键字段不被意外覆盖。

---

## 5. 测试体系

### 5.1 测试概览

```
backend/tests/
├── conftest.py                              # 全局 fixtures
├── unit/
│   ├── test_analytics_funnel.py             # 漏斗分析
│   ├── test_analytics_profile_dashboard.py  # 画像仪表盘
│   ├── test_analytics_major_heatmap.py      # 专业热力图
│   ├── test_analytics_region_distribution.py # 地域分布
│   ├── test_analytics_dialogue_quality.py   # 对话质量
│   ├── test_analytics_annual_report.py      # 年报
│   ├── test_analytics_competitive.py        # 竞争分析
│   ├── test_auth_service.py                 # 认证服务
│   ├── test_chat_service.py                 # 对话服务
│   ├── test_recommendation_service.py       # 推荐服务
│   ├── test_tenant_resolution.py            # 租户解析
│   ├── test_module_gate.py                  # 模块开关
│   ├── test_module_registry.py              # 模块注册表
│   ├── test_knowledge_indexer.py            # 知识索引器
│   ├── test_guard.py                        # 输入守卫
│   ├── test_excel_importer.py               # Excel 导入
│   ├── test_excel_validator.py              # Excel 验证
│   ├── test_b2b_prompt.py                   # B2B Prompt
│   ├── test_evidence_accumulator.py         # 证据累积器
│   └── test_admin_knowledge.py              # 管理后台知识库
├── integration/
│   ├── test_auth_api.py                     # Auth API 端到端
│   ├── test_chat_api.py                     # Chat API 端到端
│   └── test_tenant_isolation.py             # 租户隔离
├── test_profile_analyzer.py                 # 画像分析
└── test_evidence_accumulator.py             # 证据累积
```

**统计**: 26 个测试文件，114 个测试用例，全部通过。

### 5.2 测试基础设施 — conftest.py

#### 关键设计

- **测试数据库强制隔离**: `os.environ["DATABASE_URL"] = "gaokao_test"` — **强制覆盖**环境变量，不使用 `setdefault`，确保测试绝不污染生产数据库
- **Session 级建表 + Function 级清数据**: `setup_db` fixture（autouse）在首次运行时创建表结构，每个测试后 DELETE 所有数据
- **Lazy Engine 模式**: `models/__init__.py` 使用 `_LazyEngine` / `_LazySessionMaker` 代理类，延迟 engine 创建到首次 DB 操作，避免 pytest event loop 冲突
- **pytest.ini**: `asyncio_mode = auto` + `asyncio_default_fixture_loop_scope = session` + `asyncio_default_test_loop_scope = session` — 确保所有 fixture 和测试共享同一 event loop
- **async_client**: 集成测试使用 `httpx.AsyncClient` + `ASGITransport`，不使用同步 TestClient（会导致 event loop 冲突）

#### 核心 Fixtures

| Fixture | 作用域 | 说明 |
|---------|--------|------|
| `setup_db` | function (autouse) | 建表 + 每测试后清理 12 张表 |
| `test_tenant` | function | 创建 `test` 租户 |
| `other_tenant` | function | 创建 `other` 租户（隔离测试用） |
| `tenant_admin_user` | function | 创建 admin 用户 |
| `seed_event` | function | 工厂 fixture: 插入 event_log |
| `seed_session_profile` | function | 工厂 fixture: 插入 SessionProfile |
| `app_client` | function | FastAPI TestClient（单元测试用） |
| `async_client` | function | httpx.AsyncClient（集成测试用） |

### 5.3 models/__init__.py — Lazy Engine 模式

**背景**: pytest-asyncio 管理 event loop 生命周期，如果 engine 在模块导入时创建，会绑定到错误的 loop。

**解决方案**: 使用代理类延迟 engine 创建到首次实际使用时。

```python
_engine = None
_async_session = None

def _init_engine():
    global _engine, _async_session
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _async_session = async_sessionmaker(_engine, ...)
    return _engine

class _LazyEngine:
    def __getattr__(self, name):
        return getattr(_init_engine(), name)

class _LazySessionMaker:
    def __call__(self):
        _init_engine()
        return _async_session()

engine = _LazyEngine()
async_session = _LazySessionMaker()
```

**影响**: `from models import async_session` 不再触发 engine 创建。首次 `async_session()` 或 `engine.begin()` 调用时才创建，此时 event loop 已正确设置。

### 5.4 Analytics 模块 Lazy Import

所有 `backend/analytics/*.py` 模块的 `from models import async_session` 从模块顶层移到函数内部：

```python
# 之前（模块级导入，触发 engine 创建）
from models import async_session

async def get_funnel(tenant_id: str, days: int = 365) -> dict:
    async with async_session() as db:
        ...

# 之后（函数内导入，延迟到调用时）
async def get_funnel(tenant_id: str, days: int = 365) -> dict:
    from models import async_session
    async with async_session() as db:
        ...
```

---

## 6. Docker 容器化与部署

### 6.1 文件清单

```
docker/
├── Dockerfile.backend       # Python 后端镜像
├── Dockerfile.frontend      # 通用前端镜像 (ARG 参数化)
├── nginx.conf               # 反向代理配置
└── static.conf              # 前端静态文件 Nginx 配置

docker-compose.yml           # 本地开发/演示部署
docker-compose.prod.yml      # 生产覆盖配置
.dockerignore                # 构建排除
```

### 6.2 docker-compose.yml 服务

| 服务 | 镜像 | 端口 | 关键配置 |
|------|------|------|----------|
| `db` | postgres:16-alpine | 5432 | 持久卷 `postgres_data`，healthcheck: `pg_isready` |
| `redis` | redis:7-alpine | 6379 | AOF 持久化，healthcheck: `redis-cli ping` |
| `backend` | 构建 `docker/Dockerfile.backend` | 8000 | depends_on db+redis (healthy)，uvicorn 2 workers |
| `admin-spa` | 构建 `docker/Dockerfile.frontend` | 80 | ARG: admin-spa，VITE_BASE_PATH=/admin/ |
| `mini-app` | 构建 `docker/Dockerfile.frontend` | 80 | ARG: mini-app，TENANT=scnu |
| `nginx` | nginx:1.27-alpine | 80 | 反向代理，WebSocket 升级 |

**持久卷**: `postgres_data`、`redis_data`、`chroma_data`、`uploads`、`modelscope_cache`

### 6.3 Dockerfile.backend 关键特性

```dockerfile
FROM python:3.11-slim
# 非 root 用户 app
# HEALTHCHECK: curl /api/health
# CMD: alembic upgrade head && uvicorn main:app --workers 2 --timeout-keep-alive 300
```

- **非 root 用户运行**: 安全
- **启动自动 migration**: alembic upgrade head
- **ModelScope 缓存**: `MODELSCOPE_CACHE=/app/.cache/modelscope`，卷持久化

### 6.4 Nginx 配置

```
/api/   → backend:8000    (WebSocket Upgrade, 3600s timeout)
/admin/ → admin-spa:80    (SPA routing)
/       → mini-app:80     (H5)
```

安全头: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `CSP`

### 6.5 docker-compose.prod.yml 覆盖

- `restart: always` — 所有服务
- 日志: json-file, 10MB 轮转, 保留 5 个文件
- 资源限制: backend 2 CPU / 3GB 内存

---

## 7. 数据导入脚本

### 7.1 脚本清单

```
scripts/
├── seed_db.py                 # 种子数据导入（162 院校 + 194K 录取记录）
├── import_scnu_data.py        # SCNU 深度数据导入（录取 + 培养 + 就业）
├── import_scnu_knowledge.py   # SCNU 综合咨询知识导入（16 条 campus_life）
├── create_scnu_tenant.py      # 创建 SCNU 租户
├── index_chroma.py            # ChromaDB 全局索引重建
├── verify_scnu_data.py        # SCNU 数据完整性验证
├── smoke_test.py              # E2E 冒烟测试
├── seed_conversations.py      # 模拟对话数据生成
└── monitor_chroma.py          # ChromaDB 索引进度监控
```

### 7.2 SCNU 知识导入流程

```bash
# 1. 创建 SCNU 租户
python scripts/create_scnu_tenant.py

# 2. 导入综合咨询知识（16 条 campus_life）
python scripts/import_scnu_knowledge.py

# 3. 验证数据完整性
python scripts/verify_scnu_data.py
```

### 7.3 import_scnu_knowledge.py 工作原理

1. 读取 `data/approved/scnu_comprehensive_knowledge.json`（16 条记录）
2. 逐条创建 `TenantData` 记录（data_type=campus_life）
3. 每条记录写入后立即调用 `index_tenant_data()` 写入 ChromaDB
4. 更新 `tenant_data.indexed_at` 时间戳
5. 更新租户 config 中的 `knowledge_base` 元数据

**数据内容** (`scnu_comprehensive_knowledge.json`): 华南师范大学招生咨询高频问答，覆盖学校概况、学科实力、专业分布、体检限制、录取政策、学费资助、转专业、校园生活、联系方式等 16 个主题。

---

## 8. 环境变量参考

### 8.1 后端必需

```bash
DATABASE_URL=postgresql+asyncpg://gaokao:gaokao@db:5432/gaokao
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<生产环境必须修改>
DEEPSEEK_API_KEY=<DeepSeek API Key>
```

### 8.2 后端可选

```bash
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
CHROMA_PERSIST_DIR=/app/chroma_data
MODELSCOPE_CACHE=/app/.cache/modelscope
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
```

### 8.3 测试专用

```bash
TEST_DATABASE_URL=postgresql+asyncpg://gaokao:gaokao@db:5432/gaokao_test
TEST_REDIS_URL=redis://redis:6379/15
```

---

## 9. 数据采集层 (Scrapers) — 参考

### 9.1 BaseScraper — 异步基类

所有爬虫的公共基类，提供:

| 能力 | 实现方式 |
|------|----------|
| 速率控制 | `asyncio.Lock` + `delay_seconds` 最小间隔 |
| 自动重试 | `tenacity`，指数退避 (2s→4s→8s)，最多 3 次 |
| 重试条件 | 仅超时/传输错误/429/5xx；4xx 直接失败 |
| 结构化日志 | `loguru`，独立日志文件，10MB 轮转，保留 7 天 |
| 原始数据保存 | `save_raw()` — JSON 格式化存储到 `data/raw/` |

### 9.2 数据源

| 爬虫 | 数据源 | 产出 |
|------|--------|------|
| `GaokaoScoreScraper` | EOL API | 院校信息 + 录取分数 |
| `SunshineGaokaoScraper` | 阳光高考网 | 院校详情 |
| `ScnuAdmissionsScraper` | SCNU 招生网 | 华师录取数据 |
| `ScnuCurriculumScraper` | SCNU 教务处 | 华师培养计划 |
| `ScnuEmploymentScraper` | SCNU 就业报告 | 华师就业数据 |
| `IndustryDataBuilder` | 内置行业知识 | 行业分析 + 专业映射 |

### 9.3 数据验证器

Pydantic 校验 + 去重，验证失败不阻断流水线（记录错误日志继续导出）。

---

## 10. 已知缺口与后续计划

| 缺口 | 严重程度 | 说明 | 负责人 |
|------|----------|------|-------|
| **对话 RAG 未接线** | 中 | `chat.py` WebSocket 未调用知识库搜索 | A |
| **CI/CD 空白** | 中 | `.github/workflows/` 未创建 | D |
| **前端服务未启动** | 低 | admin-spa/mini-app/nginx 未构建运行 | B/C |
| **pre-commit hooks 未配置** | 低 | `.pre-commit-config.yaml` 未创建 | D |
| **DEPLOYMENT.md 缺失** | 低 | 部署文档待补 | D |
| **OPERATIONS.md 缺失** | 低 | 运维手册待补 | D |
| **ChromaDB 无高可用** | 低 | 单机 PersistentClient | 后续 |

---

## 11. 关键文件修改注意事项

- **`backend/models/__init__.py`** — Lazy Engine 模式。不要在模块顶层调用 `create_async_engine()`，使用 `_LazyEngine` / `_LazySessionMaker` 代理
- **`backend/analytics/*.py`** — 所有 analytics 函数内部导入 `from models import async_session`，不要放在模块顶层
- **`backend/knowledge/indexer.py`** — `reindex_tenant()` 会删除并重建整个 ChromaDB 集合。`index_tenant_data()` 逐条索引，用于单条导入场景
- **`backend/knowledge/indexer.py:_sanitize_meta_val()`** — None → ""（ChromaDB 不允许 None 值）
- **`backend/knowledge/indexer.py:extra_meta`** — 展开时放在最前面，显式键（tenant_slug 等）放后面，确保不被覆盖
- **`backend/tests/conftest.py`** — 使用 `os.environ["DATABASE_URL"] = ...` 强制覆盖，不要用 `setdefault`
- **`pytest.ini`** — 三项配置缺一不可：`asyncio_mode = auto`、`asyncio_default_fixture_loop_scope = session`、`asyncio_default_test_loop_scope = session`
