import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { authApi } from "@/utils/api";

export interface UserInfo {
  user_id: string;
  nickname: string;
  phone: string;
}

export const useUserStore = defineStore("user", () => {
  const token = ref<string | null>(getStoredToken());
  const userInfo = ref<UserInfo | null>(getStoredUser());
  const isGuest = computed(() => !token.value);

  function getStoredToken(): string | null {
    try {
      return uni.getStorageSync("token") || null;
    } catch {
      return null;
    }
  }

  function getStoredUser(): UserInfo | null {
    try {
      const raw = uni.getStorageSync("userInfo");
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function setToken(t: string): void {
    token.value = t;
    uni.setStorageSync("token", t);
  }

  function setUserInfo(info: UserInfo): void {
    userInfo.value = info;
    uni.setStorageSync("userInfo", JSON.stringify(info));
  }

  /** 清除所有会话存储（咨询 + 推荐），用于账号切换时避免复用旧 session */
  function clearAllSessions(): void {
    try {
      uni.removeStorageSync("scnu_consult_session_id");      // 推荐/chat session
      uni.removeStorageSync("scnu_consult_module_session_id"); // 咨询 session
      uni.removeStorageSync("chat_prefill");                   // 残留 prefill
      uni.removeStorageSync("consult_prefill");                // 残留 prefill
    } catch {
      // 静默忽略
    }
  }

  async function register(data: {
    username: string;
    password: string;
    region: string;
    subjects: string;
    score: number;
    rank: number;
  }): Promise<boolean> {
    try {
      const res = await authApi.register({
        username: data.username,
        password: data.password,
        region: data.region,
        score: data.score,
        subjects: data.subjects,
        rank: data.rank,
      });
      const body: any = res as any;
      const payload = body?.data ?? body;
      if (payload?.access_token) {
        // 新账号必须使用新 session，清除上一个账号的 session 存储
        clearAllSessions();
        setToken(payload.access_token);
        setUserInfo({ user_id: payload.user_id, nickname: data.username, phone: data.username });
        return true;
      }
    } catch (e: any) {
      uni.showToast({ title: e?.message || "注册失败", icon: "none" });
    }
    return false;
  }

  async function login(data: { username: string; password: string }): Promise<boolean> {
    try {
      const res = await authApi.login(data);
      const body: any = res as any;
      const payload: any = body?.data ?? body;
      if (payload?.access_token) {
        // 切换账号时清除旧 session，确保新登录用户拿到属于自己的新 session
        clearAllSessions();
        setToken(payload.access_token);
        setUserInfo({ user_id: payload.user_id, nickname: payload.username, phone: data.username });
        return true;
      }
    } catch (e: any) {
      uni.showToast({ title: e?.message || "登录失败", icon: "none" });
    }
    return false;
  }

  function logout(): void {
    token.value = null;
    userInfo.value = null;
    uni.removeStorageSync("token");
    uni.removeStorageSync("userInfo");
    // 登出必须清会话，否则下次登录/注册会复用旧账号的 session 与聊天记录
    clearAllSessions();
  }

  return {
    token,
    userInfo,
    isGuest,
    register,
    login,
    logout,
    clearAllSessions,
  };
});
