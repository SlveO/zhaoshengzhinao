# 招生智脑部署实施方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将招生智脑全栈应用部署到 Hugging Face Spaces（免费后端）+ Supabase（免费 PostgreSQL）+ Upstash（免费 Redis）+ Cloudflare Pages（免费前端），实现零成本对外可访问的 Demo 环境。

**Architecture:** Hugging Face Spaces Docker 容器运行 FastAPI 后端（16GB RAM / CPU），通过 Supabase pgvector 替代本地 PostgreSQL，Upstash 替代本地 Redis，Cloudflare Pages 托管 admin-spa（已部署）和 mini-app（新部署）两个前端 SPA。

**Tech Stack:** Docker, Python 3.11, FastAPI, Supabase (PostgreSQL + pgvector), Upstash (Redis), Cloudflare Pages, Hugging Face Spaces

---

## 文件变更总览

| 操作 | 文件 | 职责 |
|---|---|---|
| 创建 | `hf-space/Dockerfile` | HF Space 的容器镜像定义 |
| 创建 | `hf-space/README.md` | HF Space 首页说明文档 |
| 修改 | `backend/config.py:4-21` | 增加 `cors_origins` 配置项 |
| 修改 | `backend/main.py:105-117` | CORS origins 改为从配置读取 |
| 修改 | `.env.example` | 增加 Supabase/Upstash/生产环境配置示例 |
| 不改 | `backend/knowledge_base/chroma_client.py` | 已从 `settings.chroma_persist_dir` 读取路径，通过环境变量覆盖 |
| 不改 | `admin-spa/` `mini-app/` | 零代码改动，仅在 Cloudflare Pages 面板配环境变量 |

---

### Task 1: 创建 HF Space Dockerfile

**Files:**
- Create: `hf-space/Dockerfile`

- [ ] **Step 1: 编写 Dockerfile**

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# 系统依赖：build-essential 给 sentence-transformers 编译用
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# HF Spaces 固定端口
EXPOSE 7860

# 模型缓存放 /data 避免重启后重下载
ENV MODELSCOPE_CACHE=/data/model-cache
ENV SENTENCE_TRANSFORMERS_HOME=/data/model-cache

# ChromaDB 向量库持久化
ENV CHROMA_PERSIST_DIR=/data/chroma

# 单 worker 避免多进程重复加载模型撑爆内存
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1", "--timeout-keep-alive", "300"]
```

- [ ] **Step 2: 验证 Dockerfile 语法**

```bash
docker build -f hf-space/Dockerfile -t gaokao-hf-test . 2>&1 | tail -5
```

- [ ] **Step 3: 提交**

```bash
git add hf-space/Dockerfile
git commit -m "feat: add HF Spaces Dockerfile for free deployment"
```

---

### Task 2: 创建 HF Space README

**Files:**
- Create: `hf-space/README.md`

- [ ] **Step 1: 编写 README**

```markdown
---
title: 招生智脑 API
emoji: 🎓
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 招生智脑 · 院校招生管理平台 API

为高校招生办打造的 B2B SaaS 平台后端服务。

## 技术栈

- FastAPI + LangGraph AI 对话引擎
- ChromaDB 向量知识库
- PostgreSQL + pgvector（Supabase）
- Redis（Upstash）

## 环境变量

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL 连接串 |
| `REDIS_URL` | Upstash Redis 连接串 |
| `JWT_SECRET` | JWT 签名密钥 |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `CHROMA_PERSIST_DIR` | ChromaDB 持久化路径（默认 /data/chroma） |

## API 文档

启动后访问 `/docs` 查看 Swagger UI。
```

- [ ] **Step 2: 提交**

```bash
git add hf-space/README.md
git commit -m "docs: add HF Space README"
```

---

### Task 3: 添加 CORS 环境变量配置

**Files:**
- Modify: `backend/config.py:4-21`

**Why:** 当前 CORS origins 硬编码为 localhost，部署后需要接受 HF Space 和 Cloudflare Pages 的域名。

- [ ] **Step 1: 修改 config.py — 增加 cors_origins 字段**

Edit `backend/config.py`，在 `chroma_persist_dir` 行之后新增：

```python
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:3001,http://localhost:3002"
```

完整文件变成：

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gaokao:gaokao@db:5432/gaokao"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    refresh_token_expire_days: int = 7
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-v4-flash"
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    chroma_persist_dir: str = "./chroma_data"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:3001,http://localhost:3002"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 2: 修改 main.py — CORS 改为从配置读取**

Edit `backend/main.py`，将 106-117 行替换为：

```python
# CORS (allow local dev + Cloudflare Pages production origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 3: 验证本地后端仍可启动**

