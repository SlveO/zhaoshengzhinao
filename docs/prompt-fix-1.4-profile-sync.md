# Prompt: Fix Problem 1.4 — Recommendations Page Profile Sync

## Background

Problem 1.4 from @docs/problem.txt: "AI咨询收集信息后，'报考建议'页面没有更新学生个人信息".

Root cause: Backend profile extraction + persistence + API all work correctly. The recommendations page never calls `GET /student/profile`, so `studentInfo` stays at hardcoded empty defaults (line 156).

## Fix: Single file, 3 changes

**File:** `mini-app/src/pages/recommendations/index.vue`

### Change 1: Import `onShow`

Line 141:
```typescript
// Before
import { onLoad } from "@dcloudio/uni-app"

// After
import { onLoad, onShow } from "@dcloudio/uni-app"
```

### Change 2: Add `loadProfile` function

After `loadRecommendations` (after line 180):

```typescript
async function loadProfile(): Promise<void> {
  const sid = getStoredSessionId()
  if (!sid) return
  try {
    const res = await api.get<any>(`/student/profile?session_id=${sid}`)
    if (res.data?.profile) {
      studentInfo.value = { ...studentInfo.value, ...res.data.profile }
    }
  } catch {
    // API unreachable — keep existing defaults
  }
}
```

### Change 3: Replace `onLoad`, add `onShow`

Replace lines 182-184:

```typescript
onLoad(async () => {
  await Promise.all([loadProfile(), loadRecommendations()])
})

onShow(() => {
  loadProfile()
})
```

## Why no SSE event in chat page

`onShow` fires every time the user switches to the "报考建议" tab. A single `GET /student/profile` request is negligible (~50 bytes of JSON). Avoiding `uni.$emit`/`uni.$on` keeps the two pages decoupled with zero cross-component coordination.

## Data Flow

```
AI response → backend extracts profile → saves to DB
  → user switches to "报考建议" tab
  → onShow() → loadProfile() → GET /student/profile
  → studentInfo updated → template re-renders
```

## Verification

1. Open `http://localhost/`, enter as guest
2. Chat: "我是广东物理类考生，高考620分，想学计算机"
3. Wait for AI response to complete
4. Switch to "报考建议" tab
5. "考生信息" card shows: **广东 / 物理类 / 620 分**

## Constraints

- Do NOT modify backend code
- Do NOT modify `mini-app/src/pages/chat/index.vue`
- Do NOT modify `mini-app/src/pages/profile/index.vue`
- Rebuild: `docker compose build mini-app && docker compose up -d mini-app`
