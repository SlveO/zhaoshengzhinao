# Login Gating + 10min Session Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Always show entry overlay + LoginModal on first visit, auto-skip when token present + active within 10 minutes.

**Architecture:** Pure frontend — add `last_active_at` storage key, refactor `onLoad` decision tree in chat page, move LoginModal outside v-if/v-else, add timeout gate to profile page onLoad.

**Tech Stack:** Vue 3 Composition API, uni-app storage, TypeScript

**Spec:** `docs/superpowers/specs/2026-05-31-login-gating-design.md`

---

### Task 1: Move LoginModal outside v-if/v-else (critical fix)

**Files:**
- Modify: `mini-app/src/pages/chat/index.vue:1-141` (template only)

**Context:** LoginModal at L140 is inside `<view v-else class="chat-page">`. When `showEntry=true`, the entire chat-page block (including LoginModal) is not in DOM. Setting `showLogin=true` has no effect -- this is a pre-existing bug that also breaks `handleRegister()`. LoginModal uses `v-if="visible"` and `position: fixed`, so it works fine as a sibling element.

- [ ] **Step 1: Move LoginModal to after the v-else block**

Current template structure:
```html
<template>
  <view v-if="showEntry" class="entry-overlay">
    ...
  </view>

  <view v-else class="chat-page">
    ...
    <LoginModal :visible="showLogin" @close="showLogin = false" @success="onLoginSuccess" />
  </view>
</template>
```

Change to:
```html
<template>
  <view v-if="showEntry" class="entry-overlay">
    ...
  </view>

  <view v-else class="chat-page">
    ...
  </view>

  <LoginModal :visible="showLogin" @close="showLogin = false" @success="onLoginSuccess" />
</template>
```

Concretely: cut L140 `<LoginModal ... />` and paste it after `</view>` on L138 (closing tag of chat-page), before `</template>` on L141.

- [ ] **Step 2: Verify template compiles**

Run: `cd mini-app && npx vue-tsc --noEmit --skipLibCheck src/pages/chat/index.vue 2>&1 | head -5`
Expected: no new errors (there may be pre-existing type warnings)

- [ ] **Step 3: Commit**

```bash
git add mini-app/src/pages/chat/index.vue
git commit -m "fix: move LoginModal outside v-if/v-else so it renders when showEntry=true"
```

---

### Task 2: Refactor onLoad entry logic with last_active_at gate

**Files:**
- Modify: `mini-app/src/pages/chat/index.vue:179-219` (onLoad function)

**Context:** Current onLoad tries session restore, falls through to `showEntry.value = true`. New logic adds a fast path: if token exists AND `last_active_at` is within 10 minutes, skip entry overlay entirely. On API failure in fast path, fall back to entry overlay with LoginModal.

- [ ] **Step 1: Replace onLoad with gated entry logic**

Replace the entire `onLoad` function (L179-219):

```typescript
onLoad(async () => {
  const token = getToken()
  const stored = getStoredSessionId()
  const lastActive = uni.getStorageSync("last_active_at")
  const withinWindow = lastActive && (Date.now() - Number(lastActive)) < 10 * 60 * 1000

  // Fast path: token valid + within 10min window, skip entry
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
      // Token may be expired server-side, fall through to entry
      clearStoredSessionId()
    }
  }

  // Slow path: try session restore (existing logic)
  if (stored) {
    try {
      const headers: Record<string, string> = {}
      if (token) headers["Authorization"] = `Bearer ${token}`

      const res = await api.post<any>("/miniapp/enter", {
        session_id: stored,
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
      clearStoredSessionId()
    }
  }

  // Entry gating: show overlay + auto-pop LoginModal
  showEntry.value = true
  showLogin.value = true
})
```

Note: `uni` is globally available in uni-app, no import needed.

- [ ] **Step 2: Commit**

```bash
git add mini-app/src/pages/chat/index.vue
git commit -m "feat: add 10min login window gate to chat onLoad"
```

---

### Task 3: Add last_active_at to handleGuest and onLoginSuccess

**Files:**
- Modify: `mini-app/src/pages/chat/index.vue:225-271` (handleGuest, onLoginSuccess)

- [ ] **Step 1: Add `uni.setStorageSync("last_active_at", Date.now())` to handleGuest success path**

