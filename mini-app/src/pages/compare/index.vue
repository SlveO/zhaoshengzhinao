<template>
  <view class="compare-page">
    <!-- Header -->
    <view class="page-header">
      <text class="back-btn" @tap="goBack">← 返回</text>
      <text class="header-title">跨院校对比</text>
      <text class="compare-toggle" :class="{ active: compareMode }" @tap="toggleCompareMode">
        {{ compareMode ? '取消' : '对比' }}
      </text>
    </view>

    <!-- Loading -->
    <view v-if="loading" class="status-area">
      <text class="status-text">正在分析跨院校匹配...</text>
    </view>

    <!-- Error -->
    <view v-else-if="error" class="status-area">
      <text class="error-text">{{ error }}</text>
      <button class="retry-btn" @tap="fetchData">重试</button>
    </view>

    <!-- Empty -->
    <view v-else-if="!recommendations.length" class="status-area">
      <text class="empty-icon">📊</text>
      <text class="empty-text">暂无跨院校对比数据</text>
      <text class="empty-hint">完成画像后将展示不同院校的匹配结果</text>
      <button class="back-btn" @tap="goBack">返回对话</button>
    </view>

    <!-- Compare panel (side-by-side) -->
    <view v-if="compareMode && selectedSlugs.length > 0" class="compare-panel">
      <scroll-view class="compare-scroll" scroll-x>
        <view class="compare-row">
          <view
            v-for="slug in selectedSlugs"
            :key="slug"
            class="compare-college"
          >
            <text class="cc-name">{{ getRecBySlug(slug)?.tenant_name }}</text>
            <text class="cc-score">匹配 {{ getRecBySlug(slug)?.match_score }}%</text>
            <view
              v-for="(major, mi) in getRecBySlug(slug)?.majors || []"
              :key="mi"
              class="cc-major"
            >
              <text class="cc-major-name">{{ major.major_name }}</text>
              <text class="cc-major-meta">分数: {{ major.min_score }} | 位次: {{ major.min_rank }}</text>
              <text class="cc-major-meta">{{ major.level }} · {{ major.city }}</text>
            </view>
          </view>
        </view>
      </scroll-view>
      <text class="compare-hint">← 左右滑动查看更多 →</text>
    </view>

    <!-- College card list -->
    <scroll-view v-else class="card-list" scroll-y>
      <view
        v-for="rec in recommendations"
        :key="rec.tenant_slug"
        class="college-card"
        :class="{
          expanded: expandedSlug === rec.tenant_slug,
          selected: selectedSlugs.includes(rec.tenant_slug),
        }"
      >
        <!-- Card header -->
        <view class="card-header" @tap="toggleExpand(rec.tenant_slug)">
          <view class="card-left">
            <view class="checkbox-dot" v-if="compareMode" @tap.stop="toggleSelect(rec.tenant_slug)">
              <text v-if="selectedSlugs.includes(rec.tenant_slug)">✓</text>
            </view>
            <view class="card-info">
              <text class="card-name">{{ rec.tenant_name }}</text>
              <text class="card-hint">点击查看专业详情</text>
            </view>
          </view>
          <view class="card-right">
            <view class="score-ring">
              <text class="score-num">{{ rec.match_score }}</text>
              <text class="score-unit">%</text>
            </view>
            <text class="score-label">匹配度</text>
          </view>
        </view>

        <!-- Top 3 majors preview (always visible) -->
        <view class="major-preview">
          <view
            v-for="(major, mi) in rec.majors"
            :key="mi"
            class="preview-row"
          >
            <text class="preview-rank">{{ mi + 1 }}</text>
            <text class="preview-name">{{ major.major_name }}</text>
            <text class="preview-score">{{ major.min_score }}分</text>
          </view>
        </view>

        <!-- Expanded major details -->
        <view v-if="expandedSlug === rec.tenant_slug" class="major-details">
          <view
            v-for="(major, mi) in rec.majors"
            :key="mi"
            class="detail-block"
          >
            <text class="detail-title">{{ major.major_name }}</text>
            <view class="detail-grid">
              <view class="detail-item">
                <text class="detail-label">院校</text>
                <text class="detail-value">{{ major.college_name }}</text>
              </view>
              <view class="detail-item">
                <text class="detail-label">层次</text>
                <text class="detail-value">{{ major.level }}</text>
              </view>
              <view class="detail-item">
                <text class="detail-label">城市</text>
                <text class="detail-value">{{ major.city }}</text>
              </view>
              <view class="detail-item">
                <text class="detail-label">最低分数</text>
                <text class="detail-value">{{ major.min_score }}</text>
              </view>
              <view class="detail-item">
                <text class="detail-label">最低位次</text>
                <text class="detail-value">{{ major.min_rank }}</text>
              </view>
              <view class="detail-item">
                <text class="detail-label">选科要求</text>
                <text class="detail-value">{{ major.subjects || '不限' }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view v-if="recommendations.length" class="list-footer">
        <text class="footer-text">共 {{ recommendations.length }} 所院校参与对比</text>
      </view>
    </scroll-view>

    <!-- Compare action bar -->
    <view v-if="compareMode && selectedSlugs.length > 0" class="compare-bar">
      <text class="compare-count">已选 {{ selectedSlugs.length }}/3 所</text>
      <button
        class="compare-start-btn"
        :disabled="selectedSlugs.length < 2"
        @tap="startCompare"
      >
        开始对比
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { api } from "@/utils/api";

interface MajorMeta {
  college_name: string;
  major_name: string;
  level: string;
  province: string;
  city: string;
  min_rank: number;
  min_score: number;
  subjects: string;
  source_url: string;
}

interface CompareRec {
  tenant_slug: string;
  tenant_name: string;
  majors: MajorMeta[];
  match_score: number;
}

const recommendations = ref<CompareRec[]>([]);
const loading = ref(true);
const error = ref("");
const expandedSlug = ref("");
const compareMode = ref(false);
const selectedSlugs = ref<string[]>([]);

function getRecBySlug(slug: string): CompareRec | undefined {
  return recommendations.value.find((r) => r.tenant_slug === slug);
}

async function fetchData(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    const res = await api.get<{
      recommendations: CompareRec[];
      profile_snapshot: Record<string, any>;
      tenants_compared: number;
    }>("/compare/recommendations");
    if (res.data) {
      recommendations.value = res.data.recommendations || [];
    }
  } catch (e: any) {
    error.value = e?.message || "获取对比数据失败";
  } finally {
    loading.value = false;
  }
}

