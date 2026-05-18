<template>
  <view class="msg-wrapper" :class="positionClass">
    <view class="msg-bubble" :class="bubbleClass">
      <text v-if="role === 'thinking'" class="thinking-dots">
        <text class="dot">•</text><text class="dot">•</text><text class="dot">•</text>
      </text>
      <text v-else class="msg-text">{{ content }}</text>
    </view>
    <text v-if="showStage && stage" class="stage-tag">{{ stageLabel }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  role: "user" | "assistant" | "thinking" | "system";
  content: string;
  stage?: string;
  showStage?: boolean;
}>();

const positionClass = computed(() =>
  props.role === "user" ? "msg-right" : "msg-left"
);

const bubbleClass = computed(() => ({
  "bubble-user": props.role === "user",
  "bubble-assistant": props.role === "assistant" || props.role === "system",
  "bubble-thinking": props.role === "thinking",
}));

const stageLabels: Record<string, string> = {
  explore: "信息探索",
  focus: "聚焦方向",
  confirm: "确认画像",
  done: "完成",
};

const stageLabel = computed(() =>
  props.stage ? stageLabels[props.stage] || props.stage : ""
);
</script>

<style scoped>
.msg-wrapper {
  display: flex;
  flex-direction: column;
  margin-bottom: 16px;
  padding: 0 16px;
}
.msg-left {
  align-items: flex-start;
}
.msg-right {
  align-items: flex-end;
}
.msg-bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 15px;
  line-height: 1.6;
  word-break: break-all;
}
.bubble-user {
  background: var(--brand-primary, #1a56db);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.bubble-assistant {
  background: #fff;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}
.bubble-thinking {
  background: #f0f4ff;
  padding: 12px 24px;
}
.thinking-dots {
  display: flex;
  gap: 4px;
  align-items: center;
}
.dot {
  animation: dotPulse 1.4s infinite;
  font-size: 20px;
  color: var(--brand-primary, #1a56db);
}
.dot:nth-child(2) {
  animation-delay: 0.2s;
}
.dot:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes dotPulse {
  0%,
  80%,
  100% {
    opacity: 0.2;
  }
  40% {
    opacity: 1;
  }
}
.stage-tag {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
  padding: 2px 8px;
  background: #f5f5f5;
  border-radius: 8px;
}
</style>
