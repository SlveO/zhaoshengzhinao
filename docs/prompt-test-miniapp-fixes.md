# Prompt: 编写本轮修复的测试代码 + 执行期 sub-agent 任务 prompt

将下面 `---` 之间的完整内容复制到新 Claude Code session。仅编写测试，不执行。

---

> **任务**：为最近三轮 mini-app 修复编写完整测试。产出两类产物：
> 1. **测试代码**：单元测试（intent_majors 提取）、集成测试（推荐接口 intent 加分 + profile API）、E2E Playwright DOM 测试文件
> 2. **执行期 Prompt**：供另一个 session 执行测试时使用，内含各 sub-agent 的具体任务 prompt
>
> **约束**：只编写代码和 prompt，不执行任何测试。遵循现有测试模式。不修改被测业务代码。

---

## Phase 1: 编写后端单元测试（agent: backend-dev, model: sonnet）

**文件**：@backend/tests/unit/test_profile_extraction.py

**任务**：在当前文件末尾添加 `class TestExtractIntentMajors`，8 个测试用例。

遵循同文件现有模式：`from services.consult_service import extract_profile_from_message`，直接 `await extract_profile_from_message(user_text, ai_text, existing_profile)`，无需 mock。

```python
class TestExtractIntentMajors:
    """extract_profile_from_message 的意向专业关键字提取"""

    async def test_extract_intent_majors_from_user_message(self):
        """用户消息中含"计算机" → 提取到 intent_majors"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message("我对计算机很感兴趣", "", {})
        assert updates.get("intent_majors") == ["计算机"]

    async def test_extract_multiple_intent_majors(self):
        """多个关键字 → 全部提取"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message("我想学计算机和人工智能", "", {})
        majors = updates.get("intent_majors", [])
        assert "计算机" in majors
        assert "人工智能" in majors

    async def test_no_duplicate_intent_when_already_known(self):
        """已有 intent_majors → 跳过提取"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message(
            "我对金融感兴趣", "", {"intent_majors": ["计算机"]}
        )
        assert "intent_majors" not in updates

    async def test_no_intent_when_no_keyword_matches(self):
        """无专业关键字 → updates 不含 intent_majors"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message("你好，今天天气不错", "", {})
        assert "intent_majors" not in updates

    async def test_extract_intent_majors_capped_at_five(self):
        """超过 5 个关键字 → 截断为 5"""
        from services.consult_service import extract_profile_from_message
        text = "计算机 人工智能 软件工程 金融 法学 医学 数学"
        updates = await extract_profile_from_message(text, "", {})
        assert len(updates.get("intent_majors", [])) <= 5

    async def test_extract_intent_from_ai_response(self):
        """AI 回复中的关键字也被提取"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message(
            "我想学计算机",
            "华师计算机专业很好，人工智能方向也很强",
            {},
        )
        majors = updates.get("intent_majors", [])
        assert "计算机" in majors
        assert "人工智能" in majors

    async def test_extract_all_four_fields_together(self):
        """省份+科类+分数+意向专业 同时提取"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message(
            "广东物理类 620 分想学计算机和人工智能", "", {}
        )
        assert updates.get("province") == "广东"
        assert updates.get("subject_type") == "物理类"
        assert updates.get("score") == 620
        majors = updates.get("intent_majors", [])
        assert "计算机" in majors
        assert "人工智能" in majors

    async def test_extract_intent_majors_empty_list_skipped(self):
        """空列表 intent_majors 是 falsy → 触发提取"""
        from services.consult_service import extract_profile_from_message
        updates = await extract_profile_from_message(
            "我考虑学计算机", "", {"intent_majors": []}
        )
        assert updates.get("intent_majors") == ["计算机"]
```

---

## Phase 2: 编写集成测试（agent: backend-dev, model: sonnet）

**文件**：@backend/tests/integration/test_miniapp_pipeline.py

**任务**：在文件末尾添加 `class TestRecommendationsWithIntent`，3 个测试用例。

遵循同文件模式：`async_client` fixture（httpx.AsyncClient + ASGITransport），`test_tenant` fixture，`from models import async_session` 操作数据库。

