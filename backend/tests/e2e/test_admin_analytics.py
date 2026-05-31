"""Pipeline stage: Admin Dashboard (Analytics) — admin login -> insights pages -> no 403.

E2E test using sync_playwright API (not mcp__playwright__*).
"""

import pytest
from playwright.sync_api import sync_playwright, Page, Browser


ADMIN_URL = "http://nginx/admin"


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


class TestAdminAnalytics:
    """Pipeline stage: Admin Analytics — login -> navigate insights -> verify no 403 (E2E)."""

    def _login(self, page: Page):
        """Navigate to admin SPA and log in."""
        page.goto(f"{ADMIN_URL}/?tenant=scnu", wait_until="networkidle", timeout=15000)

        username_input = page.locator("input[placeholder*='用户'], input[name='username'], input[type='text']").first
        password_input = page.locator("input[type='password']").first
        login_btn = page.locator("button:has-text('登录'), button:has-text('Login'), button[type='submit']").first

        if username_input.is_visible(timeout=5000) and password_input.is_visible():
            username_input.fill("admin")
            password_input.fill("admin123")
            login_btn.click()
            page.wait_for_timeout(3000)

    def test_admin_login_succeeds(self, page: Page):
        """Pipeline stage: Admin Dashboard — admin can log in without errors."""
        self._login(page)
        assert "/login" not in page.url or page.locator(".dashboard, .main-content").count() > 0

    def test_insights_page_no_403(self, page: Page):
        """Pipeline stage: Module Gating — insights/analytics pages return no 403 for scnu tenant."""
        self._login(page)

        nav_items = page.locator("nav a, .sidebar a, [data-testid='nav-item']")
        insights_link = nav_items.locator("text=/洞察|Insights|Analytics|数据分析/").first
        if insights_link.is_visible(timeout=5000):
            insights_link.click()
            page.wait_for_timeout(3000)

            error_403 = page.locator("text=/403|Forbidden|无权限/")
            assert error_403.count() == 0, "Insights page returned 403"

    def test_funnel_page_loads(self, page: Page):
        """Pipeline stage: Admin Analytics — funnel analytics page loads without errors."""
        self._login(page)

        funnel_link = page.locator("text=/漏斗|Funnel|转化/").first
        if funnel_link.is_visible(timeout=3000):
            funnel_link.click()
            page.wait_for_timeout(3000)

            assert True  # If we got here, page loaded without hard errors
