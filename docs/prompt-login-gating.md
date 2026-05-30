# Prompt: Login Gating + 10min Session Window

将下面 `---` 之间的完整内容复制到新 Claude Code session。串行执行。

---

> **目标**: 入口改为总是先弹出 LoginModal，token 有效 + 10min 内活跃则自动跳过。解决 @reports/miniapp-rebuild-verify-report.md 中"v-if 条件未满足导致 UI 元素不可见"的根因。
>
> **Spec**: @docs/superpowers/specs/2026-05-31-login-gating-design.md
> **Plan**: @docs/superpowers/plans/2026-05-31-login-gating-plan.md
>
> **执行顺序**: Task 1 -> 2 -> 3 -> 4 (串行，每 task commit 一次)
> **修改文件**: `mini-app/src/pages/chat/index.vue`, `mini-app/src/pages/profile/index.vue`
> **注意**: LoginModal (L140) 已是 `<template>` 直接子节点，正确放置。无需移动。

---

## Task 1: 重构 onLoad 入口逻辑 -- 两分支决策树

**Agent**: mini-app-dev
**文件**: `mini-app/src/pages/chat/index.vue` onLoad 函数 (L179-219)

**关键设计决策**: 只有 `token && withinWindow` 两条同时满足才跳过入口。没有独立的慢路径 -- 无 token 的访客即使有 stored session 也走入口门控。API 失败时 fall through 到入口。

替换整个 `onLoad` 函数:

```typescript
onLoad(async () => {
  const token = getToken()
  const stored = getStoredSessionId()
  const lastActive = uni.getStorageSync("last_active_at")
  const withinWindow = lastActive && (Date.now() - Number(lastActive)) < 10 * 60 * 1000

  // Fast path: token valid + within 10min window -> skip entry, restore session
  if (token && withinWindow) {
    const headers: Record<string, string> = { "Authorization": `Bearer ${token}` }
    try {
      const res = await api.post<any>("/miniapp/enter", {
        session_id: stored || null,
        tenant_slug: TENANT_SLUG,
      }, { headers })

      if (res.data) {
        sessionId.value = res.data.session_id
        saveSessionId(res.data.session_id)
        hasSession.value = true
        showEntry.value = false
        uni.setStorageSync("last_active_at", Date.now())
        if (res.data.profile_summary) {
          profileSummary.value = res.data.profile_summary
        }
        if (res.data.chat_history && res.data.chat_history.length) {
          messages.value = res.data.chat_history.map((m: any) => ({
            id: m.message_id || m.id,
            role: m.role,
            content: m.content,
            timestamp: new Date(m.created_at).getTime(),
          }))
        }
        nextTick(() => { scrollToBottom() })
        return
      }
    } catch {
      // Token may be expired server-side -> fall through to entry gating
      clearStoredSessionId()
    }
  }

  // All other cases -> entry gating: show overlay + auto-pop LoginModal
  // Includes: no token, expired window, guest with stored session, first visit
  showEntry.value = true
  showLogin.value = true
})
```

**验证**: `cd mini-app && npm run build:h5 2>&1 | tail -5`

**提交**: `git commit -m "feat: add 10min login window gate to chat onLoad"`

---

## Task 2: handleGuest + onLoginSuccess 成功路径写 last_active_at

**Agent**: mini-app-dev
**文件**: `mini-app/src/pages/chat/index.vue` handleGuest (L225-244) + onLoginSuccess (L246-271)

在 `handleGuest()` 的 `if (res.data)` 块内，`showEntry.value = false` 之后插入一行:
```typescript
uni.setStorageSync("last_active_at", Date.now())
```

在 `onLoginSuccess()` 的 `if (res.data)` 块内，同样位置插入相同一行。

**catch 块不添加** -- 失败降级路径不更新时间戳。

**提交**: `git commit -m "feat: update last_active_at on guest entry and login success"`

---

## Task 3: Profile 页 onLoad 超时门控

**Agent**: mini-app-dev
**文件**: `mini-app/src/pages/profile/index.vue` onLoad + onShow (L127-133)

替换 L127-133:

```typescript
onLoad(async () => {
  const token = uni.getStorageSync("token")
  const lastActive = uni.getStorageSync("last_active_at")
  const expired = !lastActive || (Date.now() - Number(lastActive)) > 10 * 60 * 1000

  if (!token || expired) {
    uni.switchTab({ url: "/pages/chat/index" })
    return
  }

  await loadProfile()
})

onShow(() => {
  loadProfile()
})
```

**验证**: `cd mini-app && npm run build:h5 2>&1 | tail -5`

**提交**: `git commit -m "feat: add 10min timeout gate to profile page onLoad"`

---

## Task 4: 构建 + 产物验证 + visual-verifier

### 4.1 重建 mini-app 镜像

