# 管理后台前端页面审计与重设计文档

> 日期: 2026-05-20 | 分支: `feat/foundation` | 范围: admin-spa 全部 7 页面

---

## 1. 当前页面全量审计

### 1.1 页面总览

| 路由 | 页面 | TSX 文件 | 行数 | 复杂度 |
|------|------|---------|------|--------|
| `/login` | 登录页 | `LoginPage.tsx` | 107 | 中 |
| `/funnel` | 招生漏斗 | `FunnelPage.tsx` | 30 | 低 |
| `/profile` | 画像看板 | `ProfileDashboardPage.tsx` | 89 | 中 |
| `/brand` | 品牌设置 | `BrandSettingsPage.tsx` | 153 | 中 |
| `/knowledge` | 知识库 | `KnowledgeSettingsPage.tsx` | 78 | 低 |
| `/insights` | 增强分析 | `InsightsPage.tsx` | 148 | 高 |
| `/agent-settings` | AI 设置 | `AgentSettingsPage.tsx` | 150 | 中 |

### 1.2 共享组件

| 组件 | 文件 | 用途 |
|------|------|------|
| `DashboardLayout` | `components/DashboardLayout.tsx` | 侧边栏 + 顶栏 + `<Outlet>` 布局壳 |
| `Sidebar` | `components/Sidebar.tsx` | 侧边导航，6 个菜单项，按模块功能过滤 |
| `ProtectedRoute` | `components/ProtectedRoute.tsx` | 登录守卫，保留 `?tenant=` 参数跳转 |
| `StatusCard` | `components/StatusCard.tsx` | 三态容器：loading spinner / error icon / empty hint |
| `PageHeader` | `components/PageHeader.tsx` | 统一页面标题 + 副标题 + 右侧操作区 |
| `FunnelChart` | `components/charts/FunnelChart.tsx` | ECharts 漏斗图 + 转化率指标卡 |
| `RadarChart` | `components/charts/RadarChart.tsx` | ECharts 雷达图（RIASEC 6 维） |

### 1.3 基础设施

| 模块 | 文件 | 功能 |
|------|------|------|
| `api` | `api/client.ts` | axios 实例，自动注入 `X-Tenant` + `Authorization` 头 |
| `authStore` | `stores/authStore.ts` | Zustand 登录/登出，token + user 持久化到 localStorage |
| `useBrandConfig` | `hooks/useBrandConfig.ts` | 登录后拉取品牌配置，设置 CSS 变量换肤 |
| `types` | `types/index.ts` | 9 个 TypeScript 接口 |

---

## 2. 逐页面元素与 API 映射（当前现状）

### 2.1 LoginPage — 登录页

**UI 元素：**

| 元素 | 类型 | 说明 |
|------|------|------|
| 品牌 Logo | `<div>` 背景图 | 通过 `--brand-logo` CSS 变量渲染（登录前不可用，总是显示灰色占位） |
| 标题 "招生智脑" | `<h1>` | 硬编码文字 |
| 副标题 "院校管理后台" | `<p>` | 硬编码文字 |
| 院校标识文本框 | `<input>` | 仅当 URL 无 `?tenant=` 时显示 |
| 院校标识已识别 | `<div>` | 当 `?tenant=scnu` 时显示灰色确认卡片 |
| 用户名输入框 | `<input type="text">` | placeholder "请输入用户名" |
| 密码输入框 | `<input type="password">` | placeholder "请输入密码" |
| 错误提示 | `<div>` | 红色背景，字段为空或登录失败时显示 |
| 登录按钮 | `<button>` | 品牌色背景，loading 态禁用 |

**API 调用：** `POST /api/v1/auth/login` — `{ username, password }` → `{ access_token, refresh_token, user_id, username }`

**状态变量：** `username`, `password`, `tenant`, `error`, `loading`

**问题：**
- Logo 在登录前不可用（`useBrandConfig` 依赖 token），登录页永远看不到品牌 Logo
- 院校标识输入框在无 `?tenant=` 时手动填写，用户体验差

