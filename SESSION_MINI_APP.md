# Session 指令：Mini-App 轨道

> 分支: `feat/mini-app` | 基于: `feat/foundation` | 与 Admin SPA 轨道无冲突

---

## 启动清单（按顺序执行）

### 1. 阅读文档（必读，5 分钟）

打开并阅读以下文件：

| 顺序 | 文件 | 关注内容 |
|------|------|---------|
| 1 | `COLLABORATION.md` | 分支策略、Session 启动清单、通信规则 |
| 2 | `CONVENTIONS.md` | Vue/TS 规范、API 契约 §2.2、§2.5（WebSocket 协议）、测试规范 |
| 3 | `SESSION_STATE.md` | 确认 Mini-App 轨道状态为 ⬜，更新为 🔵 |
| 4 | `docs/superpowers/specs/2026-05-18-b2b-platform-design.md` §6.2 | 白标方案——uni-app 构建配置注入 |
| 5 | `docs/superpowers/specs/2026-05-18-b2b-platform-design.md` §5.6 | 学生匿名对话 + 画像双归属模型 |

### 2. 创建分支

```bash
git fetch origin
git checkout feat/foundation           # Foundation 轨道的最新产出
git checkout -b feat/mini-app          # 从 foundation 切出新分支
```

### 3. 确认 Foundation API 可用

Foundation 后端需启动（端口 8000）。验证以下端点可访问：

```bash
# 1. 健康检查
curl http://localhost:8000/api/health

# 2. Guest 创建会话
curl -X POST http://localhost:8000/api/v1/chat/session \
  -H "X-Tenant: gdufs" \
  -H "Content-Type: application/json"

# 应返回 {"session_id": "...", "guest": true}
```

### 4. 更新状态

编辑 `SESSION_STATE.md`，将 Mini-App 轨道状态改为 `🔵 进行中`。

---

## 工作内容

### 目标

用 uni-app (Vue 3) 从零创建院校招生咨询小程序。一套源码，每院校独立构建产出独立小程序包。

### 项目位置

```
gaokao_agents/mini-app/          # 新建目录，不影响 backend/ 和 admin-spa/
```

### 依赖关系

**Mini-App → Foundation API**

| 你需要的 API | 端点 | 状态 |
|-------------|------|------|
| 创建会话 (guest) | `POST /api/v1/chat/session` | ✅ 已实现，支持匿名 |
| WebSocket 对话 | `WS /api/v1/chat/session/{id}` | ✅ 已实现，支持 LLM 容错 |
| 获取推荐 | `GET /api/v1/recommendations` | ✅ 已实现 |
| 提交反馈 | `POST /api/v1/recommendations/feedback` | ✅ 已实现 |
| 学生注册 | `POST /api/v1/auth/register` | ✅ 已实现 |
| 学生登录 | `POST /api/v1/auth/login` | ✅ 已实现 |
| 获取画像 | `GET /api/v1/profiles` | ✅ 已实现 |
| 院校信息 | `GET /api/v1/colleges` | ✅ 已实现 |

**所有请求必须带 `X-Tenant: <slug>` 头**，slug 在构建时注入。

### 你要创建的文件

```
mini-app/
├── package.json
├── vite.config.ts                    # uni-app Vite 配置
├── build.config.js                   # 读取 TENANT 环境变量
├── tenants/
│   └── gdufs.json                    # 广东工业大学构建配置
├── scripts/
│   ├── build_one.sh                  # TENANT=gdufs npm run build
│   └── build_all.sh                  # 批量构建所有 tenants
├── src/
│   ├── App.vue                       # 初始化：读取构建配置 → 设置 X-Tenant
│   ├── manifest.json                 # 微信小程序配置
│   ├── pages.json                    # 页面路由
│   ├── utils/
│   │   ├── config.ts                 # 构建时注入的 tenant 配置读取
│   │   ├── api.ts                    # HTTP 请求封装 (自动带 X-Tenant + JWT)
│   │   └── websocket.ts             # WebSocket 连接管理 (断连重连)
│   ├── stores/
│   │   ├── chat.ts                   # Pinia: sessionId, messages, stage, profile
│   │   └── user.ts                   # Pinia: token, userInfo, isGuest
│   ├── pages/
│   │   ├── chat/
│   │   │   └── index.vue             # AI 对话页（消息列表 + 输入框 + 阶段指示器）
│   │   ├── recommendations/
│   │   │   └── index.vue             # 推荐结果页
│   │   └── profile/
│   │       └── index.vue             # 画像展示页 + 注册引导
│   └── components/
│       ├── ChatMessage.vue           # 单条消息气泡 (user/assistant/thinking)
│       ├── StageIndicator.vue        # 四阶段进度条
│       ├── ProfileSidebar.vue        # 可展开的画像侧边面板
│       ├── RecommendationCard.vue    # 推荐专业卡片（专业名、推荐理由、分数线溯源）
│       └── LoginModal.vue            # 登录/注册弹窗（不阻断对话）
```

