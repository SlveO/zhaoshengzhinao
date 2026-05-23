<template>
  <view class="profile-page">
    <view class="page-bg-light page-bg-left" />
    <view class="page-bg-light page-bg-right" />
    <text class="page-watermark">SCNU</text>

    <view class="hero-card">
      <view class="hero-glow" />
      <text class="eyebrow">华南师范大学</text>
      <text class="page-title">我的咨询档案</text>
      <text class="page-subtitle">
        系统会根据你的招生咨询内容，整理分数、意向方向和关注重点
      </text>
    </view>

    <view class="status-card glass-card">
      <view class="status-icon">
        <text>档</text>
      </view>

      <view class="status-content">
        <text class="status-title">咨询档案尚未生成</text>
        <text class="status-desc">
          完成一轮招生咨询后，系统会根据你的问题和意向生成咨询档案。
        </text>
        <text v-if="sessionId" class="session-note">
          已关联当前咨询会话
        </text>
      </view>

      <button class="primary-btn" @tap="goChat">去 AI 咨询</button>
    </view>

    <view class="demo-card glass-card">
      <view class="section-header">
        <view>
          <text class="section-title">演示咨询档案</text>
          <text class="section-note">用于国创赛第一阶段页面展示</text>
        </view>
        <text class="demo-badge">演示</text>
      </view>

      <view class="info-grid">
        <view class="info-item">
          <text class="item-label">生源地</text>
          <text class="item-value">{{ studentInfo.province }}</text>
        </view>

        <view class="info-item">
          <text class="item-label">科类</text>
          <text class="item-value">{{ studentInfo.subject_type }}</text>
        </view>

        <view class="info-item">
          <text class="item-label">分数</text>
          <text class="item-value score">{{ studentInfo.score }} 分</text>
        </view>

        <view class="info-item wide">
          <text class="item-label">意向方向</text>
          <text class="item-value">{{ intentMajorsText }}</text>
        </view>
      </view>

      <view class="focus-section">
        <text class="focus-title">关注点</text>

        <view class="focus-list">
          <text
            v-for="item in focusPoints"
            :key="item"
            class="focus-chip"
          >
            {{ item }}
          </text>
        </view>
      </view>
    </view>

    <view class="guide-card glass-card">
      <text class="guide-title">档案如何生成？</text>
      <text class="guide-desc">
        你可以在 AI 咨询中补充省份、科类、分数、意向专业和关心的问题。后续接入后端后，系统会将咨询信息沉淀为招生线索和报考建议依据。
      </text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { mockStudentInfo } from "@/mock/student"
import { getStoredSessionId } from "@/utils/session"

const studentInfo = mockStudentInfo
const focusPoints = ["专业实力", "就业方向", "录取参考"]

const sessionId = ref<string | null>(null)

onLoad(() => {
  sessionId.value = getStoredSessionId()

  /**
   * 后续真实后端接入时：
   * 使用 session_id 请求 /api/v1/student/profile
   * 获取当前咨询会话对应的学生档案。
   */
})

const intentMajorsText = computed(() => studentInfo.intent_majors.join(" / "))

function goChat(): void {
  uni.switchTab({
    url: "/pages/chat/index"
  })
}
</script>

<style scoped>
.profile-page {
  position: relative;
  min-height: 100vh;
  padding: 24rpx 24rpx 38rpx;
  box-sizing: border-box;
  background: linear-gradient(180deg, #f6f8fa 0%, #eaf4ff 100%);
  overflow: hidden;
}

.page-bg-light {
  position: absolute;
  border-radius: 50%;
  z-index: 0;
  pointer-events: none;
}

.page-bg-left {
  top: 180rpx;
  left: -180rpx;
  width: 480rpx;
  height: 480rpx;
  background: radial-gradient(
    circle,
    rgba(147, 197, 253, 0.24) 0%,
    rgba(147, 197, 253, 0) 68%
  );
}

.page-bg-right {
  right: -220rpx;
  bottom: 200rpx;
  width: 560rpx;
  height: 560rpx;
  background: radial-gradient(
    circle,
    rgba(191, 219, 254, 0.32) 0%,
    rgba(191, 219, 254, 0) 70%
  );
}

.page-watermark {
  position: absolute;
  top: 440rpx;
  right: -10rpx;
  color: rgba(37, 99, 235, 0.04);
  font-size: 126rpx;
  font-weight: 900;
  letter-spacing: 10rpx;
  z-index: 0;
}

.hero-card,
.glass-card {
  position: relative;
  z-index: 1;
}

.hero-card {
  padding: 34rpx 30rpx;
  border-radius: 36rpx;
  overflow: hidden;
  background: linear-gradient(
    135deg,
    rgba(26, 86, 219, 0.92) 0%,
    rgba(37, 99, 235, 0.78) 58%,
    rgba(96, 165, 250, 0.62) 100%
  );
  box-shadow: 0 18rpx 46rpx rgba(37, 99, 235, 0.18);
}

.hero-glow {
  position: absolute;
  right: -120rpx;
  bottom: -170rpx;
  width: 380rpx;
  height: 320rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
}

.eyebrow {
  position: relative;
  z-index: 1;
  display: inline-flex;
  margin-bottom: 12rpx;
  padding: 7rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.18);
  color: #dbeafe;
  font-size: 23rpx;
  line-height: 1.35;
}

