<template>
  <view class="chat-page">
    <view class="chat-hero">
      <image
        class="hero-bg"
        src="/static/images/scnu-building.png"
        mode="aspectFill"
      />
      <view class="hero-mask" />
      <view class="hero-bottom-glow" />
      <view class="hero-fade" />

      <view class="hero-content">
        <text class="school-tag">华南师范大学</text>
        <text class="hero-title">AI 个性化推荐</text>
        <text class="hero-subtitle">基于咨询画像，提供个性化专业推荐与引导</text>
      </view>
    </view>

    <view class="chat-body">
      <view class="ambient-light ambient-light-one" />
      <view class="ambient-light ambient-light-two" />
      <text class="scnu-watermark">SCNU</text>
      <text class="school-watermark">华南师范大学</text>

      <view v-if="profileSummary" class="profile-indicator" @tap="goRecommendations">
        <text class="profile-indicator-text">
          已识别: {{ profileSummary.province || '' }} {{ profileSummary.subjects || '' }} {{ profileSummary.score || '' }}分
        </text>
        <text class="profile-indicator-arrow">查看建议 ›</text>
      </view>

      <view v-if="hasConsultHistory" class="consult-context-indicator">
        <text class="consult-context-dot" />
        <text class="consult-context-text">已结合咨询历史，推荐更精准</text>
      </view>

      <scroll-view
        class="message-scroll"
        scroll-y
        enhanced
        :bounces="false"
        :scroll-top="scrollTop"
        :scroll-with-animation="true"
        @scroll="onScroll"
        @scrolltolower="onScrollToLower"
      >
        <view class="message-inner">
          <view
            v-for="message in messages"
            :key="message.id"
            class="message-row"
            :class="message.role === 'user' ? 'message-row-user' : 'message-row-ai'"
          >
            <view
              class="avatar"
              :class="message.role === 'user' ? 'avatar-user' : 'avatar-ai'"
            >
              <text>{{ message.role === "user" ? "我" : (message.kind === 'understanding' ? '理解' : 'AI') }}</text>
            </view>

            <view
              class="bubble"
              :class="[
                message.role === 'user' ? 'bubble-user' : 'bubble-ai',
                message.kind === 'understanding' ? 'bubble-understanding' : ''
              ]"
            >
              <text v-if="message.kind === 'understanding'" class="bubble-kind-label">问题理解</text>
              <text class="bubble-text">{{ message.content }}</text>
              <view
                v-if="message.kind === 'answer' && message.sources && message.sources.length > 0"
                class="sources-toggle"
                @tap="toggleSources(message.id)"
              >
                <text class="sources-toggle-text">
                  {{ expandedSources.has(message.id) ? '收起引用 «' : `查看本次引用 ${message.sources.length} 条数据 »` }}
                </text>
              </view>
              <view
                v-if="message.kind === 'answer' && message.sources && message.sources.length > 0 && expandedSources.has(message.id)"
                class="sources-box"
              >
                <text class="sources-title">参考来源</text>
                <view v-for="(s, i) in message.sources" :key="i" class="source-item">
                  <text class="source-text">{{ s.text }}</text>
                  <text v-if="s.source_title" class="source-label">{{ s.source_title }}</text>
                </view>
              </view>
            </view>
          </view>

          <view v-if="isSearching" class="search-status-row">
            <view class="search-spinner" />
            <text class="search-status-text">{{ searchStatusText }}</text>
          </view>

          <view v-if="isThinking" class="message-row message-row-ai">
            <view class="avatar avatar-ai">
              <text>AI</text>
            </view>
            <view class="bubble bubble-ai">
              <view class="typing-dots">
                <text class="typing-dot" />
                <text class="typing-dot" />
                <text class="typing-dot" />
              </view>
              <text v-if="thinkingStatus" class="bubble-status">{{ thinkingStatus }}</text>
            </view>
          </view>
        </view>
      </scroll-view>
    </view>

    <view class="composer">
      <scroll-view class="quick-scroll" scroll-x :show-scrollbar="false">
        <view class="quick-list">
          <text
            v-for="question in quickQuestions"
            :key="question"
            class="quick-chip"
            @tap="sendQuick(question)"
          >
            {{ question }}
          </text>
        </view>
      </scroll-view>

      <view class="input-capsule">
        <input
          v-model="inputText"
          class="message-input"
          placeholder="输入你想了解的招生问题..."
          placeholder-class="input-placeholder"
          confirm-type="send"
          :adjust-position="true"
          @confirm="sendMessage"
        />
        <button
          class="send-button"
          :disabled="!inputText.trim()"
          @tap="sendMessage"
        >
          发送
        </button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue"
