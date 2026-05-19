# Session: QA 审阅与测试

> 分支: `feat/qa-review` | 基于: `develop` | **只读为主，修复为辅**

## 启动

```bash
git checkout develop && git checkout -b feat/qa-review
docker compose up -d db redis
cd backend && uvicorn main:app --host 127.0.0.1 --port 8000 --log-level error &
cd admin-spa && npm run dev -- --port 3001 &
cd mini-app && TENANT=scnu node build.config.js && npm run dev:h5 -- --port 3002 &
```

## 必读文档

| 顺序 | 文件 |
|------|------|
| 1 | `docs/superpowers/specs/2026-05-19-qa-review.md` — 测试清单（本文档） |
| 2 | `docs/PROJECT_MILESTONE.md` — 系统架构 + 数据现状 |
| 3 | `COLLABORATION.md` — 分支策略 |
| 4 | `SESSION_STATE.md` — 当前所有轨道状态 |

## 工作流程

### Phase 1: 自动验证 (10 min)

运行所有自动构建和单元测试，确认基线。

```bash
# 1. Admin SPA TypeScript 编译
cd admin-spa && npm run build

# 2. Mini-App H5 构建
cd mini-app && TENANT=scnu node build.config.js && npm run build:h5

# 3. 后端核心测试（35 个应全绿）
cd backend
pytest tests/unit/test_guard.py test_b2b_prompt.py test_module_registry.py test_evidence_accumulator.py -v

# 4. 后端全量测试（22 个预存失败可忽略）
pytest tests/unit/ -v --tb=line 2>&1 | tail -20
```

**判定标准**: 构建全过，35 核心测试全绿。

### Phase 2: API 端点遍历 (15 min)

用 Swagger UI (`http://127.0.0.1:8000/docs`) 或 curl 遍历 [QA 文档 §3.1](#) 的 39 个端点。

关键验证：
- `GET /compare/recommendations` 返回 tenant 列表 + 匹配分（非 404/403）
- `GET /admin/analytics/topic-cloud` 返回词频数据（非空）
- `GET /admin/ai-persona` 返回 `{}`（默认无自定义）
- `GET /admin/knowledge/documents` 返回 1997 条 SCNU 文档
- `WS /chat/session/{id}?tenant=scnu` WebSocket 连接成功

### Phase 3: 浏览器端到端 (20 min)

用 Playwright 或手动浏览器执行 [QA 文档 §3.2](#) 的检查清单。

**管理端核心路径**:
1. 打开 `http://localhost:3001?tenant=scnu`
2. 登录 admin/admin123
3. 依次浏览 6 个页面：漏斗 → 画像 → 品牌 → 知识库 → 增强分析 → AI 设置
4. 在品牌页面改颜色 → 侧边栏实时更新
5. 在 AI 设置页面编辑提示词 → 保存 → 刷新 → 仍存在

**学生端核心路径**:
1. 打开 `http://localhost:3002`
2. 发送快捷问题 → AI 回复
3. 输入"分数线" → temp 0.3 精确回复
4. 输入"我喜欢动手" → temp 0.7 引导回复
5. 画像 L2+ 后点"对比" → 跨院校卡片
6. 连续发 21+ 条 → 被 MessageLimitGuard 拦截
7. 输入单字"好" → 被 ContentLengthGuard 跳过

### Phase 4: 问题记录与修复

发现的问题按严重度分级记录：

| 严重度 | 标准 | 动作 |
|--------|------|------|
| 🔴 阻断 | 核心流程不可用 | **立即修复** |
| 🟡 功能 | 功能存在但行为不对 | 记录 + 视情况修复 |
| 🟢 体验 | UI 瑕疵、性能等 | 记录到 issue |

**修复原则**: 只改必要行，不加新功能。提交信息写 `fix: <问题描述>`。

## 不碰

- 不重构现有代码
- 不加新功能
- 不改 agent 提示词逻辑（除非有 bug）
- 不改数据库 schema

## 完成标志

- [ ] 构建全过（admin-spa + mini-app）
- [ ] 35 核心测试全绿
- [ ] 管理端 6 页面可访问
- [ ] 学生端对话可用
- [ ] 跨院校对比有数据
- [ ] 所有发现的问题已记录在 `SESSION_QA_REVIEW.md` 末尾（或修复并提交）
- [ ] 最终 commit message: `chore: QA review complete — N issues found, M fixed`