.page-title {
  position: relative;
  z-index: 1;
  display: block;
  color: #ffffff;
  font-size: 42rpx;
  font-weight: 800;
  line-height: 1.28;
}

.page-subtitle {
  position: relative;
  z-index: 1;
  display: block;
  margin-top: 12rpx;
  color: rgba(255, 255, 255, 0.92);
  font-size: 25rpx;
  line-height: 1.62;
}

.glass-card {
  border: 1rpx solid rgba(255, 255, 255, 0.78);
  border-radius: 32rpx;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16rpx 40rpx rgba(15, 23, 42, 0.08);
}

.status-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-top: 24rpx;
  padding: 28rpx;
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 68rpx;
  height: 68rpx;
  border-radius: 24rpx;
  background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
  color: #1d4ed8;
  font-size: 28rpx;
  font-weight: 800;
}

.status-content {
  margin-top: 18rpx;
}

.status-title {
  display: block;
  color: #0f172a;
  font-size: 33rpx;
  font-weight: 800;
  line-height: 1.35;
}

.status-desc {
  display: block;
  margin-top: 10rpx;
  color: #475569;
  font-size: 25rpx;
  line-height: 1.68;
}

.primary-btn {
  width: 100%;
  height: 78rpx;
  margin-top: 24rpx;
  line-height: 78rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #5b8df6 0%, #2563eb 100%);
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 800;
  box-shadow: 0 12rpx 24rpx rgba(37, 99, 235, 0.16);
}

.primary-btn::after {
  border: none;
}

.demo-card,
.guide-card {
  margin-top: 24rpx;
  padding: 28rpx;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.section-title {
  display: block;
  color: #0f172a;
  font-size: 32rpx;
  font-weight: 800;
  line-height: 1.35;
}

.section-note {
  display: block;
  margin-top: 6rpx;
  color: #64748b;
  font-size: 24rpx;
  line-height: 1.45;
}

.demo-badge {
  padding: 7rpx 15rpx;
  border-radius: 999rpx;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 22rpx;
  font-weight: 700;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14rpx;
  margin-top: 24rpx;
}

.info-item {
  padding: 18rpx;
  border-radius: 24rpx;
  background: #f8fbff;
  box-sizing: border-box;
}

.info-item.wide {
  grid-column: span 3;
}

.item-label {
  display: block;
  color: #64748b;
  font-size: 22rpx;
  line-height: 1.35;
}

.item-value {
  display: block;
  margin-top: 8rpx;
  color: #0f172a;
  font-size: 27rpx;
  font-weight: 800;
  line-height: 1.35;
}

.score {
  color: #1d4ed8;
}

.focus-section {
  margin-top: 24rpx;
  padding: 22rpx;
  border-radius: 26rpx;
  background: rgba(239, 246, 255, 0.7);
}

.focus-title,
.guide-title {
  display: block;
  color: #0f172a;
  font-size: 28rpx;
  font-weight: 800;
  line-height: 1.35;
}

.focus-list {
  display: flex;
  flex-wrap: wrap;
  margin-top: 16rpx;
}

.focus-chip {
  margin-right: 12rpx;
  margin-bottom: 12rpx;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.86);
  color: #1d4ed8;
  font-size: 24rpx;
  font-weight: 700;
  line-height: 1.35;
}

.guide-desc {
  display: block;
  margin-top: 12rpx;
  color: #475569;
  font-size: 25rpx;
  line-height: 1.68;
}

.session-note {
  display: inline-flex;
  margin-top: 16rpx;
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 23rpx;
  font-weight: 700;
  line-height: 1.35;
}

</style>