### 与 Admin SPA 轨道的隔离

| | Admin SPA | Mini-App |
|---|---|---|
| 目录 | `admin-spa/` | `mini-app/` |
| 技术栈 | React + TS + Tailwind | Vue 3 + uni-app |
| 构建工具 | Vite | uni-app Vite |
| API 消费 | 管理端端点 | 学生端端点 |
| Git 分支 | `feat/admin-spa` | `feat/mini-app` |

**完全隔离。零文件重叠。** 唯一可能冲突的 `SESSION_STATE.md` 各自更新自己的轨道行。

---

## 开发规范

### 构建配置注入

每个 tenant 的配置在 `tenants/<slug>.json`，构建时注入到 `src/utils/config.ts`：

```json
// tenants/gdufs.json
{
  "appId": "wx_gdufs_app_id",
  "tenantSlug": "gdufs",
  "brand": {
    "name": "广东工业大学",
    "shortName": "广工",
    "primaryColor": "#1a56db",
    "welcomeText": "欢迎了解广东工业大学！我是你的专属AI招生顾问..."
  },
  "features": {
    "guestMode": true,
    "crossCollegeCompare": true
  }
}
```

```typescript
// src/utils/config.ts（构建时替换）
import tenantConfig from '@/tenant.config';
export const TENANT_SLUG = tenantConfig.tenantSlug;
export const BRAND = tenantConfig.brand;
```

### X-Tenant 请求头

所有 API 调用**必须**带 `X-Tenant: <slug>`。在 `api.ts` 的请求拦截器中统一注入：

```typescript
// ✅ 每个请求自动带
uni.request({
  url: '/api/v1/chat/session',
  header: {
    'X-Tenant': TENANT_SLUG,        // 从构建配置读取
    'Authorization': `Bearer ${token}` // 如果已登录
  }
});
```

### WebSocket 消息协议

见 `CONVENTIONS.md` §2.5。关键消息类型：

| 接收 (Server→Client) | 处理方式 |
|----------------------|---------|
| `thinking` | 显示 "..." 输入中动画 |
| `message` | 添加 AI 消息到列表，清除 thinking |
| `profile_update` | 更新侧边面板的 RIASEC 进度 |
| `stage_change` | 更新阶段指示器 |
| `summary` | 弹窗展示阶段总结 |
| `error` | Toast 错误提示，不断开连接 |

### 匿名对话流程

```
用户扫码打开小程序
  → POST /api/v1/chat/session (无 Authorization 头)
    → 返回 { session_id, guest: true }
  → WebSocket 连接 /api/v1/chat/session/{session_id}
  → 开始对话（无需注册）
  → 对话过程中画像实时更新（profile_update 消息）
  → 到达 CONFIRM/DONE 阶段 → 引导注册 "想保存画像并对比多所院校？"
  → 用户注册 → session 数据合并
```

### 构建命令

```bash
# 单院校构建
TENANT=gdufs npm run dev:mp-weixin    # 开发
TENANT=gdufs npm run build:mp-weixin  # 生产

# 产物在 dist/gdufs/，用微信开发者工具打开
```

---

## 每日维护

### Session 开始时

1. `git pull origin feat/mini-app`
2. 读 `SESSION_STATE.md` 确认状态

### Session 结束时

1. `git push origin feat/mini-app`
2. 更新 `SESSION_STATE.md`：今天完成了什么、接下来做什么
3. Commit 并 push

### 提交规范

```
feat: init uni-app project with tenant build config injection
feat: add chat page with WebSocket integration
feat: add recommendation page with evidence trace display
fix: WebSocket reconnect not resuming session state
```

---

## 完成标志

- [ ] `TENANT=gdufs npm run build:mp-weixin` 成功
- [ ] 扫码 → 对话 3+ 轮 → 画像更新 → 推荐展示 全链路
- [ ] 匿名可对话（不需登录）
- [ ] 构建配置不同 tenant 产出不同品牌色和名称
- [ ] WebSocket 断连后重连可恢复对话
