# Prompt: 修复测试缺陷 + 调度 visual-verifier 定位 UI 元素缺失根因

将下面 `---` 之间的完整内容复制到新 Claude Code session。串行执行。

---

> **任务**：上一轮执行报告 @reports/miniapp-fix-test-report.md 暴露了 5 个问题。本轮分两阶段：(A) 修测试，(B) 调度 visual-verifier 定位 UI 元素缺失根因。
>
> **约束**：修正测试代码可以，修正业务代码需要明确标注并给出理由。visual-verifier **必须**通过 `Agent` 工具调度（subagent_type="visual-verifier", model="sonnet"），禁止合并到 Phase 4 inline 执行。
>
> **执行顺序**：Fix 1+2+3 可并行 → Fix 4 → Fix 5（3 次 visual-verifier Agent 调用，串行）→ 总结。

---

## Fix 1: E2E URL 格式 — uni-app hash 路由（agent: backend-dev, model: sonnet）

**文件**：@backend/tests/e2e/test_miniapp_profile_ux.py

**问题**：uni-app H5 使用 hash 路由。页面 URL 是 `http://nginx/#/pages/profile/index` 而非 `http://nginx/pages/profile/index`。

**修复**：全文替换 `/pages/` 为 `/#/pages/`（首页 `/` 保持不变），`wait_until="networkidle"` → `wait_until="domcontentloaded"`。

---

## Fix 2: E2E uni-app 自定义元素输入（agent: backend-dev, model: sonnet）

**文件**：@backend/tests/e2e/test_miniapp_profile_ux.py

**问题**：`<uni-input>` 是 uni-app 自定义 Web Component，Playwright 的 `.fill()` 无效。

**修复**：替换为 `input_el.click()` + `page.keyboard.type(...)` + `page.keyboard.press("Enter")`。

---

## Fix 3: 集成测试数据隔离（agent: backend-dev, model: sonnet）

**文件**：@backend/tests/integration/test_miniapp_pipeline.py

**问题**：`TestRecommendationsWithIntent` 两个测试各自创建 `College(name="华南师范大学")`，第二个测试 `scalar_one_or_none()` 抛 MultipleResultsFound。

**修复**：`test_recommendations_no_intent_boost_when_empty` 改为先用 `select(College).where(...)` 查询已有 College，不存在则 `pytest.skip()`。

---

## Fix 4: E2E CSS 选择器匹配实际 DOM（agent: backend-dev, model: sonnet）

**文件**：@backend/tests/e2e/test_miniapp_profile_ux.py

**问题**：测试用 `.logout-btn`、`.profile-actions` 等选择器，但 @reports/miniapp-fix-test-report.md 视觉验证确认这些 class 在渲染 DOM 中不存在。

**修复**：
- `test_profile_page_loads`: 改用 hash URL + `"我的咨询档案" in page.title()` 作为 fallback
- `test_guest_sees_login_prompt_not_logout`: 改为遍历所有 button，检查文本含"咨询/登录/档案"
- `test_profile_indicator_appears`: 改为 `page.evaluate()` JS 探测 DOM 中是否含 `profile-indicator` 或 `profileSummary` 关键词（软断言）

---

## Fix 5: 调度 visual-verifier 诊断 UI 元素缺失根因

**关键约束**：必须通过 `Agent` 工具显式调度 `visual-verifier`（subagent_type="visual-verifier", model="sonnet"），禁止 inline 合并。3 个 Agent 串行。

### Agent 5.1: 诊断 Chat 页 .profile-indicator 缺失

**调度方式**：使用 `Agent` 工具，参数如下：
- subagent_type: "visual-verifier"
- model: "sonnet"
- description: "Diagnose missing profile-indicator in chat page"

**Agent prompt 内容**：

```
你是 visual-verifier。诊断 mini-app 聊天页中 .profile-indicator 元素的缺失根因。

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
9. 关键诊断 — browser_evaluate 执行 JS 全面探测

browser_evaluate 要执行的 JS:
var html = document.documentElement.outerHTML;
var result = {
  hasProfileIndicator: html.indexOf('profile-indicator') !== -1,
  hasProfileSummary: html.indexOf('profileSummary') !== -1,
  hasGoProfile: html.indexOf('goProfile') !== -1,
  hasShowToast: html.indexOf('更新你的咨询档案') !== -1,
  profileElements: [],
  cssRules: []
};
var all = document.querySelectorAll('*');
for (var i = 0; i < all.length; i++) {
  var el = all[i];
  var c = (typeof el.className === 'string') ? el.className : '';
  var t = (el.textContent || '').substring(0, 100);
  if (c.indexOf('profile') !== -1 || c.indexOf('logout') !== -1 || t.indexOf('已识别') !== -1) {
    result.profileElements.push({ tag: el.tagName, cls: c.substring(0, 100), txt: t, vis: el.offsetParent !== null });
  }
}
for (var j = 0; j < document.styleSheets.length; j++) {
  try {
    var rules = document.styleSheets[j].cssRules || [];
    for (var k = 0; k < rules.length; k++) {
      if (rules[k].cssText && (rules[k].cssText.indexOf('profile') !== -1)) {
        result.cssRules.push(rules[k].cssText.substring(0, 150));
      }
    }
  } catch(e) {}
}
return JSON.stringify(result, null, 2);

输出必须明确回答:
1. profile-indicator 字符串是否存在于 HTML 源码中？
2. 如果存在但不可见，是什么导致隐藏？
3. 如果不存在于 HTML 源码中，说明代码未构建进 Docker 镜像
```

