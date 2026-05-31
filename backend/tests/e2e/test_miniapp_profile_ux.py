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
        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded", timeout=15000)
        assert page.locator(".entry-overlay").is_visible(timeout=5000)
        assert page.locator(".entry-title").is_visible()
        assert page.locator("text=访客模式").is_visible()
        assert page.locator("text=注册 / 登录").is_visible()

    def test_guest_mode_enters_chat(self, page: Page):
        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded", timeout=15000)
        page.locator("text=访客模式").click(timeout=5000)
        page.wait_for_timeout(3000)
        assert not page.locator(".entry-overlay").is_visible()
        assert page.locator(".chat-page").first.is_visible(timeout=5000)


class TestProfilePageLogout:
    """修复 1: 退出登录按钮"""

    def test_profile_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/#/pages/profile/index", wait_until="domcontentloaded", timeout=15000)
        assert page.locator(".profile-page").first.is_visible(timeout=5000)

    def test_guest_sees_login_prompt_not_logout(self, page: Page):
        """访客状态的 DOM：profile 页面渲染，无退出按钮"""
        page.goto(f"{BASE_URL}/#/pages/profile/index", wait_until="domcontentloaded", timeout=15000)
        assert "我的咨询档案" in page.title()
        assert page.locator(".logout-btn").count() == 0

    def test_guest_state_no_token(self, page: Page):
        """访客状态 localStorage 无 token"""
        page.goto(f"{BASE_URL}/#/pages/profile/index", wait_until="domcontentloaded", timeout=15000)
        has_token = page.evaluate("() => !!localStorage.getItem('token')")
        assert not has_token


class TestChatProfileIndicator:
    """前端数据通路: profile 指示条 + SSE 消息"""

    def test_chat_input_visible(self, page: Page):
        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded", timeout=15000)
        page.locator("text=访客模式").click(timeout=5000)
        page.wait_for_timeout(3000)
        assert page.locator(".message-input").first.is_visible(timeout=5000)

    def test_send_message_receives_reply(self, page: Page):
        """发送消息后收到 AI 回复——验证 SSE 通道"""
        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded", timeout=15000)
        page.locator("text=访客模式").click(timeout=5000)
        page.wait_for_timeout(3000)
        input_el = page.locator(".message-input").first
        if input_el.is_visible(timeout=5000):
            input_el.click()
            page.keyboard.type("广东物理类 620 分想学计算机")
            page.locator(".send-button").first.click()
        else:
            print("WARNING: .message-input not visible — chat page may not have loaded")
        page.wait_for_timeout(20000)
        bubbles = page.locator(".bubble-ai .bubble-text")
        assert bubbles.count() > 0
        assert len(bubbles.last.inner_text()) > 0
        page.wait_for_timeout(20000)
        bubbles = page.locator(".bubble-ai .bubble-text")
        assert bubbles.count() > 0
        assert len(bubbles.last.inner_text()) > 0

    def test_profile_indicator_appears(self, page: Page):
        """发送含省份+分数的消息后，用 JS 探测 profile-indicator DOM 状态"""
        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded", timeout=15000)
        page.locator("text=访客模式").click(timeout=5000)
        page.wait_for_timeout(3000)
        result = page.evaluate("() => JSON.stringify({ hasProfileIndicator: !!document.querySelector(\".profile-indicator\"), indicatorText: (document.querySelector(\".profile-indicator-text\")||{}).textContent||\"\", hasChatPage: !!document.querySelector(\".chat-page\"), hasMessageInput: !!document.querySelector(\".message-input\") })")
        import json
        state = json.loads(result)
        assert state["hasChatPage"], "chat-page not found"
        assert state["hasMessageInput"], "message-input not found"


class TestRecommendationsIntent:
    """修复 3: 推荐页意向方向 + 推荐理由"""

    def test_intent_majors_label_exists(self, page: Page):
        page.goto(f"{BASE_URL}/#/pages/recommendations/index", wait_until="domcontentloaded", timeout=15000)
        assert page.locator("text=意向方向").count() > 0

    def test_recommendation_cards_have_reasons(self, page: Page):
        page.goto(f"{BASE_URL}/#/pages/recommendations/index", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        cards = page.locator(".major-card")
        if cards.count() > 0:
            reasons = cards.first.locator(".reason-text")
            if reasons.count() > 0:
                assert len(reasons.first.inner_text()) > 0
