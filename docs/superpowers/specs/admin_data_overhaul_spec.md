# 招生智脑管理后台数据大整修 Spec

> 状态：Draft，待用户 review
> 创建日期：2026-06-27
> 涉及子系统：admin-spa、backend、mini-app

## 一、概述

### 1.1 目标

完成 4 个相互独立但有序的子项目，解决管理后台当前的数据混乱、可视化不当、数据链路未验证、缺乏 DB 管理工具等问题。

### 1.2 子项目与执行顺序

| 顺序 | 子项目 | 目标 |
|---|---|---|
| 1 | 清理所有 mock 数据 | 删除 inline mock、mock 文件、mock 兜底逻辑 |
| 4 | 构建 DB 可视化管理面板 | admin-spa 新增 `/db` 路由，仅开发者可见，可读写 10 张表 + 知识库 raw |
| 2 | 规范所有数据呈现 | 重设计/删除/合并多个页面，统一字段、修复假数据、改进可视化 |
| 3 | 端到端数据链路测试 | 10 个环节 × 真人 1 场景 + Seed 8-12 场景 × 逐环节验收点 |

执行顺序：**1 → 4 → 2 → 3**（先清理、再建管理工具、再规范呈现、最后端到端验证）

### 1.3 当前管理后台页面清单

| 路由 | 页面 | 处置 |
|---|---|---|
| /dashboard | 工作台 | 子项目 2：重设计 |
| /leads | 线索管理 | 子项目 2：删除（合并入咨询工作台） |
| /consultations | 咨询管理 | 子项目 2：合并为咨询工作台 |
| /profile | 画像看板 | 子项目 2：修假数据 + 雷达图改 Top 3 卡片 |
| /insights | 洞察分析 | 子项目 2：删情绪时间线 + 移除 mock 兜底 |
| /reports | 招生报告 | 子项目 2：下线 |
| /channels | 渠道管理 | 子项目 2：删除 |
| /knowledge | 知识库 | 子项目 2：移除 mock 兜底 |
| /brand | 品牌配置 | 子项目 2：删除页面 |
| /agent-settings | Agent 设置 | 不动 |
| /modules | 模块管理 | 子项目 2：删除页面 + 后端取消模块门控 |
| /distribution/tasks | 文件分发 | 子项目 2：隐藏入口（不修改代码） |
| /distribution/channels | 分发渠道 | 子项目 2：隐藏入口（不修改代码） |
| /distribution/logs | 分发日志 | 子项目 2：隐藏入口（不修改代码） |
| /db | DB 可视化（新） | 子项目 4：新增 |

---

## 二、子项目 1：清理所有 mock 数据

### 2.1 inline mock 清单（删除）

| 文件 | inline 变量 | 处置 |
|---|---|---|
| `admin-spa/src/pages/DashboardPage.tsx` | `MOCK` 对象 | 子项目 2 重设计时整体替换，本子项目仅删除 MOCK 常量定义 |
| `admin-spa/src/pages/ChannelsPage.tsx` | `MOCK_CHANNELS` | 整个文件在子项目 2 中删除，本子项目不单独处理 |
| `admin-spa/src/pages/ConsultationsPage.tsx` | `MOCK_SESSIONS` | 子项目 2 合并重写时整体替换 |
| `admin-spa/src/pages/LeadWorkbenchPage.tsx` | `MOCK_LEADS` | 子项目 2 删除整个文件 |
| `admin-spa/src/pages/ReportsPage.tsx` | `REPORT_DATA` | 子项目 2 下线该页时整体删除 |

### 2.2 mock 文件清单（删除）

| 文件 | 被引用位置 |
|---|---|
| `admin-spa/src/mock/profileDashboard.ts` | ProfileDashboardPage.tsx |
| `admin-spa/src/mock/insights.ts` | InsightsPage.tsx |
| `admin-spa/src/mock/knowledgeBase.ts` | KnowledgeSettingsPage.tsx |
| `admin-spa/src/mock/distribution.ts` | DistributionTasksPage.tsx / DistributionChannelsPage.tsx / DistributionLogsPage.tsx（注：distribution 模块整体隐藏，mock 文件保留不删） |

删除上述 3 个 mock 文件（distribution.ts 保留，因 distribution 模块整体隐藏不修改），并清理 `admin-spa/src/mock/` 目录（如目录变空则删除目录）。

### 2.3 mock 兜底逻辑清理清单

每个文件的 `.catch()` 块中移除 `setXxx(mockXxx)` 调用，保留 `setError(...)` 即可。前端组件已有 error 状态显示。

| 文件 | 行号 | 修改 |
|---|---|---|
| `ProfileDashboardPage.tsx` | ~25-29 | 移除 `setData(mockProfileDashboard)` |
| `InsightsPage.tsx` | ~42-53 | 移除 `setTopicCloud(mockTopicCloud)` / `setHotQuestions(mockHotQuestions)` / `setEmotionTimeline(mockEmotionTimeline(days))`，删除 `mockEmotionTimeline` 相关引用 |
| `KnowledgeSettingsPage.tsx` | ~32 | 移除 `setDocs(mockDocuments)` |

> 注：Distribution 3 页（Tasks/Channels/Logs）不做任何修改，模块整体隐藏入口（见 4.8 节）。

### 2.4 验收标准

- [ ] `admin-spa/src/mock/` 目录及其下 profileDashboard.ts / insights.ts / knowledgeBase.ts 被删除（distribution.ts 保留）
- [ ] 全项目 `grep -r "from '../mock/" admin-spa/src/` 无结果
- [ ] 全项目 `grep -r "mock[A-Z]" admin-spa/src/` 无结果（除了变量名中包含 mock 的非 mock 用途）
- [ ] admin-spa 能正常 `npm run build` 无 TypeScript 报错
- [ ] 所有页面的 `.catch()` 块不再引用任何 mock 数据
- [ ] 6 个页面的 error 状态正常显示（断开后端时显示错误提示而非假数据）

