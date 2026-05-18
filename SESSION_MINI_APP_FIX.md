# Mini-App 修复指令：补 Build 验证

> 在 `feat/mini-app` 分支上执行。目标：`npm install && TENANT=gdufs bash scripts/build_one.sh` 成功。

---

## Step 1: 进入工作区并安装依赖

```bash
git checkout feat/mini-app
cd mini-app
npm install
```

如果 `npm install` 失败（alpha 包未发布），改用：

```bash
npm install --legacy-peer-deps
# 或切换到稳定版 uni-app
npm install @dcloudio/uni-app@latest @dcloudio/uni-mp-weixin@latest
```

## Step 2: 修复硬编码 localhost

**文件: `src/utils/api.ts`**

```typescript
// 改前
const BASE_URL = "http://localhost:8000/api/v1";

// 改后
const BASE_URL = process.env.NODE_ENV === 'development'
  ? 'http://localhost:8000/api/v1'
  : '/api/v1';  // 生产环境走 nginx 代理
```

**文件: `src/utils/websocket.ts`**

```typescript
// 改前
const WS_BASE = "ws://localhost:8000/api/v1";

// 改后
const WS_PROTOCOL = process.env.NODE_ENV === 'development' ? 'ws://localhost:8000' : `wss://${window.location.host}`;
const WS_BASE = `${WS_PROTOCOL}/api/v1`;
```

## Step 3: 修复 TypeScript 类型错误

**文件: `src/utils/websocket.ts`**

```typescript
// 改前
private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
private pingTimer: ReturnType<typeof setInterval> | null = null;

// 改后（uni-app 目标下 setTimeout 返回 number）
private reconnectTimer: number | null = null;
private pingTimer: number | null = null;
```

## Step 4: 生成 tenant.config.ts 并尝试 build

```bash
# 先单独测试 build.config.js 能否正常生成
TENANT=gdufs node build.config.js

# 检查生成的文件
cat src/tenant.config.ts
# 应输出: const tenantConfig = { ... } as const; export default tenantConfig;

# 如果 node 报 ESM 错误（require is not defined），将 build.config.js 改为 ESM：
# mv build.config.js build.config.cjs
# 然后更新 build_one.sh 中 node build.config.cjs

# 试 build
npx uni build -p mp-weixin
```

## Step 5: 修复 build 中出现的 TS 编译错误

常见的 uni-app 项目错误：

| 错误 | 修复 |
|------|------|
| `Cannot find module '@/utils/...'` | 确认 vite.config.ts 中 alias `@` 路径正确 |
| `Cannot find module '@tenant'` | 确认 build.config.js 已生成 `src/tenant.config.ts` |
| `xxx is not exported from 'vue'` | 检查 pinia/vue 版本兼容：`npm i pinia@2 vue@3` |
| `document/window is not defined` | uni-app 编译目标不能使用浏览器 API——在 .vue 的 `<script setup>` 中用 uni API |
| `.vue files need @vue/compiler-sfc` | `npm install @vue/compiler-sfc` |

## Step 6: 成功标志

```bash
TENANT=gdufs bash scripts/build_one.sh
# 输出: ✓ Build complete: dist/gdufs/

ls dist/gdufs/
# 应看到编译产物
```

## Step 7: 修复完成后

```bash
git add -A
git commit -m "fix: resolve build issues — localhost config, TS types, build pipeline"
git push origin feat/mini-app
```

然后更新 `SESSION_STATE.md` 的 Mini-App 轨道状态为 ✅。

---

如果遇到 `@dcloudio` alpha 包完全无法安装的问题，降级到 uni-app 2.x stable：

```bash
npm uninstall @dcloudio/uni-app @dcloudio/uni-mp-weixin @dcloudio/vite-plugin-uni
npm install @dcloudio/uni-app@2 @dcloudio/uni-mp-weixin@2 @dcloudio/vite-plugin-uni@2
```

然后手动创建 `vue.config.js` 替换 `vite.config.ts`（2.x 用 webpack 而非 vite）。