import { onLoad, onShow } from "@dcloudio/uni-app"
import { api, getToken } from "@/utils/api"
import { getStoredSessionId, saveSessionId, clearStoredSessionId } from "@/utils/session"
import { getConsultSessionId } from "@/utils/consultSession"
import { TENANT_SLUG } from "@/utils/config"

const DEFAULT_WELCOME =
  "你好，我是华南师范大学个性化推荐助手。\n\n本系统仅提供国际留学项目相关咨询，涵盖 2+2 出国留学培训项目（商科/新媒体方向）与 3+1 SQA-AD 项目（市场营销/人力资源管理/商务会计）的专业选择与报考引导。\n\n基于你的咨询画像与基本信息，我会为你提供更贴合的专业推荐。你可以告诉我分数、位次、选科和意向方向，我会结合你的咨询历史给出更精准的建议。"

// 知识库高频主题（对齐 KB001/003/005-007/011-012/017-019/021-023/030）
const quickQuestions = [
  "我适合 2+2 还是 3+1 项目？",
  "毕业后能申请什么硕士？",
  "项目的对接院校有哪些？",
  "学费和奖学金政策？"
]

const sessionId = ref<string | null>(null)
const inputText = ref("")
const scrollTop = ref(0)
const shouldAutoScroll = ref(true)
const prevScrollTop = ref(0)
let scrollTimer: ReturnType<typeof setTimeout> | null = null
const profileSummary = ref<any>(null)
const hasConsultHistory = ref<boolean>(Boolean(getConsultSessionId()))
const isThinking = ref(false)
const thinkingStatus = ref("")
const sources = ref<any[]>([])
const isSearching = ref(false)
const searchStatusText = ref("")
const expandedSources = ref<Set<string>>(new Set())
const messages = ref<any[]>([
  { id: "welcome", role: "assistant", content: DEFAULT_WELCOME, kind: "answer", timestamp: Date.now() }
])

const hasSession = ref(false)

onLoad(async () => {
  const token = getToken()
  if (!token) {
    uni.reLaunch({ url: "/pages/auth/index" })
    return
  }
  const stored = getStoredSessionId()
  const headers: Record<string, string> = { "Authorization": `Bearer ${token}` }
  try {
    const res = await api.post<any>("/miniapp/enter", {
      session_id: stored || null,
      tenant_slug: TENANT_SLUG,
    }, { headers })

    if (res.data) {
      sessionId.value = res.data.session_id
      saveSessionId(res.data.session_id)
      hasSession.value = true
      uni.setStorageSync("last_active_at", Date.now())
      if (res.data.profile_summary) {
        profileSummary.value = res.data.profile_summary
      }
      if (res.data.chat_history && res.data.chat_history.length) {
        messages.value = res.data.chat_history.map((m: any) => ({
          id: m.message_id || m.id,
          role: m.role,
          content: m.content,
          kind: m.role === "assistant" ? "answer" : undefined,
          sources: [],
          timestamp: new Date(m.created_at).getTime(),
        }))
      } else if (res.data.greeting) {
        // 新会话且后端配置了开场白：覆盖默认欢迎语
        messages.value = [{
          id: "welcome",
          role: "assistant",
          content: res.data.greeting,
          kind: "answer",
          timestamp: Date.now()
        }]
      }
      nextTick(() => { scrollToBottom() })
    }
  } catch {
    clearStoredSessionId()
    uni.reLaunch({ url: "/pages/auth/index" })
    return
  }
  handlePrefill()
})

