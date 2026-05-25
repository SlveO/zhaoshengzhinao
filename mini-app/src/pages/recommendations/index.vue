<template>
  <view class="recommendations-page">
    <view class="page-bg-light page-bg-left" />
    <view class="page-bg-light page-bg-right" />
    <text class="page-watermark">SCNU</text>

    <view class="hero-card">
      <view class="hero-glow" />
      <view class="hero-content">
        <text class="eyebrow">华南师范大学</text>
        <text class="page-title">本校专业推荐</text>
        <text class="page-subtitle">
          结合你的分数、科类和兴趣方向，生成华南师范大学专业报考参考
        </text>
      </view>
    </view>

    <view class="student-card glass-card">
      <view class="section-header">
        <view>
          <text class="section-title">考生信息</text>
          <text class="section-subtitle">用于第一阶段演示</text>
        </view>
        <text class="student-status">已识别</text>
      </view>

      <view class="student-grid">
        <view class="student-item">
          <text class="item-label">生源地</text>
          <text class="item-value">{{ studentInfo.province }}</text>
        </view>

        <view class="student-item">
          <text class="item-label">科类</text>
          <text class="item-value">{{ studentInfo.subject_type }}</text>
        </view>

        <view class="student-item">
          <text class="item-label">分数</text>
          <text class="item-value score">{{ studentInfo.score }} 分</text>
        </view>

        <view class="student-item wide">
          <text class="item-label">意向方向</text>
          <text class="item-value">{{ intentMajorsText }}</text>
        </view>
      </view>
    </view>

    <view class="notice-card glass-card">
      <text class="notice-title">报考参考说明</text>
      <text class="notice-text">{{ disclaimer }}</text>
      <text v-if="hasSession" class="session-note">
        已关联当前咨询会话，后续可按会话生成个性化建议。
      </text>


    </view>

    <view class="list-header">
      <view>
        <text class="section-title">专业建议</text>
        <text class="list-subtitle">共 {{ recommendations.length }} 个本校专业方向</text>
      </view>
    </view>

    <view
      v-for="item in recommendations"
      :key="item.id"
      class="major-card glass-card"
    >
      <view class="major-card-header">
        <view class="major-title-wrap">
          <text class="major-name">{{ item.major_name }}</text>
          <text class="school-name">所属学校：华南师范大学</text>
        </view>

        <view class="score-badge">
          <text class="score-number">{{ item.match_score }}</text>
          <text class="score-label">匹配度</text>
        </view>
      </view>

      <view class="risk-row">
        <text class="risk-tag" :class="riskClass(item.risk_level)">
          {{ riskLabel(item.risk_level) }}
        </text>
        <text class="risk-desc">本校专业报考风险参考</text>
      </view>

      <view class="info-grid">
        <view class="info-item">
          <text class="info-label">参考最低分</text>
          <text class="info-value">{{ formatOptionalNumber(item.min_score) }}</text>
        </view>

        <view class="info-item">
          <text class="info-label">参考最低位次</text>
          <text class="info-value">{{ formatRank(item.min_rank) }}</text>
        </view>

        <view class="info-item wide">
          <text class="info-label">选科要求</text>
          <text class="info-value">{{ item.subjects || "待确认" }}</text>
        </view>
      </view>

      <view class="reasons">
        <text class="reasons-title">推荐理由</text>

        <view
          v-for="reason in item.reasons"
          :key="reason"
          class="reason-line"
        >
          <text class="reason-dot" />
          <text class="reason-text">{{ reason }}</text>
        </view>
      </view>

      <button class="analysis-btn" @tap="goAnalysis(item)">
        查看本校专业分析
      </button>
    </view>

    <view class="bottom-tip">
      <text>后续可由后端结合招生计划、专业组和咨询档案实时生成建议。</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { api } from "@/utils/api"
import { getStoredSessionId } from "@/utils/session"