```bash
docker compose build mini-app --no-cache && docker compose up -d mini-app
```

### 4.2 构建产物关键词检查

```bash
# uni-app H5 build outputs to static/js/ not assets/
docker compose exec mini-app sh -c "ls /usr/share/nginx/html/static/js/*.js 2>/dev/null | head -5 || ls /usr/share/nginx/html/assets/*.js 2>/dev/null | head -5"
# Grep in correct directory
docker compose exec mini-app sh -c "grep -rl 'last_active_at' /usr/share/nginx/html/static/js/ /usr/share/nginx/html/assets/ 2>/dev/null && echo 'FOUND: last_active_at' || echo 'NOT FOUND'"
```

### 4.3 调度 visual-verifier 验证完整流程

**调度**: `Agent({subagent_type: "visual-verifier", model: "haiku", description: "Verify login gating flow", prompt: "..."})`

**Prompt:**

```
Verify login gating flow and profile page UI elements in mini-app.

URL: http://localhost:3002 (fallback: http://localhost)
Test credentials: phone=13800000001, password=123456, nickname=testuser

Step 1: Clear storage, verify LoginModal auto-pops via showLogin=true
- browser_resize 375x812
- browser_navigate to http://localhost:3002
- browser_evaluate: localStorage.clear()
- browser_navigate to http://localhost:3002
- browser_wait_for 3000
- browser_snapshot
- Verify: LoginModal visible (showLogin=true set by onLoad entry gating)

Step 2: Guest mode works and sets last_active_at
- Close LoginModal (click backdrop or close button in snapshot)
- browser_snapshot
- Verify: guest mode button visible on entry overlay
- browser_click guest mode button
- browser_wait_for 3000
- browser_snapshot
- Verify: chat page loaded (message input visible)
- browser_evaluate: return JSON.stringify({ lastActive: !!localStorage.getItem('last_active_at'), token: !!localStorage.getItem('token') })
- Verify: last_active_at exists (guest mode also gets a 10min window)

Step 3: Login flow
- browser_navigate to http://localhost:3002
- browser_wait_for 3000
- browser_snapshot
- Verify: LoginModal visible again (guest has no token, always shows entry)
- Fill login form: phone=13800000001, password=123456, click submit
- browser_wait_for 3000
- If login fails: switch to register tab, fill same credentials + nickname=testuser, click register
- browser_wait_for 3000
- browser_snapshot
- Verify: chat page loaded

Step 4: Fast path -- revisit within window
- browser_navigate to http://localhost:3002
- browser_wait_for 2000
- browser_snapshot
- browser_evaluate: return JSON.stringify({ token: !!localStorage.getItem('token'), lastActive: localStorage.getItem('last_active_at') })
- Verify: directly to chat page (NOT entry overlay), token exists, last_active_at recent
- Skip this step if Step 3 both login and register failed

Step 5: Profile page with token -- verify rebuild report fixes
- browser_navigate to http://localhost:3002/#/pages/profile/index
- browser_wait_for 2000
- browser_snapshot
- browser_evaluate: return JSON.stringify({ hasLogoutBtn: !!document.querySelector('.logout-btn'), hasProfileActions: !!document.querySelector('.profile-actions'), hasToken: !!localStorage.getItem('token') })
- Verify: .logout-btn and .profile-actions visible (v-else branch active because token exists)

Output: pass/fail for each step with snapshot summaries. For Step 5, confirm whether the rebuild report hidden UI elements are now visible.
```

### 4.4 后端全量回归

```bash
docker compose exec backend python -m pytest tests/ -q --tb=short 2>&1 | tail -3
```
期望: 273 passed

---

## 总结报告

写入 @reports/miniapp-login-gating-report.md (不超过 50 行):

```
# Mini-App Login Gating + 10min Window Report

## Code Changes
- Task 1: onLoad two-branch decision tree (token+window=fast, rest=entry gate)
- Task 2: handleGuest/onLoginSuccess write last_active_at on success path
- Task 3: Profile page onLoad timeout gate

## Build Artifacts
- last_active_at: FOUND/NOT FOUND

## Backend Tests
- N/N passed

## Visual Verification

### Step 1: LoginModal auto-pop (clear storage, showLogin=true)
- Result: pass/fail

### Step 2: Guest mode
- Result: pass/fail
- last_active_at written: yes/no

### Step 3: Login/Register
- Result: pass/fail

### Step 4: Fast path (revisit within window)
- Result: pass/fail

### Step 5: Profile page with token
- .logout-btn DOM: yes/no
- .profile-actions DOM: yes/no
- token: present/absent
- Result: pass/fail

## Rebuild Report Issue Resolution
- .logout-btn visible: Y/N (new flow guides to login, token present)
- .profile-actions visible: Y/N
- .profile-indicator visible: WARNING needs actual chat to produce profile data
```
