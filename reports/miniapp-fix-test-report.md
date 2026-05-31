# Mini-App 修复测试综合报告

**日期**: 2026-05-30  
**分支**: feat/admin-redesign-v2

---

## 后端测试

### 单元测试
- **intent_majors 新增测试**: 8 passed / 0 failed
- **全量单元测试**: 194 passed / 0 failed

### 集成测试
- **TestRecommendationsWithIntent (新增)**: 2 passed / 1 failed
- **全量集成测试**: 26 passed / 1 failed

| 测试 | 状态 | 备注 |
|------|------|------|
| test_student_profile_returns_intent_majors | PASS | profile API 返回 intent_majors |
| test_recommendations_returns_intent_boost_reason | PASS | 推荐理由含"意向方向" |
| test_recommendations_no_intent_boost_when_empty | FAIL | 已有 bug — miniapp.py:315 scalar_one_or_none() 因重复 college 名称报 MultipleResultsFound |

---

## E2E Playwright DOM 测试

| 测试类 | 通过/总数 | 状态 |
|--------|-----------|------|
| TestEntryAndGuestFlow | 2/2 | PASS |
| TestProfilePageLogout | 1/3 | 2 FAIL |
| TestChatProfileIndicator | 1/3 | 2 FAIL |
| TestRecommendationsIntent | 1/2 | 1 FAIL |
| **合计** | **5/10** | |

### 失败根因分析

| 失败测试 | 原因 |
|----------|------|
| test_profile_page_loads | URL 格式错误：测试用 `/pages/profile/index`，应用使用 hash 路由 `/#/pages/profile/index` |
| test_guest_sees_login_prompt_not_logout | 同上 + 实际 UI 不含"登录查看完整档案"按钮 |
| test_send_message_receives_reply | `<uni-input>` 是 uni-app 自定义元素，Playwright `.fill()` 不支持 |
| test_profile_indicator_appears | 依赖上一个测试(消息发送失败) |
| test_intent_majors_label_exists | URL 格式错误：测试用 `/pages/recommendations/index`，需用 `/#/pages/recommendations/index` |

---

## E2E 视觉验证

### Chat 页 (`http://localhost/#/`)
| 检查项 | 结果 |
|--------|------|
| .chat-page 存在 | ✅ |
| .message-input 存在 | ✅ |
| .send-button 存在 | ✅ |
| AI bubbles (.bubble-ai) | 2 条 |
| .entry-overlay 存在 | ❌ (已有历史会话，跳过入口页) |
| .profile-indicator 存在 | ❌ (demo 模式，无活跃 profile 数据) |

### Profile 页 (`http://localhost/#/pages/profile/index`)
| 检查项 | 结果 |
|--------|------|
| 页面加载 (title: "我的咨询档案") | ✅ |
| .profile-page CSS 类 | ✅ |
| 意向方向标签 | ✅ |
| 意向方向值 | 空 (demo 模式) |
| 生源地/科类/分数 标签 | ✅ |
| .logout-btn | ❌ (UI 设计不同) |
| .profile-actions | ❌ (UI 设计不同) |
| localStorage token | ✅ 有 |

### 推荐页 (`http://localhost/#/pages/recommendations/index`)
| 检查项 | 结果 |
|--------|------|
| 页面加载 (title: "报考建议") | ✅ |
| .student-card 存在 | ✅ |
| 意向方向标签 | ✅ |
| 意向方向值 | 空 (demo 模式) |
| 推荐卡片数 (.major-card) | 20 |
| 推荐理由含"意向方向" | ❌ (demo 模式，intent_majors 为空) |

---

## 根因判断

1. **intent_majors 后端提取逻辑正确** — 8 个单元测试全过，profile API + 推荐 API 集成测试通过
2. **E2E Playwright 测试失败非代码缺陷**，而是：
   - URL 格式：uni-app H5 使用 hash 路由 `/#/pages/...`，测试用 path 路由 `/pages/...`
   - 自定义元素：uni-app 的 `<uni-input>` 不支持 Playwright `.fill()`
   - CSS class 不匹配：实际 UI 结构与测试预期不同（测试假设 `.logout-btn`、`.profile-actions`，但实际设计不同）
3. **集成测试 `test_recommendations_no_intent_boost_when_empty` 失败**是已有 bug — `miniapp.py:315` 硬编码 `select(College).where(College.name == "华南师范大学")` 然后调用 `scalar_one_or_none()`，测试创建的重复 college 名称导致 MultipleResultsFound。非 intent_majors 相关
4. **视觉验证**：所有页面正常渲染，意向方向标签在三页中均存在，值为空是因为 demo 模式未填写 profile

## 截图清单

- Chat: `chat-page-final.png`
- Profile: `profile-page-correct.png`
- Recommendations: `recommendations-page-correct.png`