// tab 页 onLoad 只触发一次，logout 后切换 tab 需要重新初始化
onShow(async () => {
  const token = getToken()
  if (!token) {
    uni.reLaunch({ url: "/pages/auth/index" })
    return
  }
  // 检测 session 是否已被清除（logout/register/login 会清存储）
  const storedId = getStoredSessionId()
  if (sessionId.value && !storedId) {
    // 存储已清但内存 ref 还在 → 账号已切换，重新进入会话
    sessionId.value = null
    messages.value = [{
      id: "welcome",
      role: "assistant",
      content: DEFAULT_WELCOME,
      kind: "answer",
      timestamp: Date.now()
    }]
    profileSummary.value = null
    const headers: Record<string, string> = { "Authorization": `Bearer ${token}` }
    try {
      const res = await api.post<any>("/miniapp/enter", {
        session_id: null,
        tenant_slug: TENANT_SLUG,
      }, { headers })
      if (res.data) {
        sessionId.value = res.data.session_id
        saveSessionId(res.data.session_id)
        if (res.data.profile_summary) {
          profileSummary.value = res.data.profile_summary
        }
        if (res.data.greeting) {
          messages.value = [{
            id: "welcome",
            role: "assistant",
            content: res.data.greeting,
            kind: "answer",
            timestamp: Date.now()
          }]
        }
      }
    } catch {
      // 静默失败，保留默认欢迎语
    }
  }
})

const prefillQuestion = ref<string | null>(null)

function handlePrefill(question?: string): void {
  const q = question || uni.getStorageSync("chat_prefill")
  if (!q) return
  uni.removeStorageSync("chat_prefill")
  prefillQuestion.value = q
  trySendPrefill()
}

function trySendPrefill(): void {
  if (prefillQuestion.value && sessionId.value) {
    inputText.value = prefillQuestion.value
    prefillQuestion.value = null
    sendMessage()
  }
}

watch(sessionId, () => trySendPrefill())

// 流式 token 累积时自动滚动到底（监听最后一条消息内容变化）
watch(() => messages.value[messages.value.length - 1]?.content, () => {
  scrollToBottom()
})

// 消息数量变化时滚动到底
watch(() => messages.value.length, () => {
  scrollToBottom()
})

onMounted(() => {
  uni.$on("chat:prefill", handlePrefill)
})

onUnmounted(() => {
  uni.$off("chat:prefill", handlePrefill)
})

function sendQuick(question: string): void {
  inputText.value = question
  sendMessage()
}