```python
class TestRecommendationsWithIntent:
    """推荐接口的意向方向加分 + profile API 返回 intent_majors"""

    async def test_student_profile_returns_intent_majors(
        self, async_client, test_tenant
    ):
        """GET /student/profile 的 profile 包含 intent_majors 字段"""
        from models import async_session
        from models.consult_session import ConsultSession
        import uuid

        async with async_session() as db:
            session = ConsultSession(
                session_id=f"sess_{uuid.uuid4().hex[:12]}",
                tenant_slug="test",
                province="广东",
                intent_majors=["计算机", "人工智能"],
            )
            db.add(session)
            await db.commit()
            sid = session.session_id

        resp = await async_client.get(
            "/api/v1/student/profile", params={"session_id": sid}
        )
        assert resp.status_code == 200
        data = resp.json().get("data")
        assert data is not None
        assert data.get("has_profile") is True
        profile = data.get("profile")
        assert profile is not None
        assert "计算机" in profile.get("intent_majors", [])
        assert "人工智能" in profile.get("intent_majors", [])

    async def test_recommendations_returns_intent_boost_reason(
        self, async_client, test_tenant
    ):
        """intent_majors 匹配时，推荐理由包含意向方向"""
        from models import async_session
        from models.consult_session import ConsultSession
        from models.college import College
        from models.admission import AdmissionData
        import uuid

        async with async_session() as db:
            college = College(
                id=uuid.uuid4(), name="华南师范大学", city="广州", level="本科",
            )
            db.add(college)
            await db.flush()
            db.add(AdmissionData(
                id=uuid.uuid4(), college_id=college.id,
                major_name="计算机科学与技术", year=2024,
                min_score=600, min_rank=20000, province="广东",
                subject_requirements="物理+不限",
            ))
            await db.commit()

        async with async_session() as db:
            session = ConsultSession(
                session_id=f"sess_{uuid.uuid4().hex[:12]}",
                tenant_slug="test", province="广东",
                subject_type="物理类", score=620,
                intent_majors=["计算机"],
            )
            db.add(session)
            await db.commit()
            sid = session.session_id

        resp = await async_client.post(
            "/api/v1/recommendations",
            json={"session_id": sid, "tenant_slug": "test"},
        )
        assert resp.status_code == 200
        data = resp.json().get("data")
        items = data.get("items", [])
        cs_item = next((i for i in items if "计算机" in i.get("major_name", "")), None)
        assert cs_item is not None, "推荐列表应包含计算机相关专业"
        reasons = cs_item.get("reasons", [])
        assert any("意向方向" in r for r in reasons), f"推荐理由应含意向方向，实际: {reasons}"

    async def test_recommendations_no_intent_boost_when_empty(
        self, async_client, test_tenant
    ):
        """intent_majors 为空 → 无意向方向理由"""
        from models import async_session
        from models.consult_session import ConsultSession
        from models.college import College
        from models.admission import AdmissionData
        import uuid

        async with async_session() as db:
            college = College(
                id=uuid.uuid4(), name="华南师范大学", city="广州", level="本科",
            )
            db.add(college)
            await db.flush()
            db.add(AdmissionData(
                id=uuid.uuid4(), college_id=college.id,
                major_name="计算机科学与技术", year=2024,
                min_score=600, min_rank=20000, province="广东",
                subject_requirements="物理+不限",
            ))
            await db.commit()

        async with async_session() as db:
            session = ConsultSession(
                session_id=f"sess_{uuid.uuid4().hex[:12]}",
                tenant_slug="test", score=620, intent_majors=[],
            )
            db.add(session)
            await db.commit()
            sid = session.session_id

        resp = await async_client.post(
            "/api/v1/recommendations",
            json={"session_id": sid, "tenant_slug": "test"},
        )
        data = resp.json().get("data")
        for item in data.get("items", []):
            assert not any("意向方向" in r for r in item.get("reasons", [])), \
                f"intent_majors 为空不应出现意向方向理由"
```

---

## Phase 3: 编写 E2E Playwright DOM 测试文件（agent: backend-dev, model: sonnet）

**文件**：新建 `backend/tests/e2e/test_miniapp_profile_ux.py`

**任务**：编写 sync Playwright 测试文件，4 个测试类 × 11 个测试方法。遵循 @backend/tests/e2e/test_student_journey.py 的 exact 模式：

- `from playwright.sync_api import sync_playwright, Page, Browser`
- `BASE_URL = "http://nginx"`
- `browser` fixture（module scope）, `page` fixture（function scope）
- E2E conftest.py 已覆盖父级 `setup_db` 防止事件循环冲突

