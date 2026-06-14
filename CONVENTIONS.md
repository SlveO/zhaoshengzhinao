# 招生智脑 B2B 平台 — 开发规范与接口契约

> 所有轨道必须遵守。修改跨轨道接口必须先更新本文档。

---

## 1. 代码规范

### 1.1 Python（后端）

```python
# 命名
class TenantService:           # PascalCase 类
def get_current_tenant():      # snake_case 函数
tenant_id = Column(UUID)       # snake_case 变量
TENANT_CACHE_TTL = 300         # UPPER_CASE 常量

# 类型注解（所有函数签名必须有）
async def resolve_tenant(slug: str) -> Optional[Tenant]:

# 导入顺序
# 1. stdlib
# 2. third-party
# 3. local
from typing import Optional
from fastapi import FastAPI
from core.tenant_context import get_current_tenant
```

### 1.2 TypeScript（管理端 + 小程序）

```typescript
// 命名
const TenantService = {}       // PascalCase 类/组件
const getBrandConfig = () => {}// camelCase 函数
const tenantId = ref<string>() // camelCase 变量

// 类型定义（所有 API 响应必须有 interface）
interface TenantBrand {
  name: string
  shortName: string
  primaryColor: string
  logoUrl: string
}
```

### 1.3 提交信息

```
feat: add tenant resolution middleware
fix: WebSocket disconnect not cleaning up session
refactor: extract event writer to core module
chore: update Alembic migration scripts
docs: update API contract for brand config endpoint
```

---

## 2. API 契约（跨轨道接口）

### 2.1 通用约定

| 规则 | 说明 |
|------|------|
| Base URL | `/api/v1/` |
| 学生端请求头 | `X-Tenant: <slug>` 必须 |
| 管理端请求头 | `Authorization: Bearer <jwt>` 必须 |
| 响应格式 | `{ "data": ..., "error": null }` 或 `{ "data": null, "error": { "code": "...", "message": "..." } }` |
| 分页 | `?page=1&page_size=20`，响应含 `{ "items": [], "total": N, "page": 1, "page_size": 20 }` |
| 日期 | ISO 8601 格式 `2026-05-18T10:30:00Z` |

### 2.2 核心 API（Foundation 轨道产出）

```
POST   /api/v1/auth/register          # 学生注册
POST   /api/v1/auth/login             # 统一登录（学生+staff）
POST   /api/v1/auth/refresh           # Token 刷新

POST   /api/v1/chat/session           # 创建对话会话
WS     /api/v1/chat/session/{id}      # WebSocket 对话
GET    /api/v1/chat/session/{id}      # 获取会话历史
DELETE /api/v1/chat/session/{id}      # 删除会话

GET    /api/v1/recommendations        # 获取推荐结果
POST   /api/v1/recommendations/feedback # 提交推荐反馈

GET    /api/v1/profiles               # 获取用户画像
POST   /api/v1/profiles/feedback      # 画像反馈

GET    /api/v1/colleges               # 院校列表（tenant-scoped）
GET    /api/v1/colleges/{id}          # 院校详情

GET    /api/v1/industries             # 行业数据（全局）
GET    /api/v1/industries/mappings    # 专业→行业映射（全局）

GET    /api/v1/knowledge/search       # 租户知识库 RAG 检索（学生端/LLM 工具可用）
```

### 2.3 管理端 API（Admin SPA + Analytics 轨道消费）

```
# 品牌配置
GET    /api/v1/admin/brand-config          # 获取品牌配置
PUT    /api/v1/admin/brand-config          # 更新品牌配置
POST   /api/v1/admin/brand-config/logo     # 上传 Logo

# 知识库管理
GET    /api/v1/admin/knowledge/documents   # 文档列表
POST   /api/v1/admin/knowledge/documents   # 上传文档/Excel
DELETE /api/v1/admin/knowledge/documents/{id}
POST   /api/v1/admin/knowledge/reindex     # 触发重新索引
GET    /api/v1/admin/knowledge/index-status # 索引状态

# 分析面板（按模块开关控制访问）
GET    /api/v1/admin/analytics/funnel            # 招生漏斗
GET    /api/v1/admin/analytics/profile-dashboard  # 画像看板
GET    /api/v1/admin/analytics/major-heatmap      # 专业热度
GET    /api/v1/admin/analytics/region-distribution # 地域分布
GET    /api/v1/admin/analytics/competitive        # 对比+流失分析
GET    /api/v1/admin/analytics/dialogue-quality   # 对话质量
GET    /api/v1/admin/analytics/annual-report      # 年度报告

# 租户管理
GET    /api/v1/admin/tenants/{id}          # 租户信息
PUT    /api/v1/admin/tenants/{id}/config   # 更新配置
PUT    /api/v1/admin/tenants/{id}/modules  # 模块开关
GET    /api/v1/admin/tenants/{id}/users    # 租户用户列表
POST   /api/v1/admin/tenants/{id}/users    # 创建租户用户
DELETE /api/v1/admin/tenants/{id}/users/{uid}

# 院系管理（增值模块）
GET    /api/v1/admin/departments
POST   /api/v1/admin/departments
PUT    /api/v1/admin/departments/{id}
DELETE /api/v1/admin/departments/{id}

# 角色管理（增值模块）
GET    /api/v1/admin/roles
PUT    /api/v1/admin/roles/{id}
```

### 2.4 接口契约：Foundation → Admin SPA