---

### 2.2 FunnelPage — 招生漏斗

**UI 元素：**

| 元素 | 类型 | API 数据来源 |
|------|------|-------------|
| PageHeader 标题 "招生漏斗" | 组件 | — |
| PageHeader 副标题（日期范围） | 组件 | `data.period.start ~ end` |
| 漏斗图 | ECharts funnel | `data.stages.{visitors, conversations, deepConsultations, intentExpressed, enrolled}` |
| 转化率指标卡 ×4 | `<div>` 网格 | `data.conversionRates` |
| 空状态提示 | StatusCard empty | `data._stub === true` 时显示 |

**API 调用：** `GET /api/v1/admin/analytics/funnel` — 需要模块 `funnel` 开启

**状态变量：** `data: FunnelData | null`, `error: string | null`

**ECharts 配置：** 漏斗图使用 `sort: 'descending'`，max 取数据最大值，无硬编码上限

---

### 2.3 ProfileDashboardPage — 画像看板

**UI 元素：**

| 元素 | 类型 | API 数据来源 |
|------|------|-------------|
| PageHeader "画像看板" + 累计人数 | 组件 | `data.totalProfiles` |
| stub 警告横幅（琥珀色） | `<div>` | `data._stub === true` |
| RIASEC 雷达图 | RadarChart (ECharts radar) | `data.riasecDistribution[{dimension, avgScore, count}]` |
| 价值观分布条形图 | 自定义 CSS 进度条 | `data.valuesDistribution[{value, percentage}]` |
| 画像完整度卡片 ×3 | `<div>` 网格 | `data.completenessBreakdown[{level, count}]` |

**API 调用：** `GET /api/v1/admin/analytics/profile-dashboard` — 需要模块 `profile_dashboard` 开启

**状态变量：** `data: ProfileDashboard | null`, `error: string | null`

---

### 2.4 BrandSettingsPage — 品牌设置

**UI 元素：**

| 元素 | 类型 | API 数据来源 |
|------|------|-------------|
| PageHeader "品牌设置" | 组件 | — |
| 院校全称输入框 | `<input>` | `brand.name` |
| 院校简称输入框 | `<input>` | `brand.short_name` |
| 主题色 color picker + hex 输入 | `<input type="color">` + `<input>` | `brand.primary_color` |
| 辅助色 color picker + hex 输入 | `<input type="color">` + `<input>` | `brand.secondary_color` |
| Logo URL 输入框 | `<input>` | `brand.logo_url` |
| 实时预览卡片 | `<div>` 缩略图 | 显示 logo 背景 + 两色块 + 院校名 |
| 保存成功/失败提示 | `<div>` 颜色状态条 | — |
| 保存按钮 | `<button>` | — |

**API 调用：**
- `GET /api/v1/admin/brand-config` → 获取配置
- `PUT /api/v1/admin/brand-config` → 保存配置（全量提交 BrandConfig 对象）

**状态变量：** `brand: BrandConfig | null`, `saving`, `message`, `error`

**额外行为：** 保存成功后立即通过 `document.documentElement.style.setProperty` 更新 CSS 变量，实现实时换肤

---

### 2.5 KnowledgeSettingsPage — 知识库

**UI 元素：**

| 元素 | 类型 | API 数据来源 |
|------|------|-------------|
| PageHeader "知识库管理" + 上传按钮（禁用） | 组件 | — |
| 文档表格 | `<table>` 4 列 | `data.documents[{id, title, data_type, year, indexed_at}]` |
| 索引状态徽章 | `<span>` 绿/琥珀色 | `doc.indexed_at` 是否为空 |
| 空状态提示 | StatusCard empty | 文档列表为空时 |

**API 调用：** `GET /api/v1/admin/knowledge/documents` → `{ documents: DocumentItem[] }`

**状态变量：** `docs: DocumentItem[]`, `loading`, `error`