---

## 三、子项目 4：构建 DB 可视化管理面板

### 3.1 技术栈

| 维度 | 选择 | 说明 |
|---|---|---|
| 前端位置 | admin-spa 内新增 `/db` 路由 | 复用现有 React 19 + Vite + Zustand |
| CRUD 框架 | Refine（`@refinedev/core` + `@refinedev/simple-rest` + `@refinedev/antd` 或 `@refinedev/mui`） | 开箱即用 CRUD |
| 后端 | FastAPI 新增 `/api/v1/admin/db/*` 端点 | 仅 `is_developer=True` 用户可访问 |
| 鉴权 | 开发者账号识别（环境变量 `DEV_ADMIN_USERNAME` + JWT claim） | 登录时识别开发者账号，JWT 带 `is_developer`，前端据此显示侧边栏入口，后端据此校验权限 |
| JSON 编辑器 | `@monaco-editor/react` | 知识库 raw 数据在线编辑 |

### 3.2 数据库字段变更

#### `users` 表新增字段

`users` 表已有 `region`（省份）、`subjects`（选科）、`score`（分数）字段，仅新增 `rank`（位次）：

```sql
ALTER TABLE users
  ADD COLUMN rank INTEGER;

COMMENT ON COLUMN users.rank IS '高考位次（全省排名）';
```

> 注：不新增 `is_developer` 字段。DB 面板访问权限通过"开发者账号识别"实现（见 3.2.1）。

#### 3.2.1 开发者账号识别（无 DB 字段）

通过后端环境变量配置开发者用户名，登录时识别：

```env
# backend/.env
DEV_ADMIN_USERNAME=admin
```

**登录流程**（`backend/services/auth_service.py` 的 `authenticate_user`）：
- 验证账密通过后，检查 `username == settings.DEV_ADMIN_USERNAME`
- 若匹配，返回的 `info` dict 中带 `is_developer: True`
- `TokenResponse` 透传该字段

**JWT payload**：`generate_tokens()` 在 payload 中加入 `is_developer` claim（bool），后端 `/api/v1/admin/db/*` 通过解析 JWT 校验权限，无需查库。

**前端**：`authStore` 存储 `is_developer`，侧边栏据此显示 `/db` 入口。

**默认开发者账号**：现有 `admin` 账户即开发者，无需额外迁移数据。

### 3.3 面板结构

`/db` 路由下 3 个 Tab：

#### Tab 1: PostgreSQL 表管理

左侧表列表，右侧 Refine 自动生成的 CRUD 表格。

**可写范围矩阵**：

| 表名 | 读 | 写 | 删 | 写范围限制 |
|---|---|---|---|---|
| users | ✅ | ✅ | ❌ | 全字段 |
| user_profiles | ✅ | ✅ | ❌ | 全字段 |
| consult_sessions | ✅ | ✅ | ❌ | 仅 follow_status / follow_note / followed_at / followed_by |
| chat_messages | ✅ | ❌ | ✅ | 仅可删除 |
| recommendations | ✅ | ❌ | ✅ | 仅可删除 |
| recommendation_feedback | ✅ | ❌ | ✅ | 仅可删除 |
| admission_data | ✅ | ✅ | ✅ | 全字段（知识库） |
| colleges | ✅ | ✅ | ✅ | 全字段（知识库） |
| major_industry_mapping | ✅ | ✅ | ✅ | 全字段（知识库） |
| industry_analysis | ✅ | ✅ | ✅ | 全字段（知识库） |

#### Tab 2: 知识库 raw 数据

- **列表**：调用 `GET /admin/knowledge/documents` 显示所有 JSON 文档（标题/类型/年份/索引状态/索引时间）
- **详情编辑**：点击文档 → 抽屉显示 JSON 原文（Monaco Editor 在线编辑）
- **操作**：
  - 编辑 JSON → `PUT /admin/knowledge/documents/{id}` 保存 → 自动触发 ChromaDB 重新索引
  - 删除 JSON → `DELETE /admin/knowledge/documents/{id}`
  - 上传新 JSON → `POST /admin/knowledge/documents`
- **ChromaDB 状态**：显示每个 collection 的文档数、向量维度、最后索引时间

#### Tab 3: 表结构查看

只读视图，展示每张表的字段定义（name/type/nullable/default/comment），由后端从 `information_schema.columns` 查询。

### 3.4 后端新增 API

| Method | Path | 用途 | 鉴权 |
|---|---|---|---|
| GET | `/api/v1/admin/db/tables` | 列出所有可管理表 + 字段定义 | is_developer |
| GET | `/api/v1/admin/db/{table}` | 表数据列表（支持过滤/分页/排序） | is_developer |
| GET | `/api/v1/admin/db/{table}/{id}` | 单条记录详情 | is_developer |
| POST | `/api/v1/admin/db/{table}` | 新建记录（仅可写表） | is_developer |
| PUT | `/api/v1/admin/db/{table}/{id}` | 更新记录（受可写范围约束） | is_developer |
| DELETE | `/api/v1/admin/db/{table}/{id}` | 删除记录（仅可删表） | is_developer |
| GET | `/api/v1/admin/db/knowledge/raw` | 知识库 JSON 原文列表 | is_developer |
| PUT | `/api/v1/admin/db/knowledge/raw/{doc_id}` | 编辑 JSON 原文 + 重新索引 | is_developer |

**后端实现要点**：
1. 新增 `backend/api/routes/db_admin.py` 路由文件
2. 新增 `backend/services/db_admin_service.py` 服务层，封装表元数据查询、CRUD 操作、可写范围校验
3. 新增 `backend/core/developer_guard.py` 中间件/依赖，校验 `current_user.is_developer == True`
4. `{table}` 参数校验白名单，仅允许 10 张表
5. `PUT` 操作时根据表名应用字段白名单（如 consult_sessions 仅允许 follow_* 字段）
6. `DELETE` 操作时根据表名校验是否允许删除