async function sendMessage(): Promise<void> {
  const content = inputText.value.trim()
  if (!content || !sessionId.value) return
  inputText.value = ""

  messages.value.push({ id: `user-${Date.now()}`, role: "user", content, timestamp: Date.now() })

  // 气泡按需创建：理解气泡（understanding）与回答气泡（answer）
  let understandingId: string | null = null
  let answerId: string | null = null
  isThinking.value = true
  thinkingStatus.value = "正在理解你的问题..."
  isSearching.value = false
  searchStatusText.value = ""
  sources.value = []
  shouldAutoScroll.value = true
  scrollToBottom()

  const apiBase = import.meta.env.DEV
    ? "/api/v1"
    : (import.meta.env.VITE_API_BASE_URL as string) || "/api/v1"

  // AbortController for SSE fetch (shared between SSE timeout and poll fallback)
  const abortCtrl = new AbortController()
  let sseReceived = false
  let polling = false

  // Polling fallback: if SSE doesn't deliver within 8s, poll /miniapp/enter
  const pollTimer = setTimeout(async () => {
    if (sseReceived) return
    polling = true
    thinkingStatus.value = "正在生成回答..."
    const poll = async () => {
      if (sseReceived) return
      try {
        const res = await api.post<any>("/miniapp/enter", {
          session_id: sessionId.value,
          tenant_slug: TENANT_SLUG,
          scene: "miniapp_enter",
        })
        if (res.data?.chat_history?.length) {
          const last = res.data.chat_history[res.data.chat_history.length - 1]
          if (last.role === "assistant" && last.content) {
            sseReceived = true
            abortCtrl.abort()
            isThinking.value = false
            thinkingStatus.value = ""
            isSearching.value = false
            if (!answerId) {
              answerId = `ai-${Date.now()}`
              messages.value.push({ id: answerId, role: "assistant", kind: "answer", content: last.content, sources: [], timestamp: Date.now() })
            } else {
              const msg = messages.value.find(m => m.id === answerId)
              if (msg) msg.content = last.content
            }
            scrollToBottom()
            return
          }
        }
        setTimeout(poll, 2000)
      } catch {
        setTimeout(poll, 2000)
      }
    }
    poll()
  }, 8000)

  try {
    const token = getToken()
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Tenant": TENANT_SLUG,
    }
    if (token) headers["Authorization"] = `Bearer ${token}`
    const response = await fetch(`${apiBase}/chat/messages`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        session_id: sessionId.value,
        tenant_slug: TENANT_SLUG,
        message: { role: "user", content },
      }),
      signal: abortCtrl.signal,
    })

    if (!response.ok) {
      isThinking.value = false
      isSearching.value = false
      clearTimeout(pollTimer)
      answerId = `ai-${Date.now()}`
      messages.value.push({ id: answerId, role: "assistant", kind: "answer", content: `请求失败 (${response.status})，请稍后重试`, sources: [], timestamp: Date.now() })
      return
    }

    // HF Spaces proxy buffers SSE into a single JSON response
    const contentType = response.headers.get("content-type") || ""
    if (contentType.includes("application/json")) {
      sseReceived = true
      clearTimeout(pollTimer)
      isThinking.value = false
      isSearching.value = false
      thinkingStatus.value = ""
      try {
        const json = await response.json()
        const data = json.data || json
        answerId = `ai-${Date.now()}`
        if (json.error) {
          messages.value.push({ id: answerId, role: "assistant", kind: "answer", content: json.error.message || "AI 服务暂时不可用", sources: [], timestamp: Date.now() })
        } else if (data?.assistant_message?.content) {
          messages.value.push({ id: answerId, role: "assistant", kind: "answer", content: data.assistant_message.content, sources: [], timestamp: Date.now() })
        } else {
          messages.value.push({ id: answerId, role: "assistant", kind: "answer", content: "AI 服务暂时不可用，请稍后重试", sources: [], timestamp: Date.now() })
        }
      } catch {
        answerId = `ai-${Date.now()}`
        messages.value.push({ id: answerId, role: "assistant", kind: "answer", content: "AI 服务暂时不可用，请稍后重试", sources: [], timestamp: Date.now() })
      }
      scrollToBottom()
      return
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let firstUnderstandingToken = true
    let firstAnswerToken = true

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      sseReceived = true
      clearTimeout(pollTimer)
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const evt = JSON.parse(line.slice(6))
            if (evt.type === "thinking") {
              thinkingStatus.value = evt.message
            } else if (evt.type === "understanding_start") {
              // 理解阶段开始 — 保持 typing dots 直到首个 token
            } else if (evt.type === "understanding") {
              if (firstUnderstandingToken) {
                firstUnderstandingToken = false
                isThinking.value = false
                thinkingStatus.value = ""
                understandingId = `understanding-${Date.now()}`
                messages.value.push({ id: understandingId, role: "assistant", kind: "understanding", content: "", timestamp: Date.now() })
              }
              const msg = messages.value.find(m => m.id === understandingId)
              if (msg) msg.content += evt.text
            } else if (evt.type === "understanding_end") {
              // 理解阶段结束 — 若无 token 则隐藏 typing dots
              if (firstUnderstandingToken) {
                isThinking.value = false
                thinkingStatus.value = ""
              }
            } else if (evt.type === "search_start") {
              isSearching.value = true
              searchStatusText.value = "正在检索知识库..."
            } else if (evt.type === "source") {
              sources.value.push(evt.item)
              const title = evt.item?.source_title || (evt.item?.text || "").slice(0, 30) || "数据片段"
              searchStatusText.value = `正在检索 (${evt.index + 1}/${evt.total}): ${title}`
            } else if (evt.type === "search_end") {
              isSearching.value = false
              searchStatusText.value = ""
            } else if (evt.type === "token") {
              if (firstAnswerToken) {
                firstAnswerToken = false
                isThinking.value = false
                isSearching.value = false
                thinkingStatus.value = ""
                answerId = `ai-${Date.now()}`
                messages.value.push({ id: answerId, role: "assistant", kind: "answer", content: "", sources: [...sources.value], timestamp: Date.now() })
              }
              const msg = messages.value.find(m => m.id === answerId)
              if (msg) msg.content += evt.text
            } else if (evt.type === "sources") {
              // 兼容旧版一次性 sources 事件
              sources.value = evt.items
              if (answerId) {
                const msg = messages.value.find(m => m.id === answerId)
                if (msg) msg.sources = [...sources.value]
              }
            } else if (evt.type === "done") {
              isThinking.value = false
              isSearching.value = false
              thinkingStatus.value = ""
              if (evt.assistant_message && answerId) {
                const msg = messages.value.find(m => m.id === answerId)
                if (msg) {
                  msg.id = evt.assistant_message.message_id || answerId
                  msg.sources = [...sources.value]
                }
              }
              if (evt.profile_updated && evt.profile_summary) {
                profileSummary.value = evt.profile_summary
                uni.showToast({
                  title: "已更新你的咨询档案",
                  icon: "success",
                  duration: 2000,
                })
              }
            } else if (evt.type === "error") {
              isThinking.value = false
              isSearching.value = false
              thinkingStatus.value = ""
              if (!answerId) {
                answerId = `ai-${Date.now()}`
                messages.value.push({ id: answerId, role: "assistant", kind: "answer", content: evt.message || "AI 服务暂时不可用", sources: [], timestamp: Date.now() })
              } else {
                const msg = messages.value.find(m => m.id === answerId)
                if (msg) msg.content = evt.message || "AI 服务暂时不可用"
              }
            }
          } catch { /* skip parse errors */ }
        }
      }
      scrollToBottom()
    }
    // 流正常结束但未收到 done 事件，确保状态归位
    if (isThinking.value || isSearching.value) {
      isThinking.value = false
      isSearching.value = false
      thinkingStatus.value = ""
    }
  } catch {
    clearTimeout(pollTimer)
    isThinking.value = false
    isSearching.value = false
    thinkingStatus.value = ""
    if (!sseReceived) {
      answerId = `ai-${Date.now()}`
      messages.value.push({ id: answerId, role: "assistant", kind: "answer", content: "AI 服务暂时不可用，请稍后重试", sources: [], timestamp: Date.now() })
    }
  }
}

