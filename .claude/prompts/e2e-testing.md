# Session Prompt — 端到端测试与问题修复

> 分支: feat/admin-redesign-v2 | Docker 已运行 | admin-spa 已重建

## 开始前

读取 `.claude/SESSION_STATE.md` 了解完整历史上下文。调用 `deepseek-write` skill（禁止 Write 工具，用 Bash heredoc）。调用 `andrej-karpathy-skills:karpathy-guidelines` skill。

## 当前状态

4 项任务已实现，2 个 Bug 已修复：

| 任务 | 文件 | 状态 |
|------|------|------|
| D-1 本地环境 | startup_seed.py, main.py, models/__init__.py | 已实现，pytest 单独通过 |
| A-2 ChromaDB | docker-compose.yml | 已添加 3 个 volumes |
| D-2 知识库 | KnowledgeSettingsPage.tsx, types/index.ts | 已实现 |
| D-3 品牌Logo | router.py, main.py, BrandSettingsPage.tsx | 已实现 |
| BugFix vite base | vite.config.ts | `base: process.env.VITE_BASE_PATH` |
| BugFix router | App.tsx | `basename="/admin"` |

登录页已通过 Chrome DevTools 验证。访问：
- 管理端: `http://localhost/admin/?tenant=scnu` (admin/admin123)
- 学生端: `http://localhost/`

## 待验证

1. 品牌配置页 — 登录后进入 `/brand`，保存配置、上传 Logo
2. 知识库页 — 进入 `/knowledge`，文件上传、重新索引、文档列表
3. Mini-app 聊天 RAG — 学生端发消息，验证 AI 回复和 RAG 来源
4. `docker compose exec backend pytest backend/tests/unit/ -v` — 检查批量运行报错

## 可用子代理

调用: `Agent({subagent_type: "name", description: "简述", prompt: "指令"})`

| 子代理 | 模型 | 用途 |
|--------|------|------|
| `backend-dev` | opus | 后端开发 |
| `admin-spa-dev` | opus | 管理端开发 |
| `mini-app-dev` | opus | 学生端开发 |
| `test-runner` | opus | 运行测试，过滤噪音 |
| `codebase-scanner` | opus | 代码探索和搜索 |
| `cmd-executor` | haiku | 执行命令，只返回错误 |
| `tool-writer` | sonnet | Write/Edit 回退，只写不读 |
| `code-reviewer` | opus | 代码审查 |

## 核心规则

1. **禁止 Write/Edit 工具** — 用 `cat > file << 'ENDOFFILE'` 写文件
2. **工具调用失败** — Write 连续失败 3 次 → `tool-writer` 子代理（最多 2 次）→ `reports/block.md`
3. **权限阻断** → 记录 `reports/block.md`，不重试
4. **Chrome DevTools MCP 可用** — 用于检查浏览器渲染、控制台错误、网络请求
5. **验证优先** — 每个问题先复现、定位根因，再修复

完成后更新 `.claude/SESSION_STATE.md`。
