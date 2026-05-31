# 招生智脑 — 技术架构与部署机制

> 面向接手者的技术上手文档。说明项目结构、代码如何到达生产环境、以及常见陷阱。

---

## 1. 项目概览

三个独立子系统，部署在不同平台：

| 子系统 | 目录 | 技术栈 | 生产环境 |
|--------|------|--------|----------|
| Backend API | `backend/` | FastAPI + LangGraph + SQLAlchemy + ChromaDB | HF Spaces Docker |
| Admin-SPA | `admin-spa/` | React 19 + TypeScript + Vite + Zustand | Cloudflare Pages |
| Mini-App | `mini-app/` | Vue 3 + uni-app + TypeScript | Cloudflare Pages |

**外部依赖（免费层）：**
- **Supabase** — PostgreSQL（含 pgvector 扩展），存储所有业务数据
- **Upstash** — Redis，缓存和会话
- **DeepSeek API** — LLM 推理

---

## 2. 目录结构

```
gaokao_agents/
├── backend/                  # FastAPI 后端
│   ├── api/routes/           # 路由层（auth, chat, profile, recommendations...）
│   ├── services/             # 业务逻辑层（consult_service, recommendation_service...）
│   ├── agents/               # LangGraph Agent 定义
│   ├── models/               # SQLAlchemy ORM 模型
│   ├── knowledge/            # 知识库索引与检索
│   ├── tenants/              # B2B 多租户（TenantData, 模块开关）
│   ├── analytics/            # 分析看板（画像、洞察）
│   ├── core/                 # 中间件（租户解析、用户认证、模块门控）
│   ├── config.py             # 环境变量配置（pydantic-settings）
│   ├── main.py               # FastAPI app 入口 + lifespan 启动逻辑
│   └── requirements.txt
├── admin-spa/                # B2B 管理后台 SPA
│   ├── src/
│   │   ├── api/client.ts     # Axios 封装 + token 注入
│   │   ├── stores/           # Zustand stores（auth, mobile）
│   │   ├── components/       # 共享组件（BottomSheet, Sidebar...）
│   │   └── pages/            # 页面（Dashboard, Leads, Channels, Profile...）
│   └── package.json
├── mini-app/                 # C 端学生小程序
│   ├── src/
│   │   ├── pages/            # 页面（school, chat, recommendations, profile）
│   │   ├── utils/api.ts      # API 封装（含 SSE fetch）
│   │   └── pages.json        # uni-app 页面配置（tabBar、路由）
│   ├── build.config.js       # 构建时租户配置（TENANT=scnu）
│   └── package.json
├── docker/                   # Docker Compose 部署文件
│   ├── Dockerfile.backend    # 后端镜像（python:3.11-slim）
│   ├── Dockerfile.frontend   # 前端镜像（node:20 build → nginx:1.27 runtime）
│   ├── nginx.conf            # Nginx 反向代理
│   └── static.conf           # SPA 静态文件服务（try_files 回退）
├── hf-space/                 # HuggingFace Space 部署
│   ├── Dockerfile            # 独立于 docker/ 的简化 Dockerfile（单 worker, 端口 7860）
│   └── README.md             # HF 元数据（sdk: docker, 环境变量列表）
├── data/
│   ├── approved/             # 审核后知识库 JSON
│   └── seed/                 # 种子数据（schools.json, scores.json）
├── scripts/                  # 工具脚本（import_scnu_knowledge.py 等）
├── docs/
│   └── ARCHITECTURE.md       # 本文档
├── docker-compose.yml        # 本地/VPS 全栈部署
├── docker-compose.prod.yml   # 生产 overlay（重启策略、日志、资源限制）
└── .github/workflows/        # CI only（无 CD）
    ├── backend-ci.yml        # pytest
    ├── frontend-ci.yml       # npm run build（admin-spa + mini-app）
    └── lint.yml              # ruff + eslint
```

---

## 3. 部署机制：Commit 如何到达生产环境

### 3.1 Cloudflare Pages（前端 — 自动）

**触发方式：** `git push origin feat/admin-redesign-v2`

**机制：**
- Cloudflare Pages 在仪表板中连接到 GitHub 仓库
- 每次推送，CF 自动拉取最新 commit 并执行构建
- 构建成功 → 自动发布到 `.pages.dev` 域名

**两个 CF Pages 项目的构建配置：**

| 项目 | 域名 | 构建命令 | 输出目录 |
|------|------|----------|----------|
| admin-spa | zhaoshengzhinao.pages.dev | `npm run build` | `admin-spa/dist` |
| mini-app | zhaoshengzhinao-mini-app.pages.dev | `TENANT=scnu node build.config.js && npm run build:h5` | `mini-app/dist/build/h5` |

**CF Pages 环境变量：**

| 变量 | 值 |
|------|-----|
| `VITE_API_BASE_URL` | `https://slveo-gaokao-api.hf.space/api/v1` |
| `TENANT` | `scnu` |

