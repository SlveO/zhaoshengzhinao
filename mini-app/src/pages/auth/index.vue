<template>
  <view class="auth-page">
    <view class="auth-card">
      <text class="auth-title">招生智脑</text>
      <text class="auth-subtitle">AI 智能高考志愿咨询</text>
      <view class="auth-buttons">
        <button class="auth-btn auth-btn-primary" @tap="openAuth">
          注册 / 登录
        </button>
      </view>
      <text class="auth-hint">登录后即可开始咨询，对话记录保存 30 天</text>
    </view>

    <LoginModal :visible="showLogin" @close="onCloseModal" @success="onAuthSuccess" />
  </view>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import LoginModal from "@/components/LoginModal.vue";

const showLogin = ref(false);

onLoad(() => {
  // 进入页面自动弹出注册表单
  showLogin.value = true;
});

function openAuth(): void {
  showLogin.value = true;
}

function onCloseModal(): void {
  // 不允许关闭，必须完成注册/登录
  showLogin.value = true;
}

function onAuthSuccess(): void {
  showLogin.value = false;
  uni.setStorageSync("last_active_at", Date.now());
  // 注册/登录成功后进入学校信息页面
  uni.reLaunch({ url: "/pages/school/index" });
}
</script>

<style scoped>
.auth-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px 32px;
  margin: 0 32px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.auth-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  display: block;
  margin-bottom: 8px;
}

.auth-subtitle {
  font-size: 16px;
  color: #666;
  display: block;
  margin-bottom: 32px;
}

.auth-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.auth-btn {
  width: 100%;
  height: 48px;
  border-radius: 24px;
  font-size: 16px;
  font-weight: 600;
  line-height: 48px;
  border: none;
}

.auth-btn-primary {
  background: #667eea;
  color: #fff;
}

.auth-hint {
  font-size: 12px;
  color: #999;
  margin-top: 24px;
  display: block;
}
</style>