**问题：**
- "上传文档"按钮永久禁用（`disabled` 硬编码），上传功能不可用
- 表格无搜索/筛选/分页
- 缺少删除确认操作（DELETE API 已存在但前端未接线）

---

### 2.6 InsightsPage — 增强分析

**UI 元素：**

| 元素 | 类型 | API 数据来源 |
|------|------|-------------|
| PageHeader "增强分析" + 副标题 | 组件 | — |
| 关键词词云图 | ECharts wordCloud | `topicCloud[{word, count}]` |
| 词云空状态 | StatusCard empty | `topicCloud.length === 0` |
| 情绪时间线折线图 | ECharts lines (多系列) | `emotionTimeline.{timeline[], dates[]}` |
| 情绪图空状态 | StatusCard empty | `emotionTimeline.timeline.length === 0` |
| 咨询热点 Top-10 横向柱状图 | ECharts bar (横向) | `hotQuestions[{topic, count}]` |
| 热点图空状态 | StatusCard empty | `hotQuestions.length === 0` |

**API 调用（并行 3 个）：**
- `GET /api/v1/admin/analytics/topic-cloud` → `TopicCloudItem[]`
- `GET /api/v1/admin/analytics/emotion-timeline` → `EmotionTimelineData`
- `GET /api/v1/admin/analytics/hot-questions` → `HotQuestionItem[]`

**状态变量：** `topicCloud`, `emotionTimeline`, `hotQuestions`, `loading`, `error`

**ECharts 配置细节：**
- 词云：`shape: 'circle'`, `sizeRange: [14, 48]`, 随机颜色（品牌色 + 7 种辅助色）
- 情绪：多系列折线，5 种情绪色（positive 绿 / neutral 蓝 / negative 红 / confused 橙 / anxious 深橙）
- 热点：横向柱状，品牌色填充，`barMaxWidth: 28`，Y 轴反向排列

---

### 2.7 AgentSettingsPage — AI 设置

**UI 元素：**

| 元素 | 类型 | API 数据来源 |
|------|------|-------------|
| PageHeader "AI 对话设置" + 副标题 | 组件 | — |
| 自定义提示词 textarea | `<textarea>` 6 行 | `persona.custom_prompt` |
| 占位符文档提示 | `<p>` 静态文本 | `{stage}` / `{slots_summary}` |
| 对话风格选择（亲切/正式） | radio cards ×2 | `persona.style` |
| 主动推荐开关 | `<button role="switch">` 自定义 toggle | `persona.proactive_recommend` |
| 保存成功/失败提示 | `<div>` | — |
| 保存按钮 | `<button>` | — |

**API 调用：**
- `GET /api/v1/admin/ai-persona` → PersonaConfig（合并默认值 `DEFAULT_PERSONA`）
- `PUT /api/v1/admin/ai-persona` → 保存 PersonaConfig

**状态变量：** `persona: PersonaConfig | null`, `saving`, `message`, `error`

---

## 3. 当前页面问题清单

### 3.1 严重问题

| # | 页面 | 问题 | 影响 |
|---|------|------|------|
| B1 | LoginPage | Logo 依赖 token，登录前永远不显示 | 品牌形象缺失 |
| B2 | KnowledgeSettingsPage | 上传按钮永久禁用 | 核心功能不可用 |
| B3 | KnowledgeSettingsPage | 无删除按钮 | DELETE API 存在但前端未接线 |
| B4 | KnowledgeSettingsPage | 无搜索/分页 | 1997 条文档无法浏览 |

### 3.2 功能缺失

| # | 页面 | 问题 |
|---|------|------|
| F1 | LoginPage | 无租户下拉选择（需手动输入 slug） |
| F2 | FunnelPage | 无时间范围选择器（API 支持 `?days=` 参数但前端未暴露） |
| F3 | BrandSettingsPage | Logo 上传按钮缺失（POST logo API 存根存在） |
| F4 | InsightsPage | 无时间范围选择器 |
| F5 | KnowledgeSettingsPage | 无 Excel 上传流程（API 存在，前端未接线） |
| F6 | 全局 | 无租户切换能力（需手动改 URL `?tenant=`） |
| F7 | 全局 | 无模块功能开关管理页面 |

