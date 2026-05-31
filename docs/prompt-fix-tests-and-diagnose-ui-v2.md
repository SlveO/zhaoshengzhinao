# Prompt: 修复测试缺陷 + 调度 visual-verifier 定位 UI 元素缺失根因（审阅修订版）

将下面 `---` 之间的完整内容复制到新 Claude Code session。串行执行。

---

> **任务**：修复 @reports/miniapp-fix-test-report.md 暴露的 5 个问题。修订版根据审阅意见做了以下改进：
> - Fix 2：保留 `.send-button` 点击，只替换输入方式
> - Fix 3：改修 conftest 清理列表（根治），而非 `pytest.skip()`（绕过）
> - Fix 4：推迟——Fix 1 修完后先验证，CSS 选择器大概率不需要修
> - Fix 5：修正 JS 探测（不搜索 JS 函数名、`nginx` → `localhost`）
>
> **执行顺序**：Fix 1 → Fix 3 → E2E 验证（决定是否要 Fix 4）→ Fix 5 → Fix 2

---

## Fix 1: E2E URL 格式 — uni-app hash 路由（agent: backend-dev, model: sonnet）

**文件**：@backend/tests/e2e/test_miniapp_profile_ux.py

**问题**：uni-app H5 使用 hash 路由。页面 URL 是 `http://nginx/#/pages/profile/index` 而非 `http://nginx/pages/profile/index`。SPA 的 SSE 长连接会让 `networkidle` 永不触发。

**修复**：
- `/pages/` → `/#/pages/`（首页 `/` 保持不变，5 处替换：L53, L58, L64, L108, L112）
- `wait_until="networkidle"` → `wait_until="domcontentloaded"`（全文替换）

---

## Fix 3: 集成测试数据隔离 — 修 conftest 清理列表（agent: backend-dev, model: sonnet）

**文件**：@backend/tests/conftest.py

**问题**：`TestRecommendationsWithIntent` 中两个测试各自创建 `College(name="华南师范大学")`，跨测试数据残留导致 `scalar_one_or_none()` 抛 `MultipleResultsFound`。根因是 `colleges` 和 `admission_data` 不在 conftest 清理列表中。

**修复**：在 `setup_db` fixture 的清理循环（L80-83）中添加两表。注意外键依赖——`admission_data` 引用 `colleges`，所以先删 `admission_data`：

```python
for table in ["event_logs", "session_profiles", "tenant_data", "tenant_users",
               "departments", "tenants", "recommendation_feedback",
               "recommendations", "user_profiles", "users",
               "chat_messages", "consult_sessions",
               "admission_data", "colleges"]:
```

同时**撤销**上一轮对 `test_recommendations_no_intent_boost_when_empty` 的任何修改——恢复为原始的"创建 College + AdmissionData"版本。表清理修好后，跨测试污染消失。

**验证**：
```bash
docker compose exec backend python -m pytest tests/integration/test_miniapp_pipeline.py::TestRecommendationsWithIntent -v --tb=short 2>&1
```
期望 3 passed。

---

## Gate Check: E2E 验证 — 判断 Fix 4 是否需要

Fix 1 + Fix 3 完成后，先跑一次 E2E：

```bash
docker compose exec backend python -m pytest tests/e2e/test_miniapp_profile_ux.py -v --tb=long 2>&1
```

**判断标准**：
- 如果 `TestProfilePageLogout` 中的 `.logout-btn`、`.profile-actions` 断言通过了 → **跳过 Fix 4**（审阅确认这些 class 存在于源码 `profile/index.vue:32-34`，路由修好后应该可见）
- 如果仍然 FAIL（排除了路由原因）→ **执行 Fix 4**：将选择器改为通用 button 文本遍历

---

## Fix 4（条件执行）: E2E CSS 选择器匹配实际 DOM

**仅当 Gate Check 中 `TestProfilePageLogout` 仍然因为 `.logout-btn` 或 `.profile-actions` 不可见而失败时执行。**

**文件**：@backend/tests/e2e/test_miniapp_profile_ux.py

**修复**：
- `test_profile_page_loads`: 改用 hash URL + `"我的咨询档案" in page.title()` fallback
- `test_guest_sees_login_prompt_not_logout`: 改为遍历所有 button，检查文本含"咨询/登录/档案"
- `test_profile_indicator_appears`: 改为 `page.evaluate()` JS 探测 DOM

---

## Fix 5: 调度 visual-verifier 诊断 UI 元素缺失根因

**关键约束**：必须通过 `Agent` 工具调度 `visual-verifier`（subagent_type="visual-verifier", model="sonnet"），禁止 inline。3 个 Agent 串行。

---

### Agent 5.1: 诊断 Chat 页 .profile-indicator 缺失

**调度方式**：使用 `Agent` 工具，`subagent_type="visual-verifier"`, `model="sonnet"`

