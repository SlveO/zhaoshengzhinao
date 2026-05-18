<template>
  <view class="modal-mask" v-if="visible" @tap="$emit('close')">
    <view class="modal-panel" @tap.stop>
      <view class="modal-header">
        <text class="modal-title">{{ mode === 'login' ? '登录' : '注册' }}</text>
        <text class="modal-close" @tap="$emit('close')">✕</text>
      </view>

      <view class="modal-body">
        <text class="modal-desc">
          {{ mode === 'login' ? '登录后可跨校对比，发现更多可能' : '保存画像后即可解锁多校对比功能' }}
        </text>

        <view class="form-group">
          <text class="form-label">手机号</text>
          <input
            class="form-input"
            v-model="phone"
            type="number"
            maxlength="11"
            placeholder="请输入手机号"
          />
        </view>

        <view class="form-group">
          <text class="form-label">密码</text>
          <input
            class="form-input"
            v-model="password"
            type="password"
            placeholder="请输入密码"
          />
        </view>

        <view v-if="mode === 'register'" class="form-group">
          <text class="form-label">昵称（选填）</text>
          <input
            class="form-input"
            v-model="nickname"
            placeholder="给自己起个名字吧"
          />
        </view>

        <button
          class="btn-submit"
          :disabled="!canSubmit || loading"
          @tap="handleSubmit"
        >
          {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
        </button>

        <text class="toggle-mode" @tap="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === 'login' ? '还没有账号？去注册' : '已有账号？去登录' }}
        </text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useUserStore } from "@/stores/user";

const emit = defineEmits<{
  close: [];
  success: [];
}>();

defineProps<{ visible: boolean }>();

const userStore = useUserStore();

const mode = ref<"login" | "register">("register");
const phone = ref("");
const password = ref("");
const nickname = ref("");
const loading = ref(false);

const canSubmit = computed(() => {
  return phone.value.length === 11 && password.value.length >= 6;
});

async function handleSubmit(): Promise<void> {
  if (!canSubmit.value || loading.value) return;
  loading.value = true;

  let ok = false;
  if (mode.value === "login") {
    ok = await userStore.login({ username: phone.value, password: password.value });
  } else {
    ok = await userStore.register({
      username: phone.value,
      password: password.value,
    });
  }

  loading.value = false;
  if (ok) {
    emit("success");
    emit("close");
  }
}
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-panel {
  width: 320px;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}
.modal-title {
  font-size: 17px;
  font-weight: 600;
}
.modal-close {
  font-size: 20px;
  color: #999;
  padding: 4px;
}
.modal-body {
  padding: 20px;
}
.modal-desc {
  font-size: 13px;
  color: #999;
  margin-bottom: 20px;
  display: block;
  text-align: center;
}
.form-group {
  margin-bottom: 16px;
}
.form-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 6px;
  display: block;
}
.form-input {
  height: 44px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0 12px;
  font-size: 15px;
  background: #f9fafb;
}
.btn-submit {
  width: 100%;
  height: 44px;
  line-height: 44px;
  text-align: center;
  background: var(--brand-primary, #1a56db);
  color: #fff;
  border-radius: 22px;
  font-size: 16px;
  border: none;
  margin-top: 8px;
}
.btn-submit[disabled] {
  opacity: 0.5;
}
.toggle-mode {
  display: block;
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
  color: var(--brand-primary, #1a56db);
}
</style>
