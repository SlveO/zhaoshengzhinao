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
          可以直接向 AI 招生咨询助手提问，例如招生政策、专业方向、录取参考、校园生活等。
        </text>
      </view>
      <button class="consult-btn" @tap="goChat">去 AI 咨询</button>
    </view>
  </view>
</template>

<script setup lang="ts">
interface InfoEntry {
  title: string
  desc: string
  icon: string
}

const infoEntries: InfoEntry[] = [
  {
    title: "学校概况",
    desc: "了解学校办学特色与基本情况",
    icon: "校"
  },
  {
    title: "学院介绍",
    desc: "查看学院设置与培养方向",
    icon: "院"
  },
  {
    title: "专业介绍",
    desc: "了解专业课程、方向与就业",
    icon: "专"
  },
  {
    title: "招生政策",
    desc: "咨询招生规则与录取要求",
    icon: "策"
  },
  {
    title: "招生计划",
    desc: "了解招生人数与专业计划",
    icon: "计"
  },
  {
    title: "招生联系方式",
    desc: "获取官方咨询渠道",
    icon: "联"
  },
  {
    title: "招生咨询群",
    desc: "了解咨询群与答疑安排",
    icon: "群"
  },
  {
    title: "校园生活",
    desc: "了解住宿、社团与校园环境",
    icon: "园"
  }
]

const questionMap: Record<string, string> = {
  "学校概况": "请介绍一下华南师范大学的学校概况和办学特色",
  "学院介绍": "华南师范大学有哪些学院？请介绍一下各学院的方向",
  "专业介绍": "请介绍华南师范大学的专业设置和培养方向",
  "招生政策": "华南师范大学的招生政策是怎样的？有哪些录取要求？",
  "招生计划": "华南师范大学今年的招生计划是怎样的？各专业招多少人？",
  "招生联系方式": "华南师范大学的招生联系方式有哪些？怎么联系招办？",
  "招生咨询群": "怎么加入华南师范大学的招生咨询群？有官方答疑吗？",
  "校园生活": "华南师范大学的校园生活怎么样？住宿、社团、食堂条件如何？"
}

function handleEntryTap(title: string): void {
  const question = questionMap[title] || `请介绍一下${title}`
  uni.setStorageSync("chat_prefill", question)   // fallback: first visit (chat not mounted)
  uni.$emit("chat:prefill", question)
  uni.switchTab({ url: "/pages/chat/index" })
}

function goChat(): void {
  uni.switchTab({
    url: "/pages/chat/index"
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