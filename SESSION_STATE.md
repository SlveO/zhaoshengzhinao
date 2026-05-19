# Session 状态跟踪

> 高频更新。每个 session 开始和结束时更新自己的轨道状态。

---

## 全局状态

| 里程碑 | 目标日期 | 状态 |
|--------|---------|------|
| Phase 0 完成：核心引擎稳定 | Week 2 | ✅ 已完成 |
| Phase 1 完成：多租户地基 | Week 5 | ✅ 已完成 |
| Phase 2 完成：外壳重建 | Week 9 | ✅ 已完成 |
| Phase 3 完成：增值模块 | Week 13 | ✅ 已完成 |
| Phase 4 完成：调试修复 + 单院校数据 | 当前 | ✅ 已完成 |
| Phase 5 完成：多院校数据扩展 | 待定 | ⬜ 未开始 |
| Phase 6 完成：压测 + 部署准备 | 待定 | ⬜ 未开始 |

---

## 轨道状态

| 轨道 | 分支 | 状态 | 核心产出 |
|------|------|------|---------|
| Foundation | `feat/foundation` | ✅ 已完成 | 多租户框架、中间件、事件系统、guest 对话、18 单元测试 |
| Admin SPA | `feat/admin-spa` | ✅ 已完成 | 管理端 5 页面 + CSS 换肤 + ECharts |
| Mini-App | `feat/mini-app` | ✅ 已完成 | 小程序 29 文件 + 白标构建 + build 通过 |
| Analytics | `feat/analytics` | ✅ 已完成 | 7 个真实 SQL 聚合模块 |
| Data Onboarding | `feat/data-onboarding` | ✅ 已完成 | Excel 导入 + 校验 + 模板 + 知识库 API |
| SCNU Scraper | `feat/data-scnu-scraper` | ✅ 已完成 | 华师 1,567 录取 + 86 培养 + 344 就业 |
| SCNU Import | `feat/data-scnu-import` | ✅ 已完成 | 华师 tenant + 1,997 条数据全量导入 |
| Bug Fixes | `develop` | ✅ 已完成 | 4 根因修复（WS/API/CORS/BaseHTTPMiddleware） |
| Compare Page | `feat/compare-page` | ✅ 已完成 | V2 session | 跨院校对比 API + 页面 |
| Dual Agent | `feat/dual-agent` | ✅ 已完成 | V2 session | 双 agent 智能路由 (15行) |
| Enhanced Analytics | `feat/enhanced-analytics` | ✅ 已完成 | V2 session | 词云+情绪+热点 + InsightsPage |
| Custom Agent | `feat/custom-agent` | ✅ 已完成 | V2 session | Persona CRUD + AgentSettingsPage |

状态: ⬜ 未开始 | 🔵 进行中 | ✅ 已完成 | 🔴 阻塞 | ⏸️ 暂停

---

## 阻塞队列

| 阻塞方 | 等待 | 提供方 | 创建时间 | 解决时间 |
|--------|------|--------|---------|---------|
| — | — | — | — | — |

---

## 当前可运行服务

| 服务 | 端口 | 启动命令 |
|------|------|---------|
| 后端 API | 8000 | `cd backend && uvicorn main:app --host 127.0.0.1 --port 8000` |
| Admin SPA | 3001 | `cd admin-spa && npm run dev -- --port 3001` |
| Mini-App H5 | 3002 | `cd mini-app && TENANT=scnu node build.config.js && npm run dev:h5 -- --port 3002` |
| PostgreSQL | 5432 | `docker compose up -d db` |
| Redis | 6379 | `docker compose up -d redis` |

**演示账号**：admin / admin123（华南师大，X-Tenant: scnu）
