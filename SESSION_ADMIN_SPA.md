# Session 指令：Admin SPA 轨道

> 分支: `feat/admin-spa` | 基于: `feat/foundation` | 与 Mini-App 轨道无冲突

---

## 启动清单（按顺序执行）

### 1. 阅读文档（必读，5 分钟）

打开并阅读以下文件：

| 顺序 | 文件 | 关注内容 |
|------|------|---------|
| 1 | `COLLABORATION.md` | 分支策略、Session 启动清单、通信规则 |
| 2 | `CONVENTIONS.md` | TypeScript 规范、API 契约 §2.2-2.4、测试规范 |
| 3 | `SESSION_STATE.md` | 确认 Admin SPA 轨道状态为 ⬜，更新为 🔵 |
| 4 | `docs/superpowers/specs/2026-05-18-b2b-platform-design.md` §6.1 | 白标方案——CSS 变量换肤机制 |
| 5 | `docs/superpowers/specs/2026-05-18-b2b-platform-design.md` §4 | 后端 API 路由结构（了解有哪些端点） |

### 2. 创建分支

```bash
git fetch origin
git checkout feat/foundation           # Foundation 轨道的最新产出
git checkout -b feat/admin-spa         # 从 foundation 切出新分支
```

### 3. 确认 Foundation 可用

```bash
cd backend
# 确认后端可启动（需要 Docker）
docker compose up -d db redis
DATABASE_URL="postgresql+asyncpg://gaokao:gaokao@localhost:5432/gaokao" python -c "
from main import app; print('FastAPI app loaded OK')
"
```

不需要启动后端开发服务器——Admin SPA 开发时用 Vite proxy 或 mock 数据。

### 4. 更新状态

编辑 `SESSION_STATE.md`，将 Admin SPA 轨道状态改为 `🔵 进行中`。

---

## 工作内容

### 目标

用全新 Vite + React + TypeScript + Tailwind 项目重建管理端。CSS 变量驱动态换肤。**一套代码，所有院校共用。**

### 项目位置

```
gaokao_agents/admin-spa/          # 新建目录，不影响 backend/
```

### 依赖关系

**Admin SPA → Foundation API**

| 你需要的 API | 端点 | 状态 |
|-------------|------|------|
| 品牌配置 | `GET/PUT /api/v1/admin/brand-config` | ✅ 已实现 |
| Logo 上传 | `POST /api/v1/admin/brand-config/logo` | ✅ stub |
| 招生漏斗 | `GET /api/v1/admin/analytics/funnel` | ✅ stub (返回空数据) |
| 画像看板 | `GET /api/v1/admin/analytics/profile-dashboard` | ✅ stub |
| 租户信息 | `GET /api/v1/admin/tenants/me` | ✅ 已实现 |
| 租户配置 | `GET/PUT /api/v1/admin/tenants/me/config` | ✅ 已实现 |
| 知识库文档 | `GET /api/v1/admin/knowledge/documents` | ✅ 已实现 |
| 登录 | `POST /api/v1/auth/login` | ✅ 已实现 |

**不需要的 API：** 专业热度、地域分布、对比流失、年度报告、院系、角色——这些是增值模块，Phase 3 再做。

### 你要创建的文件

```
admin-spa/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx                    # 路由 + BrandProvider
│   ├── api/
│   │   └── client.ts              # Axios 实例 (Base URL, X-Tenant, JWT interceptor)
│   ├── hooks/
│   │   └── useBrandConfig.ts      # 拉取品牌配置 → 设置 CSS 变量
│   ├── stores/
│   │   └── authStore.ts           # Zustand: token, user, login(), logout()
│   ├── components/
│   │   ├── DashboardLayout.tsx     # 侧边栏 + 顶栏 + <Outlet>
│   │   ├── Sidebar.tsx            # 按模块开关过滤菜单项
│   │   ├── ProtectedRoute.tsx     # 未登录 → /login
│   │   └── charts/
│   │       ├── FunnelChart.tsx    # ECharts 漏斗图
│   │       └── RadarChart.tsx     # ECharts 雷达图
│   └── pages/
│       ├── LoginPage.tsx          # 品牌 Logo + 主题色 + 登录表单
│       ├── FunnelPage.tsx         # 招生漏斗数据面板
│       ├── ProfileDashboardPage.tsx # 画像看板（雷达图+饼图）
│       ├── BrandSettingsPage.tsx  # Logo 上传 + 颜色设置 + 名称编辑
│       └── KnowledgeSettingsPage.tsx # 文档列表 + Excel 上传
```

### 与 Mini-App 轨道的隔离

- **Admin SPA 目录**: `admin-spa/`
- **Mini-App 目录**: `mini-app/`
- **互不重叠**。你们可以同时改各自目录的文件，不会冲突。
- 两个轨道都不修改 `backend/` 下的文件
- **共用同一个 backend API**，但各自消费不同的端点

### 两个轨道同时修改的文件

**只有两个文件可能冲突：**

| 文件 | 谁会改 | 如何避免冲突 |
|------|--------|-------------|
| `SESSION_STATE.md` | 两个轨道 | 各自更新自己的轨道行，不要改对方的行 |
| `.gitignore` | 可能需要 | 如果需要加 ignore 规则，加在文件末尾，不要删别人的 |

**其他所有文件都是各自目录的，不存在冲突。**

---

## 开发规范

### CSS 变量命名

所有品牌色通过 CSS 变量引用，永远不硬编码颜色值：

```css
/* ✅ 正确 */
.sidebar { background: var(--brand-primary); }
.button { background: var(--brand-secondary); }

/* ❌ 错误 */
.sidebar { background: #1a56db; }
```

### 模块开关

侧边栏菜单项必须检查 `tenant.config.modules` 来控制可见性。服务端也已经做了模块开关校验（403），前端也做一遍避免用户看到不可用的菜单。

### API 请求头

每个请求必须带：
```
X-Tenant: <slug>           # 从登录响应或 URL 参数获取
Authorization: Bearer <jwt> # 从 authStore 获取
```

### 登录流程

```
用户打开 admin.our-domain.com
  → 前端检查 localStorage 是否有 token
  → 有：调 GET /api/v1/admin/tenants/me 验证 token
    → 成功：进入 Dashboard
    → 失败：清除 token → 显示登录页
  → 无：显示登录页
  → 用户输入 username + password
  → POST /api/v1/auth/login
  → 成功：存 token → 调 GET /api/v1/admin/brand-config → 设置 CSS 变量 → 进入 Dashboard
  → 失败：显示错误信息
```

---

## 每日维护

### Session 开始时

1. `git pull origin feat/admin-spa`（如果之前有其他 session 在此分支）
2. 读 `SESSION_STATE.md` 确认状态

### Session 结束时

1. `git push origin feat/admin-spa`
2. 更新 `SESSION_STATE.md`：今天完成了什么、接下来做什么
3. Commit 并 push `SESSION_STATE.md`

### 提交规范

```
feat: add login page with brand-aware theming
feat: add funnel dashboard with ECharts
fix: sidebar menu not filtering by module config
```

---

## 完成标志

- [ ] `npm run build` 成功
- [ ] 登录 → Dashboard → 漏斗页面 → 画像页面 → 品牌设置 → 知识库管理 全流程可用
- [ ] 用 `X-Tenant: gdufs` 和 `X-Tenant: default` 分别登录，侧边栏颜色不同
- [ ] 模块开关控制菜单项可见性（gdufs 开启了 major_heatmap，default 没开）