function onScrollToLower(): void {
  shouldAutoScroll.value = true
}

function onScroll(e: any): void {
  const current = e.detail.scrollTop || 0
  if (current < prevScrollTop.value - 15) {
    shouldAutoScroll.value = false
  }
  prevScrollTop.value = current
}

function scrollToBottom(): void {
  if (!shouldAutoScroll.value) return
  if (scrollTimer) return
  scrollTimer = setTimeout(() => {
    scrollTimer = null
    // 两步法：先重置为 0，下一 tick 再设大值，强制 scroll-view 触发滚动到底
    scrollTop.value = 0
    nextTick(() => {
      scrollTop.value = Date.now()
    })
  }, 80)
}

function goRecommendations(): void {
  uni.switchTab({ url: "/pages/recommendations/index" })
}

function toggleSources(msgId: string): void {
  const next = new Set(expandedSources.value)
  if (next.has(msgId)) {
    next.delete(msgId)
  } else {
    next.add(msgId)
  }
  expandedSources.value = next
}
</script>

<style scoped>
.chat-page {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding-bottom: calc(154rpx + var(--window-bottom));
  box-sizing: border-box;
  background: linear-gradient(180deg, #f6f8fa 0%, #eaf4ff 100%);
  overflow: hidden;
}

.chat-hero {
  position: relative;
  height: calc(178rpx + var(--status-bar-height));
  overflow: hidden;
  background: #dbeafe;
  flex-shrink: 0;
}

.hero-bg {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.hero-mask {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background: linear-gradient(
    105deg,
    rgba(26, 86, 219, 0.48) 0%,
    rgba(37, 99, 235, 0.32) 52%,
    rgba(37, 99, 235, 0.12) 100%
  );
}

.hero-bottom-glow {
  position: absolute;
  right: -160rpx;
  bottom: -190rpx;
  width: 420rpx;
  height: 320rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.24);
}

.hero-fade {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 62rpx;
  background: linear-gradient(
    180deg,
    rgba(234, 244, 255, 0) 0%,
    rgba(234, 244, 255, 0.72) 100%
  );
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: calc(178rpx + var(--status-bar-height));
  padding: calc(var(--status-bar-height) + 14rpx) 30rpx 26rpx;
  box-sizing: border-box;
}

.school-tag {
  align-self: flex-start;
  margin-bottom: 7rpx;
  padding: 5rpx 15rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.28);
  color: #eef6ff;
  font-size: 22rpx;
  font-weight: 600;
  line-height: 1.3;
  text-shadow: 0 2rpx 6rpx rgba(15, 23, 42, 0.16);
}

