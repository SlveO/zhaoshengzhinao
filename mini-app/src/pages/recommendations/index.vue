<template>
  <view class="rec-page">
    <view v-if="loading" class="loading-area">
      <text class="loading-text">正在分析你的画像...</text>
    </view>

    <view v-else-if="error" class="error-area">
      <text class="error-text">{{ error }}</text>
      <button class="retry-btn" @tap="fetchRecommendations">重试</button>
    </view>

    <view v-else-if="!recommendations.length" class="empty-area">
      <text class="empty-icon">📋</text>
      <text class="empty-text">暂无推荐结果</text>
      <text class="empty-hint">继续和AI对话，完善画像后将生成个性化推荐</text>
      <button class="back-btn" @tap="goBack">返回对话</button>
    </view>

    <scroll-view v-else class="rec-list" scroll-y>
      <RecommendationCard
        v-for="rec in recommendations"
        :key="rec.id"
        :rec="rec"
        @feedback="handleFeedback"
      />
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { recommendationsApi } from "@/utils/api";
import RecommendationCard from "@/components/RecommendationCard.vue";

const recommendations = ref<any[]>([]);
const loading = ref(true);
const error = ref("");

async function fetchRecommendations(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    const res = await recommendationsApi.getAll();
    if (res.data) {
      const items = Array.isArray(res.data) ? res.data : (res.data as any)?.items || [];
      recommendations.value = items;
    }
  } catch (e: any) {
    error.value = e?.message || "获取推荐失败";
  } finally {
    loading.value = false;
  }
}

async function handleFeedback(data: { recommendation_id: string; rating: number }): Promise<void> {
  try {
    await recommendationsApi.submitFeedback(data);
    uni.showToast({ title: "反馈已记录", icon: "success", duration: 1500 });
  } catch {
    uni.showToast({ title: "反馈提交失败", icon: "none" });
  }
}

function goBack(): void {
  uni.navigateBack();
}

onMounted(() => {
  fetchRecommendations();
});
</script>

<style scoped>
.rec-page {
  min-height: 100vh;
  background: #f5f5f5;
}
.loading-area,
.error-area,
.empty-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 32px;
}
.loading-text {
  font-size: 15px;
  color: #999;
}
.error-text {
  font-size: 15px;
  color: #ef4444;
  margin-bottom: 16px;
}
.retry-btn,
.back-btn {
  margin-top: 16px;
  padding: 8px 24px;
  border-radius: 20px;
  background: var(--brand-primary, #1a56db);
  color: #fff;
  font-size: 14px;
  border: none;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.empty-text {
  font-size: 17px;
  color: #333;
  margin-bottom: 8px;
}
.empty-hint {
  font-size: 13px;
  color: #999;
  text-align: center;
  line-height: 1.6;
}
.rec-list {
  padding: 16px;
  min-height: 100vh;
}
</style>