In `handleGuest()` (L225-244), inside `if (res.data)` block, after `showEntry.value = false` add:
```typescript
uni.setStorageSync("last_active_at", Date.now())
```
Do NOT add it in the catch block -- failed entry should not update the timestamp.

- [ ] **Step 2: Add same line to onLoginSuccess success path**

In `onLoginSuccess()` (L246-271), inside `if (res.data)` block, after `showEntry.value = false` add:
```typescript
uni.setStorageSync("last_active_at", Date.now())
```
Do NOT add it in the catch block.

- [ ] **Step 3: Commit**

```bash
git add mini-app/src/pages/chat/index.vue
git commit -m "feat: update last_active_at on guest entry and login success"
```

---

### Task 4: Profile page timeout gate in onLoad

**Files:**
- Modify: `mini-app/src/pages/profile/index.vue:127-133` (onLoad + onShow)

- [ ] **Step 1: Add timeout check to onLoad, before loadProfile**

Replace L127-133:
```typescript
onLoad(async () => {
  await loadProfile()
})

onShow(() => {
  loadProfile()
})
```

With:
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

This prevents the flicker issue (onShow would fire after onLoad rendered the page, causing a visible flash before redirect).

- [ ] **Step 2: Commit**

```bash
git add mini-app/src/pages/profile/index.vue
git commit -m "feat: add 10min timeout gate to profile page onLoad"
```

---

### Task 5: Rebuild and visual verification

- [ ] **Step 1: Full rebuild**

```bash
cd D:\_Greatest_programmer\_Projects\gaokao_agents && docker compose build mini-app --no-cache && docker compose up -d mini-app
```

- [ ] **Step 2: Verify build artifacts contain new code**

```bash
docker compose exec mini-app sh -c "grep -l 'last_active_at' /usr/share/nginx/html/assets/*.js && echo 'FOUND: last_active_at' || echo 'NOT FOUND'"
```

- [ ] **Step 3: Schedule visual-verifier**

Dispatch via `Agent({subagent_type: "visual-verifier", model: "haiku", description: "Verify login gating flow", prompt: "..."})`:

```
Verify login gating flow in mini-app.

URL: http://localhost:3002 (fallback: http://localhost)

Step 1: Clear storage and load page
- browser_resize 375x812
- browser_navigate to http://localhost:3002
- browser_evaluate: localStorage.clear()
- browser_navigate to http://localhost:3002
- browser_wait_for 3000
- browser_snapshot
- Verify: LoginModal should be visible (entry overlay + login form)

Step 2: Guest mode still works
- Close LoginModal (click backdrop)
- browser_snapshot
- Verify: guest mode button visible on entry overlay
- browser_click guest mode button
- browser_wait_for 3000
- browser_snapshot
- Verify: chat page loaded
- browser_evaluate: return JSON.stringify({ lastActive: !!localStorage.getItem('last_active_at'), token: !!localStorage.getItem('token') })
- Verify: last_active_at timestamp exists

Step 3: Login flow
- browser_navigate to http://localhost:3002
- browser_wait_for 3000
- browser_snapshot
- Login via LoginModal (phone: 13800000001, password: 123456)
- browser_wait_for 3000
- browser_snapshot
- Verify: chat page loaded

Step 4: Fast path - revisit within window
- browser_navigate to http://localhost:3002
- browser_wait_for 2000
- browser_snapshot
- Verify: directly to chat page (NOT entry overlay)

Output: pass/fail for each step with snapshot summaries.
```

- [ ] **Step 4: Run backend tests**

```bash
docker compose exec backend python -m pytest tests/ -q --tb=short 2>&1 | tail -3
```
Expected: 273 passed

- [ ] **Step 5: Final commit**

```bash
git add -A && git commit -m "chore: login gating rebuild and verification complete"
```

---

## Verification Checklist

1. Clear storage -> open app -> LoginModal auto-pops
2. Close LoginModal -> guest mode button visible
3. Guest mode -> chat loads -> last_active_at set
4. Login -> chat loads -> last_active_at updated
5. Revisit within 10min -> directly to chat (no entry overlay)
6. Profile page with token + within window -> loads normally
7. Profile page without token -> redirects to chat entry
8. All 273 backend tests pass