.hero-title {
  color: #ffffff;
  font-size: 38rpx;
  font-weight: 800;
  line-height: 1.22;
  letter-spacing: 1rpx;
  text-shadow: 0 4rpx 12rpx rgba(15, 23, 42, 0.24);
}

.hero-subtitle {
  margin-top: 6rpx;
  color: rgba(255, 255, 255, 0.94);
  font-size: 24rpx;
  line-height: 1.45;
  text-shadow: 0 2rpx 8rpx rgba(15, 23, 42, 0.18);
}

.chat-body {
  position: relative;
  flex: 1;
  min-height: 0;
  margin: 10rpx 18rpx 0;
  border-radius: 38rpx 38rpx 0 0;
  overflow: hidden;
  background: linear-gradient(
    180deg,
    rgba(248, 251, 255, 0.98) 0%,
    #eaf4ff 100%
  );
  box-shadow: 0 12rpx 36rpx rgba(37, 99, 235, 0.08);
  z-index: 2;
}

.ambient-light {
  position: absolute;
  border-radius: 50%;
  z-index: 0;
  pointer-events: none;
}

.ambient-light-one {
  top: 64rpx;
  left: -150rpx;
  width: 470rpx;
  height: 470rpx;
  background: radial-gradient(
    circle,
    rgba(147, 197, 253, 0.28) 0%,
    rgba(147, 197, 253, 0) 68%
  );
}

.ambient-light-two {
  right: -210rpx;
  bottom: 90rpx;
  width: 560rpx;
  height: 560rpx;
  background: radial-gradient(
    circle,
    rgba(191, 219, 254, 0.34) 0%,
    rgba(191, 219, 254, 0) 70%
  );
}

.scnu-watermark {
  position: absolute;
  top: 24%;
  left: 50%;
  width: 700rpx;
  margin-left: -350rpx;
  color: rgba(37, 99, 235, 0.045);
  font-size: 132rpx;
  font-weight: 900;
  line-height: 1;
  letter-spacing: 12rpx;
  text-align: center;
  z-index: 0;
  pointer-events: none;
}

.school-watermark {
  position: absolute;
  top: 38%;
  left: 50%;
  width: 560rpx;
  margin-left: -280rpx;
  color: rgba(29, 78, 216, 0.05);
  font-size: 42rpx;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 8rpx;
  text-align: center;
  z-index: 0;
  pointer-events: none;
}

