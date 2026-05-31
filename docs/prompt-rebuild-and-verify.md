# Prompt: 条件渲染验证 + 构建产物检查

将下面 `---` 之间的完整内容复制到新 Claude Code session。串行执行。

---

> **背景**：273 测试全过（@reports/miniapp-fix-test-report-v3.md）。但 `.profile-indicator`、`.logout-btn`、`.profile-actions` 在渲染 DOM 中不可见——这是 `v-if` 条件不满足的设计行为（访客模式无 profile、无 token），不是构建过期。方案改为：(A) 静态检查代码是否打入镜像，(B) 注入预置条件触达目标分支后截图验证。
>
> **执行顺序**：Step 1 → Step 2 → Step 3（3 个 visual-verifier 串行）→ Step 4 报告

---

## Step 1: 检查是否需要重建 + 验证构建产物

```bash
# 对比最近 mini-app 源码提交时间和镜像创建时间
echo "=== Source last commit ===" && git log --oneline -1 -- mini-app/src/
echo "=== Image created ===" && docker compose images mini-app 2>/dev/null || docker images | grep mini-app
```

判断：如果镜像时间早于源码提交时间 → 执行重建；否则跳过。

**仅当需要重建时**：
```bash
docker compose build mini-app --no-cache && docker compose up -d mini-app
```

**构建产物关键词检查**（无论是否重建，必须执行）：
```bash
# 检查修复代码是否在构建产物 JS 中
docker compose exec mini-app sh -c "grep -l 'profile-indicator' /usr/share/nginx/html/*.js 2>/dev/null && echo 'FOUND: profile-indicator' || echo 'NOT FOUND: profile-indicator'"
docker compose exec mini-app sh -c "grep -l 'handleLogout' /usr/share/nginx/html/*.js 2>/dev/null && echo 'FOUND: handleLogout' || echo 'NOT FOUND: handleLogout'"
docker compose exec mini-app sh -c "grep -l 'profileSummary' /usr/share/nginx/html/*.js 2>/dev/null && echo 'FOUND: profileSummary' || echo 'NOT FOUND: profileSummary'"
docker compose exec mini-app sh -c "grep -l 'logout-btn' /usr/share/nginx/html/*.js 2>/dev/null && echo 'FOUND: logout-btn' || echo 'NOT FOUND: logout-btn'"
```

---

## Step 2: backend conftest 验证（无需重建——卷挂载已生效）

```bash
docker compose exec backend python -m pytest tests/integration/test_miniapp_pipeline.py::TestRecommendationsWithIntent -v --tb=short 2>&1
```

期望 3 passed。

---

## Step 3: 调度 visual-verifier 条件渲染验证

**关键约束**：
- 通过 `Agent` 工具调度 `visual-verifier`
- 优先 `model: "haiku"`（Sonnet 已连续两次 API 错误），失败则 retry `model: "sonnet"`
- 3 个 Agent 串行
- **核心策略**：用 `page.evaluate` / `localStorage.setItem` 注入预置条件，触达 `v-if` 的目标分支，然后截图

---

### Agent 3.1: Profile 页 — 注入 token 验证 .logout-btn 出现

**调度**：`Agent({subagent_type: "visual-verifier", model: "haiku", description: "Verify logout-btn with injected token", prompt: "..."})`

**Prompt**：
```
验证 mini-app profile 页：当用户已登录（有 token）时，退出按钮是否渲染。

URL: http://localhost:3002/#/pages/profile/index（不通则 http://localhost/#/pages/profile/index）

步骤:
1. browser_resize 375x812
2. browser_navigate 到 profile 页
3. browser_wait_for 2000
4. browser_snapshot — 记录当前状态（游客：应显示"登录查看完整档案"）
5. browser_evaluate 注入 token + userInfo:

localStorage.setItem('token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAwIiwidXNlcm5hbWUiOiJ0ZXN0dXNlciJ9.fake_signature');
localStorage.setItem('userInfo', JSON.stringify({user_id:'00000000-0000-0000-0000-000000000000', nickname:'testuser', phone:'13800000000'}));
return 'token injected';

6. browser_navigate 到同一 URL 重新加载（让 Vue 读取 localStorage token）
7. browser_wait_for 3000
8. browser_snapshot
9. browser_take_screenshot
10. browser_evaluate:

var logoutBtn = document.querySelector('.logout-btn');
var profileActions = document.querySelector('.profile-actions');
var allBtns = document.querySelectorAll('uni-button, button, [class*="btn"]');
var btns = [];
for (var i = 0; i < allBtns.length; i++) {
  btns.push({
    tag: allBtns[i].tagName,
    cls: (allBtns[i].className || '').toString().substring(0, 80),
    text: (allBtns[i].textContent || '').trim().substring(0, 40),
    vis: allBtns[i].offsetParent !== null
  });
}
return JSON.stringify({
  logoutBtnInDOM: !!logoutBtn,
  logoutBtnVisible: logoutBtn ? logoutBtn.offsetParent !== null : false,
  logoutBtnText: logoutBtn ? logoutBtn.textContent.trim() : '',
  profileActionsInDOM: !!profileActions,
  allBtns: btns
}, null, 2);

输出必须明确:
- 注入 token 前按钮状态（截图1）
- 注入 token 后 .logout-btn 是否出现在 DOM？是否可见？文本是"退出登录"？
- 所有按钮列表
```

### Agent 3.2: Chat 页 — 构建产物验证 + DOM 探测

**调度**：`Agent({subagent_type: "visual-verifier", model: "haiku", description: "Verify chat profile-indicator code presence", prompt: "..."})`