### 3.5 前端实现要点

1. 新增 `admin-spa/src/pages/DbAdminPage.tsx`，包含 3 个 Tab
2. 新增 `admin-spa/src/components/db/` 目录，存放 Tab1/Tab2/Tab3 组件
3. Refine 数据提供者配置为 `/api/v1/admin/db`
4. 侧边栏 `Sidebar.tsx` 中 `/db` 入口仅在 `useAuthStore.user.is_developer === true` 时显示
5. 路由 `App.tsx` 中新增 `/db` 路由，受 `RequireDeveloper` 守卫保护
6. 新增 `admin-spa/src/components/RequireDeveloper.tsx` 路由守卫，检查 `useAuthStore.user.is_developer`
7. `authStore.ts` 登录成功后存储后端返回的 `is_developer` 标志（来自 JWT/登录响应）

### 3.6 验收标准

- [ ] `users` 表已新增 `rank` 字段
- [ ] 后端 `.env` 配置 `DEV_ADMIN_USERNAME=admin`
- [ ] 用 `admin` 账号登录时，响应中带 `is_developer: true`；其他账号不带
- [ ] 非开发者登录时侧边栏无 `/db` 入口，访问 `/db` 重定向到 `/dashboard`
- [ ] 开发者（admin）登录时侧边栏有 `/db` 入口，可访问 `/db`
- [ ] Tab 1 可查看 10 张表数据，可按可写范围矩阵执行 CRUD
- [ ] Tab 2 可查看/编辑/删除知识库 JSON 原文，编辑后自动重新索引
- [ ] Tab 3 可查看 10 张表的字段定义
- [ ] 后端 `/api/v1/admin/db/*` 端点对非开发者（JWT 无 is_developer claim）返回 403
- [ ] 后端对 `{table}` 参数做白名单校验，非白名单表返回 404

---

## 四、子项目 2：规范所有数据呈现

### 4.1 DashboardPage 重设计

#### 4.1.1 移除清单

移除所有 inline mock 数据依赖的板块：
- 渠道汇总（channelSummary）— 后端无渠道归因数据
- 咨询汇总的"趋势数据"（trendData）— 后端无此聚合
- 意向汇总（intentSummary）— 后端无此聚合
- 热门专业 Top5（hotMajors）— 后端无此聚合
- 转化漏斗（funnelData）— 后端无漏斗模型，后续子项目 3 后再考虑

#### 4.1.2 新设计（基于已有后端 API）

| 板块 | 数据源（后端 API） | 展示形式 |
|---|---|---|
| 今日核心数据卡 | `GET /admin/analytics/profile-dashboard` 的 `totalProfiles` | 4 个 stat-card：累计咨询学生数 / 今日新增会话数 / 待跟进会话数 / 本月新增画像数 |
| 咨询学生画像 Top 3 兴趣 | `GET /admin/analytics/profile-dashboard` 的 `riasecDistribution` | 3 张卡片，按 avgScore 降序，每张显示：类型名 + 占比 + 推荐匹配专业方向 |
| 价值观分布 | `GET /admin/analytics/profile-dashboard` 的 `valuesDistribution` | 横向条形图（保留现有实现） |
| 咨询热点 Top 10 | `GET /admin/analytics/hot-questions?days=7` | 横向条形图 |
| 画像完整度分布 | `GET /admin/analytics/profile-dashboard` 的 `completenessBreakdown` | 3 个 stat-card（L1/L2/L3 各 1 个） |

#### 4.1.3 后端 API 增强

`GET /admin/analytics/profile-dashboard` 响应新增字段：
- `monthlyNew`：本月新增画像数（基于 `consult_sessions.created_at` 在本月计数）
- `growthRate`：本月新增 / 上月新增 - 1（保留 2 位小数）
- `todayNewSessions`：今日新增会话数
- `pendingFollowSessions`：待跟进会话数（`follow_status = 'pending'`）

### 4.2 ChannelsPage 删除

- 删除 `admin-spa/src/pages/ChannelsPage.tsx`
- 从 `Sidebar.tsx` 移除 `/channels` 入口
- 从 `App.tsx` 移除 `/channels` 路由

### 4.3 ConsultationsPage + LeadWorkbenchPage 合并为咨询工作台

#### 4.3.1 路由与文件

- 保留路由 `/consultations`
- 删除路由 `/leads`
- 删除 `admin-spa/src/pages/LeadWorkbenchPage.tsx`
- 重写 `admin-spa/src/pages/ConsultationsPage.tsx` 为咨询工作台
- 侧边栏「咨询管理」标签可改名为「咨询工作台」，移除「线索管理」项

#### 4.3.2 后端字段变更

`consult_sessions` 表新增字段（`subjects` 与 `users.subjects` 对齐，会话创建时从 user 表读取快照）：

```sql
ALTER TABLE consult_sessions
  ADD COLUMN subjects VARCHAR(20) DEFAULT '',
  ADD COLUMN rank INTEGER,
  ADD COLUMN consult_summary TEXT,
  ADD COLUMN consult_started_at TIMESTAMPTZ,
  ADD COLUMN follow_status VARCHAR(20) NOT NULL DEFAULT 'pending',
  ADD COLUMN follow_note TEXT,
  ADD COLUMN followed_at TIMESTAMPTZ,
  ADD COLUMN followed_by UUID;

COMMENT ON COLUMN consult_sessions.subjects IS '选科组合快照，如物化生（会话创建时从users.subjects复制）';
COMMENT ON COLUMN consult_sessions.rank IS '高考位次快照（会话创建时从users.rank复制）';
COMMENT ON COLUMN consult_sessions.consult_summary IS 'AI/程序生成的咨询摘要，30字以内';
COMMENT ON COLUMN consult_sessions.consult_started_at IS '学生首条user message时间';
COMMENT ON COLUMN consult_sessions.follow_status IS '跟进状态：pending/processed/ignored';
COMMENT ON COLUMN consult_sessions.follow_note IS '跟进备注';
COMMENT ON COLUMN consult_sessions.followed_at IS '跟进时间';
COMMENT ON COLUMN consult_sessions.followed_by IS '跟进人user_id';
```

