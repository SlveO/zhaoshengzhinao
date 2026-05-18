<template>
  <view class="profile-page">
    <view v-if="loading" class="loading-area">
      <text class="loading-text">加载中...</text>
    </view>

    <view v-else-if="!profile" class="empty-area">
      <text class="empty-icon">📊</text>
      <text class="empty-title">画像尚未生成</text>
      <text class="empty-desc">完成一轮对话（通常 5-8 轮）后，系统将自动生成你的兴趣画像</text>
      <button class="go-btn" @tap="goChat">去对话</button>
    </view>

    <view v-else class="profile-content">
      <view class="profile-header">
        <text class="profile-title">我的画像</text>
        <text class="profile-confidence">置信度 {{ Math.round(profile.confidence * 100) }}%</text>
      </view>

      <view class="completeness-card">
        <text class="card-label">画像完整度</text>
        <view class="completeness-track">
          <view class="completeness-fill" :style="{ width: completenessPercent + '%' }" />
        </view>
        <text class="completeness-level">{{ profile.completeness || 'L1' }}</text>
        <text class="completeness-hint">继续对话可以提高完整度</text>
      </view>

      <view class="riasec-card">
        <text class="card-label">RIASEC 职业兴趣</text>
        <view v-for="(score, dim) in profile.riasec" :key="dim" class="riasec-row">
          <text class="riasec-dim">{{ dimLabels[dim] || dim }}</text>
          <text class="riasec-desc">{{ dimDescs[dim] || '' }}</text>
          <view class="riasec-bar-track">
            <view class="riasec-bar-fill" :style="{ width: (score / 10) * 100 + '%' }" />
          </view>
          <text class="riasec-score">{{ score }}/10</text>
        </view>
      </view>

      <view v-if="profile.values?.length" class="values-card">
        <text class="card-label">职业价值观</text>
        <view class="values-wrap">
          <text v-for="v in profile.values" :key="v" class="value-tag">{{ v }}</text>
        </view>
      </view>

      <view class="actions">
        <button class="action-btn primary" @tap="goChat">继续对话</button>
        <button class="action-btn secondary" @tap="goRecommendations">查看推荐</button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { profileApi } from "@/utils/api";

interface Profile {
  riasec: Record<string, number>;
  values: string[];
  confidence: number;
  completeness: string;
}

const loading = ref(true);
const profile = ref<Profile | null>(null);

const dimLabels: Record<string, string> = {
  R: "实践型", I: "研究型", A: "艺术型", S: "社会型", E: "企业型", C: "常规型",
};
const dimDescs: Record<string, string> = {
  R: "喜欢动手操作、使用工具",
  I: "喜欢思考研究、分析问题",
  A: "喜欢创造表达、追求美感",
  S: "喜欢帮助他人、服务社会",
  E: "喜欢领导管理、影响他人",
  C: "喜欢规范有序、注重细节",
};

const completenessPercent = computed(() => {
  if (!profile.value) return 0;
  const map: Record<string, number> = { L0: 0, L1: 25, L2: 50, L3: 75, L4: 100 };
  return map[profile.value.completeness] || 0;
});

async function fetchProfile(): Promise<void> {
  loading.value = true;
  try {
    const res = await profileApi.get();
    if (res.data) {
      profile.value = res.data as Profile;
    }
  } catch {
    // stay empty, show empty state
  } finally {
    loading.value = false;
  }
}

function goChat(): void {
  uni.navigateBack();
}
function goRecommendations(): void {
  uni.navigateTo({ url: "/pages/recommendations/index" });
}

onMounted(() => {
  fetchProfile();
});
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: #f5f5f5;
}
.loading-area,
.empty-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 32px;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.empty-title {
  font-size: 17px;
  color: #333;
  margin-bottom: 8px;
}
.empty-desc {
  font-size: 13px;
  color: #999;
  text-align: center;
  line-height: 1.6;
  margin-bottom: 20px;
}
.go-btn {
  padding: 8px 32px;
  border-radius: 20px;
  background: var(--brand-primary, #1a56db);
  color: #fff;
  font-size: 14px;
  border: none;
}
.profile-content {
  padding: 16px;
}
.profile-header {
  margin-bottom: 16px;
}
.profile-title {
  font-size: 22px;
  font-weight: 700;
  color: #333;
  display: block;
}
.profile-confidence {
  font-size: 13px;
  color: #999;
}
.card-label {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
  display: block;
}
.completeness-card,
.riasec-card,
.values-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}
.completeness-track {
  height: 10px;
  background: #e5e7eb;
  border-radius: 5px;
  overflow: hidden;
  margin-bottom: 8px;
}
.completeness-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand-primary, #1a56db), #6366f1);
  border-radius: 5px;
  transition: width 0.5s;
}
.completeness-level {
  font-size: 14px;
  font-weight: 600;
  color: var(--brand-primary, #1a56db);
}
.completeness-hint {
  font-size: 12px;
  color: #bbb;
  margin-left: 8px;
}
.riasec-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.riasec-dim {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  width: 50px;
}
.riasec-desc {
  font-size: 11px;
  color: #bbb;
  width: 90px;
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
  transition: width 0.5s;
}
.riasec-score {
  font-size: 13px;
  font-weight: 600;
  color: var(--brand-primary, #1a56db);
  width: 36px;
  text-align: right;
}
.values-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.value-tag {
  font-size: 13px;
  padding: 6px 14px;
  background: #f0f4ff;
  color: var(--brand-primary, #1a56db);
  border-radius: 16px;
}
.actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}
.action-btn {
  flex: 1;
  height: 44px;
  line-height: 44px;
  text-align: center;
  border-radius: 22px;
  font-size: 15px;
  border: none;
  padding: 0;
}
.action-btn.primary {
  background: var(--brand-primary, #1a56db);
  color: #fff;
}
.action-btn.secondary {
  background: #fff;
  color: var(--brand-primary, #1a56db);
  border: 1px solid var(--brand-primary, #1a56db);
}
</style>
