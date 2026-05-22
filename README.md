# 招生智脑 · 院校招生管理平台

为高校招生办打造的 B2B SaaS 平台 —— AI 招生顾问替代人工答询，自动画像 + 院校匹配 + 数据分析。

## 架构

```
┌─────────────────┐  ┌─────────────────┐
│   admin-spa      │  │   mini-app       │
│   React + TS     │  │   uni-app H5     │
│   管理后台 :3001  │  │   学生端 :3002    │
└────────┬────────┘  └────────┬────────┘
         │                    │
         └──────────┬─────────┘
                    │ REST + WebSocket
              ┌─────┴─────┐
              │  backend   │
              │  FastAPI   │
              │  :8000     │
              └─────┬─────┘
                    │
         ┌──────────┼──────────┐
         │          │          │
    PostgreSQL  ChromaDB   Redis
```

## 快速启动

```bash
# 1. 基础设施
docker compose up -d db redis

# 2. 后端
cd backend
cp ../.env.example .env    # 填写 OPENAI_API_KEY
uvicorn main:app --host 127.0.0.1 --port 8000

# 3. 管理后台
cd admin-spa
npm install && npm run dev -- --port 3001

# 4. 小程序 (学生端)
cd mini-app
npm install
TENANT=scnu node build.config.js && npm run dev:h5 -- --port 3002
```

访问：管理后台 `http://localhost:3001?tenant=scnu`（演示账号 admin/admin123），学生端 `http://localhost:3002`

## 技术栈

| 子系统 | 语言/框架 | 数据库 | 端口 |
|--------|----------|--------|------|
| backend | Python 3.11 / FastAPI / LangGraph | PostgreSQL + ChromaDB + Redis | 8000 |
| admin-spa | TypeScript / React 19 / Vite / ECharts | — | 3001 |
| mini-app | Vue 3 / uni-app / WebSocket | — | 3002 |

## 目录结构

```
├── backend/            # FastAPI 后端
│   ├── api/routes/     # REST + WebSocket 端点（39 个路由）
│   ├── agents/         # LangGraph 对话引擎 + B2B Prompt
│   ├── analytics/      # SQL 聚合分析模块（漏斗/画像/词云/情绪）
│   ├── core/           # 中间件/Guard/Event/ModuleRegistry
│   ├── knowledge_base/ # ChromaDB 向量知识库
│   ├── migrations/     # Alembic 数据库迁移
│   ├── models/         # SQLAlchemy 模型
│   ├── schemas/        # Pydantic 请求/响应模式
│   ├── services/       # 业务逻辑层
│   ├── tenants/        # 多租户模型 + 中间件
│   ├── data/           # 种子数据 fixtures
│   ├── data_pipeline/  # 数据导入管道
│   └── tests/          # pytest 测试套件
├── admin-spa/src/
│   ├── pages/          # 10 个管理页面
│   ├── components/     # 共享组件（Sidebar/StatusCard/Modal）
│   ├── api/            # Axios 客户端（自动注入 X-Tenant）
│   ├── stores/         # Zustand 状态管理
│   └── hooks/          # 品牌配置 hook
├── mini-app/src/
│   ├── pages/          # 聊天/对比/画像页
│   ├── stores/         # Pinia 状态管理
│   ├── utils/          # WebSocket 客户端
│   └── components/     # Vue 组件
├── scrapers/           # 数据爬虫（7 个数据源）
├── scripts/            # 运维脚本（种子数据/索引/导入/测试）
├── data/approved/      # 已审核数据（14 MB）
├── docker/             # Docker 部署配置
├── docs/               # 技术文档 + 设计规范
├── CONVENTIONS.md      # 代码规范 + 完整 API 契约
└── COLLABORATION.md    # 分支策略 + 并行开发轨道
```

## 团队分工

