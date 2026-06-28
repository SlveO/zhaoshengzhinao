<template>
  <view class="consult-page">
    <view class="consult-hero">
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
                v-if="message.regenerated"
                class="regen-tag"
              >
                <text class="regen-tag-text">已重新生成</text>
              </view>
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
          placeholder="输入招生问题，如：2+2 和 3+1 有什么区别"
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
import { ref, nextTick, onMounted, onUnmounted, watch } from "vue";
import { onLoad, onShow } from "@dcloudio/uni-app";
import { storeToRefs } from "pinia";
import { useConsultStore } from "@/stores/consult";
import { getToken } from "@/utils/api";
import { getConsultSessionId } from "@/utils/consultSession";

const consultStore = useConsultStore();
const { messages, isLoading, validationWarning, sessionId } = storeToRefs(consultStore);

const inputText = ref("");
const scrollTop = ref(0);
const prefillQuestion = ref<string | null>(null);

// 流式 token 更新时自动滚动到底
watch(() => messages.value.length, async () => {
  await nextTick();
  scrollTop.value = 0;
  await nextTick();
  scrollTop.value = 99999;
});

// 监听最后一条消息内容变化（流式 token 累积）
watch(() => messages.value[messages.value.length - 1]?.content, async () => {
  await nextTick();
  scrollTop.value = 0;
  await nextTick();
  scrollTop.value = 99999;
});

// 知识库高频主题（对齐 KB003/005-007/008-010/011-012/017-019/021-023/030）
const quickQuestions = [
  "这个项目正规吗？学历国家承认吗？",
  "2+2 和 3+1 有什么区别？",
  "学费多少？有奖学金吗？",
  "怎么报名？需要什么材料？",
  "可以对接哪些国外大学？",
  "毕业后能申请什么硕士？"
];

onLoad(async () => {
  const token = getToken();
  if (!token) {
    uni.reLaunch({ url: "/pages/auth/index" });
    return;
  }
  const ok = await consultStore.enterSession();
  if (!ok) {
    uni.reLaunch({ url: "/pages/auth/index" });
    return;
  }
  uni.setStorageSync("last_active_at", Date.now());

  // 会话恢复后处理 prefill（来自学校信息页入口）
  handlePrefill();
});

// tab 页 onLoad 只触发一次，logout 后切换 tab 需要重新初始化
onShow(async () => {
  const token = getToken();
  if (!token) {
    uni.reLaunch({ url: "/pages/auth/index" });
    return;
  }
  // 检测 session 是否已被清除（logout/register/login 会清存储）
  const storedId = getConsultSessionId();
  if (sessionId.value && !storedId) {
    // 存储已清但内存 ref 还在 → 账号已切换，重新进入会话
    consultStore.clearSession();
    const ok = await consultStore.enterSession();
    if (!ok) {
      uni.reLaunch({ url: "/pages/auth/index" });
    }
  }
});

onMounted(() => {
  uni.$on("consult:prefill", handlePrefill);
});

onUnmounted(() => {
  uni.$off("consult:prefill", handlePrefill);
});

function handlePrefill(question?: string): void {
  const q = question || uni.getStorageSync("consult_prefill");
  if (!q) return;
  uni.removeStorageSync("consult_prefill");
  prefillQuestion.value = q;
  trySendPrefill();
}

function trySendPrefill(): void {
  if (prefillQuestion.value && sessionId.value) {
    inputText.value = prefillQuestion.value;
    prefillQuestion.value = null;
    sendMessage();
  }
}

async function sendMessage() {
  const content = inputText.value.trim();
  if (!content || isLoading.value) return;
  inputText.value = "";
  await consultStore.sendMessage(content);
  await nextTick();
  // 两步法：先重置为 0，下一 tick 再设大值，强制 scroll-view 触发滚动到底
  scrollTop.value = 0;
  await nextTick();
  scrollTop.value = 99999;
}

function sendQuick(q: string) {
  inputText.value = q;
  sendMessage();
}
</script>

<style lang="scss" scoped>
.consult-page {
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

.consult-hero {
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

.consult-body {
  position: relative;
  flex: 1;
  min-height: 0;
  margin: 10rpx 18rpx 0;
  border-radius: 38rpx 38rpx 0 0;
  overflow: hidden;
  background: linear-gradient(180deg, rgba(248, 251, 255, 0.98) 0%, #eaf4ff 100%);
  box-shadow: 0 12rpx 36rpx rgba(37, 99, 235, 0.08);
  z-index: 2;
}

.validation-banner {
  position: relative;
  z-index: 1;
  margin: 16rpx 24rpx 0;
  padding: 12rpx 20rpx;
  background: #fef3c7;
  border: 1rpx solid #fcd34d;
  border-radius: 12rpx;
}

.validation-banner-text {
  font-size: 24rpx;
  color: #92400e;
  line-height: 1.5;
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
  overflow: hidden;
  word-break: break-word;
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

.bubble-warning-label {
  display: block;
  font-size: 22rpx;
  color: #92400e;
  margin-bottom: 8rpx;
  font-weight: 600;
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

.regen-tag {
  margin-top: 12rpx;
}

.regen-tag-text {
  font-size: 20rpx;
  color: #6b7280;
  background: #f3f4f6;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}

.sources-box {
  margin-top: 16rpx;
  padding: 16rpx;
  background: #f8f9fb;
  border-radius: 12rpx;
  box-sizing: border-box;
  overflow: hidden;
  width: 100%;
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

.source-item:last-child {
  border-bottom: none;
}

.source-text {
  display: block;
  font-size: 22rpx;
  color: #333;
  line-height: 1.5;
  word-break: break-all;
  overflow-wrap: anywhere;
  white-space: normal;
}

.typing-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 30rpx;
}

.typing-dots {
  display: flex;
  align-items: center;
  height: 28rpx;
  padding: 8rpx 0;
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
  0%, 100% {
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
  background: linear-gradient(180deg, rgba(246, 248, 250, 0) 0%, rgba(246, 250, 255, 0.94) 28%, rgba(255, 255, 255, 0.98) 100%);
  z-index: 10;
}

.quick-scroll {
  width: 100%;
  white-space: nowrap;
  margin-bottom: 12rpx;
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
