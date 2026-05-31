# ABC 子任务实现报告

> 日期: 2026-05-26 | 分支: feat/admin-redesign-v2

---

## 一、变更概览

本次在 `feat/admin-redesign-v2` 分支上完成 4 项子任务，涉及 5 个文件、+193/-9 行。

| 任务 | 说明 | 涉及文件 |
|------|------|----------|
| C-3 | 聊天等待状态指示 | `mini-app/src/pages/chat/index.vue` |
| C-1 | 学校信息页 → 聊天页自动提问 | `mini-app/src/pages/school/index.vue` + `chat/index.vue` |
| C-2 | 登录弹窗集成 | `profile/index.vue` + `recommendations/index.vue` |
| B   | 事件日志管道 | `backend/api/routes/miniapp.py` |

---

## 二、各任务详细说明

### C-3: 聊天等待状态指示

**问题:** 用户发送消息后，在 AI 回复到达前无任何视觉反馈，尤其在 HF Spaces 代理的 JSON 模式下等待时间较长。

**方案:** 新增 `thinkingStatus` ref，在消息发送各阶段显示不同状态文本：

| 阶段 | 状态文本 | 触发时机 |
|------|----------|----------|
| 消息发出 | "正在检索数据..." | `sendMessage()` 开始时 |
| 8秒轮询回退 | "正在生成回答..." | `pollTimer` 触发时 |
| 收到任何响应 | 状态消失 | JSON/SSE done/error/轮询成功 |

**UI:** 在消息列表底部添加带 `statusPulse` 呼吸动画的状态栏，仅在 `thinkingStatus` 非空时显示。

---

### C-1: 学校信息页入口跳转

**问题:** 学校信息页 8 个入口原先使用 `uni.showToast` 桩代码，无实际功能。

**方案:** 使用 uni-app 事件总线实现跨页面通信：

1. **学校信息页** (`school/index.vue`): 构建问题映射表 `questionMap`，点击入口时 `uni.$emit("chat:prefill", question)` + `uni.switchTab` 到聊天页
2. **聊天页** (`chat/index.vue`): `onMounted` 时注册 `uni.$on("chat:prefill", handlePrefill)`，收到事件后自动填入问题并发送

**原因:** `uni.switchTab` 不支持 `query` 参数传递给 tab 页面，因此使用事件总线方案。

---

### C-2: 登录弹窗集成

**问题:** `LoginModal.vue` 组件已存在但未被任何页面使用，未登录用户无法感知登录入口。

**方案:**

- **profile 页面:** 导入 `useUserStore` + `LoginModal`，条件渲染按钮 — 游客显示"登录查看完整档案"，已登录用户显示"去 AI 咨询"
- **recommendations 页面:** 同上，额外为游客显示登录提示卡 `.login-prompt`
- 登录成功后各自重新加载页面数据（`loadProfile()` / `loadRecommendations()`）

---

### B: 事件日志管道

**问题:** 聊天流程缺少行为追踪，无法分析用户会话质量。

**方案:** 在 `send_chat_message` 路由的 4 个关键节点插入 `write_event()` 调用：

| 事件类型 | 触发位置 | Payload |
|----------|----------|---------|
| `chat_message_sent` | 用户消息保存后 | `message_length` |
| `chat_rag_completed` | RAG 检索完成后 | `sources_count`, `top_score` |
| `chat_error` | LLM 流式异常 | `error_code`, `error_message` |
| `chat_response_completed` | AI 回复完成 | `response_length`, `profile_updated` |

所有事件写入均包在 `try/except: pass` 中，确保日志失败不阻断聊天流程。`tenant_id` 通过 `resolve_tenant()` 在函数开头统一获取。

---

## 三、如何启动服务进行体验

### 前提条件

- Docker Desktop 已安装并运行
- 已设置 `DEEPSEEK_API_KEY` 环境变量（AI 聊天功能必须）

### 启动命令

```bash
# 进入项目目录
cd D:\_Greatest_programmer\_Projects\gaokao_agents

# 设置 DeepSeek API Key（必须）
# Windows PowerShell:
$env:DEEPSEEK_API_KEY = "your-api-key-here"

# Windows CMD:
set DEEPSEEK_API_KEY=your-api-key-here

# 构建并启动全部服务
docker compose up -d --build

# 查看服务启动状态
docker compose ps

# 查看后端日志（确认无报错）
docker compose logs backend --tail=30
```

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 学生端 (Mini-App) | **http://localhost** | 小程序 H5 版，默认端口 80 |
| 管理端 (Admin-SPA) | **http://localhost/admin/** | B2B 管理后台 |
| 后端 API | **http://localhost/api/v1/docs** | FastAPI Swagger 文档 |

### 验收测试流程

#### C-3: 聊天等待状态

1. 打开 http://localhost → 进入"AI 咨询"标签页
2. 输入任意问题（如"华师的计算机专业怎么样？"）并发送
3. 观察消息气泡下方出现"正在检索数据..."状态文本
4. 如网络较慢，8秒后文本变为"正在生成回答..."
5. AI 回复到达后，状态文本消失

#### C-1: 学校信息页入口

1. 打开 http://localhost → 点击底部"学校"标签页
2. 点击任意入口卡片（如"学校概况"）
3. 页面自动跳转到"AI 咨询"标签页，输入框自动填入对应问题并发送
4. 验证 AI 开始回答该问题