type RiskLevel = "reach" | "match" | "safe"

interface RiskMeta {
  label: string
  className: string
}

const studentInfo = ref<any>({ province: "", subject_type: "", score: 0, intent_majors: [] })
const recommendations = ref<any[]>([])
const disclaimer = ref("以下建议为华南师范大学校内专业报考参考，不代表录取承诺。")

const sessionId = ref<string | null>(null)
const hasSession = computed(() => Boolean(sessionId.value))

onLoad(async () => {
  const sid = getStoredSessionId()
  sessionId.value = sid
  if (sid) {
    try {
      const res = await api.post<any>("/recommendations", {
        session_id: sid,
        tenant_slug: "scnu",
      })
      if (res.data) {
        recommendations.value = res.data.items || []
        disclaimer.value = res.data.disclaimer || disclaimer.value
      }
    } catch {
      // API 不通时保留空列表
    }
  }
})

const intentMajorsText = computed(() => (studentInfo.value.intent_majors || []).join(" / "))

const riskMap: Record<RiskLevel, RiskMeta> = {
  reach: { label: "可冲", className: "risk-reach" },
  match: { label: "较匹配", className: "risk-match" },
  safe: { label: "较稳妥", className: "risk-safe" },
}

function riskLabel(level?: string): string {
  if (!level) return "待评估"
  return riskMap[level as RiskLevel]?.label || "待评估"
}

function riskClass(level?: string): string {
  if (!level) return "risk-unknown"
  return riskMap[level as RiskLevel]?.className || "risk-unknown"
}

function formatOptionalNumber(value?: number): string {
  if (typeof value !== "number") return "待确认"
  return `${value} 分`
}

function formatRank(value?: number): string {
  if (typeof value !== "number") return "待确认"
  return value.toLocaleString("zh-CN")
}

function goAnalysis(item: any): void {
  uni.navigateTo({
    url: `/pages/compare/index?major=${encodeURIComponent(item.major_name)}`
  })
}
</script>

<style scoped>
.recommendations-page {
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
  top: 140rpx;
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
  right: -230rpx;
  bottom: 220rpx;
  width: 580rpx;
  height: 580rpx;
  background: radial-gradient(
    circle,
    rgba(191, 219, 254, 0.34) 0%,
    rgba(191, 219, 254, 0) 70%
  );
}

.page-watermark {
  position: absolute;
  top: 420rpx;
  right: -10rpx;
  color: rgba(37, 99, 235, 0.04);
  font-size: 126rpx;
  font-weight: 900;
  letter-spacing: 10rpx;
  z-index: 0;
}

.hero-card,
.glass-card,
.list-header,
.bottom-tip {
  position: relative;
  z-index: 1;
}

.hero-card {
  position: relative;
  min-height: 230rpx;
  padding: 34rpx 30rpx;
  border-radius: 36rpx;
  box-sizing: border-box;
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

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
}

.eyebrow {
  align-self: flex-start;
  margin-bottom: 12rpx;
  padding: 7rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.18);
  color: #dbeafe;
  font-size: 23rpx;
  line-height: 1.35;
}

.page-title {
  color: #ffffff;
  font-size: 42rpx;
  font-weight: 800;
  line-height: 1.28;
}

