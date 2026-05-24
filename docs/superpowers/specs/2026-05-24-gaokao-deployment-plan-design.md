# 招生智脑部署方案 Spec

**日期:** 2026-05-24
**方案:** Hugging Face Spaces + Supabase + Upstash + Cloudflare Pages（完全免费）
**后备方案:** Hetzner VPS Docker Compose（~$4/月）

---

## 架构

```
用户浏览器
    │
    ▼
Cloudflare Pages（admin-spa + mini-app + admin-mobile）
    │  API 请求 → https://your-space.hf.space
    ▼
Hugging Face Spaces（FastAPI Docker，16GB RAM CPU）
    ├── LangChain + LangGraph AI 引擎
    ├── ChromaDB（持久化到 /data/chroma）
    ├── sentence-transformers（CPU 推理）
    │
    ├── HTTP → Supabase（PostgreSQL + pgvector，500MB 免费）
    └── HTTP → Upstash（Redis，10K cmd/天 免费）
```

## 费用

| 组件 | 服务商 | 费用 |
|---|---|---|
| 后端 FastAPI | Hugging Face Spaces | $0 |
| PostgreSQL + pgvector | Supabase | $0 |
| Redis | Upstash | $0 |
| 前端托管 | Cloudflare Pages | $0 |
| **合计** | | **$0.00/月** |

## 新增文件

```
新增：
├── hf-space/
│   ├── Dockerfile          # HF 专用 Docker 镜像
│   └── README.md           # Space 首页说明（中文）

修改：
├── .env.example            # 增加 SUPABASE/UPSTASH 示例
├── backend/
│   ├── core/config.py      # 确认 DATABASE_URL / REDIS_URL 从环境变量读取
│   ├── services/           # ChromaDB persist_directory → /data/chroma
│   └── main.py             # host 0.0.0.0, port 7860
```

## 部署步骤

### 1. HF Space — 后端

**Dockerfile** (`hf-space/Dockerfile`):

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 7860

ENV MODELSCOPE_CACHE=/data/model-cache
ENV SENTENCE_TRANSFORMERS_HOME=/data/model-cache

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

**操作:**
- hf.co → New Space → 选 Docker → 创建
- git clone Space 仓库到本地
- 把 hf-space 和 backend 文件 push 上去 → 自动构建
- Space Settings → Secrets 配置环境变量

**环境变量:**
```
DATABASE_URL=postgresql+asyncpg://postgres:<pwd>@db.<project>.supabase.co:6543/postgres
REDIS_URL=redis://default:<pwd>@<host>.upstash.io:6379
JWT_SECRET=<随机生成>
DEEPSEEK_API_KEY=<你的 key>
```

**代码适配点:**
- ChromaDB `persist_directory` 指向 `/data/chroma`（HF 唯一持久化目录）
- `main.py` 端口改为 7860（HF 固定端口），host 0.0.0.0
- 所有配置从环境变量读取（确认 config.py 已支持）

### 2. Supabase — PostgreSQL + pgvector

- supabase.com 注册 → Create Project
- SQL Editor 执行: `CREATE EXTENSION IF NOT EXISTS vector;`
- 本地连接 Supabase 跑迁移:
```bash
DATABASE_URL=postgresql+asyncpg://postgres:<pwd>@db.<project>.supabase.co:6543/postgres \
  alembic upgrade head
```
- 灌种子数据:
```bash
DATABASE_URL=... python scripts/seed_db.py
```

### 3. Upstash — Redis

- upstash.com 注册 → Create Redis → 复制 REST URL
- 免费层限制: 10,000 命令/天，演示够用

### 4. Cloudflare Pages — 前端

| 站点 | 状态 | 操作 |
|---|---|---|
| admin-spa（院校端） | 已部署 | 添加环境变量 `VITE_API_BASE_URL=https://xxx.hf.space` |
| admin-spa 移动端适配 | 待任务 B 完成 | 完成后同一仓库构建部署 |
| mini-app（学生端） | 待部署 | 新建 Pages 项目，`npm run build:h5`，输出 `dist/` |

## 保活策略

HF Spaces 免费层空闲后会休眠，首次访问冷启动 2-4 分钟（ML 模型加载）。

缓解方式: 用 [UptimeRobot](https://uptimerobot.com)（免费）每 5 分钟 ping 一次 Space URL。

## 方案 2 迁移路径

如果后续升级到 Hetzner VPS:

1. 买 Hetzner CX22（€3.99/月），装 Ubuntu + Docker
2. `git clone` 仓库 → `docker compose up -d`
3. `pg_dump` 从 Supabase 导出 → 导入 VPS PostgreSQL
4. hf-space/Dockerfile 直接用作 backend 容器
5. Cloudflare Pages 改 `VITE_API_BASE_URL` 指向新域名
6. 30 分钟内完成迁移

## 风险

| 风险 | 缓解 |
|---|---|
| 冷启动 2-4 分钟 | UptimeRobot 保活；或接受首次慢 |
| CPU 推理比 GPU 慢 | 演示场景可接受 |
| Supabase 免费层限制 | 每 90 天确认账户活动即可，数据库不删 |
| WebSocket 兼容性 | HF Spaces 支持 WebSocket 代理 |
| Docker 镜像过大（>2GB） | HF 免费构建可能超时；本地 build + push |

---

*记录于 2026-05-24，部署方案 1 执行中。*
