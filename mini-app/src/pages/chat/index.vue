<template>
  <view class="chat-page">
    <StageIndicator :stage="chatStore.currentStage" />

    <view class="chat-header">
      <text class="header-title">{{ brandName }}</text>
      <view class="header-actions">
        <text class="ws-dot" :class="'ws-' + chatStore.wsStatus" />
        <text class="header-btn" @tap="showProfile = true">画像</text>
        <text class="header-btn" @tap="goCompare">对比</text>
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
        <text v-if="chatStore.isGuest" class="summary-cta" @tap="showLogin = true">
          注册保存画像，解锁多校对比 →
        </text>
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
  uni.navigateTo({ url: "/pages/compare/index" });
}

function onLoginSuccess(): void {
  uni.showToast({ title: "登录成功！画像已保存", icon: "success" });
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
  background: #f5f5f5;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: var(--brand-primary, #1a56db);
}
.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #fff;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-btn {
  font-size: 14px;
  color: #fff;
  padding: 4px 8px;
}
.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.ws-connected {
  background: #10b981;
}
.ws-connecting,
.ws-reconnecting {
  background: #f59e0b;
}
.ws-disconnected {
  background: #ef4444;
}
.msg-list {
  flex: 1;
  padding-top: 12px;
}
.welcome-area {
  padding: 24px 16px;
}
.welcome-text {
  font-size: 15px;
  color: #555;
  line-height: 1.7;
  display: block;
  margin-bottom: 24px;
}
.quick-start {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
}
.quick-title {
  font-size: 13px;
  color: #999;
  margin-bottom: 12px;
  display: block;
}
.quick-item {
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}
.quick-item:last-child {
  border-bottom: none;
}
.quick-text {
  font-size: 14px;
  color: var(--brand-primary, #1a56db);
}
.summary-banner {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  margin: 12px 16px;
  padding: 16px;
  border-radius: 12px;
}
.summary-text {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
  display: block;
  margin-bottom: 8px;
}
.summary-cta {
  font-size: 14px;
  color: var(--brand-primary, #1a56db);
  font-weight: 600;
}
.input-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fff;
  border-top: 1px solid #eee;
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
}
.msg-input {
  flex: 1;
  height: 40px;
  background: #f5f5f5;
  border-radius: 20px;
  padding: 0 16px;
  font-size: 15px;
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
  border: none;
  padding: 0;
}
.send-btn[disabled] {
  opacity: 0.4;
}
</style>