**Prompt**：
```
验证 mini-app 聊天页的 profile-indicator 代码是否在构建产物中，并探测其 DOM 条件。

URL: http://localhost:3002（不通则 http://localhost）

步骤:
1. browser_resize 375x812
2. browser_navigate 到首页
3. browser_snapshot
4. 若有 entry-overlay: browser_click "访客模式", browser_wait_for 3000
5. browser_snapshot
6. browser_take_screenshot
7. browser_evaluate 探测 profile-indicator 代码存在性：

var html = document.documentElement.outerHTML;
var scripts = document.querySelectorAll('script');
var foundInScripts = [];
for (var i = 0; i < scripts.length; i++) {
  var src = scripts[i].src || '(inline)';
  var txt = scripts[i].textContent || '';
  if (txt.indexOf('profile-indicator') !== -1 || txt.indexOf('profileSummary') !== -1 || src.indexOf('profile') !== -1) {
    foundInScripts.push({ src: src.substring(src.lastIndexOf('/') + 1), hasProfileIndicator: txt.indexOf('profile-indicator') !== -1, hasProfileSummary: txt.indexOf('profileSummary') !== -1 });
  }
}
var indicator = document.querySelector('.profile-indicator');
return JSON.stringify({
  profileIndicatorInDOM: !!indicator,
  profileIndicatorVisible: indicator ? indicator.offsetParent !== null : false,
  foundInScripts: foundInScripts,
  profileIndicatorInHTML: html.indexOf('profile-indicator') !== -1,
  profileSummaryInHTML: html.indexOf('profileSummary') !== -1,
  chatPageVisible: !!document.querySelector('.chat-page')
}, null, 2);

输出必须明确:
- `<script>` 标签中是否包含 profile-indicator / profileSummary 字符串？
- .profile-indicator 元素当前是否在 DOM 中？(预期：否——访客无 profile)
- 如果代码在构建产物中但 DOM 中不可见，确认是 v-if="profileSummary" 条件不满足
```

### Agent 3.3: 推荐页 — API 数据流验证

**调度**：`Agent({subagent_type: "visual-verifier", model: "haiku", description: "Verify recommendations intent data flow", prompt: "..."})`

**Prompt**：
```
验证 mini-app 推荐页意向方向数据流。先通过 API 创建带 intent_majors 的 session，再检查 DOM。

URL: http://localhost:3002/#/pages/recommendations/index（不通则 http://localhost/#/pages/recommendations/index）

步骤:
1. browser_resize 375x812
2. 先 browser_evaluate 通过 API 创建 session 并存储:

(async function() {
  var resp = await fetch('http://localhost/api/v1/miniapp/enter', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tenant_slug: 'scnu' })
  });
  var d = await resp.json();
  var sid = d && d.data ? d.data.session_id : null;
  if (sid) { localStorage.setItem('scnu_consult_session_id', sid); }
  return JSON.stringify({ sid: sid });
})()

3. browser_navigate 到推荐页
4. browser_wait_for 3000
5. browser_snapshot
6. browser_take_screenshot
7. browser_evaluate 检查 DOM:

(async function() {
  var sid = localStorage.getItem('scnu_consult_session_id');
  var apiProfile = null;
  if (sid) {
    try {
      var resp = await fetch('http://localhost/api/v1/student/profile?session_id=' + sid);
      var d = await resp.json();
      apiProfile = (d && d.data) ? d.data.profile : null;
    } catch(e) { apiProfile = { error: e.message }; }
  }
  var labels = document.querySelectorAll('.item-label');
  var intentValue = '';
  for (var i = 0; i < labels.length; i++) {
    if (labels[i].textContent.indexOf('意向方向') !== -1) {
      var v = labels[i].nextElementSibling;
      intentValue = v ? v.textContent.trim() : '(no sibling)';
    }
  }
  return JSON.stringify({
    sessionId: sid,
    apiProfile: apiProfile,
    intentValueInDOM: intentValue,
    majorCardCount: document.querySelectorAll('.major-card').length
  }, null, 2);
})()

输出必须明确:
- API 是否成功创建 session？
- GET /student/profile 返回了 intent_majors 吗？
- DOM 中意向方向字段显示什么值？
```

---

## Step 4: 综合报告

写入 @reports/miniapp-condition-verify-report.md：

```
# Mini-App 条件渲染验证报告

## Step 1: 构建产物检查
- profile-indicator 在 .js 产物: 是/否
- handleLogout 在 .js 产物: 是/否
- profileSummary 在 .js 产物: 是/否
- logout-btn 在 .js 产物: 是/否
- 重建执行: 是/否（时间对比: 源码提交 vs 镜像创建）

## Step 2: Backend
- TestRecommendationsWithIntent: N/3

## Step 3: 条件渲染验证

### Profile 页（token 注入后）
- .logout-btn DOM: 是/否 | 可见: 是/否 | 文本: "退出登录"/其他
- .profile-actions DOM: 是/否
- 结论: 登录状态下退出按钮 [正确渲染 / 仍然缺失]

### Chat 页（代码探测）
- <script> 中含 profile-indicator: 是/否
- <script> 中含 profileSummary: 是/否
- .profile-indicator 当前在 DOM: 否（预期——访客无 profile）
- 结论: 代码 [已/未] 打入构建产物

### 推荐页（API 创建 session）
- API 返回 intent_majors: 是/否/null
- DOM 意向方向值: "..." / 空
- 结论: 数据流 [贯通 / 中断于哪个环节]

## 最终判定
- 所有修复代码在构建产物中: ✅/❌
- 条件满足时元素正确渲染: ✅/❌（列出各元素）
- 遗留问题: （如有）
```
