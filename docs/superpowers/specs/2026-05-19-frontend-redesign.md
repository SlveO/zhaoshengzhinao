# 招生智脑前端重设计 — 技术文档

> 日期: 2026-05-19 | 背景: V2 四子系统后端已完成，前端需统一重构

---

## 一、当前问题诊断

| # | 问题 | 影响 |
|---|------|------|
| 1 | `AgentSettingsPage` 已创建但未接入 App.tsx 路由 | AI 设置页面无法访问 |
| 2 | `AgentSettingsPage` 未在 Sidebar 添加菜单项 | 用户找不到入口 |
| 3 | 新建 tenant 的 modules config 不含新模块 key | 增强分析菜单被隐藏 |
| 4 | 学生端对比页需要注册登录才能访问 | 匿名用户无法用跨院校对比 |
| 5 | 管理端页面为 V1 阶段独立开发，风格不统一 | 用户体验割裂 |

**1-3 已修复，4-5 需要新 session 处理。**

---

## 二、前端架构现状

### 管理端 (Admin SPA)

```
admin-spa/src/
├── App.tsx                         # 路由（缺 agent-settings）
├── api/client.ts                   # Axios + X-Tenant + JWT
├── hooks/useBrandConfig.ts         # CSS 变量换肤
├── stores/authStore.ts             # Zustand 认证
├── components/
│   ├── DashboardLayout.tsx         # 侧边栏 + 顶栏 + <Outlet>
│   ├── Sidebar.tsx                  # 菜单（缺 AI 设置）
│   ├── ProtectedRoute.tsx          # 登录守卫
│   └── charts/{Funnel,Radar}Chart.tsx
├── pages/
│   ├── LoginPage.tsx               # ✅ 品牌感知登录
│   ├── FunnelPage.tsx              # ✅ 招生漏斗
│   ├── ProfileDashboardPage.tsx    # ✅ 画像看板
│   ├── BrandSettingsPage.tsx       # ✅ 品牌设置
│   ├── KnowledgeSettingsPage.tsx   # ✅ 知识库管理
│   ├── InsightsPage.tsx            # ✅ 增强分析（新）
│   └── AgentSettingsPage.tsx       # ❌ 已创建但未接入
└── types/index.ts
```

### 学生端 (Mini-App H5)

```
mini-app/src/
├── App.vue                         # 品牌配置注入
├── pages/
│   ├── chat/index.vue              # AI 对话（主页面）
│   ├── recommendations/index.vue   # 推荐结果
│   ├── profile/index.vue           # 个人画像
│   └── compare/index.vue           # 跨院校对比（新）
├── components/
│   ├── ChatMessage.vue
│   ├── StageIndicator.vue
│   ├── ProfileSidebar.vue
│   ├── RecommendationCard.vue
│   └── LoginModal.vue
├── stores/{chat,user}.ts
└── utils/{api,config,websocket}.ts
```

---

## 三、需修复项（按优先级）

### P0: 管理端 AgentSettingsPage 接入

**文件**: `admin-spa/src/App.tsx`, `admin-spa/src/components/Sidebar.tsx`

```tsx
// App.tsx — 加 import + route
import AgentSettingsPage from './pages/AgentSettingsPage'
<Route path="agent-settings" element={<AgentSettingsPage />} />

// Sidebar.tsx — 加菜单项
{ path: '/agent-settings', label: 'AI 设置', module: null, icon: '🤖' },
```
✅ 已修复

### P0: Tenant 默认启用新模块

新建 tenant 时在 config.modules 中包含 topic_cloud, emotion_timeline, hot_questions。
✅ 已修复 SCNU tenant

### P1: 学生端对比页支持匿名访问

当前 `compare/recommendations` 需要 JWT auth。匿名用户应能用当前 session 的 profile 快照做对比。

**方案**: 
- 对比 API 接受 `?profile_snapshot={JSON}` 备选参数
- chat 页面跳转对比页时传递 profile_snapshot

### P2: 管理端 UI 统一

当前 6 个页面各自独立实现，风格不完全一致。建议：
- 统一卡片样式（border-radius, shadow, padding）
- 统一 loading/error/empty 状态组件
- 统一图表配色方案（使用品牌色）

### P3: 学生端对话页增强

- chat 页面 header 按钮"对比"应动态可用（画像 L2+ 才可点）
- 添加"重新开始"按钮（清除 session 重建）
- 对话完成后自动弹出对比引导

---

## 四、新 session 执行清单

### 分支: `feat/frontend-polish`

### 任务

1. **AgentSettingsPage 接入** [5 min] — 已在 App.tsx + Sidebar 添加
2. **学生端对比页匿名支持** [20 min] — 改 compare API + chat 页面跳转
3. **统一管理端 UI** [30 min]
   - 抽取 `StatusCard` 组件（loading/error/empty 三态）
   - 统一图表配色为 CSS 变量 `--brand-primary`
   - 统一页面头部 `PageHeader` 组件
4. **学生端对话页增强** [20 min]
   - 对比按钮状态管理
   - 阶段完成自动弹窗引导对比
5. **npm run build 验证** [5 min]

### 碰的文件

```
admin-spa/src/App.tsx                    # 加 AgentSettingsPage route
admin-spa/src/components/Sidebar.tsx     # 加 AI 设置菜单
admin-spa/src/components/StatusCard.tsx  # 新建：通用状态组件
admin-spa/src/components/PageHeader.tsx  # 新建：页面头部
admin-spa/src/pages/*.tsx               # 统一使用 StatusCard + PageHeader
mini-app/src/pages/chat/index.vue       # 对比按钮状态 + 自动引导
mini-app/src/pages/compare/index.vue    # 支持匿名 profile_snapshot
backend/api/routes/compare.py           # 支持 profile_snapshot 参数
```

### 不碰

```
backend/agents/      ← 不动
backend/core/        ← 不动
backend/admin/       ← 不动
```

---

## 五、验证标准

- [ ] `http://localhost:3001?tenant=scnu` → 侧边栏有 "增强分析" 和 "AI 设置"
- [ ] 增强分析页展示词云、情绪线、热点图（非空数据）
- [ ] AI 设置页可编辑提示词并保存
- [ ] `http://localhost:3002` → 匿名对话后点"对比" → 看到跨院校推荐
- [ ] Admin SPA 所有页面 loading/error/empty 状态一致
