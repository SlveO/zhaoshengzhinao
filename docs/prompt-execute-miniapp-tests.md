# Prompt: 执行 mini-app 修复的测试（单元 + 集成 + E2E 双轨）

将下面 `---` 之间的完整内容复制到新 Claude Code session。串行执行 Phase 0→1→2→3→4。

---

> **任务**：执行已编写的测试，验证 miniapp 修复。E2E 双轨并行：Playwright DOM 断言 + visual-verifier 视觉截图。
>
> **前提**：Docker 环境已启动（`docker compose up -d`），测试代码已由 @docs/prompt-test-miniapp-fixes.md 编写完成。

---

## Phase 0: 环境确认

```bash
docker compose ps
docker compose exec backend python -c "import httpx; r=httpx.get('http://nginx/'); print(f'nginx OK: {r.status_code}')"
```

---

## Phase 1: 后端单元测试（agent: test-runner, model: sonnet）

```
执行后端单元测试——intent_majors 提取（8 个新增测试 + 全部已有测试）。

## Step 1: 运行新增测试
docker compose exec backend python -m pytest tests/unit/test_profile_extraction.py::TestExtractIntentMajors -v --tb=short 2>&1

## Step 2: 运行全部单元测试（确保无回退）
docker compose exec backend python -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5

## 输出
列出每个测试的 PASS/FAIL 状态。只输出摘要行，过滤掉 warnings。
```

---

## Phase 2: 集成测试（agent: test-runner, model: sonnet）

```
执行集成测试——推荐接口 intent 加分 + profile API（3 个新增测试 + 全部已有集成测试）。

## Step 1: 运行新增测试
docker compose exec backend python -m pytest tests/integration/test_miniapp_pipeline.py::TestRecommendationsWithIntent -v --tb=long 2>&1

## Step 2: 运行全部集成测试
docker compose exec backend python -m pytest tests/integration/ -q --tb=short 2>&1 | tail -5

## 输出
列出每个测试的 PASS/FAIL 状态 + 失败项 traceback 摘要。
```

---

## Phase 3: E2E 双轨并行（3 个 agent 同时启动）

**关键**：此阶段同时启动 3 个 agent——1 个 test-runner 执行 Playwright DOM 测试 + 2 个 visual-verifier 视觉检查。它们互不依赖，用单条消息并行 tool call。

### Agent 1: E2E Playwright DOM 测试（agent: test-runner, model: sonnet）

```
执行 E2E Playwright DOM 测试文件（@backend/tests/e2e/test_miniapp_profile_ux.py × 11 个测试）。

## 命令
docker compose exec backend python -m pytest tests/e2e/test_miniapp_profile_ux.py -v --tb=long 2>&1

## 输出
每个测试的 PASS/FAIL 状态。FAIL 项附 full traceback。列出所有 DOM 元素不可见的测试。
```

### Agent 2: 视觉验证 — Chat + Profile 页面（agent: visual-verifier, model: sonnet）

```
你是 visual-verifier。请视觉验证 mini-app 的聊天页和 profile 页。

## 目标 URL
- Chat: http://localhost:3002（如不通则 http://localhost）
- Profile: http://localhost:3002/pages/profile/index（如不通则 http://localhost/pages/profile/index）

## 聊天页步骤
1. browser_resize 375x812
2. browser_navigate 到 chat 首页
3. browser_snapshot → 确认 .entry-overlay 可见
4. browser_click "访客模式"
5. browser_wait_for 3000
6. 在 .message-input 输入"广东物理类 620 分想学计算机"
7. browser_click .send-button
8. browser_wait_for 25000
9. browser_snapshot → 检查 DOM 结构
10. browser_take_screenshot → 保存截图
11. browser_evaluate 执行:
    ```js
    JSON.stringify({
      profileIndicator: !!document.querySelector('.profile-indicator'),
      indicatorText: document.querySelector('.profile-indicator-text')?.textContent || '',
      aiBubbles: document.querySelectorAll('.bubble-ai').length,
      hasChatPage: !!document.querySelector('.chat-page')
    })
    ```

## Profile 页步骤
1. browser_navigate 到 profile 页
2. browser_snapshot
3. browser_take_screenshot
4. browser_evaluate:
    ```js
    JSON.stringify({
      logoutBtn: !!document.querySelector('.logout-btn'),
      profileActions: !!document.querySelector('.profile-actions'),
      loginBtn: !!document.querySelector('button') && Array.from(document.querySelectorAll('button')).some(b => b.textContent.includes('登录查看完整档案')),
      hasToken: !!localStorage.getItem('token')
    })
    ```

## 输出格式
```
🎯 Visual Report: Mini-app Chat + Profile
Viewport: 375×812