### 3.3 UI/UX 问题

| # | 页面 | 问题 |
|---|------|------|
| U1 | LoginPage | 无登录背景图（`login_bg_url` 字段存在但未使用） |
| U2 | 全局 | 侧边栏收起/展开不支持 |
| U3 | InsightsPage | 3 个 API 任一失败全部不显示（Promise.all 无容错） |
| U4 | BrandSettingsPage | favicon_url 字段未暴露在表单中 |
| U5 | AgentSettingsPage | textarea 太小，200 字提示词就需要滚动 |

---

## 4. 新前端重设计方案

### 4.1 设计原则

1. **不增加新 API** — 复用现有全部 39 个后端端点
2. **每页可独立加载** — Promise.all 改为独立请求 + 独立 error boundary
3. **零硬编码 disabled** — 所有禁用状态来自真实权限/数据
4. **移动端响应式** — 侧边栏在 <768px 时折叠为汉堡菜单

### 4.2 页面重设计：元素 → API 映射

---

#### 4.2.1 LoginPage（重设计）

**新增元素：**

| 元素 | 类型 | 来源 / 行为 |
|------|------|------------|
| 登录背景图 | CSS `background-image` | 从 `GET /api/v1/admin/brand-config` 读取 `login_bg_url`（登录前调用，无需 token） |
| 品牌 Logo | `<img>` 或 CSS | 同上述 API |
| 院校名称 | `<h2>` | 同上述 API 的 `brand.name` |
| 租户选择下拉框 | `<select>` | **新增 API 需要**: `GET /api/v1/tenants`（列出活跃租户 — 当前不存在，见下文方案） |

**LoginPage 租户选择方案：** 后端目前没有公开的 "列出活跃租户" API。两个方案：
- **方案 A（推荐）**：保持现有 `?tenant=` URL 参数方式（院校给招生办发带租户标识的链接）
- **方案 B**：新增 `GET /api/v1/tenants/public` 公开端点返回 `[{slug, name, logo_url}]`

**API 调用：**
```
GET  /api/v1/admin/brand-config          → 页面加载时（无需 token，但中间件当前需要...）
POST /api/v1/auth/login                  → 登录提交
```

**注意：** `brand-config` 当前需要登录（中间件验证）。要让登录页显示品牌，需要将 `/api/v1/admin/brand-config` 加入 `TENANT_PUBLIC_PATHS` 或新建公开端点。

---

#### 4.2.2 FunnelPage（增强）

**保留元素：** PageHeader + FunnelChart + 转化率卡片（与现状一致）

**新增元素：**

| 元素 | 类型 | 来源 / 行为 |
|------|------|------------|
| 时间范围选择器 | `<select>` 或日期范围 | 修改 `days` 参数重新请求 API：`GET /api/v1/admin/analytics/funnel?days=30\|90\|180\|365` |
| 阶段详情 tooltip | ECharts tooltip | 悬停显示各阶段人数 + 环比变化（数据已在 `stages` 中） |
| 对比上周期箭头 | `<span>` 指示器 | 需要 API 返回 `prevPeriod` 数据（当前不返回，存为 P2 需求） |

**API 调用（不变）：**
```
GET  /api/v1/admin/analytics/funnel?days={N}
```

---

#### 4.2.3 ProfileDashboardPage（增强）

**保留元素：** RadarChart + 价值观分布 + 完整度卡片

**新增/修改元素：**

| 元素 | 类型 | 来源 / 行为 |
|------|------|------------|
| 时间范围选择器 | `<select>` | 同 funnel |
| RIASEC 维度详情卡片 | 点击雷达图展开 | 显示该维度的分数分布直方图（数据已包含 `avgScore + count`） |
| 价值观 TOP-N 排序切换 | toggle | 默认按 percentage 降序，支持按字母 |

