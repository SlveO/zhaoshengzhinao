# Admin Frontend Redesign V2 — Design Spec

> 基于 `招生智脑_前端复刻指令.md`，经 brainstorming 确认方向后修订。
> 分支：`feat/admin-redesign-v2`

## 1. 整体设计方向

- **布局**：顶部导航栏 + 左侧可收起深色侧栏 + 右侧内容区
- **主色**：深蓝 `#1E40AF`（Tailwind blue-800），hover `#1E3A8A`（blue-900）
- **侧栏背景**：`#0F172A`（slate-900）
- **页面背景**：`#F4F7FB`
- **卡片背景**：`#FFFFFF`，边框 `#E5E9F2`，圆角 10px
- **字体**：Noto Sans SC（Google Fonts），主体 13px
- **目标宽度**：1440px，最小兼容 1280px

## 2. 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 框架 | React 18 + TypeScript | 沿用现有 |
| 样式 | Tailwind CSS v4 | 已安装，本次开始实际使用 |
| 图标 | lucide-react | 新增依赖，替换 Unicode 符号 |
| 图表 | ECharts (echarts-for-react) | 沿用现有，功能完整 |
| 路由 | react-router-dom v7 | 沿用现有 |
| 状态 | zustand | 沿用现有 |
| HTTP | axios | 沿用现有 |

**不引入 shadcn/ui**：当前自定义组件体系（Modal、StatusCard、卡片、按钮等）功能完整，用 Tailwind 重绘即可，避免额外复杂度。

## 3. 布局框架

### 3.1 顶部导航栏（Header）

```
[Logo] | 招生管理平台                    📅 2025年5月21日 星期四  🔔2  [头像] 招生办公室 ▽
```

- 高度 56px，白色背景，底部 1px 灰色边框
- 左侧：品牌 Logo（从 brand-config API 获取）+ 竖线分隔 + "招生管理平台"
- 右侧：日期（动态）+ 通知铃铛（红色角标 unreadNotificationCount）+ 用户头像 + 角色名 + 下拉箭头

### 3.2 左侧导航（Sidebar）

- 宽度：展开 220px / 收起 64px，CSS transition
- 背景 `#0F172A`，文字 `rgba(255,255,255,0.55)`，选中态 `rgba(255,255,255,0.1)` bg + 白色文字
- 菜单项使用 lucide-react 图标

```text
导航
  LayoutDashboard    工作台        /dashboard
  Users              线索管理      /leads
  MessageSquare      咨询管理      /consultations
  User               画像看板      /profile
  BarChart3          洞察分析      /insights
  FileText           招生报告      /reports
  Radio              渠道管理      /channels
管理
  BookOpen           知识库        /knowledge
  Palette            品牌配置      /brand
  Bot                Agent设置     /agent-settings
  Blocks             模块管理      /modules
```

- 底部"收起"按钮（ChevronLeft/ChevronRight 图标）
- 侧栏顶部：品牌 Logo + 名称

## 4. 页面设计

### 4.1 登录页 /login

- 保持现有双栏布局（品牌面板 + 登录表单）
- 品牌面板使用深蓝渐变（`linear-gradient(135deg, #1E40AF, #1E3A8A)`）
- 预填 tenant 时显示品牌 Logo（从 brand-config API 获取）
- 支持 login_bg_url 作为背景图

### 4.2 工作台 /dashboard（重点改造）

**Hero 区**：
- 深蓝渐变背景（`#1E40AF → #1E3A8A`），半透明水印文字
- 标题"高校招生运营工作台"（24px 700 白色）
- 副标题"· 生源转化闭环 ·"

**4 列指标卡片**（替换原有的 stat-grid）：
1. 渠道汇总 · 今日 — 大数字 + 迷你趋势图（mock）
2. 咨询承接 · 今日 — AI/人工接待量 + 平均响应时长（mock）
3. 意向识别 · 今日 — 圆形进度环 + 高/中/低意向（mock）
4. 跟进进度 · 今日 — 百分比 + 进度条 + 明细（mock）

**底部两列**：
- 左：招生动态 — 列表形式，NEW 角标（mock）
- 右：待办提醒 — 红色数字气泡（mock）

所有数据使用 `const MOCK_DATA` 占位，顶部注释 `// TODO: replace with API`。

### 4.3 线索管理 /leads（新增，mock 数据）

全宽工作台布局，不含左侧营销面板。

- 顶部：标题"高意向生源工作台" + "今日新增 N 条高意向线索" + 四步流程指示（咨询沉淀→标签提取→意向评分→人工跟进，当前步骤高亮）
- 线索表格：学生名 + 意向积分气泡 + 画像（省份/科类/分数）+ 关注点标签 + 动作按钮（优先跟进/建议联系/持续观察）
- 选中行展开底部详情面板：当前线索建议 + 学生画像 + 核心关注 + 推荐材料
- 动作按钮：priority → 蓝色实心"优先跟进"，suggest → 蓝色文字"建议联系"，observe → 灰色文字"持续观察"

全部 mock 数据。

