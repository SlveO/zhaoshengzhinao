<template>
  <view class="sidebar-mask" v-if="visible" @tap="$emit('close')">
    <view class="sidebar-panel" @tap.stop>
      <view class="sidebar-header">
        <text class="sidebar-title">我的画像</text>
        <text class="sidebar-close" @tap="$emit('close')">✕</text>
      </view>

      <view v-if="!profile" class="sidebar-empty">
        <text class="empty-icon">📊</text>
        <text class="empty-text">对话后画像将在这里实时更新</text>
      </view>

      <view v-else class="sidebar-body">
        <view class="completeness-bar">
          <text class="completeness-label">完整度</text>
          <view class="completeness-track">
            <view class="completeness-fill" :style="{ width: completenessPercent + '%' }" />
          </view>
          <text class="completeness-text">{{ profile.completeness || 'L1' }}</text>
        </view>

        <view class="section">
          <text class="section-title">RIASEC 评估</text>
          <view v-for="(score, dim) in profile.riasec" :key="dim" class="riasec-row">
            <text class="riasec-dim">{{ dimLabels[dim] || dim }}</text>
            <view class="riasec-bar-track">
              <view
                class="riasec-bar-fill"
                :style="{ width: (score / 10) * 100 + '%' }"
              />
            </view>
            <text class="riasec-score">{{ score }}/10</text>
          </view>
        </view>

        <view v-if="profile.values?.length" class="section">
          <text class="section-title">关键词</text>
          <view class="values-wrap">
            <text v-for="v in profile.values" :key="v" class="value-tag">{{ v }}</text>
          </view>
        </view>

        <view class="sidebar-footer">
          <text class="confidence-text">置信度: {{ Math.round((profile.confidence || 0) * 100) }}%</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  visible: boolean;
  profile: {
    riasec: Record<string, number>;
    values?: string[];
    confidence?: number;
    completeness?: string;
  } | null;
}>();

defineEmits<{ close: [] }>();

const dimLabels: Record<string, string> = {
  R: "实践型",
  I: "研究型",
  A: "艺术型",
  S: "社会型",
  E: "企业型",
  C: "常规型",
};

const completenessPercent = computed(() => {
  if (!props.profile) return 0;
  const level = props.profile.completeness || "L1";
  const map: Record<string, number> = { L0: 0, L1: 25, L2: 50, L3: 75, L4: 100 };
  return map[level] || 0;
});
</script>

<style scoped>
.sidebar-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 100;
}
.sidebar-panel {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 300px;
  background: #fff;
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #eee;
}
.sidebar-title {
  font-size: 17px;
  font-weight: 600;
}
.sidebar-close {
  font-size: 20px;
  color: #999;
  padding: 4px;
}
.sidebar-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.empty-icon {
  font-size: 48px;
}
.empty-text {
  color: #999;
  font-size: 14px;
}
.sidebar-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.completeness-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}
.completeness-label {
  font-size: 13px;
  color: #666;
}
.completeness-track {
  flex: 1;
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}
.completeness-fill {
  height: 100%;
  background: var(--brand-primary, #1a56db);
  border-radius: 3px;
  transition: width 0.5s ease;
}
.completeness-text {
  font-size: 12px;
  color: var(--brand-primary, #1a56db);
  font-weight: 600;
}
.section {
  margin-bottom: 20px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
  display: block;
}
.riasec-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.riasec-dim {
  font-size: 12px;
  color: #666;
  width: 50px;
}
.riasec-bar-track {
  flex: 1;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}
.riasec-bar-fill {
  height: 100%;
  background: var(--brand-primary, #1a56db);
  border-radius: 4px;
  transition: width 0.5s ease;
}
.riasec-score {
  font-size: 12px;
  color: var(--brand-primary, #1a56db);
  font-weight: 600;
  width: 36px;
  text-align: right;
}
.values-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.value-tag {
  font-size: 12px;
  padding: 4px 12px;
  background: #f0f4ff;
  color: var(--brand-primary, #1a56db);
  border-radius: 12px;
}
.sidebar-footer {
  padding-top: 16px;
  border-top: 1px solid #eee;
}
.confidence-text {
  font-size: 12px;
  color: #999;
}
</style>
