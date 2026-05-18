<template>
  <view class="stage-bar">
    <view
      v-for="(s, idx) in stages"
      :key="s.key"
      class="stage-item"
      :class="{
        'stage-done': idx < currentIdx,
        'stage-active': idx === currentIdx,
        'stage-pending': idx > currentIdx,
      }"
    >
      <view class="stage-circle">
        <text v-if="idx < currentIdx" class="stage-check">✓</text>
        <text v-else class="stage-num">{{ idx + 1 }}</text>
      </view>
      <text class="stage-label">{{ s.label }}</text>
      <view v-if="idx < stages.length - 1" class="stage-line" :class="{ 'line-done': idx < currentIdx }" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  stage: string;
}>();

const stages = [
  { key: "explore", label: "了解兴趣" },
  { key: "focus", label: "聚焦方向" },
  { key: "confirm", label: "确认画像" },
  { key: "done", label: "查看推荐" },
];

const currentIdx = computed(() => {
  const idx = stages.findIndex((s) => s.key === props.stage);
  return idx >= 0 ? idx : 0;
});
</script>

<style scoped>
.stage-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 8px;
  background: #fff;
  border-bottom: 1px solid #eee;
}
.stage-item {
  display: flex;
  align-items: center;
  position: relative;
  flex-shrink: 0;
}
.stage-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}
.stage-active .stage-circle {
  background: var(--brand-primary, #1a56db);
  color: #fff;
}
.stage-done .stage-circle {
  background: var(--brand-primary, #1a56db);
  color: #fff;
}
.stage-pending .stage-circle {
  background: #e5e7eb;
  color: #999;
}
.stage-check {
  font-size: 14px;
}
.stage-label {
  font-size: 11px;
  color: #666;
  margin-left: 4px;
  white-space: nowrap;
}
.stage-active .stage-label {
  color: var(--brand-primary, #1a56db);
  font-weight: 600;
}
.stage-line {
  width: 24px;
  height: 2px;
  background: #e5e7eb;
  margin: 0 6px;
}
.line-done {
  background: var(--brand-primary, #1a56db);
}
</style>