**API 调用（不变）：**
```
GET  /api/v1/admin/analytics/profile-dashboard?days={N}
```

---

#### 4.2.4 BrandSettingsPage（增强）

**保留元素：** 完整表单 + 实时预览 + 保存按钮

**新增/修改元素：**

| 元素 | 类型 | 来源 / 行为 |
|------|------|------------|
| Logo 上传按钮 | `<input type="file">` + 上传 | `POST /api/v1/admin/brand-config/logo`（multipart 上传，当前为存根） |
| Logo 预览 | `<img>` | 上传后显示预览；回退到 `brand.logo_url` |
| favicon URL 输入 | `<input>` | `brand.favicon_url`（类型定义已存在，表单缺少） |
| 欢迎语 textarea | `<textarea>` | `brand.welcome_text`（类型定义已存在，表单缺少） |
| 登录背景图 URL 输入 | `<input>` | `brand.login_bg_url`（类型定义已存在，表单缺少） |
| 重置默认按钮 | `<button type="button">` | 恢复到 `#2563eb` / `#f59e0b` / 空 logo |

**API 调用：**
```
GET  /api/v1/admin/brand-config
PUT  /api/v1/admin/brand-config
POST /api/v1/admin/brand-config/logo   ← 接线（当前存根，上传返回占位 URL）
```

---

#### 4.2.5 KnowledgeSettingsPage（重设计）

**保留元素：** 文档表格（核心）

**新增/修改元素：**

| 元素 | 类型 | 来源 / 行为 |
|------|------|------------|
| 上传文档按钮 | `<button>` + 文件选择 | `POST /api/v1/admin/knowledge/documents`（multipart: file + data_type 字段） |
| data_type 下拉框 | `<select>` | 在上传前选择：admission_score / curriculum / employment / campus_life |
| 搜索输入框 | `<input>` | 前端过滤 `doc.title`（客户端搜索，不需要 API） |
| 分页控件 | `<button>` 上一页/下一页 | 前端分页，每页 20 条 |
| 删除按钮 | `<button>` 每行 | `DELETE /api/v1/admin/knowledge/documents/{id}` + 确认对话框 |
| 重新索引按钮 | `<button>` | `POST /api/v1/admin/knowledge/reindex` |
| 索引状态栏 | `<div>` 统计条 | `GET /api/v1/admin/knowledge/index-status` → `{total_docs, indexed_docs, pending_docs}` |
| 上传进度条 | `<progress>` | 大文件上传时的视觉反馈 |

**API 调用：**
```
GET     /api/v1/admin/knowledge/documents
POST    /api/v1/admin/knowledge/documents       ← 接线
DELETE  /api/v1/admin/knowledge/documents/{id}  ← 接线
POST    /api/v1/admin/knowledge/reindex         ← 接线
GET     /api/v1/admin/knowledge/index-status    ← 新增调用
```

---

#### 4.2.6 InsightsPage（容错增强）

**保留元素：** 词云 + 情绪时间线 + 热点柱状图

**新增/修改元素：**

| 元素 | 类型 | 来源 / 行为 |
|------|------|------------|
| 独立 loading/error 边界 | 每图表独立 StatusCard | 替代 Promise.all，单个图表失败不影响其他 |
| 时间范围选择器 | `<select>` | `?days=7\|30\|90` |
| 词云形状切换 | toggle | `circle` / `cardioid` / `diamond`（纯前端，ECharts wordCloud `shape` 参数） |
| 情绪图例交互 | ECharts legend toggle | 点击图例隐藏/显示系列（ECharts 内置） |

**API 调用（改为独立请求）：**
```
GET  /api/v1/admin/analytics/topic-cloud?days={N}
GET  /api/v1/admin/analytics/emotion-timeline?days={N}
GET  /api/v1/admin/analytics/hot-questions?days={N}
```

---

#### 4.2.7 AgentSettingsPage（增强）

**保留元素：** 提示词 textarea + 风格选择 + 主动推荐开关