**subject_type 字段处理**：废弃 `subject_type`（保留列但不再读写，default=""），统一用 `subjects`。

**关键变更：基本信息改为学生表单填写（非 AI 提取）**：
省份/选科/分数/位次由学生在 mini-app 对话前置表单填写，存入 `users` 表；会话创建时复制快照到 `consult_sessions`。AI 画像提取不再负责这 4 个字段。需修改：
- `backend/services/consult_service.py`：`extract_profile_from_message` 移除对 province/subjects/score/rank 的提取逻辑（这些由表单提供）；会话创建函数 `create_session()` 增加从 `users` 表读取 region/subjects/score/rank 并写入 consult_sessions 快照的逻辑
- `backend/services/cend_profile_analyzer.py`：LLM 提取 prompt 移除 `subject_type` / `score` / `province` 字段，仅保留 `intent_majors` / `focus_points` 等意向类字段
- `backend/services/profile_bridge.py`：移除 `consult_updates["subject_type"]` 等赋值
- `backend/api/routes/miniapp.py`：响应字段 `subject_type` 改为 `subjects`；会话创建接口从 JWT 取 user_id 查 users 表填充快照
- `mini-app` 4 个页面（profile/recommendations/compare/chat）：展示"科类"改为"选科"，字段名 `subjectType` 改为 `subjects`
- 历史数据：`subject_type` 列保留不读写；`subjects`/`rank` 由学生下次进入表单时补填或保持空

#### 4.3.2a mini-app 对话前置表单（新增）

学生开始 AI 咨询前，强制填写基本信息表单：

**新增页面**：`mini-app/src/pages/chat/pre-form.vue`（或在 chat/index.vue 内增加前置步骤）

**表单字段**：

| 字段 | 控件 | 校验 | 存储字段 |
|---|---|---|---|
| 省份 | 下拉选择（34 省份） | 必填 | `users.region` |
| 选科 | 下拉选择（物化生/物化地/物化政/物生地/物生政/物政地/历化生/历化地/历化政/历生地/历生政/历政地 等常见组合） | 必填，3 字 | `users.subjects` |
| 分数 | 数字输入 | 必填，0-750 | `users.score` |
| 位次 | 数字输入 | 必填，正整数 | `users.rank` |

**流程**：
1. 学生进入聊天页 → 检查 `users.subjects` 是否为空
2. 若空 → 显示前置表单（全屏覆盖）
3. 提交表单 → 调用 `PUT /api/v1/miniapp/profile/basic` 写入 users 表
4. 写入成功 → 进入正常聊天界面，同时创建新会话并写入快照

**后端新增 API**：`PUT /api/v1/miniapp/profile/basic`，接收 `{ region, subjects, score, rank }`，更新当前登录学生的 users 表记录。

**选科组合枚举**（前端下拉选项）：
物理类：物化生、物化地、物化政、物生地、物生政、物政地
历史类：历化生、历化地、历化政、历生地、历生政、历政地

#### 4.3.3 咨询摘要实现（触发式 LLM 总结）

**新增 `backend/services/consult_summary_service.py`**：
- 函数 `generate_summary(session_id: str) -> str`
- 拉取会话最近 8 条 `chat_messages`
- 调用 DeepSeek API，prompt: "用 30 字以内总结学生本次咨询的核心问题，例如：'计算机专业就业前景与转专业政策咨询'"
- 写回 `consult_sessions.consult_summary`

**触发点**：
- 在 `backend/api/routes/miniapp.py` SSE 响应完成后
- 判断条件：首次总结——会话 user 消息数 ≥ 4 且 `consult_summary IS NULL`；后续总结——距上次总结（以 `consult_summary` 内容 hash 或时间戳判断）新增 user 消息 ≥ 2 条
- 满足则 `asyncio.create_task(generate_summary(session_id))`

**降级**：LLM 调用失败时，回退为首条 user message 截断 30 字

**管理端 API**：`POST /api/v1/admin/consultations/{session_id}/regenerate-summary` 允许手动触发重新生成

#### 4.3.4 咨询时间字段实现

**`backend/services/consult_service.py` 的 `save_message()` 改造**：
- 当 `role='user'` 且 `consult_sessions.consult_started_at IS NULL` 时
- 同步更新 `consult_started_at = now()`

**数据回填 SQL**：
```sql
UPDATE consult_sessions cs
SET consult_started_at = (
  SELECT MIN(created_at) FROM chat_messages cm
  WHERE cm.session_id = cs.session_id AND cm.role = 'user'
)
WHERE cs.consult_started_at IS NULL
  AND EXISTS (
    SELECT 1 FROM chat_messages cm
    WHERE cm.session_id = cs.session_id AND cm.role = 'user'
  );
```

**空会话处理**：`consult_started_at IS NULL` 的会话默认不显示在列表，可通过筛选查看

#### 4.3.5 咨询工作台页面设计

**顶部筛选栏**：

| 控件 | 选项 | 后端对应 |
|---|---|---|
| 跟进状态筛选 | 全部 / 待跟进 / 已处理 / 已忽略 / 未咨询 | `follow_status` + `consult_started_at IS NULL` |
| 时间筛选 | 今天 / 近7天 / 近30天 | `consult_started_at` |
| 搜索框 | 模糊匹配学生 username / 咨询摘要 | `users.username` / `consult_sessions.consult_summary` |

**主表格列（7 列）**：

