<template>
  <view class="app-root">
    <slot />
  </view>
</template>

<script setup lang="ts">
import { onLaunch } from "@dcloudio/uni-app";
import { BRAND, getBrandCSSVars } from "@/utils/config";
import { getToken } from "@/utils/api";

onLaunch(() => {
  console.log(`[Mini-App] Launching ${BRAND.name} (${BRAND.shortName})`);

  // 全局登录检测：未登录时统一导航至注册页面
  const token = getToken();
  const lastActive = uni.getStorageSync("last_active_at");
  const withinWindow = lastActive && (Date.now() - Number(lastActive)) < 10 * 60 * 1000;

  if (!token || !withinWindow) {
    // 清除过期状态
    if (token && !withinWindow) {
      uni.removeStorageSync("token");
      uni.removeStorageSync("refresh_token");
      uni.removeStorageSync("userInfo");
      uni.removeStorageSync("last_active_at");
    }
    // 获取当前页面路径，避免重复导航
    const pages = getCurrentPages();
    const currentPath = pages.length ? `/${pages[0].route}` : "";
    if (currentPath !== "/pages/auth/index") {
      uni.reLaunch({ url: "/pages/auth/index" });
    }
  }

  // Apply brand CSS variables
  const vars = getBrandCSSVars();
});

// Provide brand config globally via uni.$brand
uni.$brand = BRAND;
</script>

<style lang="scss">
@import "./uni.scss";

.app-root {
  --brand-primary: v-bind("BRAND.primaryColor");
  --brand-secondary: v-bind("BRAND.secondaryColor");
}
</style>
