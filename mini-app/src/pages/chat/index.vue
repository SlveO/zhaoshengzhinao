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
        <text class="hero-title">AI 招生咨询助手</text>
        <text class="hero-subtitle">招生政策、专业选择、报考建议都可以问我</text>
      </view>
    </view>

    <view class="chat-body">
      <view class="ambient-light ambient-light-one" />
      <view class="ambient-light ambient-light-two" />
      <text class="scnu-watermark">SCNU</text>
      <text class="school-watermark">华南师范大学</text>

      <scroll-view
        class="message-scroll"
        scroll-y
        enhanced
        :bounces="false"
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
            <view
              class="avatar"
              :class="message.role === 'user' ? 'avatar-user' : 'avatar-ai'"
            >
              <text>{{ message.role === "user" ? "我" : "AI" }}</text>
            </view>

            <view
              class="bubble"
              :class="message.role === 'user' ? 'bubble-user' : 'bubble-ai'"
            >
              <text class="bubble-text">{{ message.content }}</text>
            </view>
          </view>

          <view v-if="isThinking" class="message-row message-row-ai">
            <view class="avatar avatar-ai">
              <text>AI</text>
            </view>
            <view class="bubble bubble-ai typing-bubble">
              <text class="typing-dot" />
              <text class="typing-dot" />
              <text class="typing-dot" />
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
import { nextTick, ref } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { api } from "@/utils/api"
import { getStoredSessionId, saveSessionId } from "@/utils/session"
import { TENANT_SLUG } from "@/utils/config"

const welcomeMessage =
  "你好，我是华南师范大学招生咨询助手。你可以直接问我招生政策、专业介绍、录取参考、校园生活等问题。如果你愿意，也可以告诉我你的省份、科类、分数和意向专业，我会为你生成更适合的本校报考建议。"

const quickQuestions = [
  "华师人工智能专业怎么样？",
  "广东物理类 585 分适合报华师哪些专业？",
  "软件工程和人工智能哪个更适合我？",
  "怎么加入华师招生咨询群？"
]

const sessionId = ref<string | null>(null)
const inputText = ref("")
const scrollTop = ref(0)
const isThinking = ref(false)
const messages = ref<any[]>([
  { id: "welcome", role: "assistant", content: welcomeMessage, timestamp: Date.now() }
])

onLoad(async () => {
  const stored = getStoredSessionId()
  try {
    const res = await api.post<any>("/miniapp/enter", {
      session_id: stored || null,
      tenant_slug: TENANT_SLUG,
      scene: "miniapp_enter",
    })
    if (res.data) {
      sessionId.value = res.data.session_id
      saveSessionId(res.data.session_id)
      if (res.data.chat_history?.length) {
        messages.value = res.data.chat_history.map((m: any) => ({
          id: m.message_id || m.id,
          role: m.role,
          content: m.content,
          timestamp: new Date(m.created_at).getTime(),
        }))
      }
    }
  } catch {
    // API 不通时保留欢迎消息（demo 后备）
  }
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
  isThinking.value = true
  scrollToBottom()

  try {
    const res = await api.post<any>("/chat/messages", {
      session_id: sessionId.value,
      tenant_slug: TENANT_SLUG,
      message: { role: "user", content },
    })
    isThinking.value = false
    if (res.data?.assistant_message) {
      messages.value.push({
        id: res.data.assistant_message.message_id || `ai-${Date.now()}`,
        role: "assistant",
        content: res.data.assistant_message.content,
        timestamp: Date.now(),
      })
    }
  } catch (e: any) {
    isThinking.value = false
    messages.value.push({
      id: `err-${Date.now()}`,
      role: "assistant",
      content: e?.error?.message || "AI 服务暂时不可用，请稍后重试",
      timestamp: Date.now(),
    })
  }
  scrollToBottom()
}

function scrollToBottom(): void {
  nextTick(() => {
    scrollTop.value = Date.now()
  })
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
  padding: 30rpx 18rpx 70rpx;
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

.typing-bubble {
  display: flex;
  align-items: center;
  width: 126rpx;
  height: 66rpx;
  padding: 0 28rpx;
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
</style>