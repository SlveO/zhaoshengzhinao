<template>
  <view class="analysis-page">
    <view class="page-bg-light page-bg-left" />
    <view class="page-bg-light page-bg-right" />
    <text class="page-watermark">SCNU</text>

    <view class="hero-card">
      <view class="hero-glow" />

      <view class="hero-content">
        <text class="eyebrow">华南师范大学</text>
        <text class="page-title">专业分析</text>
        <text class="page-subtitle">
          结合你的分数、科类和兴趣方向，分析本校专业匹配度与报考风险
        </text>
        <text class="scope-tip">本页仅用于华师校内专业分析，不展示其他高校</text>
        <text v-if="hasSession" class="session-note-light">
          已关联当前咨询会话
        </text>
      </view>
    </view>

    <view class="student-card glass-card">
      <view class="section-header">
        <view>
          <text class="section-title">学生咨询档案</text>
          <text class="section-subtitle">根据当前演示数据生成</text>
        </view>
        <text class="status-badge">演示</text>
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

    <view class="major-card glass-card">
      <view class="major-header">
        <view class="major-title-wrap">
          <text class="major-name">{{ currentMajor.name }}</text>
          <text class="school-name">所属学校：华南师范大学</text>
        </view>

        <view class="match-badge">
          <text class="match-number">{{ currentMajor.match_score }}</text>
          <text class="match-label">匹配度</text>
        </view>
      </view>

      <view class="risk-row">
        <text class="risk-tag" :class="riskClass">
          {{ currentMajor.risk_label }}
        </text>
        <text class="risk-text">报考参考：{{ currentMajor.risk_label }}</text>
      </view>

      <view class="core-grid">
        <view class="core-item">
          <text class="core-label">参考最低分</text>
          <text class="core-value">{{ currentMajor.min_score }} 分</text>
        </view>

        <view class="core-item">
          <text class="core-label">参考最低位次</text>
          <text class="core-value">{{ currentMajor.min_rank }}</text>
        </view>

        <view class="core-item wide">
          <text class="core-label">选科要求</text>
          <text class="core-value">{{ currentMajor.subjects }}</text>
        </view>
      </view>
    </view>

    <view class="analysis-card glass-card">
      <view class="analysis-section">
        <text class="analysis-title">为什么适合你</text>

        <view
          v-for="item in currentMajor.fit_reasons"
          :key="item"
          class="analysis-line"
        >
          <text class="analysis-dot" />
          <text class="analysis-text">{{ item }}</text>
        </view>
      </view>

      <view class="analysis-section">
        <text class="analysis-title">报考风险说明</text>
        <text class="paragraph-text">{{ currentMajor.risk_desc }}</text>
      </view>

      <view class="analysis-section">
        <text class="analysis-title">建议关注点</text>

        <view class="chip-list">
          <text
            v-for="item in currentMajor.focus_points"
            :key="item"
            class="focus-chip"
          >
            {{ item }}
          </text>
        </view>
      </view>

      <view class="analysis-section last">
        <text class="analysis-title">后续咨询建议</text>
        <text class="paragraph-text">
          你可以继续向 AI 咨询该专业的课程设置、培养方向、近年录取参考、就业去向和所在学院情况。
        </text>
      </view>
    </view>

    <button class="ask-btn" @tap="goChat">
      继续问 AI
    </button>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { onLoad } from "@dcloudio/uni-app"
import { api } from "@/utils/api"
import { getStoredSessionId } from "@/utils/session"

interface PageQuery {
  major?: string
}

const studentInfo = ref<any>({ province: "", subject_type: "", score: 0, intent_majors: [] })
const selectedMajorName = ref("人工智能")
const sessionId = ref<string | null>(null)
const hasSession = computed(() => Boolean(sessionId.value))

const currentMajor = ref<any>({
  name: "加载中...",
  match_score: 0,
  risk_label: "参考",
  min_score: 0,
  min_rank: "暂无",
  subjects: "待确认",
  fit_reasons: [],
  risk_desc: "",
  focus_points: [],
})

const intentMajorsText = computed(() => (studentInfo.value.intent_majors || []).join(" / "))

const riskClass = computed(() => {
  if (currentMajor.value.risk_label === "可冲") return "risk-reach"
  if (currentMajor.value.risk_label === "较匹配") return "risk-match"
  if (currentMajor.value.risk_label === "较稳妥") return "risk-safe"
  return "risk-match"
})

onLoad((query: PageQuery = {}) => {
  const sid = getStoredSessionId()
  sessionId.value = sid

  const majorName = normalizeMajorName(query.major)
  if (majorName) selectedMajorName.value = majorName

  if (sid && majorName) {
    api.get<any>(`/majors/analysis?session_id=${sid}&major=${encodeURIComponent(majorName)}`)
      .then(res => {
        if (res.data) {
          if (res.data.major) Object.assign(currentMajor.value, res.data.major)
          if (res.data.analysis) Object.assign(currentMajor.value, res.data.analysis)
        }
      })
      .catch(() => { /* 保留默认空状态 */ })
  }
})

