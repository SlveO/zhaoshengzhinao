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