**注意：**
- `VITE_*` 环境变量在 `vite build` 时内联到 JS bundle 中，修改后必须 "Retry deployment" 触发完整重建
- CF Pages 的 Git ref 可能缓存旧 commit，怀疑时可对比构建日志中的 HEAD 和本地 `git log`

### 3.2 HuggingFace Spaces（后端 — 手动 Git Push）

**关键：HF Space 有独立的 Git 仓库。推送到 GitHub 不会自动更新 HF Space。**

HF Space 运行的是推送到 `https://huggingface.co/spaces/SlveO/gaokao_api` 的代码。

**部署流程：**

```bash
# 1. Clone HF Space 仓库（首次）
git clone https://huggingface.co/spaces/SlveO/gaokao_api
cd gaokao_api

# 2. 复制最新的后端代码
cp -r /path/to/gaokao_agents/backend/ .
cp -r /path/to/gaokao_agents/hf-space/Dockerfile .
cp -r /path/to/gaokao_agents/hf-space/README.md .
cp -r /path/to/gaokao_agents/data/approved/ ./data/approved/
cp -r /path/to/gaokao_agents/scripts/ ./scripts/

# 3. 提交并推送
git add -A
git commit -m "deploy: update backend with latest fixes"
git push origin main
```

推送后，HF Space 自动检测 → 构建 Docker 镜像 → 运行容器。

**HF Space 环境变量（HF 仪表板 Settings → Repository secrets）：**

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | Supabase PostgreSQL 连接字符串 |
| `REDIS_URL` | Upstash Redis 连接字符串 |
| `JWT_SECRET` | JWT 签名密钥 |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |

**Dockerfile 要点（`hf-space/Dockerfile`）：**
- 基础镜像 `python:3.11-slim`，端口固定 **7860**
- 单 worker（`--workers 1`）防止模型重复加载 → 内存溢出（16 GB 限制）
- keep-alive 300 秒（适配 SSE 长连接）
- 启动自动运行 `alembic upgrade head`

### 3.3 Docker Compose（本地 / VPS — 手动）

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Nginx 路由：`/api/*` → backend:8000，`/admin/*` → admin-spa:80，`/*` → mini-app:80

---

## 4. 关键架构决策

### Backend 启动流程（`backend/main.py` lifespan）

按顺序执行：
1. `init_db()` — 创建所有 SQLAlchemy 表
2. `_ensure_tenant_and_admin()` — 确保 SCNU 租户存在 + 合并模块配置
3. `_auto_import_knowledge()` — TenantData 为空时导入 `data/approved/` 知识 JSON
4. 种子数据 + ChromaDB 索引（仅空数据库）
5. Embedding 模型预热
6. ChromaDB 集合检查 → 空则自动索引

### 多租户中间件栈（`backend/core/middleware.py`）

按顺序：
1. **TenantResolutionMiddleware** — 从 Header `X-Tenant` 解析租户
2. **UserAuthMiddleware** — JWT Bearer token 验证（`/api/v1/auth/` 跳过）
3. **ModuleGateMiddleware** — 检查 `tenant.config.modules` 开关，未启用返回 403

---

## 5. 常见陷阱

### CF Pages

1. **环境变量内联** — `VITE_*` 在构建时写入 bundle，修改后必须 "Retry deployment"
2. **Git ref 缓存** — CF Pages 可能卡在旧 commit，推送新 commit 触发 webhook 才能刷新
3. **CDN 缓存** — 验证：`curl -s <URL> | grep "\.js"` 查看 HTML 引用的 JS 文件名

### HF Spaces

1. **独立 Git 仓库** — `git push origin` 到 GitHub 不更新 HF Space，必须 push 到 HF 仓库
2. **Factory rebuild** — 修改 Dockerfile 后需在 HF 仪表板手动点击
3. **/app/uploads 目录** — CMD 需 `mkdir -p /app/uploads`，否则 StaticFiles mount 崩溃
4. **单 worker** — 多 worker 重复加载 embedding 模型，超出 16 GB 内存限制
5. **端口 7860** — HF Spaces 代理固定要求

### 通用

1. **Alembic 迁移** — 启动自动运行 `alembic upgrade head`，迁移文件必须 commit
2. **知识库数据** — `data/approved/` 随 Dockerfile `COPY` 进镜像

---

## 6. 本地开发

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Admin-SPA
cd admin-spa && npm install
npm run dev          # http://localhost:5173

# Mini-App
cd mini-app && npm install
npm run dev:h5       # http://localhost:5174
```

本地需 `.env` 文件（见 `.env.example`）配置数据库和 API 密钥。

---

## 7. 相关链接

- GitHub 仓库：https://github.com/SlveO/zhaoshengzhinao
- HF Space 仓库：https://huggingface.co/spaces/SlveO/gaokao_api
- Admin-SPA：https://zhaoshengzhinao.pages.dev
- Mini-App：https://zhaoshengzhinao-mini-app.pages.dev
- Backend API：https://slveo-gaokao-api.hf.space