**新增/修改元素：**

| 元素 | 类型 | 来源 / 行为 |
|------|------|------------|
| 提示词预览面板 | `<div>` 实时预览 | 将 `{stage}` 和 `{slots_summary}` 替换为示例值，显示渲染结果 |
| 温度参数 slider | `<input type="range">` 0-2 | 当前后端硬编码 0.3/0.7（双 agent 路由），作为未来扩展预留 |
| textarea 高度增加 | 从 6 行 → 12 行 | 容纳更长的自定义提示词 |

**API 调用（不变）：**
```
GET  /api/v1/admin/ai-persona
PUT  /api/v1/admin/ai-persona
```

---

#### 4.2.8 新增页面：模块管理（Module Management）

**路由：** `/modules`（或集成到现有设置页）

**目的：** 让院校管理员看到当前订阅的模块及其启用状态，并可自行开关（对无依赖模块）。

**UI 元素：**

| 元素 | 类型 | 来源 / 行为 |
|------|------|------------|
| 模块卡片列表 | `<div>` 网格 | 每个模块一张卡片，显示名称、描述、依赖、开关状态 |
| 模块开关 toggle | `<button role="switch">` | 对无下游依赖的模块可切换 |
| 依赖警告 | `<div>` 琥珀色提示 | 开启依赖模块时自动提示需要先开启前置模块 |
| 保存按钮 | `<button>` | 调用 `PUT /api/v1/admin/tenants/me/config` |

**API 调用：**
```
GET  /api/v1/admin/tenants/me/config     → 读取 modules 字段
PUT  /api/v1/admin/tenants/me/config     → 更新 modules 字段
```

---

## 5. 完整 API ↔ 页面映射总表

| API 端点 | 方法 | 使用页面 | 当前状态 |
|---------|------|---------|---------|
| `/auth/login` | POST | LoginPage | ✅ 已接线 |
| `/admin/brand-config` | GET | LoginPage(新), BrandSettingsPage, useBrandConfig | ✅ 已接线 |
| `/admin/brand-config` | PUT | BrandSettingsPage | ✅ 已接线 |
| `/admin/brand-config/logo` | POST | BrandSettingsPage | ❌ 未接线（后端存根） |
| `/admin/analytics/funnel` | GET | FunnelPage | ✅ 已接线 |
| `/admin/analytics/profile-dashboard` | GET | ProfileDashboardPage | ✅ 已接线 |
| `/admin/knowledge/documents` | GET | KnowledgeSettingsPage | ✅ 已接线 |
| `/admin/knowledge/documents` | POST | KnowledgeSettingsPage | ❌ 未接线 |
| `/admin/knowledge/documents/{id}` | DELETE | KnowledgeSettingsPage | ❌ 未接线 |
| `/admin/knowledge/reindex` | POST | KnowledgeSettingsPage | ❌ 未接线 |
| `/admin/knowledge/index-status` | GET | KnowledgeSettingsPage | ❌ 未调用 |
| `/admin/analytics/topic-cloud` | GET | InsightsPage | ✅ 已接线 |
| `/admin/analytics/emotion-timeline` | GET | InsightsPage | ✅ 已接线 |
| `/admin/analytics/hot-questions` | GET | InsightsPage | ✅ 已接线 |
| `/admin/ai-persona` | GET | AgentSettingsPage | ✅ 已接线 |
| `/admin/ai-persona` | PUT | AgentSettingsPage | ✅ 已接线 |
| `/admin/tenants/me` | GET | Sidebar（标题显示） | ✅ 已接线 |
| `/admin/tenants/me/config` | GET | Sidebar（菜单过滤）, ModulePage(新) | ✅ 已接线 |
| `/admin/tenants/me/config` | PUT | ModulePage(新) | ❌ 未接线 |
| `/admin/analytics/major-heatmap` | GET | — | ⚠️ 无页面使用 |
| `/admin/analytics/region-distribution` | GET | — | ⚠️ 无页面使用 |
| `/admin/analytics/competitive` | GET | — | ⚠️ 无页面使用 |
| `/admin/analytics/dialogue-quality` | GET | — | ⚠️ 无页面使用 |
| `/admin/analytics/annual-report` | GET | — | ⚠️ 无页面使用 |
| `/admin/departments` | GET | — | ⚠️ 存根 |
| `/admin/roles` | GET | — | ⚠️ 存根 |