function toggleExpand(slug: string): void {
  expandedSlug.value = expandedSlug.value === slug ? "" : slug;
}

function toggleCompareMode(): void {
  compareMode.value = !compareMode.value;
  if (!compareMode.value) {
    selectedSlugs.value = [];
    expandedSlug.value = "";
  }
}

function toggleSelect(slug: string): void {
  const idx = selectedSlugs.value.indexOf(slug);
  if (idx >= 0) {
    selectedSlugs.value.splice(idx, 1);
  } else if (selectedSlugs.value.length < 3) {
    selectedSlugs.value.push(slug);
  } else {
    uni.showToast({ title: "最多选择3所院校", icon: "none" });
  }
}

function startCompare(): void {
  if (selectedSlugs.value.length < 2) {
    uni.showToast({ title: "请至少选择2所院校", icon: "none" });
    return;
  }
  // The compare panel is shown in the template when compareMode && selectedSlugs.length > 0
}

function goBack(): void {
  uni.navigateBack();
}

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.compare-page {
  min-height: 100vh;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--brand-primary, #1a56db);
}
.back-btn {
  font-size: 14px;
  color: #fff;
}
.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #fff;
}
.compare-toggle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  padding: 4px 12px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 14px;
}
.compare-toggle.active {
  background: #fff;
  color: var(--brand-primary, #1a56db);
  border-color: #fff;
}

/* Status areas */
.status-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 32px;
}
.status-text {
  font-size: 15px;
  color: #999;
}
.error-text {
  font-size: 15px;
  color: #ef4444;
  margin-bottom: 16px;
  text-align: center;
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

/* Compare panel */
.compare-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.compare-scroll {
  flex: 1;
  white-space: nowrap;
}
.compare-row {
  display: inline-flex;
  gap: 12px;
  padding: 16px;
}
.compare-college {
  width: 260px;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: inline-flex;
  flex-direction: column;
  white-space: normal;
}
.cc-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}
.cc-score {
  font-size: 13px;
  color: var(--brand-primary, #1a56db);
  font-weight: 600;
  margin-bottom: 12px;
}
.cc-major {
  padding: 8px 0;
  border-top: 1px solid #f0f0f0;
}
.cc-major-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  display: block;
  margin-bottom: 4px;
}
.cc-major-meta {
  font-size: 12px;
  color: #999;
  display: block;
  line-height: 1.6;
}
.compare-hint {
  text-align: center;
  font-size: 12px;
  color: #ccc;
  padding: 8px 0 16px;
}

/* Card list */
.card-list {
  flex: 1;
  padding: 12px 16px;
}
.college-card {
  background: #fff;
  border-radius: 12px;
  margin-bottom: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.2s;
}
.college-card.expanded {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
.college-card.selected {
  border: 2px solid var(--brand-primary, #1a56db);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.card-left {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
}
.checkbox-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--brand-primary, #1a56db);
  flex-shrink: 0;
  margin-top: 2px;
}
.college-card.selected .checkbox-dot {
  background: var(--brand-primary, #1a56db);
  border-color: var(--brand-primary, #1a56db);
  color: #fff;
}
.card-info {
  flex: 1;
}
.card-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 2px;
}
.card-hint {
  font-size: 11px;
  color: #bbb;
}

.card-right {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}
.score-ring {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand-primary, #1a56db), #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}
.score-num {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}
.score-unit {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1;
}
.score-label {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

/* Major preview */
.major-preview {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f5f5f5;
}
.preview-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}
.preview-rank {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #f0f0f0;
  font-size: 11px;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.preview-name {
  flex: 1;
  font-size: 13px;
  color: #555;
}
.preview-score {
  font-size: 12px;
  color: #999;
}

/* Major details */
.major-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #eee;
}
.detail-block {
  margin-bottom: 12px;
}
.detail-block:last-child {
  margin-bottom: 0;
}
.detail-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--brand-primary, #1a56db);
  display: block;
  margin-bottom: 8px;
}
.detail-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 0;
}
.detail-item {
  width: 50%;
  display: flex;
  flex-direction: column;
}
.detail-label {
  font-size: 11px;
  color: #bbb;
}
.detail-value {
  font-size: 13px;
  color: #333;
}

/* List footer */
.list-footer {
  text-align: center;
  padding: 16px 0 24px;
}
.footer-text {
  font-size: 12px;
  color: #ccc;
}

/* Compare action bar */
.compare-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-top: 1px solid #eee;
  padding-bottom: calc(12px + env(safe-area-inset-bottom));
}
.compare-count {
  font-size: 14px;
  color: #666;
}
.compare-start-btn {
  padding: 8px 24px;
  border-radius: 20px;
  background: var(--brand-primary, #1a56db);
  color: #fff;
  font-size: 14px;
  border: none;
}
.compare-start-btn[disabled] {
  opacity: 0.4;
}
</style>