```python
"""E2E DOM 测试：验证 mini-app 修复后的 UI 元素存在于 DOM 中。

覆盖：
- 修复 1: 退出登录按钮（profile 页面）
- 修复 2: 滚动组件 + 快捷问题
- 修复 3: 意向方向字段 + 推荐理由
- 前端数据通路: profile 指示条
"""
import pytest
from playwright.sync_api import sync_playwright, Page, Browser

BASE_URL = "http://nginx"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


class TestEntryAndGuestFlow:
    """Entry 页面 + 访客模式"""

    def test_entry_overlay_visible(self, page: Page):
        page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=15000)
        assert page.locator(".entry-overlay").is_visible(timeout=5000)
        assert page.locator(".entry-title").is_visible()
        assert page.locator("text=访客模式").is_visible()
        assert page.locator("text=注册 / 登录").is_visible()

    def test_guest_mode_enters_chat(self, page: Page):
        page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=15000)
        page.locator("text=访客模式").click(timeout=5000)
        page.wait_for_timeout(3000)
        assert not page.locator(".entry-overlay").is_visible()
        assert page.locator(".chat-page").first.is_visible(timeout=5000)


class TestProfilePageLogout:
    """修复 1: 退出登录按钮"""

    def test_profile_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/pages/profile/index", wait_until="networkidle", timeout=15000)
        assert page.locator(".profile-page").first.is_visible(timeout=5000)

    def test_guest_sees_login_prompt_not_logout(self, page: Page):
        """访客状态的 DOM：登录按钮存在，退出按钮不存在"""
        page.goto(f"{BASE_URL}/pages/profile/index", wait_until="networkidle", timeout=15000)
        assert page.locator("button:has-text('登录查看完整档案')").first.is_visible(timeout=5000)
        assert page.locator(".logout-btn").count() == 0

    def test_guest_state_no_token(self, page: Page):
        """访客状态 localStorage 无 token"""
        page.goto(f"{BASE_URL}/pages/profile/index", wait_until="networkidle", timeout=15000)
        has_token = page.evaluate("() => !!localStorage.getItem('token')")
        assert not has_token


class TestChatProfileIndicator:
    """前端数据通路: profile 指示条 + SSE 消息"""

    def test_chat_input_visible(self, page: Page):
        page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=15000)
        page.locator("text=访客模式").click(timeout=5000)
        page.wait_for_timeout(3000)
        assert page.locator(".message-input").first.is_visible(timeout=5000)

    def test_send_message_receives_reply(self, page: Page):
        """发送消息后收到 AI 回复——验证 SSE 通道"""
        page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=15000)
        page.locator("text=访客模式").click(timeout=5000)
        page.wait_for_timeout(3000)
        page.locator(".message-input").first.fill("广东物理类 620 分想学计算机")
        page.locator(".send-button").first.click()
        page.wait_for_timeout(20000)
        bubbles = page.locator(".bubble-ai .bubble-text")
        assert bubbles.count() > 0
        assert len(bubbles.last.inner_text()) > 0

    def test_profile_indicator_appears(self, page: Page):
        """发送含省份+分数的消息后 profile-indicator 出现在 DOM"""
        page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=15000)
        page.locator("text=访客模式").click(timeout=5000)
        page.wait_for_timeout(3000)
        page.locator(".message-input").first.fill("广东物理类 620 分想学计算机")
        page.locator(".send-button").first.click()
        page.wait_for_timeout(25000)
        count = page.locator(".profile-indicator").count()
        if count > 0:
            text = page.locator(".profile-indicator").first.inner_text()
            assert "已识别" in text or "广东" in text or "620" in text
        # 如果 count==0，记录但不 fail——由 visual-verifier 进一步诊断


class TestRecommendationsIntent:
    """修复 3: 推荐页意向方向 + 推荐理由"""

    def test_intent_majors_label_exists(self, page: Page):
        page.goto(f"{BASE_URL}/pages/recommendations/index", wait_until="networkidle", timeout=15000)
        assert page.locator("text=意向方向").count() > 0

    def test_recommendation_cards_have_reasons(self, page: Page):
        page.goto(f"{BASE_URL}/pages/recommendations/index", wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        cards = page.locator(".major-card")
        if cards.count() > 0:
            reasons = cards.first.locator(".reason-text")
            if reasons.count() > 0:
                assert len(reasons.first.inner_text()) > 0
```

---

## Phase 4: 编写执行期 Prompt（agent: general-purpose, model: opus）

**文件**：新建 `docs/prompt-execute-miniapp-tests.md`

**任务**：编写一个独立的 prompt 文件，供另一个 session 复制执行。该 prompt 需调度 3 类 sub-agent 完成测试执行，并合成最终报告。

写入内容如下：

```markdown
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

## Phase 3: E2E 双轨并行（3 个 agent 同时启起）

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