✅ Passed:
  - entry-overlay visible
  - guest mode enters chat
  - ...

⚠ Issues:
  - .profile-indicator NOT FOUND — v-if condition may be false
  - .logout-btn NOT FOUND — user may be in guest state

📸 Screenshots:
  - chat-after-message: <path>
  - profile-page: <path>

DOM JS Eval Results:
  - profileIndicator: true/false
  - indicatorText: "..."
  - logoutBtn: true/false
  - profileActions: true/false
```
```

### Agent 3: 视觉验证 — 推荐页（agent: visual-verifier, model: sonnet）

```
你是 visual-verifier。请视觉验证 mini-app 报考建议页面。

## 目标 URL
http://localhost:3002/pages/recommendations/index（如不通则 http://localhost/pages/recommendations/index）

## 步骤
1. browser_resize 375x812
2. browser_navigate 到推荐页
3. browser_wait_for 3000
4. browser_snapshot → 抓取 DOM
5. browser_take_screenshot → 截图
6. browser_evaluate 执行:
    ```js
    JSON.stringify({
      studentCard: !!document.querySelector('.student-card'),
      intentLabel: (() => {
        const labels = document.querySelectorAll('.item-label');
        for (const l of labels) { if (l.textContent.includes('意向方向')) return true; }
        return false;
      })(),
      intentValue: (() => {
        const labels = document.querySelectorAll('.item-label');
        for (const l of labels) {
          if (l.textContent.includes('意向方向')) {
            const val = l.nextElementSibling;
            return val ? val.textContent : '';
          }
        }
        return '';
      })(),
      majorCards: document.querySelectorAll('.major-card').length,
      sampleReason: document.querySelector('.reason-text')?.textContent?.substring(0, 80) || ''
    })
    ```

## 输出格式
```
🎯 Visual Report: Recommendations Page
Viewport: 375×812

✅ Passed:
  - .student-card visible
  - 意向方向 label exists
  - N major cards found

⚠ Issues:
  - 意向方向 value is empty (no session/profile data)
  - No "意向方向" in reason text (may need chat first)

📸 Screenshot: <path>

DOM JS Eval Results:
  - studentCard: true/false
  - intentLabel: true/false
  - intentValue: "..." or ""
  - majorCards: N
  - sampleReason: "..."
```
```

---

## Phase 4: 综合报告（agent: general-purpose, model: sonnet）

```
汇总 Phase 1-3 的所有结果，生成综合报告写入 @reports/miniapp-fix-test-report.md。

## 输入
1. Phase 1 单元测试结果
2. Phase 2 集成测试结果
3. Phase 3 Agent 1 E2E Playwright DOM 测试结果
4. Phase 3 Agent 2 视觉验证 Chat+Profile 报告
5. Phase 3 Agent 3 视觉验证 Recommendations 报告

## 报告格式（不超过 60 行）
# Mini-App 修复测试综合报告

## 后端测试
- 单元测试: N passed / M failed
- 集成测试: N passed / M failed
- 全量回归: N passed / M failed

## E2E Playwright DOM 测试
- TestEntryAndGuestFlow: N/N passed
- TestProfilePageLogout: N/N passed
- TestChatProfileIndicator: N/N passed
- TestRecommendationsIntent: N/N passed

## E2E 视觉验证
### Chat 页
- .profile-indicator 存在: ✅/❌
- 指示条文本: "..."
- AI 回复: N 条 bubble

### Profile 页
- .logout-btn 存在: ✅/❌
- .profile-actions 存在: ✅/❌
- token 状态: 有/无

### 推荐页
- 意向方向标签: ✅/❌
- 意向方向值: "..." or 空
- 推荐理由含意向: ✅/❌

## 根因判断
(如 UI 元素缺失，结合 DOM 测试 + 视觉验证结果推断原因)

## 截图清单
- Chat: <path>
- Profile: <path>
- Recommendations: <path>
```
```

---

## 执行顺序总结

```
Phase 0 (环境检查)
  ↓
Phase 1 (test-runner: 单元测试)
  ↓
Phase 2 (test-runner: 集成测试)
  ↓
Phase 3 (并行 3 个 agent):
  ├── Agent 1: test-runner → E2E Playwright DOM 测试
  ├── Agent 2: visual-verifier → Chat + Profile 视觉
  └── Agent 3: visual-verifier → Recommendations 视觉
  ↓
Phase 4 (综合报告)
```