```bash
cd backend && timeout 5 uvicorn main:app --host 127.0.0.1 --port 8000 2>&1 || true
```

预期：服务正常启动，无 import 错误。

- [ ] **Step 4: 提交**

```bash
git add backend/config.py backend/main.py
git commit -m "feat: make CORS origins configurable via env var"
```

---

### Task 4: 更新 .env.example

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: 更新 .env.example**

```bash
DATABASE_URL=postgresql+asyncpg://gaokao:gaokao@db:5432/gaokao
REDIS_URL=redis://redis:6379/0
JWT_SECRET=change-me-in-production
DEEPSEEK_API_KEY=sk-your-key
CHROMA_PERSIST_DIR=./chroma_data

# ── 生产部署（HF Spaces + Supabase + Upstash + Cloudflare Pages）──
# DATABASE_URL=postgresql+asyncpg://postgres:<password>@db.<project>.supabase.co:6543/postgres
# REDIS_URL=redis://default:<password>@<host>.upstash.io:6379
# CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://admin-spa.pages.dev,https://mini-app.pages.dev,https://your-space.hf.space
```

- [ ] **Step 2: 提交**

```bash
git add .env.example
git commit -m "chore: update .env.example with production deployment examples"
```

---

### Task 5: 部署到 Hugging Face Spaces

**说明:** 以下步骤在 hf.co 网站和终端操作。

- [ ] **Step 1: 在 HF 网站创建 Space**

1. 打开 https://huggingface.co/new-space
2. Space Name: `gaokao-api`（或任意名）
3. SDK: **Docker**（不是 Gradio/Streamlit）
4. 选择 **免费 CPU** plan
5. 点击 Create Space

- [ ] **Step 2: Clone Space 仓库并推送代码**

```bash
git clone https://huggingface.co/spaces/<your-username>/gaokao-api
cd gaokao-api
# 复制 hf-space 文件到 Space 根目录
cp ../hf-space/Dockerfile .
cp ../hf-space/README.md .
# 复制 backend 源码（Dockerfile 构建时需要）
cp -r ../backend .
git add -A
git commit -m "initial deploy"
git push
```

HF 会自动开始构建。在 Space Settings → Settings 页面可看到构建日志。

- [ ] **Step 3: 配置 Secrets**

Space 构建完成后，进入 Settings → Secrets，添加：

| Name | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:<pwd>@db.<project>.supabase.co:6543/postgres` |
| `REDIS_URL` | `redis://default:<pwd>@<host>.upstash.io:6379` |
| `JWT_SECRET` | （随机生成，例如 `openssl rand -hex 32`） |
| `DEEPSEEK_API_KEY` | （你的 DeepSeek key） |
| `CHROMA_PERSIST_DIR` | `/data/chroma` |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000,https://admin-spa.pages.dev,https://mini-app.pages.dev,https://<your-username>-gaokao-api.hf.space` |

- [ ] **Step 4: 验证后端健康检查**

```bash
curl https://<your-username>-gaokao-api.hf.space/api/health
```

预期返回：`{"status":"ok"}`

如果 Space 已休眠，等待 2-4 分钟冷启动后重试。

---

### Task 6: 创建 Supabase 项目并初始化数据库

**说明:** 在 supabase.com 网站和本地终端操作。

- [ ] **Step 1: 创建 Supabase 项目**

1. 打开 https://supabase.com → Sign in（GitHub 账号即可）
2. Create New Project → 输入名称 `gaokao` → 记住密码 → Create
3. 等待项目初始化（约 2 分钟）

- [ ] **Step 2: 启用 pgvector 扩展**

进入 Supabase SQL Editor，执行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

- [ ] **Step 3: 本地运行数据库迁移**

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://postgres:<password>@db.<project>.supabase.co:6543/postgres \
  alembic upgrade head