#### C-2: 登录弹窗

1. 打开 http://localhost → 进入"我的"标签页
2. 未登录状态下应看到"登录查看完整档案"按钮
3. 点击后弹出登录弹窗
4. 登录成功后弹窗关闭，页面信息刷新
5. 在"报考建议"页面验证同样流程

#### B: 事件日志

```bash
# 先执行一次聊天（发送一条消息）

# 查询事件日志
docker compose exec backend python -c "
import asyncio
from sqlalchemy import select, text
from models import async_session

async def check():
    async with async_session() as db:
        result = await db.execute(text('SELECT event_type, payload FROM event_logs ORDER BY created_at DESC LIMIT 10'))
        rows = result.fetchall()
        for r in rows:
            print(f'{r[0]}: {r[1]}')

asyncio.run(check())
"
```

预期看到 `chat_message_sent`、`chat_rag_completed`、`chat_response_completed` 三种事件。

#### 回归测试

```bash
# 运行后端单元测试，确保无破坏
docker compose exec backend pytest tests/unit/ -v
```

---

## 四、验收测试中发现并修复的 Bug

### Bug 1: 401 Unauthorized — 小程序路由未加入白名单

**现象:** `/api/v1/miniapp/enter` 返回 401 Unauthorized。

**根因:** `TenantResolutionMiddleware` 要求所有请求带 `X-Tenant` 请求头，C 端小程序使用 `tenant_slug` 请求体字段代替，但路由未加入 `TENANT_PUBLIC_PATHS` 白名单。

**修复:** 在 `backend/core/tenant_context.py` 中将 5 个 miniapp 路由添加到 `TENANT_PUBLIC_PATHS`。

### Bug 2: UnboundLocalError — `session` 闭包变量作用域

**现象:** SSE 流式响应在 `profile_updated=False` 时抛出 `UnboundLocalError: local variable 'session' referenced before assignment`。

**根因:** `event_stream()` 内部第210行 `session = await get_session(...)` 赋值使 Python 将整个函数中的 `session` 视为局部变量，导致第202行访问外层 `session` 时报错。

**修复:** 将内部变量重命名为 `updated_session = session`，仅在有更新时才 `updated_session = await get_session(...)`。

### Bug 3: `uuid.UUID(body.session_id)` — session_id 格式不兼容

**现象:** 事件日志 `write_event()` 调用抛出 `ValueError: badly formed hexadecimal UUID string`，导致整个聊天请求返回 500 Internal Server Error。

**根因:** `body.session_id` 格式为 `sess_xxxx`（字符串），而 `uuid.UUID()` 期望标准 UUID 格式。4 个 `write_event` 调用全部使用了 `uuid.UUID(body.session_id)`。

**修复:** 将所有 `session_id=uuid.UUID(body.session_id)` 替换为 `session_id=session.id`，使用 ConsultSession 模型的 `id` 字段（UUID 主键）。

### Bug 4: `try/except: pass` 静默吞异常

**现象:** 事件日志写入失败时没有任何日志输出，无法诊断问题。

**修复:** 所有 `write_event` 调用的 `except Exception: pass` 改为 `except Exception as e: logging.warning(f"Event ... failed: {e}")`，并添加 `logging.debug` 记录 `tenant_id` 为空时的跳过。

### Bug 5: 租户表为空导致事件日志被跳过

**现象:** `resolve_tenant('scnu')` 返回 None，`if tenant_id:` 判断跳过所有事件写入。

**修复:** 这是预期行为（无租户时不记录），但在数据库重置后需要重新种子租户数据。已添加 `logging.debug` 记录跳过原因。

### Bug 6: 前端 `chat:prefill` 事件时序问题

**现象:** 从学校信息页跳到聊天页时，如果聊天页是首次加载，`uni.$on("chat:prefill")` 可能还未注册，导致事件丢失。

**根因:** `uni.switchTab` 是异步的，目标页面 `onMounted` 注册监听器的时序晚于 `uni.$emit`。

**修复:** 在 `chat/index.vue` 中引入 `prefillQuestion` 缓冲 ref + `watch(sessionId)` 确保在 sessionId 就绪后自动发送。同时添加 `onUnmounted` 清理 `uni.$off`。

---

## 五、注意事项

1. **DeepSeek API Key** — 未设置时聊天功能无法工作，后端日志会报 LLM_FAILED 错误
2. **首次启动较慢** — Docker 需要构建镜像并下载 BGE embedding 模型，约 5-10 分钟
3. **ChromaDB 数据** — 如果 ChromaDB 为空，RAG 检索不会返回结果，但不会报错
4. **HF Spaces 代理** — 部署到 Spaces 后 SSE 会被代理缓冲为 JSON，前端已兼容两种模式

---

## 六、未完成任务

| 任务 | 说明 | 优先级 |
|------|------|--------|
| A-2 | 验证 ChromaDB 有索引数据、RAG 检索命中有效 | 需部署数据 |
| D-1 | 修复 admin-spa 403 认证问题 | Phase 3 |
| D-2 | 知识库管理页面 API 对接 | Phase 3 |
| D-3 | 品牌设置页面 API 对接 | Phase 3 |