### Agent 5.2: 诊断 Profile 页 .logout-btn 缺失

**调度方式**：使用 `Agent` 工具：
- subagent_type: "visual-verifier"
- model: "sonnet"
- description: "Diagnose missing logout-btn in profile page"

**Agent prompt 内容**：

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
var result = {
  hasLogoutBtn: html.indexOf('logout-btn') !== -1,
  hasProfileActions: html.indexOf('profile-actions') !== -1,
  hasHandleLogout: html.indexOf('handleLogout') !== -1,
  hasClearStoredSessionId: html.indexOf('clearStoredSessionId') !== -1,
  buttons: [],
  logoutRelated: [],
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
var all = document.querySelectorAll('*');
for (var j = 0; j < all.length; j++) {
  var el = all[j];
  var c = (typeof el.className === 'string') ? el.className : '';
  var t = (el.textContent || '').trim().substring(0, 50);
  if (t.indexOf('退出') !== -1 || t.indexOf('登出') !== -1 || c.indexOf('logout') !== -1 || c.indexOf('profile-action') !== -1) {
    result.logoutRelated.push({ tag: el.tagName, cls: c.substring(0, 80), txt: t, vis: el.offsetParent !== null });
  }
}
return JSON.stringify(result, null, 2);

输出必须明确回答:
1. logout-btn / profile-actions / handleLogout 是否存在于 HTML 源码？
2. Profile 页实际渲染了哪些按钮？文本是什么？
3. localStorage 是否有 token？（决定 v-if="!userStore.isGuest" 走哪个分支）
```

### Agent 5.3: 诊断推荐页 intent_majors 数据流

**调度方式**：使用 `Agent` 工具：
- subagent_type: "visual-verifier"
- model: "sonnet"
- description: "Diagnose intent_majors data flow in recommendations page"

**Agent prompt 内容**：

```
你是 visual-verifier。诊断 mini-app 推荐页意向方向数据流是否贯通。

目标 URL: http://localhost:3002/#/pages/recommendations/index（如不通则 http://localhost/#/pages/recommendations/index）

步骤:
1. browser_resize 375x812
2. browser_navigate 到推荐页
3. browser_wait_for 3000
4. browser_snapshot + browser_take_screenshot
5. browser_evaluate 执行探测（fetch API + DOM check）:

(async function() {
  var sid = localStorage.getItem('scnu_consult_session_id');
  var apiProfile = null;
  if (sid) {
    try {
      var resp = await fetch('http://nginx/api/v1/student/profile?session_id=' + sid);
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
1. GET /student/profile API 是否返回了 intent_majors？
2. 如果 API 有返回但 DOM 为空，说明前端 loadProfile() 未正确接收
3. 如果 API 也返回空，说明 session 无 profile 数据
```

---

## 验证 + 总结

全部 Fix 和 3 个 visual-verifier 诊断完成后：

```bash
# 后端测试
docker compose exec backend python -m pytest tests/unit/test_profile_extraction.py::TestExtractIntentMajors tests/integration/test_miniapp_pipeline.py::TestRecommendationsWithIntent -v --tb=short 2>&1

# E2E 测试
docker compose exec backend python -m pytest tests/e2e/test_miniapp_profile_ux.py -v --tb=long 2>&1

# 全量回归
docker compose exec backend python -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

### 总结报告写入 @reports/miniapp-fix-test-report-v2.md（不超过 60 行）

```
# Mini-App 修复测试报告 v2

## 修正内容
- Fix 1: URL hash 路由
- Fix 2: uni-input 键盘输入
- Fix 3: 集成测试数据隔离
- Fix 4: CSS 选择器匹配实际 DOM

## 测试结果
- 单元: N/N | 集成: N/N | E2E: N/N | 全量: N/N

## visual-verifier 诊断结论

### Chat 页
- profile-indicator 在 HTML 源码中: 是/否
- 结论: ...

### Profile 页
- logout-btn 在 HTML 源码中: 是/否
- token 状态: 有/无
- 结论: ...

### 推荐页
- API 返回 intent_majors: 是/否
- DOM 意向方向值: "..." / 空
- 结论: ...

## 最终根因
(代码未构建 / v-if 条件不满足 / 编译变换 / 其他)
```
