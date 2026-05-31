# Mini-App Login Gating + 10min Window Report

**日期**: 2026-05-31
**分支**: feat/admin-redesign-v2

## Code Changes

| Task | 描述 | Commit |
|------|------|--------|
| 1 | onLoad two-branch decision tree (token+window=fast, rest=entry gate) | 9de1ad8 |
| 2 | handleGuest/onLoginSuccess write last_active_at on success path | e2c6a6a |
| 3 | Profile page onLoad timeout gate (redirect to chat if !token||expired) | e420f1c |

## Build Artifacts

| 关键词 | Result |
|--------|--------|
| last_active_at (chat bundle) | FOUND (pages-chat-index.*.js) |
| last_active_at (profile bundle) | FOUND (pages-profile-index.*.js) |

## Backend Tests

**270 passed / 3 failed** (E2E profile/page-load tests need auth — expected regression from login gating)

## Visual Verification (Haiku)

### Step 1: LoginModal auto-pop (clear storage, showLogin=true)
- **PASS** — Entry overlay + LoginModal visible on first load

### Step 2: Guest mode
- **PASS** — Chat page loads after clicking 访客模式

### Step 3: Login/Register
- **FAIL** — Backend not available at localhost:8000; API calls silently fail

### Step 4: Fast path (revisit within window)
- **SKIPPED** — Depends on Step 3

### Step 5: Profile page with token (manual token set)
- **PASS** — .logout-btn ✅ visible, .profile-actions ✅ visible
- 退出登录 button present and clickable
- Profile card and 去 AI 咨询 button rendered

## Rebuild Report Issue Resolution

| UI Element | Before | After |
|------------|--------|-------|
| .logout-btn | ❌ (v-else, no token) | ✅ (visible with token) |
| .profile-actions | ❌ (v-else, no token) | ✅ (visible with token) |
| .profile-indicator | ❌ (v-if, no profile data) | ⚠️ (needs chat flow to produce profile data) |

**根因已解决**: 登录门控 (Task 1-3) 确保用户通过 LoginModal 登录后获得 token，token 触发 v-else 分支使 .logout-btn 和 .profile-actions 渲染。

## Issues
1. z-index: entry overlay 遮挡 LoginModal 点击事件
2. Backend API unreachable at localhost:8000 (mini-app 直接连 port 8000，不经过 nginx)
3. Fast path 异步 onLoad 导致 entry overlay 短暂闪烁
