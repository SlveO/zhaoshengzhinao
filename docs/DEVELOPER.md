# Developer Onboarding Guide

> 面向新加入的协作者。说明环境搭建、分支规范、CI 流程和常见坑。

## 环境要求

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose v2
- Git

## 快速开始

```bash
# 1. Clone
git clone https://github.com/SlveO/zhaoshengzhinao.git
cd zhaoshengzhinao

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写必需的密钥：
#   JWT_SECRET=<随机字符串>
#   DEEPSEEK_API_KEY=sk-...
#   DATABASE_URL=postgresql+asyncpg://...
#   REDIS_URL=redis://...

# 3. 启动基础设施
docker compose up -d db redis

# 4. 启动后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 5. 启动 Admin-SPA（新终端）
cd admin-spa
npm install
npm run dev -- --port 3001
# → http://localhost:3001?tenant=scnu

# 6. 启动 Mini-App（新终端）
cd mini-app
npm install
TENANT=scnu node build.config.js
npm run dev:h5 -- --port 3002
# → http://localhost:3002
```

## 租户概念

本项目是 B2B 多租户 SaaS。当前只有一个租户 **SCNU**（华南师范大学）。

- **Admin API**：通过 HTTP Header `X-Tenant: scnu` 识别租户。浏览器访问 Admin-SPA 时在 URL 加 `?tenant=scnu`
- **Mini-App API**：请求体中传 `tenant_slug: "scnu"`
- **租户数据隔离**：每个租户有独立的 ChromaDB collection（`{tenant_slug}_colleges`）和 DB 数据行

### 测试账号

| 角色 | 用户名 | 密码 | 入口 |
|------|--------|------|------|
| 管理员 | `admin` | `admin123` | `http://localhost:3001?tenant=scnu` |
| 学生（游客） | 无需登录 | — | `http://localhost:3002` |

## 分支规范

- `main` — 生产分支，保持可部署状态
- `feat/*` — 功能分支，从 `main` 切出
- `fix/*` — 修复分支

PR 需要 CI（backend-ci, frontend-ci, lint）全部通过才能合并。

## CI / CD

| 流水线 | 触发 | 内容 |
|--------|------|------|
| `backend-ci.yml` | push/PR 到 `main`/`feat/**` | pytest |
| `frontend-ci.yml` | push/PR 到 `main`/`feat/**` | `npm run build` (admin-spa + mini-app) |
| `lint.yml` | push/PR 到 `main`/`feat/**` | ruff (Python) + eslint (TypeScript) |

**部署机制**：见 `docs/ARCHITECTURE.md` 第 3 节。

## 开发命令速查

```bash
# 后端测试
pytest backend/tests/ -v --tb=short

# 后端 lint
ruff check backend/

# 前端 lint
cd admin-spa && npx eslint .

# 数据库迁移
cd backend && alembic upgrade head

# 种子数据
python scripts/seed_db.py
```

## 常见坑

1. **端口冲突**：Admin-SPA 和 Mini-App 会同时运行，必须分别指定不同的端口（3001 和 3002），否则 Vite 默认都用 5173 会冲突
2. **HF Spaces 部署**：后端有独立的 HF Git 仓库。推送到 GitHub 不会自动更新 HF Space。详见 `docs/ARCHITECTURE.md` 3.2 节
3. **CF Pages 环境变量**：`VITE_*` 变量在构建时内联。修改 CF Pages 环境变量后必须 "Retry deployment"
4. **SSE 缓冲**：HF Spaces 代理会缓冲 SSE 流。Mini-app 聊天有 8 秒超时后自动切换为轮询模式
5. **DeepSeek 模型**：Write/Edit 工具在 DeepSeek 模型上不稳定，使用 Bash heredoc 创建文件
6. **租户不匹配**：API 返回 403 时检查 `X-Tenant` header 或 `?tenant=` query param
7. **ChromaDB 冷启动**：首次启动时 embedding 模型需要下载，可能耗时几分钟

## 相关文档

| 文档 | 内容 |
|------|------|
| `docs/ARCHITECTURE.md` | 技术架构、部署机制、常见陷阱 |
| `docs/DEPLOYMENT.md` | Docker Compose 部署步骤 |
| `docs/OPERATIONS.md` | 运维手册（备份、索引重建、日志） |
| `CLAUDE.md` | Claude Code 专用项目指引 |
| `.claude/rules/` | 子模块详细规范（agent 开发时参考） |
