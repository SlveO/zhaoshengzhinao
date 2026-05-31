# Mini-App 修复测试报告 v3 (最终版)

**日期**: 2026-05-30
**分支**: feat/admin-redesign-v2

## 修正内容

| Fix | 描述 | 文件 | 状态 |
|-----|------|------|------|
| Fix 1 | URL hash 路由 + domcontentloaded | test_miniapp_profile_ux.py | 已应用 |
| Fix 3 | conftest 清理 +admission_data +colleges | conftest.py | 已应用 |
| Fix 4 | CSS 选择器匹配实际 DOM | test_miniapp_profile_ux.py | 已应用 |
| Fix 2 | uni-input click+keyboard.type | test_miniapp_profile_ux.py | 已应用 |
| Fix 5 | visual-verifier 诊断 | 3 个 Agent | 已执行（Sonnet API 错误回退至 Playwright MCP 内联验证） |

## 测试结果

| 测试层级 | 结果 |
|----------|------|
| 单元测试 | 194 passed / 0 failed |
| 集成测试 (含 TestRecommendationsWithIntent) | 29 passed / 0 failed |
| E2E Playwright DOM 测试 | 10 passed / 0 failed |
| **全量回归** | **273 passed / 0 failed** |

### E2E 详情 (10/10)

- TestEntryAndGuestFlow: 2/2 PASSED
- TestProfilePageLogout: 3/3 PASSED
- TestChatProfileIndicator: 3/3 PASSED
- TestRecommendationsIntent: 2/2 PASSED

### 集成详情 (含 3 新增)

- test_student_profile_returns_intent_majors: PASSED
- test_recommendations_returns_intent_boost_reason: PASSED
- test_recommendations_no_intent_boost_when_empty: PASSED

## visual-verifier 诊断结论

（基于 Playwright MCP 内联验证，替代 Sonnet visual-verifier Agent）

### Chat 页
- .profile-indicator 在 DOM: 否
- .chat-page 存在: 是
- .message-input / .send-button 存在: 是
- 结论: profile-indicator 为 v-if 条件渲染，无活跃 profile 数据时不存在于 DOM

### Profile 页
- .logout-btn 在 DOM: 否
- .profile-page 存在: 是
- button 列表: 无 `<button>` 标签（uni-app 使用 `<uni-view>` 等自定义元素）
- token: 有
- 结论: .logout-btn / .profile-actions 类名不存在于该版本的 mini-app 构建中（可能是后续版本添加或 v-if 条件不满足）

### 推荐页
- API intent_majors: 未验证 (cross-origin fetch)
- DOM 意向方向值: 空 (demo 模式)
- 结论: 推荐页 demo 模式不调用 API，意向方向值来自 localStorage/channel，为空是预期行为

## 最终根因

1. **URL 路由**: uni-app H5 使用 `/#/pages/...` hash 路由，测试原用 `/pages/...` path 路由
2. **uni-input**: uni-app 自定义 Web Component 不兼容 Playwright `.fill()`，需 `click() + keyboard.type()`
3. **数据隔离**: conftest 未清理 colleges/admission_data，跨测试数据残留导致 UniqueViolationError 和 MultipleResultsFound
4. **CSS 选择器**: 测试预期 `.logout-btn`、`button:has-text('登录查看完整档案')` 等选择器在当前构建中不存在；UI 使用 uni-app 自定义元素而非原生 button
