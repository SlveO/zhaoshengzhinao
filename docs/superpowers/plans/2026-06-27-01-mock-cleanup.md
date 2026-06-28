# Plan 1: Mock Data Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all mock data (inline constants, mock files, fallback logic) from admin-spa so every page renders real backend data or shows an error state.

**Architecture:** Three-layer cleanup — (1) remove mock fallback in `.catch()` blocks of 3 pages, (2) delete 3 mock files, (3) verify build + manual smoke test. Distribution module is left untouched (it will be hidden in Plan 2, not cleaned).

**Tech Stack:** React 19 + Vite + TypeScript (admin-spa)

**Spec reference:** [docs/superpowers/specs/admin_data_overhaul_spec.md](file:///d:/_Greatest_programmer/_Projects/gaokao_agents/docs/superpowers/specs/admin_data_overhaul_spec.md) §二

**Scope note:** DashboardPage / ChannelsPage / ConsultationsPage / LeadWorkbenchPage / ReportsPage inline mocks are NOT touched here — those files are deleted or rewritten in Plan 2. This plan only handles pages that stay in place but have mock fallback: ProfileDashboardPage, InsightsPage, KnowledgeSettingsPage. The 3 mock files deleted here are: profileDashboard.ts, insights.ts, knowledgeBase.ts. distribution.ts is kept (Distribution module hidden in Plan 2).

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `admin-spa/src/pages/ProfileDashboardPage.tsx` | Modify L5, L21 | Remove mock import + fallback |
| `admin-spa/src/pages/InsightsPage.tsx` | Modify L6, L41-43 | Remove mock import + 3 fallbacks |
| `admin-spa/src/pages/KnowledgeSettingsPage.tsx` | Modify L4, L31 | Remove mock import + fallback |
| `admin-spa/src/mock/profileDashboard.ts` | Delete | Mock file no longer referenced |
| `admin-spa/src/mock/insights.ts` | Delete | Mock file no longer referenced |
| `admin-spa/src/mock/knowledgeBase.ts` | Delete | Mock file no longer referenced |

---

## Task 1: Remove mock fallback from ProfileDashboardPage

**Files:**
- Modify: `admin-spa/src/pages/ProfileDashboardPage.tsx:5` (remove import)
- Modify: `admin-spa/src/pages/ProfileDashboardPage.tsx:21` (remove fallback)

- [ ] **Step 1: Read current file state**

Run: Read tool on `admin-spa/src/pages/ProfileDashboardPage.tsx` lines 1-30
Confirm line 5 is `import { mockProfileDashboard } from '../mock/profileDashboard'` and line 21 is `setData(mockProfileDashboard)`.

- [ ] **Step 2: Remove mock import on line 5**

Edit `admin-spa/src/pages/ProfileDashboardPage.tsx`:
- old_string: `import { mockProfileDashboard } from '../mock/profileDashboard'\n`
- new_string: `` (empty string — delete the entire line)

- [ ] **Step 3: Remove mock fallback in catch block (line 21)**

Edit `admin-spa/src/pages/ProfileDashboardPage.tsx`:
- old_string:
```
      .catch((e) => {
        setError(e?.message || '获取数据失败')
        setData(mockProfileDashboard)
      })
```
- new_string:
```
      .catch((e) => {
        setError(e?.message || '获取数据失败')
      })
```

- [ ] **Step 4: Verify no remaining mock references in this file**

Run: Grep tool
- pattern: `mockProfileDashboard|from '../mock`
- path: `admin-spa/src/pages/ProfileDashboardPage.tsx`
Expected: No matches.

- [ ] **Step 5: Commit**

```bash
git add admin-spa/src/pages/ProfileDashboardPage.tsx
git commit -m "refactor(admin-spa): remove mock fallback from ProfileDashboardPage"
```

---

## Task 2: Remove mock fallback from KnowledgeSettingsPage

**Files:**
- Modify: `admin-spa/src/pages/KnowledgeSettingsPage.tsx:4` (remove import)
- Modify: `admin-spa/src/pages/KnowledgeSettingsPage.tsx:31` (remove fallback)

- [ ] **Step 1: Read current file state**

Run: Read tool on `admin-spa/src/pages/KnowledgeSettingsPage.tsx` lines 1-35
Confirm line 4 is `import { mockDocuments } from '../mock/knowledgeBase'` and line 31 is `setDocs(mockDocuments)`.

- [ ] **Step 2: Remove mock import on line 4**

Edit `admin-spa/src/pages/KnowledgeSettingsPage.tsx`:
- old_string: `import { mockDocuments } from '../mock/knowledgeBase'\n`
- new_string: `` (empty)

- [ ] **Step 3: Remove mock fallback in catch block (line 31)**

Edit `admin-spa/src/pages/KnowledgeSettingsPage.tsx`:
- old_string:
```
      .catch((e) => {
        setError(e?.message || '获取知识库文档失败')
        setDocs(mockDocuments)
      })
```
- new_string:
```
      .catch((e) => {
        setError(e?.message || '获取知识库文档失败')
      })
```

- [ ] **Step 4: Verify no remaining mock references**

Run: Grep tool
- pattern: `mockDocuments|from '../mock`
- path: `admin-spa/src/pages/KnowledgeSettingsPage.tsx`
Expected: No matches.

- [ ] **Step 5: Commit**

```bash
git add admin-spa/src/pages/KnowledgeSettingsPage.tsx
git commit -m "refactor(admin-spa): remove mock fallback from KnowledgeSettingsPage"
```

---

## Task 3: Remove mock fallback from InsightsPage

**Files:**
- Modify: `admin-spa/src/pages/InsightsPage.tsx:6` (remove import)
- Modify: `admin-spa/src/pages/InsightsPage.tsx:41-43` (remove 3 fallbacks)

Note: InsightsPage also has emotion timeline section that will be deleted in Plan 2. This task ONLY removes mock fallback references — it does NOT delete the emotion timeline section (that's Plan 2's job). The `mockEmotionTimeline` import and its `.catch()` fallback call are removed here; the emotion timeline state and API call remain (will be cleaned in Plan 2).

- [ ] **Step 1: Read current file state**

Run: Read tool on `admin-spa/src/pages/InsightsPage.tsx` lines 1-55
Confirm:
- Line 6: `import { mockTopicCloud, mockHotQuestions, mockEmotionTimeline } from '../mock/insights'`
- Lines 41-43: three `setXxx(mockXxx)` calls inside the `if (rejected.length === 3)` block

- [ ] **Step 2: Remove mock import on line 6**

Edit `admin-spa/src/pages/InsightsPage.tsx`:
- old_string: `import { mockTopicCloud, mockHotQuestions, mockEmotionTimeline } from '../mock/insights'\n`
- new_string: `` (empty)

- [ ] **Step 3: Remove 3 mock fallback calls (lines 41-43)**

Edit `admin-spa/src/pages/InsightsPage.tsx`:
- old_string:
```
      if (rejected.length === 3) {
        const firstErr = (rejected[0] as PromiseRejectedResult).reason
        setError(firstErr?.message || '获取分析数据失败')
        setTopicCloud(mockTopicCloud)
        setHotQuestions(mockHotQuestions)
        setEmotionTimeline(mockEmotionTimeline(days))
        return
      }
```
- new_string:
```
      if (rejected.length === 3) {
        const firstErr = (rejected[0] as PromiseRejectedResult).reason
        setError(firstErr?.message || '获取分析数据失败')
        return
      }
```

- [ ] **Step 4: Verify no remaining mock references**

Run: Grep tool
- pattern: `mockTopicCloud|mockHotQuestions|mockEmotionTimeline|from '../mock`
- path: `admin-spa/src/pages/InsightsPage.tsx`
Expected: No matches.

- [ ] **Step 5: Commit**

```bash
git add admin-spa/src/pages/InsightsPage.tsx
git commit -m "refactor(admin-spa): remove mock fallback from InsightsPage"
```

---

## Task 4: Delete 3 mock files

**Files:**
- Delete: `admin-spa/src/mock/profileDashboard.ts`
- Delete: `admin-spa/src/mock/insights.ts`
- Delete: `admin-spa/src/mock/knowledgeBase.ts`

Prerequisite: Tasks 1-3 completed (no more imports of these files).

- [ ] **Step 1: Verify no references to the 3 mock files anywhere in admin-spa**

Run: Grep tool
- pattern: `from '../mock/profileDashboard'|from '../mock/insights'|from '../mock/knowledgeBase'|from '@/mock/profileDashboard'|from '@/mock/insights'|from '@/mock/knowledgeBase'`
- path: `admin-spa/src`
Expected: No matches.

- [ ] **Step 2: Delete the 3 files**

Use DeleteFile tool with paths:
- `admin-spa/src/mock/profileDashboard.ts`
- `admin-spa/src/mock/insights.ts`
- `admin-spa/src/mock/knowledgeBase.ts`

- [ ] **Step 3: Check if mock directory is now empty (only distribution.ts remains)**

Run: LS tool on `admin-spa/src/mock`
Expected: Only `distribution.ts` remains (kept intentionally per spec §4.8).

- [ ] **Step 4: Commit**

```bash
git add -A admin-spa/src/mock/
git commit -m "chore(admin-spa): delete 3 mock files (profileDashboard, insights, knowledgeBase)

distribution.ts kept — Distribution module hidden in Plan 2, not cleaned."
```

---

## Task 5: Build verification

**Files:** None modified.

- [ ] **Step 1: Run TypeScript build**

Run:
```bash
cd admin-spa && npm run build
```
Expected: Build succeeds with no TypeScript errors. No "Cannot find module '../mock/...'" errors.

- [ ] **Step 2: If build fails, diagnose**

If build fails with "Cannot find module" errors — a mock import was missed. Re-run Grep from Task 4 Step 1, find the offending file, remove the import, rebuild.

If build fails with unused variable errors (e.g., `mockProfileDashboard` declared but not used) — should not happen since imports were removed in Tasks 1-3.

- [ ] **Step 3: Manual smoke test (optional, dev server already running on terminal 3)**

Open `http://localhost:3001?tenant=scnu` in browser, log in as `admin`/`admin123`.
Visit each of the 3 modified pages:
- `/profile` — should show loading → error state (backend analytics may or may not return data; either way, NO mock data)
- `/insights` — same expectation
- `/knowledge` — same expectation

Confirm: No fake/garish data appears. Error states display correctly when backend is unavailable.

---

## Task 6: Final verification

**Files:** None modified.

- [ ] **Step 1: Global grep for any remaining mock imports (excluding distribution)**

Run: Grep tool
- pattern: `from '\.\./mock/|from '@/mock/`
- path: `admin-spa/src`
- output_mode: content
- -n: true
Expected: Only matches are `from '../mock/distribution'` (in DistributionTasksPage / DistributionChannelsPage / DistributionLogsPage — these are intentionally kept).

- [ ] **Step 2: Global grep for mock variable naming patterns**

Run: Grep tool
- pattern: `mock[A-Z]`
- path: `admin-spa/src`
- output_mode: content
- -n: true
Expected: Only matches are in `admin-spa/src/mock/distribution.ts` and its 3 consumers (kept intentionally).

- [ ] **Step 3: Confirm plan complete**

All 6 tasks done. Plan 1 complete. Next plan: Plan 4 (DB admin panel).

---

## Self-Review

**Spec coverage (§二 of spec):**
- §2.2 mock files: 3 of 4 deleted (distribution.ts kept per §4.8) ✅
- §2.3 mock fallback: 3 of 6 pages cleaned (Distribution 3 pages skipped per §4.8) ✅
- §2.4 acceptance: build passes, no mock imports except distribution ✅
- §2.1 inline mock in DashboardPage/ChannelsPage/ConsultationsPage/LeadWorkbenchPage/ReportsPage: NOT in this plan — these files are deleted/rewritten in Plan 2 ✅ (scope correctly delegated)

**Placeholder scan:** No TBD/TODO. All steps have concrete code or commands. ✅

**Type consistency:** No types introduced. Mock imports removed symmetrically (import line + fallback line in each file). ✅

**Scope boundary:** Distribution module mock (distribution.ts + 3 page fallbacks) intentionally NOT cleaned — matches spec §4.8 "Distribution 3 页不做任何修改". ✅