| # | 列名 | 字段 | 备注 |
|---|---|---|---|
| 1 | 学生 | `users.username` | |
| 2 | 基本信息 | 省份·选科·分数·位次（`province`/`subjects`/`score`/`rank`） | 缺省显示 "—" |
| 3 | 意向专业 | `intent_majors[]` | 最多 2 个 + "+N" |
| 4 | 咨询摘要 | `consult_sessions.consult_summary` | 截断 30 字，hover 显示完整 |
| 5 | 咨询时间 | `consult_sessions.consult_started_at` | 相对时间，hover 显示绝对时间 |
| 6 | 跟进状态 | `consult_sessions.follow_status` | 颜色徽章（pending=橙/processed=绿/ignored=灰） |
| 7 | 操作 | — | 见下文 |

**操作列（3 个按钮）**：

| 按钮 | 操作 | 后端 API |
|---|---|---|
| 👁 查看详情 | 展开右侧抽屉 | `GET /api/v1/admin/consultations/{session_id}` |
| ✓ 标记已处理 | 弹 BottomSheet 输入备注 → 提交 | `PATCH /api/v1/admin/consultations/{session_id}/follow-status` |
| ✕ 标记忽略 | 直接调用（无备注） | 同上 |

**详情侧抽屉 4 个 Section**：

| Section | 内容 | API |
|---|---|---|
| 1. 学生基本信息 | username / 省份 / 选科 / 分数 / 位次 / 意向专业 / 关注点 / 创建时间 / 咨询时间 / 最后更新 / 是否过期 | `GET /api/v1/admin/consultations/{session_id}` |
| 2. 对话历史 | 最近 20 条 chat_messages，时间线展示 | `GET /api/v1/admin/consultations/{session_id}/messages` |
| 3. 跟进记录 | 当前状态 + 备注 + 跟进人 + 时间；内联表单可修改 | `PATCH /api/v1/admin/consultations/{session_id}/follow-status` |
| 4. 关联推荐 | 该会话生成的推荐列表 + 反馈 | `GET /api/v1/admin/recommendations?session_id={session_id}` |

**分页**：每页 20 条

#### 4.3.6 后端新增 API

| Method | Path | 用途 |
|---|---|---|
| GET | `/api/v1/admin/consultations` | 会话列表（支持 follow_status/consult_stage/period/search 筛选 + 分页） |
| GET | `/api/v1/admin/consultations/{session_id}` | 会话详情（学生信息 + 画像） |
| GET | `/api/v1/admin/consultations/{session_id}/messages` | 会话消息列表（分页） |
| PATCH | `/api/v1/admin/consultations/{session_id}/follow-status` | 更新跟进状态 + 备注 |
| POST | `/api/v1/admin/consultations/{session_id}/regenerate-summary` | 重新生成咨询摘要 |

### 4.4 ReportsPage 下线

- 从 `Sidebar.tsx` 移除 `/reports` 入口
- 从 `App.tsx` 移除 `/reports` 路由
- 删除 `admin-spa/src/pages/ReportsPage.tsx`
- 后端 `/admin/analytics/annual-report` API 保留（未来可能复用）

### 4.5 ProfileDashboardPage 修改

#### 4.5.1 修复假增长率

