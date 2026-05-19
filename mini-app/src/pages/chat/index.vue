<template>
  <view class="chat-page">
    <StageIndicator :stage="chatStore.currentStage" />

    <view class="chat-header">
      <text class="header-title">{{ brandName }}</text>
      <view class="header-actions">
        <text class="ws-dot" :class="'ws-' + chatStore.wsStatus" />
        <text
          class="header-btn"
          :class="{ disabled: !chatStore.profile || chatStore.profile.completeness === 'L1' }"
          @tap="showProfile = true"
        >画像</text>
        <text
          class="header-btn"
          :class="{ disabled: !chatStore.profile || chatStore.profile.completeness === 'L1' }"
          @tap="goCompare"
        >对比</text>
      </view>
    </view>

    <scroll-view
      class="msg-list"
      scroll-y
      :scroll-top="scrollTop"
      :scroll-with-animation="true"
      ref="msgListRef"
    >
      <view v-if="!chatStore.conversationStarted" class="welcome-area">
        <text class="welcome-text">{{ brand.welcomeText }}</text>
        <view class="quick-start">
          <text class="quick-title">你可以这样开始：</text>
          <view
            v-for="q in quickQuestions"
            :key="q"
            class="quick-item"
            @tap="sendQuick(q)"
          >
            <text class="quick-text">{{ q }}</text>
          </view>
        </view>
      </view>

      <ChatMessage
        v-for="msg in chatStore.messages"
        :key="msg.id"
        :role="msg.role"
        :content="msg.content"
        :stage="msg.stage"
        :show-stage="msg.role === 'assistant'"
      />

      <ChatMessage
        v-if="chatStore.isThinking"
        role="thinking"
        content="..."
      />

      <view v-if="chatStore.summary" class="summary-banner">
        <text class="summary-text">{{ chatStore.summary }}</text>
        <view class="summary-actions">
          <text v-if="chatStore.isGuest" class="summary-cta" @tap="showLogin = true">
            注册保存画像，解锁多校对比 →
          </text>
          <text
            v-else-if="chatStore.profile && chatStore.profile.completeness !== 'L1'"
            class="summary-cta"
            @tap="goCompare"
          >
            查看跨院校对比推荐 →
          </text>
          <text class="summary-restart" @tap="restartChat">重新开始</text>
        </view>
      </view>
    </scroll-view>

    <view class="input-area">
      <input
        class="msg-input"
        v-model="inputText"
        placeholder="输入你的想法..."
        :disabled="chatStore.wsStatus !== 'connected'"
        @confirm="sendMessage"
        confirm-type="send"
      />
      <button
        class="send-btn"
        :disabled="!inputText.trim() || chatStore.wsStatus !== 'connected'"
        @tap="sendMessage"
      >
        发送
      </button>
    </view>

    <ProfileSidebar
      :visible="showProfile"
      :profile="chatStore.profile"
      @close="showProfile = false"
    />

    <LoginModal
      :visible="showLogin"
      @close="showLogin = false"
      @success="onLoginSuccess"
    />
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";
import { useChatStore } from "@/stores/chat";
import { BRAND } from "@/utils/config";
import StageIndicator from "@/components/StageIndicator.vue";
import ChatMessage from "@/components/ChatMessage.vue";
import ProfileSidebar from "@/components/ProfileSidebar.vue";
import LoginModal from "@/components/LoginModal.vue";

const chatStore = useChatStore();
const brand = BRAND;
const brandName = BRAND.shortName;

const inputText = ref("");
const showProfile = ref(false);
const showLogin = ref(false);
const scrollTop = ref(0);

const quickQuestions = [
  "我对计算机编程比较感兴趣，有什么专业推荐？",
  "我数学成绩不错，哪些专业适合我？",
  "想了解一下学校的就业情况怎么样？",
  "我比较喜欢和人打交道，有什么建议？",
];

function sendQuick(q: string): void {
  inputText.value = q;
  sendMessage();
}

function sendMessage(): void {
  const text = inputText.value.trim();
  if (!text) return;
  inputText.value = "";
  chatStore.sendMessage(text);
  scrollToBottom();
}

