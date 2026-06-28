# Mini-app 咨询页面实施计划 (Plan 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 mini-app 中实现独立咨询页面：复用现有 chat 视觉风格、调用 `/api/v1/consult/messages` SSE 接口、渲染后置校验状态徽章、通过 tabBar 入口进入。原 chat 页保留为"个性化推荐"入口。

**Architecture:** 新增 `pages/consult/index.vue` 复用 chat 页的 hero/bubble/composer 视觉但简化逻辑（无 understanding phase、无 profile extraction，仅 consult SSE 事件流）。新增 `stores/consult.ts` 管理咨询会话状态。修改 tabBar 增加"AI 咨询"入口，原"AI咨询"改名为"个性化推荐"。

**Tech Stack:** Vue 3、uni-app、TypeScript、Composition API、原生 fetch（SSE 流式）。

**依赖：** Plan 1 已完成后端 `/api/v1/consult/messages` 与 `/api/v1/miniapp/enter?module_type=consult` 接口。

**参考设计文档：** `docs/superpowers/specs/2026-06-27-consult-module-design.md`

---

## 文件结构

新增文件：
- `mini-app/src/pages/consult/index.vue` — 咨询页主体
- `mini-app/src/stores/consult.ts` — 咨询会话 store
- `mini-app/src/utils/consultSession.ts` — 咨询 session_id 存取（独立 storage key）

修改文件：
- `mini-app/src/pages.json` — 新增 consult 页路由 + tabBar 调整
- `mini-app/src/pages/chat/index.vue` — 入口遮罩改为"个性化推荐"用途
- `mini-app/src/pages/recommendations/index.vue` — 顶部追加"前往 AI 咨询"按钮（备选入口）

---

## Task 1: 创建咨询 session 存取工具

**Files:**
- Create: `mini-app/src/utils/consultSession.ts`

- [ ] **Step 1: 创建 consultSession.ts**

Create `mini-app/src/utils/consultSession.ts`:
```typescript
/** 咨询模块 session_id 存取 — 独立 storage key 与推荐模块隔离 */

const CONSULT_SESSION_KEY = 'scnu_consult_module_session_id'

export function getConsultSessionId(): string | null {
  try {
    const value = uni.getStorageSync(CONSULT_SESSION_KEY)
    if (typeof value !== 'string') return null
    const id = value.trim()
    return id.startsWith('sess_consult_') ? id : null
  } catch {
    return null
  }
}

export function saveConsultSessionId(sessionId: string): void {
  const value = sessionId.trim()
  if (!value || !value.startsWith('sess_consult_')) return
  try {
    uni.setStorageSync(CONSULT_SESSION_KEY, value)
  } catch {
    // 静默忽略
  }
}

export function clearConsultSessionId(): void {
  try {
    uni.removeStorageSync(CONSULT_SESSION_KEY)
  } catch {
    // 静默忽略
  }
}
```

- [ ] **Step 2: 验证编译**

Run: `cd mini-app && npx tsc --noEmit src/utils/consultSession.ts`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
cd mini-app
git add src/utils/consultSession.ts
git commit -m "feat(mini-app): add consultSession storage util"
```

---

## Task 2: 创建咨询会话 store

**Files:**
- Create: `mini-app/src/stores/consult.ts`

- [ ] **Step 1: 创建 consult store**

Create `mini-app/src/stores/consult.ts`:
```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, getToken } from '@/utils/api'
import { TENANT_SLUG } from '@/utils/config'
import {
  getConsultSessionId,
  saveConsultSessionId,
  clearConsultSessionId,
} from '@/utils/consultSession'

export interface ConsultMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  kind?: 'answer' | 'validation_warning'
  regenerated?: boolean
  sources?: Array<{ title: string; url: string }>
}