---

## 6. 实施优先级

### P0 — 立即修复（阻断性）

| 任务 | 文件 | 工作量 |
|------|------|--------|
| LoginPage 登录前加载品牌配置（需后端配合公开 brand-config） | `LoginPage.tsx` + `middleware.py` | 30 min |
| KnowledgeSettingsPage 上传按钮接线 | `KnowledgeSettingsPage.tsx` | 30 min |
| KnowledgeSettingsPage 删除按钮接线 | `KnowledgeSettingsPage.tsx` | 20 min |
| KnowledgeSettingsPage 搜索+分页 | `KnowledgeSettingsPage.tsx` | 40 min |

### P1 — 本周完成（功能增强）

| 任务 | 文件 | 工作量 |
|------|------|--------|
| InsightsPage 独立请求容错 | `InsightsPage.tsx` | 30 min |
| BrandSettingsPage 补充缺失字段（favicon/欢迎语/登录背景） | `BrandSettingsPage.tsx` | 30 min |
| 各分析页面添加时间范围选择器 | FunnelPage + ProfileDashboardPage + InsightsPage | 60 min |
| AgentSettingsPage 提示词预览 + textarea 加高 | `AgentSettingsPage.tsx` | 30 min |
| 新增模块管理页面 | 新建 `ModuleSettingsPage.tsx` | 60 min |

### P2 — 后续迭代

| 任务 | 说明 |
|------|------|
| Logo 上传功能 | 等待后端文件存储实现 |
| 侧边栏收起/展开 | 响应式适配 + 汉堡菜单 |
| 租户下拉选择 | 需新建公开 API 或保持 URL 参数方案 |
| 分析页面接入 major-heatmap / region-distribution / competitive 等 5 个未使用 API | 扩展 InsightsPage 或新建专项页面 |
| 登录背景图渲染 | 依赖 `login_bg_url` 字段在表单中可配置 |

---

## 7. 不改动的部分

- 后端 API 签名不变
- 数据库 schema 不变
- CSS 变量换肤机制不变
- Sidebar 菜单结构不变（仅新增 ModuleSettingsPage 入口）
- 现有组件 API（StatusCard / PageHeader / chart 组件）不变，仅扩展 props

---

## 8. 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `admin-spa/src/pages/LoginPage.tsx` | 品牌 Logo + 背景图（P0） |
| 修改 | `admin-spa/src/pages/KnowledgeSettingsPage.tsx` | 上传/删除/搜索/分页（P0） |
| 修改 | `admin-spa/src/pages/InsightsPage.tsx` | 独立请求容错 + 时间选择器（P1） |
| 修改 | `admin-spa/src/pages/BrandSettingsPage.tsx` | 补充 favicon/欢迎语/登录背景（P1） |
| 修改 | `admin-spa/src/pages/FunnelPage.tsx` | 时间选择器（P1） |
| 修改 | `admin-spa/src/pages/ProfileDashboardPage.tsx` | 时间选择器（P1） |
| 修改 | `admin-spa/src/pages/AgentSettingsPage.tsx` | textarea 加大 + 预览（P1） |
| 新建 | `admin-spa/src/pages/ModuleSettingsPage.tsx` | 模块管理页（P1） |
| 修改 | `admin-spa/src/App.tsx` | 添加 /modules 路由 |
| 修改 | `admin-spa/src/components/Sidebar.tsx` | 添加模块管理菜单项 |
| 修改 | `backend/core/middleware.py` | `/api/v1/admin/brand-config` 加入公开路径（P0） |