function goCompare(): void {
  if (!chatStore.profile || chatStore.profile.completeness === "L1") return;
  const snap = JSON.stringify(chatStore.profile);
  uni.navigateTo({ url: `/pages/compare/index?profile_snapshot=${encodeURIComponent(snap)}` });
}

function onLoginSuccess(): void {
  uni.showToast({ title: "登录成功！画像已保存", icon: "success" });
}

async function restartChat(): Promise<void> {
  chatStore.reset();
  await chatStore.createSession(true);
  uni.showToast({ title: "已重新开始", icon: "success" });
}

function scrollToBottom(): void {
  nextTick(() => {
    scrollTop.value = Date.now();
  });
}

onMounted(async () => {
  await chatStore.createSession(true);
});

onUnmounted(() => {
  chatStore.disconnect();
});
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f8f9fb;
}

/* Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: linear-gradient(135deg, var(--brand-primary, #1a56db), color-mix(in srgb, var(--brand-primary, #1a56db) 80%, #6366f1));
}
.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 0.3px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}
.header-btn {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
  padding: 4px 10px;
  border-radius: 12px;
  transition: background 0.2s, opacity 0.2s;
}
.header-btn:not(.disabled):active {
  background: rgba(255, 255, 255, 0.15);
}
.header-btn.disabled {
  opacity: 0.35;
  pointer-events: none;
}

/* WebSocket dot */
.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 6px rgba(0, 0, 0, 0.15);
}
.ws-connected {
  background: #10b981;
}
.ws-connecting,
.ws-reconnecting {
  background: #f59e0b;
  animation: pulse-dot 1.2s ease-in-out infinite;
}
.ws-disconnected {
  background: #ef4444;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Message list */
.msg-list {
  flex: 1;
  padding-top: 12px;
}

/* Welcome */
.welcome-area {
  padding: 28px 16px;
}
.welcome-text {
  font-size: 15px;
  color: #555;
  line-height: 1.8;
  display: block;
  margin-bottom: 24px;
}
.quick-start {
  background: #fff;
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.quick-title {
  font-size: 12px;
  color: #aaa;
  margin-bottom: 12px;
  display: block;
  letter-spacing: 0.5px;
}
.quick-item {
  padding: 11px 0;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.15s;
}
.quick-item:last-child {
  border-bottom: none;
}
.quick-item:active {
  background: #f8fbff;
  margin: 0 -18px;
  padding-left: 18px;
  padding-right: 18px;
}
.quick-text {
  font-size: 14px;
  color: var(--brand-primary, #1a56db);
  line-height: 1.5;
}

/* Summary */
.summary-banner {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  margin: 12px 16px;
  padding: 16px;
  border-radius: 14px;
  border-left: 3px solid var(--brand-primary, #1a56db);
}
.summary-text {
  font-size: 14px;
  color: #333;
  line-height: 1.7;
  display: block;
  margin-bottom: 10px;
}
.summary-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.summary-cta {
  font-size: 14px;
  color: var(--brand-primary, #1a56db);
  font-weight: 600;
}
.summary-restart {
  font-size: 13px;
  color: #999;
  padding: 5px 14px;
  border: 1px solid #ddd;
  border-radius: 14px;
  transition: background 0.2s;
}
.summary-restart:active {
  background: #f5f5f5;
}

/* Input */
.input-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #fff;
  border-top: 1px solid #eee;
  padding-bottom: calc(10px + env(safe-area-inset-bottom));
}
.msg-input {
  flex: 1;
  height: 40px;
  background: #f5f5f5;
  border-radius: 20px;
  padding: 0 16px;
  font-size: 15px;
  transition: background 0.2s;
}
.msg-input:focus {
  background: #fff;
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand-primary, #1a56db) 25%, transparent);
}
.send-btn {
  width: 64px;
  height: 40px;
  line-height: 40px;
  text-align: center;
  background: var(--brand-primary, #1a56db);
  color: #fff;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  padding: 0;
  box-shadow: 0 2px 8px color-mix(in srgb, var(--brand-primary, #1a56db) 35%, transparent);
  transition: opacity 0.2s, transform 0.1s;
}
.send-btn:not([disabled]):active {
  transform: scale(0.96);
}
.send-btn[disabled] {
  opacity: 0.35;
  box-shadow: none;
}
</style>
