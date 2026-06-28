<template>
  <view class="modal-mask" v-if="visible" @tap="$emit('close')">
    <view class="modal-panel" @tap.stop>
      <view class="modal-header">
        <text class="modal-title">{{ mode === 'login' ? '登录' : '注册' }}</text>
        <text class="modal-close" @tap="$emit('close')">✕</text>
      </view>

      <scroll-view scroll-y class="modal-body">
        <text class="modal-desc">
          {{ mode === 'login' ? '登录后即可继续咨询' : '填写基本信息，解锁精准推荐' }}
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
            placeholder="至少 6 位"
          />
        </view>

        <template v-if="mode === 'register'">
          <view class="form-group">
            <text class="form-label">省份</text>
            <picker
              :value="provinceIndex"
              :range="provinceList"
              @change="onProvinceChange"
            >
              <view class="form-picker">
                <text :class="['form-picker-text', form.region ? '' : 'form-placeholder']">
                  {{ form.region || '请选择省份' }}
                </text>
                <text class="form-arrow">›</text>
              </view>
            </picker>
          </view>

          <view class="form-group">
            <text class="form-label">选科</text>
            <picker
              :value="subjectsIndex"
              :range="subjectsList"
              @change="onSubjectsChange"
            >
              <view class="form-picker">
                <text :class="['form-picker-text', form.subjects ? '' : 'form-placeholder']">
                  {{ form.subjects || '请选择选科组合' }}
                </text>
                <text class="form-arrow">›</text>
              </view>
            </picker>
          </view>

          <view class="form-group">
            <text class="form-label">高考分数</text>
            <input
              class="form-input"
              type="number"
              v-model="form.score"
              placeholder="0-750"
              maxlength="3"
            />
          </view>

          <view class="form-group">
            <text class="form-label">高考位次</text>
            <input
              class="form-input"
              type="number"
              v-model="form.rank"
              placeholder="全省排名"
            />
          </view>
        </template>

        <view v-if="errorMsg" class="form-error">
          <text>{{ errorMsg }}</text>
        </view>

        <button
          class="btn-submit"
          :disabled="!canSubmit || loading"
          @tap="handleSubmit"
        >
          {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
        </button>

        <text class="toggle-mode" @tap="switchMode">
          {{ mode === 'login' ? '还没有账号？去注册' : '已有账号？去登录' }}
        </text>
      </scroll-view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from "vue";
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
const loading = ref(false);
const errorMsg = ref("");

const provinceList = [
  "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
  "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
  "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
  "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆",
];
const subjectsList = [
  "物化生", "物化地", "物化政", "物生地", "物生政", "物地政",
  "历化生", "历化地", "历化政", "历生地", "历生政", "历地政",
];

const provinceIndex = ref(0);
const subjectsIndex = ref(0);
const form = reactive({
  region: "",
  subjects: "",
  score: "",
  rank: "",
});

function onProvinceChange(e: any) {
  provinceIndex.value = e.detail.value;
  form.region = provinceList[e.detail.value];
}

function onSubjectsChange(e: any) {
  subjectsIndex.value = e.detail.value;
  form.subjects = subjectsList[e.detail.value];
}

function switchMode() {
  mode.value = mode.value === "login" ? "register" : "login";
  errorMsg.value = "";
}

const canSubmit = computed(() => {
  if (phone.value.length !== 11 || password.value.length < 6) return false;
  if (mode.value === "register") {
    if (!form.region || !form.subjects) return false;
    const score = parseInt(form.score, 10);
    const rank = parseInt(form.rank, 10);
    if (isNaN(score) || score < 0 || score > 750) return false;
    if (isNaN(rank) || rank <= 0) return false;
  }
  return true;
});

async function handleSubmit(): Promise<void> {
  if (!canSubmit.value || loading.value) return;
  errorMsg.value = "";
  loading.value = true;

  let ok = false;
  if (mode.value === "login") {
    ok = await userStore.login({ username: phone.value, password: password.value });
  } else {
    ok = await userStore.register({
      username: phone.value,
      password: password.value,
      region: form.region,
      subjects: form.subjects,
      score: parseInt(form.score, 10),
      rank: parseInt(form.rank, 10),
    });
  }

  loading.value = false;
  if (ok) {
    emit("success");
    emit("close");
  } else if (mode.value === "register") {
    errorMsg.value = "注册失败，手机号可能已被注册";
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
  width: 340px;
  max-height: 85vh;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
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
  width: 100%;
  box-sizing: border-box;
  padding: 20px 20px 8px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.modal-desc {
  font-size: 13px;
  color: #999;
  margin-bottom: 20px;
  display: block;
  text-align: center;
}
.form-group {
  margin-bottom: 14px;
}
.form-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 6px;
  display: block;
}
.form-input {
  width: 100%;
  box-sizing: border-box;
  height: 44px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0 12px;
  font-size: 15px;
  background: #f9fafb;
}
.form-picker {
  width: 100%;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 44px;
  padding: 0 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.form-picker-text {
  font-size: 15px;
  color: #1a1a1a;
}
.form-placeholder {
  color: #9ca3af;
}
.form-arrow {
  font-size: 18px;
  color: #9ca3af;
}
.form-error {
  background: #fef2f2;
  color: #dc2626;
  font-size: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 12px;
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
  margin: 16px 0 8px;
  padding: 12px 8px;
  font-size: 13px;
  color: var(--brand-primary, #1a56db);
  border-top: 1px solid #f0f0f0;
}
</style>
