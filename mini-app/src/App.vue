<template>
  <view class="app-root">
    <slot />
  </view>
</template>

<script setup lang="ts">
import { onLaunch } from "@dcloudio/uni-app";
import { BRAND, getBrandCSSVars } from "@/utils/config";

onLaunch(() => {
  console.log(`[Mini-App] Launching ${BRAND.name} (${BRAND.shortName})`);

  // Apply brand CSS variables
  const vars = getBrandCSSVars();
  // In mini-program, document is unavailable. We apply via inline style on root.
  // The uni.scss and page-level styles handle brand colors via CSS variables defined in theme.
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
