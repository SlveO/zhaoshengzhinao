<template>
  <view class="rec-card">
    <view class="card-header">
      <view class="major-info">
        <text class="major-name">{{ rec.major_name }}</text>
        <text v-if="rec.college_name" class="college-name">{{ rec.college_name }}</text>
      </view>
      <view class="match-badge">
        <text class="match-score">{{ Math.round((rec.score || 0) * 100) }}%</text>
        <text class="match-label">匹配度</text>
      </view>
    </view>

    <view class="card-body">
      <text class="rec-reason">{{ rec.reason }}</text>
    </view>

    <view v-if="rec.evidence && rec.evidence.length" class="evidence-section">
      <text class="evidence-title">推荐依据</text>
      <view v-for="(ev, idx) in rec.evidence" :key="idx" class="evidence-item">
        <text class="evidence-dot">•</text>
        <text class="evidence-text">{{ ev }}</text>
      </view>
    </view>

    <view v-if="rec.score_lines" class="score-section">
      <text class="score-title">历年分数线</text>
      <view class="score-grid">
        <view v-for="(sl, idx) in rec.score_lines.slice(0, 3)" :key="idx" class="score-item">
          <text class="score-year">{{ sl.year }}</text>
          <text class="score-value">{{ sl.score }}分</text>
          <text class="score-rank">排位{{ sl.rank }}</text>
        </view>
      </view>
    </view>

    <view class="card-actions">
      <button class="btn-like" @tap="$emit('feedback', { recommendation_id: rec.id, rating: 1 })">
        👍 有用
      </button>
      <button class="btn-dislike" @tap="$emit('feedback', { recommendation_id: rec.id, rating: -1 })">
        👎 不感兴趣
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  rec: {
    id: string;
    major_name: string;
    college_name?: string;
    score?: number;
    reason?: string;
    evidence?: string[];
    score_lines?: { year: number; score: number; rank: number }[];
  };
}>();

defineEmits<{
  feedback: [data: { recommendation_id: string; rating: number }];
}>();
</script>

<style scoped>
.rec-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}
.major-info {
  flex: 1;
}
.major-name {
  font-size: 17px;
  font-weight: 600;
  color: #333;
  display: block;
}
.college-name {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.match-badge {
  background: linear-gradient(135deg, var(--brand-primary, #1a56db), #6366f1);
  border-radius: 8px;
  padding: 6px 12px;
  align-items: center;
}
.match-score {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  display: block;
  text-align: center;
}
.match-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.8);
}
.card-body {
  margin-bottom: 12px;
}
.rec-reason {
  font-size: 14px;
  color: #555;
  line-height: 1.6;
}
.evidence-section {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}
.evidence-title {
  font-size: 13px;
  font-weight: 600;
  color: #666;
  margin-bottom: 6px;
  display: block;
}
.evidence-item {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
}
.evidence-dot {
  color: var(--brand-primary, #1a56db);
}
.evidence-text {
  font-size: 12px;
  color: #777;
  flex: 1;
}
.score-section {
  margin-bottom: 12px;
}
.score-title {
  font-size: 13px;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
  display: block;
}
.score-grid {
  display: flex;
  gap: 8px;
}
.score-item {
  flex: 1;
  background: #f5f5f5;
  border-radius: 8px;
  padding: 8px;
  text-align: center;
}
.score-year {
  font-size: 11px;
  color: #999;
}
.score-value {
  font-size: 16px;
  font-weight: 700;
  color: #333;
  display: block;
}
.score-rank {
  font-size: 11px;
  color: #999;
}
.card-actions {
  display: flex;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
.btn-like,
.btn-dislike {
  flex: 1;
  height: 36px;
  line-height: 36px;
  text-align: center;
  border-radius: 18px;
  font-size: 13px;
  background: #f5f5f5;
  border: none;
  padding: 0;
}
.btn-like {
  color: #10b981;
}
.btn-dislike {
  color: #999;
}
</style>