function normalizeMajorName(major?: string): string {
  if (!major) return ""

  try {
    return decodeURIComponent(major)
  } catch (error) {
    return major
  }
}

function goChat(): void {
  uni.switchTab({
    url: "/pages/chat/index"
  })
}
</script>

<style scoped>
.analysis-page {
  position: relative;
  min-height: 100vh;
  padding: 24rpx 24rpx 42rpx;
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
  top: 160rpx;
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
.ask-btn {
  position: relative;
  z-index: 1;
}

.hero-card {
  position: relative;
  min-height: 250rpx;
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

.scope-tip,
.session-note-light {
  align-self: flex-start;
  margin-top: 16rpx;
  padding: 9rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.2);
  color: #eef6ff;
  font-size: 23rpx;
  line-height: 1.35;
}

.session-note-light {
  margin-top: 12rpx;
}

.glass-card {
  border: 1rpx solid rgba(255, 255, 255, 0.78);
  border-radius: 32rpx;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16rpx 40rpx rgba(15, 23, 42, 0.08);
}

.student-card,
.major-card,
.analysis-card {
  margin-top: 24rpx;
  padding: 28rpx;
}

.section-header,
.major-header {
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

.section-subtitle {
  display: block;
  margin-top: 6rpx;
  color: #64748b;
  font-size: 24rpx;
  line-height: 1.45;
}

.status-badge {
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
.core-item {
  padding: 18rpx;
  border-radius: 24rpx;
  background: #f8fbff;
  box-sizing: border-box;
}

.student-item.wide {
  grid-column: span 3;
}

.item-label,
.core-label {
  display: block;
  color: #64748b;
  font-size: 22rpx;
  line-height: 1.35;
}

.item-value,
.core-value {
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

.major-title-wrap {
  flex: 1;
  min-width: 0;
  padding-right: 20rpx;
}

.major-name {
  display: block;
  color: #0f172a;
  font-size: 38rpx;
  font-weight: 900;
  line-height: 1.3;
}

.school-name {
  display: block;
  margin-top: 8rpx;
  color: #64748b;
  font-size: 24rpx;
  line-height: 1.4;
}

.match-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 104rpx;
  height: 104rpx;
  border-radius: 32rpx;
  background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
  box-shadow: 0 10rpx 22rpx rgba(37, 99, 235, 0.08);
  flex-shrink: 0;
}

.match-number {
  color: #1d4ed8;
  font-size: 36rpx;
  font-weight: 900;
  line-height: 1;
}

.match-label {
  margin-top: 7rpx;
  color: #64748b;
  font-size: 20rpx;
  line-height: 1;
}

.risk-row {
  display: flex;
  align-items: center;
  margin-top: 22rpx;
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

.risk-text {
  margin-left: 12rpx;
  color: #64748b;
  font-size: 23rpx;
}

.core-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14rpx;
  margin-top: 22rpx;
}

.core-item.wide {
  grid-column: span 2;
}

.analysis-section {
  padding-bottom: 24rpx;
  margin-bottom: 24rpx;
  border-bottom: 1rpx solid rgba(226, 232, 240, 0.8);
}

.analysis-section.last {
  padding-bottom: 0;
  margin-bottom: 0;
  border-bottom: none;
}

.analysis-title {
  display: block;
  color: #0f172a;
  font-size: 30rpx;
  font-weight: 900;
  line-height: 1.35;
}

.analysis-line {
  display: flex;
  align-items: flex-start;
  margin-top: 16rpx;
}

.analysis-dot {
  width: 9rpx;
  height: 9rpx;
  margin-top: 15rpx;
  margin-right: 12rpx;
  border-radius: 50%;
  background: #60a5fa;
  flex-shrink: 0;
}

.analysis-text,
.paragraph-text {
  color: #334155;
  font-size: 25rpx;
  line-height: 1.68;
}

.paragraph-text {
  display: block;
  margin-top: 14rpx;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  margin-top: 16rpx;
}

.focus-chip {
  margin-right: 12rpx;
  margin-bottom: 12rpx;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(239, 246, 255, 0.9);
  color: #1d4ed8;
  font-size: 24rpx;
  font-weight: 700;
  line-height: 1.35;
}

.ask-btn {
  height: 82rpx;
  margin-top: 28rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #5b8df6 0%, #2563eb 100%);
  color: #ffffff;
  font-size: 29rpx;
  font-weight: 800;
  line-height: 82rpx;
  box-shadow: 0 14rpx 28rpx rgba(37, 99, 235, 0.18);
}

.ask-btn::after {
  border: none;
}
</style>