### 4.4 咨询管理 /consultations（新增，mock 数据）

- 顶部筛选栏：时间范围、状态（已处理/待处理/AI处理）
- 咨询会话列表表格：学生信息 + 时间 + 时长 + 主题摘要 + 处理方式 + 状态
- 点击行展开咨询对话记录（mock 对话内容）
- 搜索 + 分页
- 全部 mock 数据

### 4.5 渠道管理 /channels（新增，mock 数据）

- 渠道卡片网格：官网 / 微信公众号 / 微信小程序 / 线下宣讲会
- 每个卡片：渠道名 + 图标 + 今日新增线索数 + 趋势小图 + 转化率
- 全部 mock 数据

### 4.6 画像看板 /profile

- 保持现有 ECharts 图表（雷达图 + 柱状图）
- 时间范围选择器
- 套用新视觉：卡片使用 Tailwind 类名

### 4.7 洞察分析 /insights

- 保持现有三块独立图表（词云 + 情感时间线 + 热点）
- 每个图表独立 StatusCard（loading/error/empty）
- 时间范围选择器
- 套用新视觉

### 4.8 招生报告 /reports（改造为策略反哺风格）

基于指令文档 4.1-4.4 节：
- 顶部标题区："招生策略反哺" 标签 + "让真实咨询数据，指导下一次招生动作"
- 策略视角 Tab（综合视角 / 专业吸引力 / 地域竞争力）
- 三栏数据：学生关注变化 / 现有宣讲缺口 / 建议招生动作
- 第 4 条用 `filter: blur(4px)` 模糊锁定
- 底部"还有 N 条..." 链接
- 全部 mock 数据

### 4.9 知识库 /knowledge

- 保持现有功能：上传 / 删除 / 搜索 / 分页
- 套用新视觉：Tailwind 表格、按钮、搜索框

### 4.10 品牌配置 /brand

- 保持现有功能：Logo / 品牌色 / 欢迎语 / 登录背景
- 套用新视觉：Tailwind 表单、颜色选择器

### 4.11 Agent 设置 /agent-settings

- 保持现有功能：Prompt 编辑器 + 风格选择 + 实时预览
- 套用新视觉

### 4.12 模块管理 /modules

- 保持现有功能：开关卡片 + 依赖提示
- 套用新视觉

## 5. 不做的内容

- ~~招生漏斗页~~ — 用户明确删除
- ~~六步流程条~~ — Dashboard 简化版不含
- ~~5 列指标卡 + 今日转化动作蓝卡~~ — Dashboard 简化为 4 列 + 底部两列
- 线索管理 / 咨询管理 / 渠道管理 — 用 mock 数据实现前端，不接后端
- 移动端适配 — 仅支持 1280px+

## 6. 组件清单

新增组件：
- `Header` — 顶部导航栏（替换当前 topbar）
- `Sidebar` — 重写（lucide 图标 + 分组 + 可收起）
- `DashboardHero` — Dashboard Hero 区
- `MetricCard` — 通用指标卡片
- `ProgressRing` — SVG 环形进度（意向积分用）
- `StrategyReport` — 策略报告三栏（招生报告页用）
- `BlurredRow` — 模糊锁定行
- `LeadWorkbench` — 线索页工作台（表格 + 详情面板）
- `ConsultationList` — 咨询会话列表
- `ChannelCard` — 渠道卡片网格

改造组件：
- `DashboardLayout` — 适配新 Header + Sidebar
- `StatusCard` — 保持逻辑，Tailwind 样式
- `PageHeader` — 保持逻辑，Tailwind 样式
- `Modal` — 保持逻辑，Tailwind 样式

## 7. 实现优先级

| 优先级 | 内容 |
|---|---|
| P0 | 布局框架（Header + Sidebar + DashboardLayout）|
| P0 | Dashboard 页（Hero + 4 指标卡 + 底部两列）|
| P0 | 登录页适配 |
| P1 | 线索管理页（Lead Workbench，mock 数据）|
| P1 | 招生报告页（策略反哺，mock 数据）|
| P1 | 咨询管理 + 渠道管理（mock 数据）|
| P1 | 其余页面套新视觉（profile/insights/knowledge/brand/agent/modules）|
| P2 | 图表优化、动画过渡、细节打磨 |

## 8. 与指令文档的差异

| 指令文档 | 本设计 | 原因 |
|---|---|---|
| Tailwind + shadcn/ui | Tailwind only，保留自定义组件 | shadcn/ui 引入成本高，现有组件够用 |
| recharts | ECharts | 已安装且功能更强 |
| 6 步流程条 | 去掉 | 用户要求简化 Dashboard |
| 线索/咨询/渠道等页面 | 用 mock 数据实现前端 | 用户要求先做前端，后续接后端 |
| 6 列指标卡 | 4 列指标卡 + 底部两列 | 用户要求简化 |
| #1677FF 主色 | #1E40AF 深蓝 | 用户选择 |
| 200px/64px 侧栏 | 220px/64px | 保持现有宽度逻辑 |