**Prompt**：
```
你是 visual-verifier。诊断 mini-app 聊天页中 .profile-indicator 元素缺失根因。

目标 URL: http://localhost:3002（如不通则 http://localhost）

步骤:
1. browser_resize 375x812
2. browser_navigate 到首页
3. browser_snapshot — 检查是否有 entry-overlay
4. 若有 entry-overlay: browser_click "访客模式", browser_wait_for 3000
5. browser_snapshot — 确认进入聊天页
6. 在输入框输入"广东物理类 620 分想学计算机"并发送
7. browser_wait_for 25000（等待 AI 回复 + profile 提取）
8. browser_snapshot + browser_take_screenshot
9. browser_evaluate 执行以下 JS 全面探测：

var html = document.documentElement.outerHTML;
var body = document.body.innerText;
var indicator = document.querySelector('.profile-indicator');
var result = {
  profileIndicatorInDOM: !!indicator,
  profileIndicatorVisible: indicator ? indicator.offsetParent !== null : false,
  profileIndicatorText: indicator ? indicator.textContent.trim().substring(0, 100) : '',
  hasProfileIndicatorInHTML: html.indexOf('profile-indicator') !== -1,
  hasProfileSummaryInHTML: html.indexOf('profileSummary') !== -1,
  hasHandleLogoutInHTML: html.indexOf('handleLogout') !== -1,
  hasProfileText: body.indexOf('已识别') !== -1,
  chatPageVisible: !!document.querySelector('.chat-page'),
  aiBubbleCount: document.querySelectorAll('.bubble-ai').length,
  allProfileClasses: []
};
var all = document.querySelectorAll('[class*="profile"], [class*="logout"]');
for (var i = 0; i < all.length; i++) {
  result.allProfileClasses.push({
    tag: all[i].tagName,
    class: (all[i].className || '').toString().substring(0, 100),
    visible: all[i].offsetParent !== null,
    text: (all[i].textContent || '').substring(0, 50)
  });
}
return JSON.stringify(result, null, 2);

输出必须明确回答:
1. .profile-indicator 元素是否存在于 DOM 中？是否可见（offsetParent !== null）？
2. 如果存在但不可见，是什么 CSS 属性导致隐藏？
3. HTML 源码中是否包含 profile-indicator / profileSummary / handleLogout 字符串？
4. 所有 class 含 "profile" 或 "logout" 的元素列表及其可见性
```

### Agent 5.2: 诊断 Profile 页 .logout-btn 缺失

**调度方式**：使用 `Agent` 工具，`subagent_type="visual-verifier"`, `model="sonnet"`

**Prompt**：
```
你是 visual-verifier。诊断 mini-app profile 页中 .logout-btn 和 .profile-actions 元素缺失根因。

目标 URL: http://localhost:3002/#/pages/profile/index（如不通则 http://localhost/#/pages/profile/index）

步骤:
1. browser_resize 375x812
2. browser_navigate 到 profile 页
3. browser_wait_for 3000
4. browser_snapshot + browser_take_screenshot
5. browser_evaluate 执行 JS:

var html = document.documentElement.outerHTML;
var logoutBtn = document.querySelector('.logout-btn');
var profileActions = document.querySelector('.profile-actions');
var result = {
  logoutBtnInDOM: !!logoutBtn,
  logoutBtnVisible: logoutBtn ? logoutBtn.offsetParent !== null : false,
  profileActionsInDOM: !!profileActions,
  profileActionsVisible: profileActions ? profileActions.offsetParent !== null : false,
  hasLogoutBtnInHTML: html.indexOf('logout-btn') !== -1,
  hasProfileActionsInHTML: html.indexOf('profile-actions') !== -1,
  hasHandleLogoutInHTML: html.indexOf('handleLogout') !== -1,
  hasClearStoredSessionId: html.indexOf('clearStoredSessionId') !== -1,
  buttons: [],
  hasToken: !!localStorage.getItem('token'),
  hasSessionId: !!localStorage.getItem('scnu_consult_session_id')
};
var btns = document.querySelectorAll('button');
for (var i = 0; i < btns.length; i++) {
  result.buttons.push({
    text: (btns[i].textContent || '').trim().substring(0, 40),
    className: (btns[i].className || '').toString().substring(0, 80),
    visible: btns[i].offsetParent !== null
  });
}
return JSON.stringify(result, null, 2);

输出必须明确回答:
1. .logout-btn 和 .profile-actions 是否存在于 DOM？是否可见？
2. Profile 页渲染了哪些 button？文本是什么？
3. localStorage 是否有 token？（决定 v-if="!userStore.isGuest" 走哪个分支）
4. HTML 源码中是否包含 logout-btn / profile-actions / handleLogout 字符串？
```

### Agent 5.3: 诊断推荐页 intent_majors 数据流

**调度方式**：使用 `Agent` 工具，`subagent_type="visual-verifier"`, `model="sonnet"`