| 角色 | 负责 | 目录 |
|------|------|------|
| **A: 后端核心** | API 开发、Agent 对话引擎、Analytics、Guard、租户系统、DB 迁移 | `backend/` |
| **B: 管理后台** | 管理端 10 页面开发、图表、品牌换肤、ECharts | `admin-spa/` |
| **C: 小程序** | 学生对话端、跨院校对比、WebSocket 连接、Vue 组件 | `mini-app/` |
| **D: 数据+基础设施** | 爬虫、数据导入/清洗/索引、Docker、CI/CD、测试、文档 | `scrapers/` `scripts/` `docker/` `data/` `docs/` |

### 协作方式

1. **API 先行** ：A 在 `CONVENTIONS.md` 写好接口契约 → B、C 按契约开发前端，无需等后端完成
2. **分支隔离** ：每人从 `develop` 开出 `feat/<name>` 分支，通过 PR 合并
3. **每日站会** ：同步阻塞项，更新 `COLLABORATION.md`
4. **共享数据** ：全部使用 `scnu` 租户数据，`scripts/seed_db.py` 重建测试数据

## Git 协作流程（Fork 模式）

每个团队成员在 GitHub 上 Fork 主仓库到自己的账号，在自己的 Fork 中开发，通过 PR 合并到主仓库。

### 初始设置（每人执行一次）

```bash
# 1. 在 GitHub 网页上点击 Fork 按钮，Fork 到自己的账号

# 2. Clone 自己的 Fork 到本地
git clone git@github.com:<你的用户名>/zhaoshengzhinao.git
cd zhaoshengzhinao

# 3. 添加主仓库为 upstream，用于同步最新代码
git remote add upstream https://github.com/SlveO/zhaoshengzhinao.git

# 4. 验证远程仓库配置
git remote -v
# origin    git@github.com:<你的用户名>/zhaoshengzhinao.git (fetch)
# origin    git@github.com:<你的用户名>/zhaoshengzhinao.git (push)
# upstream  https://github.com/SlveO/zhaoshengzhinao.git (fetch)
# upstream  https://github.com/SlveO/zhaoshengzhinao.git (push)
```

### 日常开发流程

```bash
# 1. 同步主仓库最新代码
git checkout develop
git fetch upstream
git merge upstream/develop

# 2. 创建功能分支
git checkout -b feat/<your-feature>

# 3. 开发 + 提交
git add <具体文件>
git commit -m "feat: <简短描述>"

# 4. 推送功能分支到自己的 Fork
git push -u origin feat/<your-feature>

# 5. 在 GitHub 网页上创建 Pull Request
#    base repository: SlveO/zhaoshengzhinao  base: develop
#    head repository: <你的用户名>/zhaoshengzhinao  compare: feat/<your-feature>

# 6. 等待 Code Review，通过后合并
```

### 分支策略

```
upstream/main ← upstream/develop ← PR ← origin/feat/*
                   ↑ 保护分支            ↑ 你的功能分支
```

### Commit 规范

```
feat:    新功能
fix:     Bug 修复
refactor: 重构
chore:   构建/工具/依赖
docs:    文档
```

详细规范见 `COLLABORATION.md`。

## API 概览

全部 39 个端点见 `CONVENTIONS.md`。核心端点：

| 端点 | 用途 | 角色 |
|------|------|------|
| `POST /auth/login` | 管理端登录 | B |
| `GET /admin/analytics/funnel` | 招生漏斗 | B |
| `GET /admin/analytics/profile-dashboard` | 画像看板 | B |
| `GET /admin/analytics/topic-cloud` | 关键词词云 | B |
| `GET /admin/brand-config` | 品牌配置 | B |
| `GET /admin/ai-persona` | AI 提示词设置 | B |
| `GET /admin/knowledge/documents` | 知识库文档 | B |
| `WS /chat/session/{id}?tenant=scnu` | 学生对话 | C |
| `GET /compare/recommendations` | 跨院校对比 | C |
| `POST /admin/knowledge/documents` | 文档上传 | D |

## 环境变量

```bash
# .env（从 .env.example 复制）
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/gaokao
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-xxx
SECRET_KEY=your-jwt-secret
```

## 部署

```bash
docker compose up -d db redis
docker build -f docker/Dockerfile.backend -t gaokao-backend .
docker build -f docker/Dockerfile.frontend -t gaokao-admin-spa .
docker compose up -d
```
