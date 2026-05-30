# Login Gating + 10min Session Window Design

**日期**: 2026-05-31
**分支**: feat/admin-redesign-v2

## 目标

将入口从"自动进访客模式"改为"总是先引导登录"，token 有效 + 10 分钟内活跃则自动跳过登录。

## 方案选择

方案 A：入口覆盖层自动弹出 LoginModal + 保留访客模式按钮。关闭弹窗后可选择访客模式。

## 架构

纯前端改动，不涉及后端 API 变更。涉及 2 个文件：

| 文件 | 改动 |
|------|------|
| `mini-app/src/pages/chat/index.vue` | `onLoad` 入口逻辑重构、`showLogin` 默认值 |
| `mini-app/src/pages/profile/index.vue` | `onShow` 超时检查、跳回入口 |

## 存储

新增 key: `login_active_at`（Unix 毫秒时间戳），存入 `uni.setStorageSync`

- 写入：每次成功进入聊天（登录/访客/token恢复）时更新
- 读取：`onLoad` 入口检查

## 入口决策树

```
用户打开任意页面
  │
  ├─ token 存在 且 now - login_active_at < 10min
  │     → 直接进入（跳过入口覆盖层）
  │
  └─ 否则
        → showEntry = true（显示入口覆盖层）
        → showLogin = true（自动弹出 LoginModal）
        → 用户可：登录 / 注册 / 关闭弹窗选访客模式
```

## chat/index.vue 改动

### onLoad 逻辑（约 L179-219）

```
原流程:
  读取 token → 读取 session_id → 尝试恢复 → 失败则 showEntry=true, showLogin=false

新流程:
  读取 token + login_active_at
    │
    ├─ token有效且未超时 → 跳过入口，恢复会话/进聊天，更新 login_active_at
    │
    └─ 否则 → showEntry=true, showLogin=true
        → handleRegister() 不变（弹出 LoginModal）
        → handleGuest() 不变，成功后更新 login_active_at
        → onLoginSuccess() 不变，成功后更新 login_active_at
```

### showLogin 默认值

从 `ref(false)` 改为 `ref(true)`。当 showEntry 变为 true 时，LoginModal 自动弹出。

### login_active_at 更新点

三处：
1. `handleGuest()` 成功进入聊天后 → `uni.setStorageSync("login_active_at", Date.now())`
2. `onLoginSuccess()` 成功进入聊天后 → 同上
3. `onLoad` 中 token 有效且未超时的直接进入分支 → 同上

## profile/index.vue 改动

### onShow 超时检查（约 L100-114）

```
onShow:
  读取 token + login_active_at
  如果无 token 或 超时 → uni.switchTab({ url: "/pages/chat/index" })
  否则 → loadProfile()
```

模板无需改动——已有 `v-if="userStore.isGuest"` / `v-else` 分支，`handleLogout()` 已正确实现。

## 对重建报告问题的解决

| UI 元素 | 旧状态 | 新方案后 |
|---------|--------|---------|
| .logout-btn | 无 token 不渲染 | 引导登录 → token 存在 → 可见 |
| .profile-actions | 同上 | 同上 |
| .profile-indicator | profileSummary 为空 | 部分解决：需聊天产生 profile |
| 意向方向值 | 无 session | 登录自动创建 session |

核心：把"登录"从可选变为默认，token 在正常使用中几乎始终存在。

## 验证

1. `docker compose build mini-app --no-cache && docker compose up -d mini-app`
2. Browser: 清除 storage → 打开应用 → 应看到 LoginModal 自动弹出
3. 登录 → 关闭页面 → 5 分钟内重新打开 → 应直接进聊天
4. 等 10 分钟 → 重新打开 → 应再次弹出 LoginModal
5. Profile 页：登录后访问 → 应看到退出按钮；超时后访问 → 应跳回入口