```

需要先 `pip install alembic asyncpg` 如果本地没装。

- [ ] **Step 4: 灌入种子数据**

```bash
DATABASE_URL=postgresql+asyncpg://postgres:<password>@db.<project>.supabase.co:6543/postgres \
  python scripts/seed_db.py
```

- [ ] **Step 5: 验证数据**

Supabase Table Editor 查看 `tenants`、`users`、`documents` 等表是否有数据。

---

### Task 7: 创建 Upstash Redis

**说明:** 在 upstash.com 网站操作。

- [ ] **Step 1: 注册并创建 Redis**

1. 打开 https://upstash.com → Sign in（GitHub 账号）
2. Console → Create Redis → 选择免费层 → Create
3. 记录连接信息：
   - Endpoint: `xxx.upstash.io:6379`
   - Password: `xxx`

- [ ] **Step 2: 验证连接**

```bash
redis-cli -h <endpoint> -p 6379 -a <password> PING
```

预期返回：`PONG`

注意：Upstash 免费层 10,000 条命令/天，演示够用。

---

### Task 8: 配置 Cloudflare Pages 前端

**说明:** 在 Cloudflare Pages 控制台操作。

- [ ] **Step 1: admin-spa — 添加环境变量**

admin-spa 已在 Cloudflare Pages 上部署。进入项目 Settings → Environment variables：

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://<your-username>-gaokao-api.hf.space` |

保存后重新部署一次使变量生效。

- [ ] **Step 2: mini-app — 新建 Pages 项目并部署**

1. Cloudflare Pages → Create a project
2. 连接 Git 仓库（你的 Fork）
3. Build settings:
   - Framework preset: None
   - Build command: `cd mini-app && TENANT=scnu node build.config.js && npm run build:h5`
   - Output directory: `mini-app/dist/build/h5`
4. 环境变量:
   - `VITE_API_BASE_URL` = `https://<your-username>-gaokao-api.hf.space`
   - `VITE_WS_URL` = `wss://<your-username>-gaokao-api.hf.space`
5. Save and Deploy

- [ ] **Step 3: admin-spa 移动端适配版**

等待任务 B（admin-spa 移动端适配）完成后，与桌面版使用同一 Pages 项目，构建命令包含移动端构建即可。具体构建命令届时根据任务 B 的实现确定。

---

### Task 9: 端到端验证

- [ ] **Step 1: 验证管理后台**

```
浏览器打开: https://admin-spa.pages.dev?tenant=scnu
用 admin/admin123 登录
检查: 仪表盘数据加载正常，图表渲染正常
```

- [ ] **Step 2: 验证学生端**

```
浏览器打开: https://mini-app.pages.dev
检查: 聊天界面正常，发送消息能收到 AI 回复
```

- [ ] **Step 3: 验证 WebSocket**

```
打开浏览器 DevTools → Network → WS
发送聊天消息
检查: WebSocket 连接状态为 101 Switching Protocols
```

- [ ] **Step 4: 记录部署信息**

```
Space URL: https://<your-username>-gaokao-api.hf.space
Supabase:  https://supabase.com/dashboard/project/<project>
Upstash:   https://upstash.com/console/<redis-id>
admin-spa: https://admin-spa.pages.dev
mini-app:  https://mini-app.pages.dev
```

---

## 保活说明

HF Spaces 免费层在无请求一段时间后自动休眠，首次唤醒需 2-4 分钟（加载 sentence-transformers 模型）。

**推荐:** 用 [UptimeRobot](https://uptimerobot.com)（免费）每 5 分钟 ping `https://<space>/api/health`，基本可以持续保活。

## 从方案 1 迁移到方案 2

如果后续需要升级到 Hetzner VPS（不休眠、更稳定）：

1. 购买 Hetzner CX22（€3.99/月），Ubuntu 22.04
2. 安装 Docker + cloudflared tunnel
3. `git clone` → `docker compose up -d`
4. pg_dump from Supabase → pg_restore to VPS PostgreSQL
5. 改 Cloudflare Pages 的 `VITE_API_BASE_URL` 指向 VPS 域名
6. 约 30 分钟完成，服务无中断