export const useConsultStore = defineStore('consult', () => {
  const sessionId = ref<string | null>(getConsultSessionId())
  const messages = ref<ConsultMessage[]>([])
  const isLoading = ref(false)
  const validationWarning = ref<string | null>(null)

  /** 初始化或恢复咨询会话 */
  async function enterSession(): Promise<boolean> {
    const token = getToken()
    if (!token) return false

    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
      'X-Tenant': TENANT_SLUG,
      'Content-Type': 'application/json',
    }

    try {
      const res = await api.post<any>(
        '/miniapp/enter',
        {
          session_id: sessionId.value || null,
          tenant_slug: TENANT_SLUG,
          module_type: 'consult',
        },
        { headers },
      )
      if (res.data?.data?.session_id) {
        sessionId.value = res.data.data.session_id
        saveConsultSessionId(res.data.data.session_id)
        // 加载历史消息
        if (res.data.data.chat_history?.length) {
          messages.value = res.data.data.chat_history.map((m: any) => ({
            id: m.message_id,
            role: m.role,
            content: m.content,
          }))
        }
        return true
      }
      return false
    } catch (e) {
      console.error('Consult enter failed:', e)
      return false
    }
  }

  /** SSE 流式发送消息 */
  async function sendMessage(content: string): Promise<void> {
    if (!sessionId.value || !content.trim()) return

    const userMsg: ConsultMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      content,
    }
    messages.value.push(userMsg)

    const aiMsg: ConsultMessage = {
      id: `a_${Date.now()}`,
      role: 'assistant',
      content: '',
      kind: 'answer',
      sources: [],
    }
    messages.value.push(aiMsg)

    isLoading.value = true
    validationWarning.value = null

    const API_BASE =
      process.env.NODE_ENV === 'development'
        ? '/api/v1'
        : (import.meta.env.VITE_API_BASE_URL as string) || '/api/v1'

    try {
      const resp = await fetch(`${API_BASE}/consult/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
          'X-Tenant': TENANT_SLUG,
        },
        body: JSON.stringify({
          session_id: sessionId.value,
          tenant_slug: TENANT_SLUG,
          message: { content },
        }),
      })

      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // 解析 SSE 事件（event: xxx\ndata: {...}\n\n）
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const evt of events) {
          const lines = evt.split('\n')
          let eventType = ''
          let dataStr = ''
          for (const line of lines) {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim()
            else if (line.startsWith('data: ')) dataStr = line.slice(6)
          }
          if (!eventType || !dataStr) continue

          try {
            const data = JSON.parse(dataStr)
            handleSSEEvent(eventType, data, aiMsg)
          } catch (e) {
            console.warn('SSE parse failed:', e, dataStr)
          }
        }
      }
    } catch (e: any) {
      aiMsg.content = '抱歉，AI 服务暂时不可用，请稍后重试。'
      console.error('Consult SSE failed:', e)
    } finally {
      isLoading.value = false
    }
  }

  function handleSSEEvent(type: string, data: any, aiMsg: ConsultMessage) {
    switch (type) {
      case 'thinking':
        // UI 可显示"正在理解你的问题..."
        break
      case 'intent_extracted':
        // 可选：展示意图抽取结果（调试用）
        break
      case 'search_start':
        // UI 显示检索中
        break
      case 'source':
        if (aiMsg.sources) {
          aiMsg.sources.push({
            title: data.title || '',
            url: data.url || '',
          })
        }
        break
      case 'search_end':
        break
      case 'token':
        // 增量累积 token（主回答与重生成都是增量 chunk）
        aiMsg.content += data.content || ''
        if (data.regenerated) {
          aiMsg.regenerated = true
        }
        break
      case 'validation_start':
        // 校验中（UI 可展示状态，此处仅标记）
        break
      case 'validation_passed':
        break
      case 'regenerating':
        // 清空当前 content 准备接收重生成
        aiMsg.content = ''
        break
      case 'validation_warning':
        validationWarning.value =
          data.message || '本次回答中的部分数据未经系统校验通过，请核对官方来源'
        aiMsg.kind = 'validation_warning'
        break
      case 'done':
        // 流结束，更新消息 id（来自后端持久化）
        if (data.message_id) {
          aiMsg.id = data.message_id
        }
        break
      case 'error':
        aiMsg.content = data.message || 'AI 服务暂时不可用'
        break
    }
  }

  function clearSession() {
    clearConsultSessionId()
    sessionId.value = null
    messages.value = []
  }

  return {
    sessionId,
    messages,
    isLoading,
    validationWarning,
    enterSession,
    sendMessage,
    clearSession,
  }
})
```

- [ ] **Step 2: 验证编译**

Run: `cd mini-app && npx tsc --noEmit src/stores/consult.ts`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
cd mini-app
git add src/stores/consult.ts
git commit -m "feat(mini-app): add consult store with SSE stream parsing"
```

---

## Task 3: 创建咨询页面 consult/index.vue

**Files:**
- Create: `mini-app/src/pages/consult/index.vue`

- [ ] **Step 1: 创建咨询页面**

Create `mini-app/src/pages/consult/index.vue`:
```vue
<template>
  <view v-if="showLogin" class="login-prompt">
    <view class="login-card">
      <text class="login-title">华南师范大学招生咨询</text>
      <text class="login-subtitle">登录后即可查询招生数据</text>
      <button class="login-btn" @tap="goToLogin">前往登录</button>
    </view>
  </view>

  <view v-else class="consult-page">
    <view class="consult-hero">
      <view class="hero-content">
        <text class="school-tag">华南师范大学</text>
        <text class="hero-title">AI 招生咨询</text>
        <text class="hero-subtitle">客观、严谨的招生数据查询</text>
      </view>
    </view>

    <view class="consult-body">
      <view v-if="validationWarning" class="validation-banner">
        <text class="validation-banner-text">{{ validationWarning }}</text>
      </view>

      <scroll-view
        class="message-scroll"
        scroll-y
        :scroll-top="scrollTop"
        :scroll-with-animation="true"
      >
        <view class="message-inner">
          <view
            v-for="message in messages"
            :key="message.id"
            class="message-row"
            :class="message.role === 'user' ? 'message-row-user' : 'message-row-ai'"
          >
            <view class="avatar" :class="message.role === 'user' ? 'avatar-user' : 'avatar-ai'">
              <text>{{ message.role === 'user' ? '我' : 'AI' }}</text>
            </view>
            <view class="bubble" :class="message.role === 'user' ? 'bubble-user' : 'bubble-ai'">
              <text
                v-if="message.kind === 'validation_warning'"
                class="bubble-warning-label"
              >⚠ 校验未通过</text>
              <text class="bubble-text">{{ message.content }}</text>
              <view
                v-if="message.sources && message.sources.length > 0"
                class="sources-box"
              >
                <text class="sources-title">参考来源</text>
                <view v-for="(s, i) in message.sources" :key="i" class="source-item">
                  <text class="source-text">{{ s.title || s.url || '未命名来源' }}</text>
                </view>
              </view>
            </view>
          </view>

          <view v-if="isLoading" class="typing-row">
            <view class="avatar avatar-ai"><text>AI</text></view>
            <view class="bubble bubble-ai">
              <view class="typing-dots">
                <text class="typing-dot" />
                <text class="typing-dot" />
                <text class="typing-dot" />
              </view>
            </view>
          </view>
        </view>
      </scroll-view>
    </view>

    <view class="composer">
      <view class="quick-scroll">
        <view class="quick-list">
          <text
            v-for="q in quickQuestions"
            :key="q"
            class="quick-chip"
            @tap="sendQuick(q)"
          >{{ q }}</text>
        </view>
      </view>
      <view class="input-capsule">
        <input
          v-model="inputText"
          class="message-input"
          placeholder="输入招生问题，如：人工智能 2024 年位次"
          confirm-type="send"
          @confirm="sendMessage"
        />
        <button
          class="send-button"
          :disabled="!inputText.trim() || isLoading"
          @tap="sendMessage"
        >发送</button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useConsultStore } from '@/stores/consult'
import { getToken } from '@/utils/api'

const consultStore = useConsultStore()
const { messages, isLoading, validationWarning } = consultStore

const inputText = ref('')
const scrollTop = ref(0)
const showLogin = ref(false)

const quickQuestions = [
  '人工智能 2024 年在广东的位次',
  '软件工程的选科要求',
  '人工智能和软件工程的录取分数对比',
  '华师有哪些师范类专业',
]

onLoad(async () => {
  const token = getToken()
  if (!token) {
    showLogin.value = true
    return
  }
  const ok = await consultStore.enterSession()
  if (!ok) {
    showLogin.value = true
  }
})

async function sendMessage() {
  const content = inputText.value.trim()
  if (!content || isLoading.value) return
  inputText.value = ''
  await consultStore.sendMessage(content)
  await nextTick()
  scrollTop.value = 99999
}

function sendQuick(q: string) {
  inputText.value = q
  sendMessage()
}

function goToLogin() {
  uni.navigateTo({ url: '/pages/chat/index' })
}
</script>

<style lang="scss" scoped>
.consult-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #F6F8FA;
}
.consult-hero {
  padding: 24rpx 32rpx 16rpx;
  background: linear-gradient(135deg, #1A56DB 0%, #2563EB 100%);
  color: white;
}
.school-tag { font-size: 24rpx; opacity: 0.85; }
.hero-title { display: block; font-size: 40rpx; font-weight: 600; margin: 8rpx 0; }
.hero-subtitle { font-size: 26rpx; opacity: 0.9; }
.consult-body { flex: 1; overflow: hidden; }
.message-scroll { height: 100%; }
.message-inner { padding: 24rpx; }
.message-row {
  display: flex;
  margin-bottom: 24rpx;
  gap: 16rpx;
}
.message-row-user { flex-direction: row-reverse; }
.avatar {
  width: 64rpx; height: 64rpx;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 24rpx; flex-shrink: 0;
}
.avatar-user { background: #1A56DB; color: white; }
.avatar-ai { background: #E5E7EB; color: #374151; }
.bubble {
  max-width: 70%;
  padding: 16rpx 24rpx;
  border-radius: 16rpx;
  font-size: 28rpx;
  line-height: 1.6;
}
.bubble-user { background: #1A56DB; color: white; }
.bubble-ai { background: white; color: #1F2937; border: 1rpx solid #E5E7EB; }
.bubble-warning-label {
  display: block;
  font-size: 22rpx;
  color: #92400E;
  margin-bottom: 8rpx;
}
.validation-banner {
  margin: 16rpx 24rpx;
  padding: 12rpx 20rpx;
  background: #FEF3C7;
  border: 1rpx solid #FCD34D;
  border-radius: 8rpx;
  font-size: 24rpx;
  color: #92400E;
}
.sources-box {
  margin-top: 12rpx;
  padding-top: 12rpx;
  border-top: 1rpx solid #E5E7EB;
}
.sources-title { font-size: 22rpx; color: #6B7280; }
.source-item { margin-top: 6rpx; }
.source-text { font-size: 22rpx; color: #4B5563; }
.typing-row { display: flex; gap: 16rpx; }
.typing-dots { display: flex; gap: 8rpx; padding: 8rpx 0; }
.typing-dot {
  width: 12rpx; height: 12rpx;
  background: #9CA3AF;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; }
  30% { opacity: 1; }
}
.composer { padding: 16rpx 24rpx 32rpx; background: white; border-top: 1rpx solid #E5E7EB; }
.quick-scroll { margin-bottom: 12rpx; }
.quick-list { display: flex; gap: 12rpx; }
.quick-chip {
  flex-shrink: 0;
  padding: 8rpx 20rpx;
  background: #F3F4F6;
  border-radius: 24rpx;
  font-size: 24rpx;
  color: #4B5563;
}
.input-capsule {
  display: flex;
  gap: 12rpx;
  align-items: center;
}
.message-input {
  flex: 1;
  height: 72rpx;
  padding: 0 24rpx;
  background: #F3F4F6;
  border-radius: 36rpx;
  font-size: 28rpx;
}
.send-button {
  padding: 0 32rpx;
  height: 72rpx;
  line-height: 72rpx;
  background: #1A56DB;
  color: white;
  border-radius: 36rpx;
  font-size: 28rpx;
}
.send-button[disabled] { background: #9CA3AF; }
.login-prompt {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  padding: 32rpx;
}
.login-card {
  text-align: center;
  padding: 48rpx 32rpx;
  background: white;
  border-radius: 16rpx;
}
.login-title { display: block; font-size: 36rpx; font-weight: 600; margin-bottom: 12rpx; }
.login-subtitle { display: block; font-size: 26rpx; color: #6B7280; margin-bottom: 32rpx; }
.login-btn {
  padding: 16rpx 48rpx;
  background: #1A56DB;
  color: white;
  border-radius: 8rpx;
  font-size: 28rpx;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd mini-app
git add src/pages/consult/index.vue
git commit -m "feat(mini-app): create consult page with SSE stream UI"
```

---

## Task 4: 在 pages.json 注册 consult 页 + 调整 tabBar

**Files:**
- Modify: `mini-app/src/pages.json`

- [ ] **Step 1: 在 pages 数组中新增 consult 页**

Edit `mini-app/src/pages.json`，在 `pages` 数组中追加：
```json
    {
      "path": "pages/consult/index",
      "style": {
        "navigationBarTitleText": "AI 招生咨询",
        "navigationBarBackgroundColor": "#1A56DB",
        "navigationBarTextStyle": "white"
      }
    },
```

- [ ] **Step 2: 修改 tabBar 增加"AI 咨询"入口**

Edit `mini-app/src/pages.json`，将 `tabBar.list` 改为：
```json
    "list": [
      {
        "pagePath": "pages/school/index",
        "text": "学校信息"
      },
      {
        "pagePath": "pages/consult/index",
        "text": "AI 咨询"
      },
      {
        "pagePath": "pages/chat/index",
        "text": "个性化推荐"
      },
      {
        "pagePath": "pages/recommendations/index",
        "text": "报考建议"
      }
    ]
```

- [ ] **Step 3: 验证 pages.json 合法性**

Run: `cd mini-app && node -e "JSON.parse(require('fs').readFileSync('src/pages.json','utf8')); console.log('OK')"`
Expected: `OK`

- [ ] **Step 4: 启动 dev server 验证**

Run: `cd mini-app && npm run dev:h5 -- --port 3002`
打开 http://localhost:3002，验证：
1. tabBar 出现 4 个入口：学校信息 / AI 咨询 / 个性化推荐 / 报考建议
2. 点击"AI 咨询"进入咨询页（未登录显示登录引导）
3. 登录后可发送消息，SSE 流式接收

- [ ] **Step 5: Commit**

```bash
cd mini-app
git add src/pages.json
git commit -m "feat(mini-app): register consult page in tabBar"
```

---

## Task 5: 修改 chat 页面入口文案为"个性化推荐"

**Files:**
- Modify: `mini-app/src/pages/chat/index.vue`

- [ ] **Step 1: 修改 hero 标题与副标题**

Edit `mini-app/src/pages/chat/index.vue`，将 hero-content 内：
```html
        <text class="hero-title">AI 招生咨询助手</text>
        <text class="hero-subtitle">招生政策、专业选择、报考建议都可以问我</text>
```
改为：
```html
        <text class="hero-title">AI 个性化推荐</text>
        <text class="hero-subtitle">基于咨询画像，提供个性化专业推荐与引导</text>
```

- [ ] **Step 2: 修改 welcomeMessage 文案**

Edit `mini-app/src/pages/chat/index.vue`，将 `welcomeMessage` 变量改为：
```typescript
const welcomeMessage =
  "你好，我是华南师范大学 AI 个性化推荐助手。我会结合你的咨询画像、分数与意向，为你提供个性化的专业推荐与报考引导。如有具体招生数据问题（如录取位次、选科要求），请前往「AI 咨询」模块。"
```

- [ ] **Step 3: 修改 quickQuestions 引导向个性化场景**

Edit `mini-app/src/pages/chat/index.vue`，将 `quickQuestions` 改为：
```typescript
const quickQuestions = [
  "根据我的分数推荐适合的华师专业",
  "我对计算机方向感兴趣，怎么规划？",
  "软件工程和人工智能哪个更适合我？",
  "我的分数报考华师有希望吗？"
]
```

- [ ] **Step 4: Commit**

```bash
cd mini-app
git add src/pages/chat/index.vue
git commit -m "feat(mini-app): rebrand chat page as personalized recommendation"
```

---

## Self-Review

**1. Spec coverage：**
- 独立咨询页面 → Task 1-4 ✓
- 复用 chat 视觉风格 → Task 3（样式参考 chat/index.vue）✓
- SSE 流式接收 + 后置校验状态展示 → Task 2 + Task 3 ✓
- 咨询 session 与推荐 session 隔离 → Task 1（独立 storage key）✓
- chat 页改名为"个性化推荐" → Task 5 ✓
- tabBar 增加"AI 咨询"入口 → Task 4 ✓

**2. Placeholder scan：** 无 TBD / TODO

**3. Type consistency：**
- `ConsultMessage` 接口在 Task 2/3 一致
- SSE 事件名（thinking/intent_extracted/source/token/validation_passed/regenerating/validation_warning/done/error）与 Plan 1 Task 15 后端 `_sse()` 调用一致
- API 路径 `/consult/messages` 与 Plan 1 Task 15 一致
- `module_type: 'consult'` 与 Plan 1 Task 14 一致

---

## Execution Handoff

Plan 3 已完成并保存至 `docs/superpowers/plans/2026-06-27-03-miniapp-consult-page.md`。

**两种执行方式：**

**1. Subagent-Driven（推荐）** — 每个 Task 派发独立 sub-agent

**2. Inline Execution** — 当前会话内顺序执行

**请选择执行方式？**