.message-scroll {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
}

.message-inner {
  padding: 30rpx 18rpx calc(220rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
}

.message-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 30rpx;
}

.message-row-user {
  flex-direction: row-reverse;
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56rpx;
  height: 56rpx;
  border-radius: 20rpx;
  font-size: 22rpx;
  font-weight: 800;
  flex-shrink: 0;
}

.avatar-ai {
  margin-right: 14rpx;
  border: 1rpx solid rgba(37, 99, 235, 0.08);
  background: linear-gradient(180deg, #edf6ff 0%, #dcecff 100%);
  color: #1d4ed8;
  box-shadow: 0 10rpx 22rpx rgba(37, 99, 235, 0.08);
}

.avatar-user {
  margin-left: 14rpx;
  background: linear-gradient(135deg, #5b8df6 0%, #2f6bea 100%);
  color: #ffffff;
  box-shadow: 0 10rpx 22rpx rgba(47, 107, 234, 0.16);
}

.bubble {
  max-width: 520rpx;
  padding: 23rpx 25rpx;
  border-radius: 34rpx;
  box-sizing: border-box;
}

.bubble-ai {
  border-top-left-radius: 11rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 16rpx 40rpx rgba(15, 23, 42, 0.08);
}

.bubble-user {
  border-top-right-radius: 11rpx;
  background: linear-gradient(135deg, #5f8ff7 0%, #2f6bea 58%, #2563eb 100%);
  box-shadow: 0 16rpx 34rpx rgba(37, 99, 235, 0.18);
}

.bubble-understanding {
  background: rgba(243, 248, 255, 0.92);
  border: 1rpx solid rgba(147, 197, 253, 0.45);
  box-shadow: 0 8rpx 20rpx rgba(37, 99, 235, 0.06);
}

.bubble-understanding .bubble-text {
  color: #4b6584;
  font-size: 26rpx;
  font-style: italic;
}

.bubble-kind-label {
  display: block;
  font-size: 20rpx;
  font-weight: 600;
  color: #93a4c4;
  margin-bottom: 6rpx;
  letter-spacing: 1rpx;
}

.bubble-text {
  font-size: 28rpx;
  line-height: 1.84;
  letter-spacing: 0.35rpx;
}

.bubble-ai .bubble-text {
  color: #243246;
}

.bubble-user .bubble-text {
  color: #ffffff;
}

.typing-dots {
  display: flex;
  align-items: center;
  height: 28rpx;
}

.typing-dot {
  width: 10rpx;
  height: 10rpx;
  margin-right: 10rpx;
  border-radius: 50%;
  background: #8da2bd;
  animation: typing 1s ease-in-out infinite;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.15s;
}

.typing-dot:nth-child(3) {
  margin-right: 0;
  animation-delay: 0.3s;
}

@keyframes typing {
  0%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }

  50% {
    opacity: 1;
    transform: translateY(-4rpx);
  }
}

.composer {
  position: fixed;
  right: 0;
  bottom: var(--window-bottom);
  left: 0;
  padding: 12rpx 20rpx calc(14rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
  background: linear-gradient(
    180deg,
    rgba(246, 248, 250, 0) 0%,
    rgba(246, 250, 255, 0.94) 28%,
    rgba(255, 255, 255, 0.98) 100%
  );
  z-index: 10;
}

.quick-scroll {
  width: 100%;
  white-space: nowrap;
}

.quick-list {
  display: inline-flex;
  padding: 2rpx 2rpx 12rpx;
}

.quick-chip {
  display: inline-flex;
  margin-right: 12rpx;
  padding: 10rpx 20rpx;
  border-radius: 999rpx;
  border: 1rpx solid rgba(219, 234, 254, 0.9);
  background: rgba(255, 255, 255, 0.78);
  color: #1d4ed8;
  font-size: 23rpx;
  line-height: 1.35;
  white-space: nowrap;
  box-shadow: 0 8rpx 20rpx rgba(37, 99, 235, 0.08);
}

.quick-chip:active {
  background: #eaf3ff;
}

.input-capsule {
  display: flex;
  align-items: center;
  padding: 9rpx 10rpx 9rpx 24rpx;
  border-radius: 999rpx;
  border: 1rpx solid rgba(219, 234, 254, 0.9);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 16rpx 42rpx rgba(15, 23, 42, 0.1);
}

.message-input {
  flex: 1;
  height: 66rpx;
  padding: 0;
  color: #0f172a;
  font-size: 27rpx;
  box-sizing: border-box;
}

.input-placeholder {
  color: #91a4bd;
  font-size: 26rpx;
}

.send-button {
  width: 98rpx;
  height: 66rpx;
  margin-left: 14rpx;
  padding: 0;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #5b8df6 0%, #2563eb 100%);
  color: #ffffff;
  font-size: 26rpx;
  font-weight: 700;
  line-height: 66rpx;
  box-shadow: 0 10rpx 22rpx rgba(37, 99, 235, 0.18);
}

.send-button::after {
  border: none;
}

.send-button:active {
  background: #2563eb;
}

.send-button[disabled] {
  background: linear-gradient(135deg, #dbe7f6 0%, #cbd8ea 100%);
  color: #ffffff;
  box-shadow: none;
}

.sources-box {
  margin-top: 16rpx;
  padding: 16rpx;
  background: #f8f9fb;
  border-radius: 12rpx;
}

.sources-title {
  font-size: 24rpx;
  font-weight: 600;
  color: #666;
  margin-bottom: 8rpx;
}

.source-item {
  padding: 8rpx 0;
  border-bottom: 1rpx solid #eee;
}

.source-text {
  font-size: 22rpx;
  color: #333;
  line-height: 1.5;
}

.source-label {
  font-size: 20rpx;
  color: #999;
  margin-top: 4rpx;
}

.sources-toggle {
  margin-top: 14rpx;
  padding-top: 12rpx;
  border-top: 1rpx solid #eef1f5;
}

.sources-toggle-text {
  font-size: 22rpx;
  color: #2563eb;
  font-weight: 500;
}

.search-status-row {
  display: flex;
  align-items: center;
  margin: 8rpx 0 16rpx 88rpx;
  padding: 8rpx 16rpx;
  background: rgba(243, 248, 255, 0.7);
  border-radius: 8rpx;
  border: 1rpx solid rgba(147, 197, 253, 0.3);
}

.search-spinner {
  width: 18rpx;
  height: 18rpx;
  margin-right: 12rpx;
  border: 2rpx solid rgba(37, 99, 235, 0.2);
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: search-spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes search-spin {
  to { transform: rotate(360deg); }
}

.search-status-text {
  font-size: 22rpx;
  color: #5b7299;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.bubble-status {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #64748b;
  animation: statusPulse 1.5s ease-in-out infinite;
}

@keyframes statusPulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.profile-indicator {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 8rpx 4rpx 0;
  padding: 14rpx 24rpx;
  border-radius: 20rpx;
  background: rgba(37, 99, 235, 0.08);
  border: 1rpx solid rgba(37, 99, 235, 0.15);
}

.profile-indicator-text {
  font-size: 23rpx;
  color: #1d4ed8;
  font-weight: 600;
}

.profile-indicator-arrow {
  font-size: 23rpx;
  color: #60a5fa;
}

.consult-context-indicator {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 10rpx;
  margin: 8rpx 4rpx 0;
  padding: 10rpx 20rpx;
  border-radius: 16rpx;
  background: rgba(16, 185, 129, 0.08);
  border: 1rpx solid rgba(16, 185, 129, 0.18);
}

.consult-context-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  background: #10b981;
  flex-shrink: 0;
}

.consult-context-text {
  font-size: 22rpx;
  color: #047857;
  font-weight: 600;
}
</style>