.page-subtitle {
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

.student-card {
  margin-top: 24rpx;
  padding: 26rpx;
}

.section-header,
.major-card-header {
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

.section-subtitle,
.list-subtitle {
  display: block;
  margin-top: 6rpx;
  color: #64748b;
  font-size: 24rpx;
  line-height: 1.45;
}

.student-status {
  padding: 7rpx 15rpx;
  border-radius: 999rpx;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 22rpx;
  font-weight: 700;
}

.student-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14rpx;
  margin-top: 22rpx;
}

.student-item,
.info-item {
  padding: 18rpx;
  border-radius: 24rpx;
  background: #f8fbff;
  box-sizing: border-box;
}

.student-item.wide,
.info-item.wide {
  grid-column: span 3;
}

.item-label,
.info-label {
  display: block;
  color: #64748b;
  font-size: 22rpx;
  line-height: 1.35;
}

.item-value,
.info-value {
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

.notice-card {
  display: flex;
  flex-direction: column;
  margin-top: 20rpx;
  padding: 22rpx 24rpx;
}

.notice-title {
  color: #1d4ed8;
  font-size: 26rpx;
  font-weight: 800;
  line-height: 1.35;
}

.notice-text {
  margin-top: 8rpx;
  color: #475569;
  font-size: 24rpx;
  line-height: 1.62;
}

.list-header {
  margin: 30rpx 4rpx 16rpx;
}

.major-card {
  margin-top: 20rpx;
  padding: 28rpx;
}

.major-title-wrap {
  flex: 1;
  min-width: 0;
  padding-right: 20rpx;
}

.major-name {
  display: block;
  color: #0f172a;
  font-size: 34rpx;
  font-weight: 900;
  line-height: 1.32;
}

.school-name {
  display: block;
  margin-top: 8rpx;
  color: #64748b;
  font-size: 24rpx;
  line-height: 1.4;
}

.score-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 96rpx;
  height: 96rpx;
  border-radius: 30rpx;
  background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
  box-shadow: 0 10rpx 22rpx rgba(37, 99, 235, 0.08);
  flex-shrink: 0;
}

.score-number {
  color: #1d4ed8;
  font-size: 34rpx;
  font-weight: 900;
  line-height: 1;
}

.score-label {
  margin-top: 6rpx;
  color: #64748b;
  font-size: 20rpx;
  line-height: 1;
}

.risk-row {
  display: flex;
  align-items: center;
  margin-top: 20rpx;
}

.risk-tag {
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  font-size: 23rpx;
  font-weight: 800;
  line-height: 1.3;
}

.risk-reach {
  background: #fff7ed;
  color: #ea580c;
}

.risk-match {
  background: #eff6ff;
  color: #1d4ed8;
}

.risk-safe {
  background: #ecfdf5;
  color: #059669;
}

.risk-unknown {
  background: #f1f5f9;
  color: #64748b;
}

.risk-desc {
  margin-left: 12rpx;
  color: #64748b;
  font-size: 23rpx;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14rpx;
  margin-top: 20rpx;
}

.info-item.wide {
  grid-column: span 2;
}

.reasons {
  margin-top: 22rpx;
  padding: 22rpx;
  border-radius: 26rpx;
  background: rgba(239, 246, 255, 0.7);
}

.reasons-title {
  display: block;
  color: #0f172a;
  font-size: 27rpx;
  font-weight: 800;
  line-height: 1.35;
}

.reason-line {
  display: flex;
  align-items: flex-start;
  margin-top: 14rpx;
}

.reason-dot {
  width: 9rpx;
  height: 9rpx;
  margin-top: 15rpx;
  margin-right: 12rpx;
  border-radius: 50%;
  background: #60a5fa;
  flex-shrink: 0;
}

.reason-text {
  flex: 1;
  color: #334155;
  font-size: 25rpx;
  line-height: 1.62;
}

.analysis-btn {
  height: 78rpx;
  margin-top: 24rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #5b8df6 0%, #2563eb 100%);
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 800;
  line-height: 78rpx;
  box-shadow: 0 12rpx 24rpx rgba(37, 99, 235, 0.16);
}

.analysis-btn::after {
  border: none;
}

.bottom-tip {
  margin: 26rpx 6rpx 0;
  color: #64748b;
  font-size: 23rpx;
  line-height: 1.6;
  text-align: center;
}

.session-note {
  display: inline-flex;
  align-self: flex-start;
  margin-top: 14rpx;
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 23rpx;
  font-weight: 700;
  line-height: 1.35;
}
</style>