Admin SPA 轨道依赖以下 Foundation 产出：

```typescript
// GET /api/v1/admin/brand-config 响应
interface BrandConfig {
  name: string
  shortName: string
  primaryColor: string    // hex, e.g. "#1a56db"
  secondaryColor: string
  logoUrl: string
  faviconUrl: string
  loginBgUrl: string | null
}

// GET /api/v1/admin/analytics/funnel 响应
interface FunnelData {
  period: { start: string; end: string }
  stages: {
    visitors: number
    conversations: number
    deepConsultations: number
    intentExpressed: number
    enrolled: number
  }
  conversionRates: {
    visitorToConversation: number
    conversationToDeep: number
    deepToIntent: number
    intentToEnrolled: number
  }
}

// GET /api/v1/admin/analytics/profile-dashboard 响应
interface ProfileDashboard {
  riasecDistribution: { dimension: string; avgScore: number; count: number }[]
  valuesDistribution: { value: string; percentage: number }[]
  completenessBreakdown: { level: string; count: number }[]
  totalProfiles: number
}
```

### 2.5 接口契约：Tenant Knowledge Search → LLM/RAG 调用方

用于按当前租户检索 ChromaDB 知识库。学生端或外部大模型工具调用时必须传 `X-Tenant` 请求头；管理端调试也可使用 `?tenant=scnu`。

```
GET /api/v1/knowledge/search?q=<query>&k=5&data_type=campus_life
```

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `q` | string | 是 | 用户问题或检索 query，1-500 字 |
| `k` | integer | 否 | 返回条数，默认 5，范围 1-20 |
| `data_type` | string | 否 | 限定知识类型，如 `admission_score` / `curriculum` / `employment` / `campus_life` |

响应：

```typescript
interface KnowledgeSearchResponse {
  query: string
  tenant: string
  results: {
    id: string
    text: string
    metadata: Record<string, string | number | boolean>
    score: number | null
    source_url: string
    source_title: string
  }[]
}
```

示例：

```bash
curl "http://localhost:8000/api/v1/knowledge/search?q=华南师范大学住宿费多少&k=5&data_type=campus_life" \
  -H "X-Tenant: scnu"
```

### 2.6 WebSocket 消息协议

```json
// Client → Server
{ "type": "message", "content": "我对计算机比较感兴趣" }

// Server → Client
{ "type": "thinking" }
{ "type": "message", "content": "了解！你提到计算机...", "stage": "explore" }
{ "type": "profile_update", "riasec": { "R": 6, "I": 5 }, "confidence": 0.7, "completeness": "L1" }
{ "type": "stage_change", "from": "explore", "to": "focus" }
{ "type": "summary", "content": "根据我们的对话，你是一个...", "profile_snapshot": {...} }
{ "type": "error", "code": "RATE_LIMIT", "message": "请稍后再试" }
```

---

## 3. 数据库规范

| 规则 | 说明 |
|------|------|
| 主键 | 统一 UUID，`gen_random_uuid()` |
| 时间戳 | `created_at TIMESTAMPTZ NOT NULL DEFAULT now()` |
| 更新时间 | `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` |
| 软删除 | `deleted_at TIMESTAMPTZ`（不用硬删除） |
| 枚举 | PostgreSQL ENUM 类型，不在代码中硬编码 |
| JSONB | 用于灵活配置（tenant.config、payload），禁止用于频繁查询的字段 |
| 迁移 | Alembic 管理，迁移脚本可逆（含 downgrade） |

### 必须的 tenant_id 过滤

所有涉及租户数据的查询必须带 `tenant_id`：

```python
# ✅ 正确
stmt = select(User).where(User.tenant_id == tenant.id)

# ❌ 错误
stmt = select(User)  # 会泄漏其他租户数据
```

---

## 4. 测试规范

| 层级 | 框架 | 覆盖要求 |
|------|------|---------|
| 单元测试 | pytest + pytest-asyncio | 核心引擎逻辑（agent, evidence_accumulator, retriever）|
| 集成测试 | pytest + httpx | API 路由 + 数据库 |
| E2E | Playwright（管理端）/ 手动（小程序） | 核心用户流程 |

### 测试文件位置

```
backend/tests/
├── unit/
│   ├── test_evidence_accumulator.py
│   ├── test_retriever.py
│   └── test_module_registry.py
├── integration/
│   ├── test_auth_api.py
│   ├── test_chat_api.py
│   └── test_analytics_api.py
└── fixtures/
    └── tenant_fixtures.py
```

---

## 5. 环境变量

```bash
# .env (共享)
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
JWT_SECRET=...
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
CHROMA_PERSIST_DIR=./chroma_data
FILE_STORE_DIR=./uploads
```

所有轨道使用同一份 `.env.example`。私有密钥通过环境变量注入，不提交到 git。

---

## 6. 跨轨道依赖声明

| 消费方 | 依赖 | 提供方 | 状态 |
|--------|------|--------|------|
| Admin SPA | Brand API + Analytics API | Foundation | 待开发 |
| Mini-App | Chat API + Recommendation API | Foundation | 待开发 |
| Analytics 模块 | event_logs 表 + tenant 模型 | Foundation | 待开发 |
| Data Onboarding | TenantData 模型 + ChromaDB indexer | Foundation | 待开发 |
| 全部 | CONVENTIONS.md 定义的 API 契约 | 本文档 | 已就绪 |
