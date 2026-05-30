# Login Gating + 10min Session Window Design

**日期**: 2026-05-31
**分支**: feat/admin-redesign-v2
**审阅**: v2（修复致命缺陷 #1 + 3 个中等问题）

## 目标

将入口从"自动进访客模式"改为"总是先引导登录"，token 有效 + 10 分钟内活跃则自动跳过登录。

## 方案选择

方案 A：入口覆盖层自动弹出 LoginModal + 保留访客模式按钮。关闭弹窗后可选择访客模式。

## 架构

纯前端改动，不涉及后端 API 变更。涉及 2 个文件：

| 文件 | 改动 |
|------|------|
| `mini-app/src/pages/chat/index.vue` | 模板：LoginModal 提升到 v-if/v-else 外；脚本：入口逻辑重构、`last_active_at` 检查 |
| `mini-app/src/pages/profile/index.vue` | `onLoad` 超时检查（在 `loadProfile` 之前） |

## 存储

新增 key: `last_active_at`（Unix 毫秒时间戳），存入 `uni.setStorageSync`

- 写入：每次**成功**进入聊天时更新（登录/注册/访客/token恢复）
- 读取：`onLoad` 入口检查
- 不在失败降级路径中更新

## 致命缺陷修复：LoginModal 提升

**当前 bug**：LoginModal 在 `<view v-else class="chat-page">` 内部。当 `showEntry=true` 时 chat-page 不挂载，LoginModal 不在 DOM 中。`handleRegister()` 设置 `showLogin=true` 也同样是无效操作。

**修复**：将 LoginModal 移到 v-if/v-else 之外：

```html
<view v-if="showEntry" class="entry-overlay">
  <!-- 入口卡片：注册/登录按钮 + 访客模式按钮 -->
</view>
<view v-else class="chat-page">
  <!-- 聊天 UI -->
</view>
<!-- LoginModal 在外层，始终可渲染，自身有 v-if="visible" 控制遮罩 -->
<LoginModal :visible="showLogin" @close="showLogin = false" @success="onLoginSuccess" />
```

LoginModal 使用 `position: fixed` 覆盖全屏，放在外层完全正常。

## 入口决策树（修订）

```
用户打开任意页面
  │
  ├─ token 存在 且 now - last_active_at < 10min
  │     → 直接进入（跳过入口覆盖层）
  │     → POST /miniapp/enter 恢复会话
  │     → 成功：进聊天，更新 last_active_at
  │     → 失败（401/网络错误）：showEntry=true, showLogin=true（回退到入口）
  │
  └─ 否则（无 token 或 超时）
        → showEntry = true（显示入口覆盖层）
        → showLogin = true（自动弹出 LoginModal，现在实际生效了）
        → 用户可：登录 / 注册 / 关闭弹窗选访客模式
```

### 快速通道 API 失败回退

token 存在但服务端已失效时（密钥轮换、账号禁用），API 返回 401，api.ts 的 refresh 逻辑清空 token。catch 分支：

```typescript
catch {
  clearStoredSessionId()
  showEntry.value = true
  showLogin.value = true
  // 不更新 last_active_at —— 失败路径不写时间戳
}
```

## chat/index.vue 改动

### 模板改动

LoginModal 从 `<view v-else class="chat-page">` 内部移到外部，作为 v-if/v-else 同级元素。

### 脚本改动

1. `showLogin` 默认值：`ref(false)` → `ref(true)`。入口覆盖层显示时 LoginModal 自动弹出（致命缺陷修复后生效）
2. `last_active_at` 更新：三处成功路径（`onLoad` 快速通道、`handleGuest` 成功、`onLoginSuccess` 成功），失败降级不更新
3. 快速通道 catch 回退：`showEntry=true, showLogin=true`
4. `handleRegister()` 无需改——`showLogin` 已经是 `true`，点击注册/登录按钮只是再次确认

## profile/index.vue 改动

### onLoad 超时检查（在 loadProfile 之前，避免闪烁）

```typescript
onLoad(() => {
  const token = uni.getStorageSync("token")
  const lastActive = uni.getStorageSync("last_active_at")
  const expired = !lastActive || (Date.now() - Number(lastActive)) > 10 * 60 * 1000
  if (!token || expired) {
    uni.switchTab({ url: "/pages/chat/index" })
    return  // 不执行 loadProfile()
  }
  loadProfile()
})
```

模板无需改动——已有 `v-if="userStore.isGuest"` / `v-else` 分支。

## 命名

使用 `last_active_at`（而非 `login_active_at`），因为访客模式也会更新此时间戳。

## 已知行为（设计内）

- **访客→登录后创建新 session**：`onLoginSuccess()` 传 `session_id: null` 创建全新 session，原有访客对话不保留。这是现有行为，本设计不改变。
- **推荐页无门控**：当前推荐页使用静态 demo 数据，无害。后续接入真实数据时需要补上超时检查。
- **handleGuest catch 降级**：失败时仍设置 `showEntry=false` 允许进入聊天，但 `last_active_at` 不更新——下次打开仍然触发入口。

## 对重建报告问题的解决

| UI 元素 | 旧状态 | 新方案后 |
|---------|--------|---------|
| .logout-btn | 无 token 不渲染 | LoginModal 引导登录 → token 存在 → v-else 可见 |
| .profile-actions | 同上 | 同上 |
| .profile-indicator | profileSummary 为空 | 部分解决：需聊天产生 profile 数据 |
| 意向方向值 | 无 session | 登录自动创建 session |

## 验证

1. `docker compose build mini-app --no-cache && docker compose up -d mini-app`
2. 清除 storage → 打开应用 → LoginModal 应自动弹出（致命缺陷修后）
3. 登录 → 关闭 → 5 分钟内重开 → 直接进聊天
4. 等 10 分钟 → 重开 → LoginModal 再次弹出
5. 登录后访问 profile 页 → 显示退出按钮
6. 超时后直接打开 profile 页 → 应跳回聊天入口（无闪烁）
