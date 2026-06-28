<template>
  <view class="school-page">
    <view class="page-bg-light page-bg-left" />
    <view class="page-bg-light page-bg-right" />
    <text class="page-watermark">SCNU</text>

    <view class="hero-card">
      <image
        class="hero-bg"
        src="/static/images/scnu-building.png"
        mode="aspectFill"
      />
      <view class="hero-mask" />
      <view class="hero-content">
        <text class="school-name">华南师范大学</text>
        <text class="page-title">学校信息服务</text>
        <text class="page-subtitle">
          了解学校概况、学院专业、招生政策与联系方式
        </text>
      </view>
    </view>

    <view class="section">
      <view class="section-header">
        <view>
          <text class="section-title">信息入口</text>
          <text class="section-note">点击后可前往 AI 咨询了解</text>
        </view>
      </view>

      <view class="entry-grid">
        <view
          v-for="item in infoEntries"
          :key="item.title"
          class="entry-card"
          @tap="handleEntryTap(item.title)"
        >
          <view class="entry-icon">
            <text>{{ item.icon }}</text>
          </view>
          <view class="entry-content">
            <text class="entry-title">{{ item.title }}</text>
            <text class="entry-desc">{{ item.desc }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="consult-card">
      <view>
        <text class="consult-title">想了解更具体的问题？</text>
        <text class="consult-desc">
          可以直接向 AI 招生咨询助手提问，例如项目模式、专业方向、费用奖学金、报名流程等。
        </text>
      </view>
      <button class="consult-btn" @tap="goConsult">去 AI 咨询</button>
    </view>
  </view>
</template>

<script setup lang="ts">
interface InfoEntry {
  title: string
  desc: string
  icon: string
}

// 8 个入口主题与知识库 KB001/005-007/008-010/011-012/013-014/019-020/021-023/026 对齐
const infoEntries: InfoEntry[] = [
  {
    title: "学校概况",
    desc: "华南师范大学与国际商学院简介",
    icon: "校"
  },
  {
    title: "项目模式",
    desc: "2+2 与 3+1 培养模式对比",
    icon: "项"
  },
  {
    title: "专业设置",
    desc: "商科、新媒体、市场营销等方向",
    icon: "专"
  },
  {
    title: "合作院校",
    desc: "对接的海外名校列表",
    icon: "院"
  },
  {
    title: "师资力量",
    desc: "雅思团队与专业课教师",
    icon: "师"
  },
  {
    title: "费用奖学金",
    desc: "学费标准与新生奖学金",
    icon: "费"
  },
  {
    title: "报名流程",
    desc: "招生对象、入学考试、报名材料",
    icon: "报"
  },
  {
    title: "联系方式",
    desc: "电话、地址、官网与公众号",
    icon: "联"
  }
]

const questionMap: Record<string, string> = {
  "学校概况": "请介绍一下华南师范大学和国际商学院的基本情况",
  "项目模式": "2+2 和 3+1 项目有什么区别？应该怎么选？",
  "专业设置": "项目有哪些专业方向？各自学什么？",
  "合作院校": "项目可以对接哪些国外大学？",
  "师资力量": "项目的师资怎么样？雅思老师有资质吗？",
  "费用奖学金": "学费多少钱？有奖学金吗？",
  "报名流程": "怎么报名？需要准备什么材料？",
  "联系方式": "怎么联系招生办？"
}

function handleEntryTap(title: string): void {
  const question = questionMap[title] || `请介绍一下${title}`
  // consult 专用 prefill 通道（与 chat:prefill 隔离）
  uni.setStorageSync("consult_prefill", question)
  uni.$emit("consult:prefill", question)
  uni.switchTab({ url: "/pages/consult/index" })
}

function goConsult(): void {
  uni.switchTab({
    url: "/pages/consult/index"
  })
}
</script>

<style scoped>
.school-page {
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
  top: 210rpx;
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
  bottom: 180rpx;
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
  top: 430rpx;
  right: -10rpx;
  color: rgba(37, 99, 235, 0.04);
  font-size: 126rpx;
  font-weight: 900;
  letter-spacing: 10rpx;
  z-index: 0;
}

.hero-card,
.section,
.consult-card {
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
  background: #dbeafe;
  box-shadow: 0 18rpx 46rpx rgba(37, 99, 235, 0.18);
}

.hero-bg {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.hero-mask {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background: linear-gradient(
    105deg,
    rgba(26, 86, 219, 0.58) 0%,
    rgba(37, 99, 235, 0.36) 58%,
    rgba(37, 99, 235, 0.14) 100%
  );
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 182rpx;
}

.school-name {
  align-self: flex-start;
  margin-bottom: 12rpx;
  padding: 7rpx 17rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.24);
  color: #eef6ff;
  font-size: 23rpx;
  font-weight: 700;
  line-height: 1.35;
  text-shadow: 0 2rpx 8rpx rgba(15, 23, 42, 0.18);
}

.page-title {
  color: #ffffff;
  font-size: 42rpx;
  font-weight: 800;
  line-height: 1.28;
  text-shadow: 0 4rpx 12rpx rgba(15, 23, 42, 0.22);
}

.page-subtitle {
  margin-top: 12rpx;
  color: rgba(255, 255, 255, 0.93);
  font-size: 25rpx;
  line-height: 1.62;
  text-shadow: 0 2rpx 8rpx rgba(15, 23, 42, 0.18);
}

.section {
  margin-top: 28rpx;
}

.section-header {
  margin-bottom: 18rpx;
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

.entry-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18rpx;
}

.entry-card {
  min-height: 186rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.78);
  border-radius: 32rpx;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16rpx 40rpx rgba(15, 23, 42, 0.07);
  box-sizing: border-box;
}

.entry-card:active {
  transform: scale(0.99);
  background: rgba(248, 251, 255, 0.96);
}

.entry-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 58rpx;
  height: 58rpx;
  border-radius: 20rpx;
  background: linear-gradient(180deg, #edf6ff 0%, #dcecff 100%);
  color: #1d4ed8;
  font-size: 24rpx;
  font-weight: 900;
  box-shadow: 0 10rpx 22rpx rgba(37, 99, 235, 0.08);
}

.entry-content {
  margin-top: 18rpx;
}

.entry-title {
  display: block;
  color: #0f172a;
  font-size: 29rpx;
  font-weight: 800;
  line-height: 1.35;
}

.entry-desc {
  display: block;
  margin-top: 8rpx;
  color: #64748b;
  font-size: 23rpx;
  line-height: 1.52;
}

.consult-card {
  margin-top: 28rpx;
  padding: 30rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.78);
  border-radius: 34rpx;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16rpx 40rpx rgba(15, 23, 42, 0.08);
}

.consult-title {
  display: block;
  color: #0f172a;
  font-size: 32rpx;
  font-weight: 800;
  line-height: 1.35;
}

.consult-desc {
  display: block;
  margin-top: 10rpx;
  color: #475569;
  font-size: 25rpx;
  line-height: 1.68;
}

.consult-btn {
  height: 80rpx;
  margin-top: 24rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #5b8df6 0%, #2563eb 100%);
  color: #ffffff;
  font-size: 28rpx;
  font-weight: 800;
  line-height: 80rpx;
  box-shadow: 0 12rpx 24rpx rgba(37, 99, 235, 0.16);
}

.consult-btn::after {
  border: none;
}
</style>