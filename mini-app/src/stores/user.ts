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

  async function register(data: { username: string; password: string }): Promise<boolean> {
    try {
      const res = await authApi.register({ ...data, region: "", score: 0, subjects: "" });
      const body: any = res as any;
      if (body.access_token) {
        setToken(body.access_token);
        setUserInfo({ user_id: body.user_id, nickname: data.username, phone: data.username });
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
      if (body.access_token) {
        setToken(body.access_token);
        setUserInfo({ user_id: body.user_id, nickname: body.username, phone: data.username });
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
  }

  return {
    token,
    userInfo,
    isGuest,
    register,
    login,
    logout,
  };
});