[ProfileDashboardPage.tsx:88-95](file:///d:/_Greatest_programmer/_Projects/gaokao_agents/admin-spa/src/pages/ProfileDashboardPage.tsx#L88) 修改：
- 删除硬编码 `+12%` 和 `+8%`
- 删除 `Math.floor(data.totalProfiles * 0.15)` 假数据
- 改用后端返回的 `monthlyNew` 和 `growthRate` 字段

#### 4.5.2 雷达图改为 Top 3 兴趣类型卡片

[ProfileDashboardPage.tsx:40-66](file:///d:/_Greatest_programmer/_Projects/gaokao_agents/admin-spa/src/pages/ProfileDashboardPage.tsx#L40) 替换：
- 删除 ECharts 雷达图
- 删除"全国均值"硬编码数据
- 改为 3 张卡片，按 `riasecDistribution.avgScore` 降序取 Top 3
- 每张卡片显示：
  - RIASEC 类型代码 + 中文名（如 "I 研究型"）
  - 学生数
  - 占比百分比
  - 推荐匹配专业方向（如 "计算机/人工智能/数据科学"）

**RIASEC 类型中文名映射**：

| 代码 | 中文名 | 推荐专业方向 |
|---|---|---|
| R | 实用型 | 机械/电气/土木 |
| I | 研究型 | 计算机/人工智能/数据科学 |
| A | 艺术型 | 设计/传媒/中文 |
| S | 社会型 | 师范/心理学/社会工作 |
| E | 企业型 | 工商管理/市场营销/金融 |
| C | 常规型 | 会计/统计学/档案学 |

### 4.6 InsightsPage 修改

#### 4.6.1 删除情绪时间线

[InsightsPage.tsx:111-117](file:///d:/_Greatest_programmer/_Projects/gaokao_agents/admin-spa/src/pages/InsightsPage.tsx#L111) 整个情绪时间线 section 删除。同时清理：
- 删除 `EMOTION_COLORS` 常量
- 删除 `emotionTimeline` state 和 API 调用
- 删除 `mockEmotionTimeline` 引用
- `Promise.allSettled` 从 3 个接口减为 2 个（topic-cloud + hot-questions）
- 删除 `emotionOption` 变量

#### 4.6.2 移除 mock 兜底

[InsightsPage.tsx:42-53](file:///d:/_Greatest_programmer/_Projects/gaokao_agents/admin-spa/src/pages/InsightsPage.tsx#L42) 移除 `setTopicCloud(mockTopicCloud)` / `setHotQuestions(mockHotQuestions)` 兜底。3 个接口全失败时显示错误状态。

### 4.7 KnowledgeSettingsPage 修改

[KnowledgeSettingsPage.tsx:32](file:///d:/_Greatest_programmer/_Projects/gaokao_agents/admin-spa/src/pages/KnowledgeSettingsPage.tsx#L32) 移除 `setDocs(mockDocuments)` 兜底。

### 4.8 Distribution 3 页隐藏入口（不修改代码）

- 在 `Sidebar.tsx` 中移除 `/distribution/tasks` / `/distribution/channels` / `/distribution/logs` 三个侧边栏入口
- 路由和页面代码保留不动（未来可能恢复）
- mock 兜底逻辑、Fragment key 等问题不修复（因页面不再展示）

### 4.9 模块管理页删除 + 后端取消模块门控

#### 4.9.1 前端删除

- 删除 `admin-spa/src/pages/ModuleSettingsPage.tsx`
- 从 `Sidebar.tsx` 移除 `/modules` 入口
- 从 `App.tsx` 移除 `/modules` 路由

#### 4.9.2 后端取消模块门控

- 移除 `backend/core/middleware.py` 中的 `ModuleGate` 中间件（或改为始终通过）
- `main.py` 中移除 `ModuleGate` 注册
- 保留 `tenant_configs.modules` 字段（兼容性，但不再生效）
- `Sidebar.tsx` 中 `module` 字段过滤逻辑可保留（始终返回 true）或移除

### 4.10 品牌配置页删除

- 删除 `admin-spa/src/pages/BrandSettingsPage.tsx`
- 从 `Sidebar.tsx` 移除 `/brand` 入口
- 从 `App.tsx` 移除 `/brand` 路由
- 后端 `/admin/brand-config` API 保留（mini-app 仍需读取品牌配置）

### 4.11 验收标准

- [ ] DashboardPage 无任何 inline mock 数据，所有数据来自真实后端 API
- [ ] ChannelsPage 文件已删除，侧边栏无入口
- [ ] LeadWorkbenchPage 文件已删除，侧边栏无"线索管理"项
- [ ] ConsultationsPage 重写为咨询工作台，7 列表格 + 详情抽屉 4 Section + 3 操作按钮
- [ ] 咨询工作台筛选、搜索、分页、跟进操作均可用
- [ ] ReportsPage 文件已删除，侧边栏无入口
- [ ] ProfileDashboardPage 无硬编码 `+12%` / `+8%`，无 `Math.floor(totalProfiles * 0.15)`
- [ ] ProfileDashboardPage 雷达图已替换为 Top 3 兴趣类型卡片
- [ ] InsightsPage 情绪时间线已删除
- [ ] KnowledgeSettingsPage 无 mock 兜底
- [ ] Distribution 3 页侧边栏入口已隐藏（页面代码不动）
- [ ] ModuleSettingsPage 文件已删除，侧边栏无入口，后端 ModuleGate 已移除
- [ ] BrandSettingsPage 文件已删除，侧边栏无入口
- [ ] `consult_sessions` 表已新增 8 个字段（subjects/rank/consult_summary/consult_started_at/follow_status/follow_note/followed_at/followed_by）
- [ ] `users` 表已新增 `rank` 字段（region/subjects/score 已存在）
- [ ] 后端 `subject_type` 引用全部改为 `subjects`（后端 4 处 + mini-app 4 个页面）
- [ ] mini-app 对话前置表单已实现（省份/选科/分数/位次 4 字段，写入 users 表）
- [ ] 后端 `PUT /api/v1/miniapp/profile/basic` API 已实现
- [ ] 会话创建时从 users 表读取快照写入 consult_sessions（province/subjects/score/rank）
- [ ] AI 画像提取不再提取省份/选科/分数/位次（仅提取意向专业/关注点等）
- [ ] 咨询摘要触发式 LLM 总结逻辑已实现
- [ ] 咨询时间字段 `consult_started_at` 写入逻辑已实现
- [ ] 后端新增 5 个咨询工作台 API + 1 个 Dashboard API 增强 + 1 个 mini-app 表单 API

---

## 五、子项目 3：端到端数据链路测试

### 5.1 测试范围（10 个环节）

| # | 环节 | 输入 | 期望输出 | 数据库验收点 |
|---|---|---|---|---|
| 1 | 学生注册 | mini-app 提交注册表单 | 创建用户 + 返回 JWT | `users` 表新增 1 条记录，`username`/`password_hash`/`tenant_slug` 正确 |
| 2 | 学生登录 | mini-app 提交登录 | 返回 JWT | `users.last_login_at` 更新 |
| 3 | AI 咨询 | mini-app 发送 N 条消息 | SSE 流式返回 AI 回复 | `consult_sessions` 新增/更新会话；`chat_messages` 新增 N 条 user + N 条 assistant 消息 |
| 4 | 基本信息填写 + 画像提取 | 学生在对话前置表单填写省份/选科/分数/位次；AI 咨询中提及意向专业 | 表单写入 users 表，会话创建写快照；AI 提取意向类字段 | `users.region`/`subjects`/`score`/`rank` 填充；`consult_sessions.subjects`/`province`/`score`/`rank`/`intent_majors` 填充；`user_profiles` 表更新 |
| 5 | 个性化推荐 | 触发推荐 | 返回 3+ 专业推荐 | `recommendations` 表新增 3+ 条记录，关联 `session_id` 和 `user_id` |
| 6 | 推荐反馈 | 学生标记 useful/not_relevant | 反馈记录 | `recommendation_feedback` 表新增记录，关联 `recommendation_id` |
| 7 | 咨询摘要生成 | 消息数 ≥ 4 时 | 异步生成 30 字摘要 | `consult_sessions.consult_summary` 非空 |
| 8 | 跟进状态更新 | 管理后台标记已处理 | 状态变更 | `consult_sessions.follow_status`='processed'，`follow_note`/`followed_at`/`followed_by` 填充 |
| 9 | 知识库检索 | AI 咨询中提问专业知识 | 检索 ChromaDB 返回相关片段 | 后端日志显示检索调用 + 返回结果；AI 回复包含知识库内容 |
| 10 | 推荐质量评估 | 对比推荐结果与 ground truth | 推荐准确率 ≥ 80% | 运行 `backend/tests/benchmarks/run_accuracy.py`，准确率达标 |

### 5.2 测试方式

#### 5.2.1 真人测试（1 个完整场景）

**测试账号**：`admin` / `admin123`（管理后台）+ 新注册学生账号（mini-app）

**测试流程**：
1. 在 mini-app 注册新学生（如 `test_student_001`）
2. 登录并进入 AI 咨询
3. **填写对话前置表单**（省份：广东，选科：物化生，分数：610，位次：12000）
4. 进行 5-8 轮对话，覆盖：
   - 自报意向专业（如"计算机/人工智能"）
   - 提问专业知识（如"计算机专业课程有哪些"）
5. 触发个性化推荐
6. 对推荐结果标记 useful/not_relevant
7. 等待咨询摘要生成（消息数 ≥ 4 后）
8. 在管理后台 `/consultations` 查看该会话
9. 验证 10 个环节的验收点

#### 5.2.2 Seed data 注入（8-12 个场景）

**新增 `backend/tests/seed/e2e_seed.py` 脚本**，注入 10 个场景：

| 场景 | 省份 | 选科 | 分数 | 位次 | 意向专业 |
|---|---|---|---|---|---|
| 1 | 广东 | 物化生 | 610 | 12000 | 计算机/人工智能 |
| 2 | 广东 | 物化地 | 580 | 25000 | 电子信息/通信 |
| 3 | 广东 | 历政地 | 560 | 8000 | 师范/汉语言文学 |
| 4 | 湖南 | 物化生 | 590 | 15000 | 计算机/软件工程 |
| 5 | 湖南 | 历史类 | 550 | 7000 | 法学/新闻传播 |
| 6 | 湖北 | 物化生 | 600 | 13000 | 人工智能/数据科学 |
| 7 | 湖北 | 物化政 | 570 | 22000 | 心理学/教育学 |
| 8 | 河南 | 物化生 | 620 | 18000 | 计算机/电子信息 |
| 9 | 河南 | 历政地 | 540 | 12000 | 师范/历史学 |
| 10 | 山东 | 物化生 | 595 | 20000 | 数学/统计学 |

**注入内容**：
- 每个场景创建 1 个 `users` 记录
- 每个场景创建 1 个 `consult_sessions` 记录（含 subjects/rank/province/score 快照 + consult_summary 等）
- 每个场景创建 5-10 条 `chat_messages`（含 user + assistant）
- 每个场景创建 3-5 条 `recommendations` 记录
- 部分场景创建 `recommendation_feedback` 记录

**验证方式**：
- 注入后在管理后台 `/consultations` 查看列表，确认 10 个场景都显示
- 在 `/db` 面板查看各表数据，确认字段正确
- 触发推荐质量评估脚本，对比推荐结果

### 5.3 推荐质量评估

复用现有 `backend/tests/benchmarks/run_accuracy.py`，针对 10 个 seed 场景运行：
- 推荐准确率 ≥ 80%
- 画像提取准确率 ≥ 90%
- 知识库检索相关性 ≥ 85%

### 5.4 验收标准

- [ ] 真人测试 1 个场景：10 个环节全部通过验收点
- [ ] Seed data 10 个场景全部注入成功
- [ ] 管理后台 `/consultations` 可见 10 个 seed 场景 + 1 个真人场景
- [ ] `/db` 面板可查看所有 seed 数据
- [ ] 推荐准确率 ≥ 80%
- [ ] 画像提取准确率 ≥ 90%
- [ ] 知识库检索相关性 ≥ 85%

---

## 六、整体验收标准

执行顺序：1 → 4 → 2 → 3

- [ ] 子项目 1 验收：mock 数据全部清理，build 无报错
- [ ] 子项目 4 验收：`/db` 面板可用，3 Tab 功能完整，仅开发者可见
- [ ] 子项目 2 验收：所有页面规范化，字段统一，无假数据，无 mock 兜底
- [ ] 子项目 3 验收：端到端 10 环节通过，准确率达标

---

## 七、风险与依赖

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| Refine 框架引入增加 bundle 体积 | admin-spa build 体积增大 | 懒加载 `/db` 路由，仅在开发者访问时加载 |
| `subject_type` → `subjects` 迁移涉及后端 4 处 + 4 个 mini-app 页面 | 改动范围大，易遗漏 | 全项目 grep `subject_type` 逐一确认，编写迁移测试 |
| 咨询摘要 LLM 调用增加成本 | DeepSeek API 调用量增加 | 触发式（消息数 ≥4 且距上次 ≥2 条），非每轮触发 |
| `DEV_ADMIN_USERNAME` 环境变量未配置导致无人能访问 `/db` | 部署后无法使用 | 后端 config.py 设置默认值 `admin`，无需额外配置即生效 |
| 学生对话前置表单增加摩擦 | 学生未填基本信息即想咨询 | 表单字段精简为 4 项；已填过的学生不重复弹窗 |
| 取消模块门控后，所有后端模块始终启用 | 无前端入口的模块（如 distribution）API 仍可访问 | distribution 前端入口已隐藏，API 保留供未来恢复；无安全风险（需鉴权） |

---

## 八、附录

### 8.1 文件改动清单

#### 新增文件

| 文件 | 用途 |
|---|---|
| `admin-spa/src/pages/DbAdminPage.tsx` | DB 可视化管理面板主页面 |
| `admin-spa/src/components/db/TablesTab.tsx` | Tab 1: PostgreSQL 表管理 |
| `admin-spa/src/components/db/KnowledgeRawTab.tsx` | Tab 2: 知识库 raw 数据 |
| `admin-spa/src/components/db/SchemaTab.tsx` | Tab 3: 表结构查看 |
| `admin-spa/src/components/RequireDeveloper.tsx` | 路由守卫 |
| `backend/api/routes/db_admin.py` | DB 管理 API 路由 |
| `backend/services/db_admin_service.py` | DB 管理服务层 |
| `backend/core/developer_guard.py` | 开发者鉴权依赖 |
| `backend/services/consult_summary_service.py` | 咨询摘要生成服务 |
| `backend/api/routes/miniapp_profile.py`（或在 miniapp.py 内新增） | 学生基本信息表单 API `PUT /api/v1/miniapp/profile/basic` |
| `mini-app/src/pages/chat/pre-form.vue`（或 chat/index.vue 内前置步骤） | 对话前置基本信息表单 |
| `backend/tests/seed/e2e_seed.py` | 端到端测试 seed 脚本 |
| `backend/migrations/versions/006_admin_data_overhaul.py` | 数据库迁移脚本 |

#### 删除文件

| 文件 | 原因 |
|---|---|
| `admin-spa/src/pages/ChannelsPage.tsx` | 无后端支撑，删除 |
| `admin-spa/src/pages/LeadWorkbenchPage.tsx` | 合并入咨询工作台 |
| `admin-spa/src/pages/ReportsPage.tsx` | 整页 mock，下线 |
| `admin-spa/src/pages/ModuleSettingsPage.tsx` | 取消模块门控 |
| `admin-spa/src/pages/BrandSettingsPage.tsx` | 用户决定删除 |
| `admin-spa/src/mock/profileDashboard.ts` | mock 文件 |
| `admin-spa/src/mock/insights.ts` | mock 文件 |
| `admin-spa/src/mock/knowledgeBase.ts` | mock 文件 |
| `admin-spa/src/mock/distribution.ts` | 不删除（distribution 模块整体隐藏，保留代码） |

#### 修改文件（主要）

| 文件 | 修改内容 |
|---|---|
| `admin-spa/src/pages/DashboardPage.tsx` | 重设计，移除 inline mock |
| `admin-spa/src/pages/ConsultationsPage.tsx` | 重写为咨询工作台 |
| `admin-spa/src/pages/ProfileDashboardPage.tsx` | 修假数据 + 雷达图改 Top 3 卡片 |
| `admin-spa/src/pages/InsightsPage.tsx` | 删情绪时间线 + 移除 mock 兜底 |
| `admin-spa/src/pages/KnowledgeSettingsPage.tsx` | 移除 mock 兜底 |
| `admin-spa/src/pages/DistributionTasksPage.tsx` | 不修改（仅隐藏入口） |
| `admin-spa/src/pages/DistributionChannelsPage.tsx` | 不修改（仅隐藏入口） |
| `admin-spa/src/pages/DistributionLogsPage.tsx` | 不修改（仅隐藏入口） |
| `admin-spa/src/components/Sidebar.tsx` | 移除多个入口 + 隐藏 distribution 3 入口 + 新增 /db 入口 |
| `admin-spa/src/App.tsx` | 移除多个路由 + 新增 /db 路由 |
| `backend/models/consult_session.py` | 新增 8 字段（subjects/rank/consult_summary/consult_started_at/follow_*），废弃 subject_type |
| `backend/models/user.py` | 新增 rank 字段（region/subjects/score 已存在） |
| `backend/services/consult_service.py` | subject_type → subjects；移除省份/选科/分数/位次的 AI 提取；create_session 从 users 表读快照；save_message 写 consult_started_at |
| `backend/services/cend_profile_analyzer.py` | LLM prompt 移除 subject_type/score/province 提取，仅保留意向类字段 |
| `backend/services/profile_bridge.py` | 移除 consult_updates["subject_type"] 等赋值 |
| `backend/services/auth_service.py` | authenticate_user 增加 DEV_ADMIN_USERNAME 识别，返回 is_developer |
| `backend/utils/jwt.py` | generate_tokens 在 payload 中加 is_developer claim |
| `backend/config.py` | 新增 DEV_ADMIN_USERNAME 配置项 |
| `backend/api/routes/miniapp.py` | subject_type → subjects；会话创建填快照；咨询摘要触发；新增 profile/basic 端点 |
| `backend/api/routes/admin.py` | 新增咨询工作台 API + DB 管理 API 注册 |
| `backend/analytics/router.py` | profile-dashboard 响应增强 |
| `backend/core/middleware.py` | 移除 ModuleGate |
| `backend/main.py` | 移除 ModuleGate 注册 + 新增 db_admin 路由 |
| `admin-spa/src/stores/authStore.ts` | 存储 is_developer 标志（来自登录响应） |
| `mini-app/src/pages/profile/index.vue` | 科类 → 选科（subjectType → subjects） |
| `mini-app/src/pages/recommendations/index.vue` | 科类 → 选科 |
| `mini-app/src/pages/compare/index.vue` | 科类 → 选科 |
| `mini-app/src/pages/chat/index.vue` | 科类 → 选科 + 增加对话前置表单逻辑 |

### 8.2 数据库迁移 SQL 汇总

```sql
-- users 表（已有 region/subjects/score，仅新增 rank；不新增 is_developer，开发者通过环境变量识别）
ALTER TABLE users
  ADD COLUMN rank INTEGER;

-- consult_sessions 表
ALTER TABLE consult_sessions
  ADD COLUMN subjects VARCHAR(20) DEFAULT '',
  ADD COLUMN rank INTEGER,
  ADD COLUMN consult_summary TEXT,
  ADD COLUMN consult_started_at TIMESTAMPTZ,
  ADD COLUMN follow_status VARCHAR(20) NOT NULL DEFAULT 'pending',
  ADD COLUMN follow_note TEXT,
  ADD COLUMN followed_at TIMESTAMPTZ,
  ADD COLUMN followed_by UUID;

-- 历史数据回填 consult_started_at
UPDATE consult_sessions cs
SET consult_started_at = (
  SELECT MIN(created_at) FROM chat_messages cm
  WHERE cm.session_id = cs.session_id AND cm.role = 'user'
)
WHERE cs.consult_started_at IS NULL
  AND EXISTS (
    SELECT 1 FROM chat_messages cm
    WHERE cm.session_id = cs.session_id AND cm.role = 'user'
  );
```