**Prompt**：
```
你是 visual-verifier。诊断 mini-app 推荐页意向方向数据流是否贯通。

目标 URL: http://localhost:3002/#/pages/recommendations/index（如不通则 http://localhost/#/pages/recommendations/index）

步骤:
1. browser_resize 375x812
2. browser_navigate 到推荐页
3. browser_wait_for 3000
4. browser_snapshot + browser_take_screenshot
5. browser_evaluate 执行探测（fetch API 用 localhost 而非 nginx）:

(async function() {
  var sid = localStorage.getItem('scnu_consult_session_id');
  var apiProfile = null;
  if (sid) {
    try {
      var resp = await fetch('http://localhost/api/v1/student/profile?session_id=' + sid);
      var data = await resp.json();
      apiProfile = (data && data.data) ? data.data.profile : null;
    } catch(e) { apiProfile = { error: e.message }; }
  }
  var labels = document.querySelectorAll('.item-label');
  var intentValue = '';
  for (var i = 0; i < labels.length; i++) {
    if (labels[i].textContent.indexOf('意向方向') !== -1) {
      var val = labels[i].nextElementSibling;
      intentValue = val ? val.textContent.trim() : '(no next sibling)';
    }
  }
  var reasonEls = document.querySelectorAll('.reason-text');
  var reasons = [];
  for (var j = 0; j < reasonEls.length; j++) {
    reasons.push(reasonEls[j].textContent.trim().substring(0, 80));
  }
  var hasIntentReason = false;
  for (var k = 0; k < reasons.length; k++) {
    if (reasons[k].indexOf('意向方向') !== -1) { hasIntentReason = true; break; }
  }
  return JSON.stringify({
    sessionId: sid,
    apiProfile: apiProfile,
    intentValueInDOM: intentValue,
    reasonSamples: reasons.slice(0, 3),
    hasIntentReason: hasIntentReason,
    majorCardCount: document.querySelectorAll('.major-card').length
  }, null, 2);
})()

输出必须明确回答:
1. GET /student/profile API 是否返回了 intent_majors？（检查 apiProfile 字段）
2. 如果 API 有返回但 DOM 为空 → 前端 loadProfile() 未正确接收或渲染
3. 如果 API 也返回空 → session 无 profile 数据，需先走 chat 流程
```

---

## Fix 2: E2E uni-app 输入 — 保留 .send-button 点击（agent: backend-dev, model: sonnet）

**文件**：@backend/tests/e2e/test_miniapp_profile_ux.py

**问题**：`<uni-input>` 是 uni-app 自定义 Web Component，Playwright `.fill()` 无效。

**修复**：只替换 `.fill()` 为 `click() + keyboard.type()`，**保留** `.send-button` 的 `.click()` 作为提交方式（uni-app 不一定绑定 Enter 事件）：

```python
# 替换 page.locator(".message-input").first.fill("...") 为:
input_el = page.locator(".message-input").first
if input_el.is_visible(timeout=5000):
    input_el.click()
    page.keyboard.type("广东物理类 620 分想学计算机")
    page.locator(".send-button").first.click()
```

涉及 `test_send_message_receives_reply` 和 `test_profile_indicator_appears` 两个方法。

---

## 验证 + 总结

全部完成后：

```bash
# 确认 conftest 清理包含新表
grep -n "admission_data\|colleges" backend/tests/conftest.py

# 后端测试（3 个集成测试应全过）
docker compose exec backend python -m pytest tests/integration/test_miniapp_pipeline.py::TestRecommendationsWithIntent -v --tb=short 2>&1

# E2E 测试
docker compose exec backend python -m pytest tests/e2e/test_miniapp_profile_ux.py -v --tb=long 2>&1

# 全量回归
docker compose exec backend python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

### 总结报告写入 @reports/miniapp-fix-test-report-v2.md

```
# Mini-App 修复测试报告 v2

## 修正内容
- Fix 1: URL hash 路由 — 5 处替换 + domcontentloaded
- Fix 3: conftest 清理 +admission_data +colleges — 根治数据隔离
- Fix 4: [执行/跳过] — Gate Check 决定
- Fix 5: 3 次 visual-verifier 诊断
- Fix 2: uni-input 键盘输入 + 保留 .send-button 点击

## 测试结果
- 集成 TestRecommendationsWithIntent: N/3
- E2E: N/10
- 全量回归: N/N

## visual-verifier 诊断结论

### Chat 页
- .profile-indicator 在 DOM: 是/否，可见: 是/否
- profile-indicator 在 HTML 源码: 是/否
- 结论: ...

### Profile 页
- .logout-btn 在 DOM: 是/否，可见: 是/否
- token 状态: 有/无
- 结论: ...

### 推荐页
- API 返回 intent_majors: 是/否
- DOM 意向方向值: "..." / 空
- 结论: ...

## 最终根因
(代码未构建 / v-if 条件不满足 / 编译变换 / 其他)
```
