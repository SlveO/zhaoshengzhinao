"""Capture screenshots of key pages for investor showcase."""
import asyncio
import json
import base64
import os
from playwright.async_api import async_playwright
import httpx

BASE = "http://localhost:3000"
API = "http://localhost:8000/api/v1"
OUT = "docs/showcase-screenshots"
os.makedirs(OUT, exist_ok=True)

async def register_and_login():
    """Register a test user and return JWT token + user info."""
    import uuid
    uid = str(uuid.uuid4())[:8]
    async with httpx.AsyncClient() as client:
        # Register
        r = await client.post(f"{API}/auth/register", json={
            "username": f"showcase_{uid}",
            "password": "showcase123",
            "region": "广东",
            "score": 620,
            "subjects": "物理+化学+生物"
        })
        data = r.json()
        token = data.get("access_token") or data.get("token") or data.get("accessToken")
        if not token:
            # Try login
            r2 = await client.post(f"{API}/auth/login", json={
                "username": f"showcase_{uid}",
                "password": "showcase123"
            })
            data2 = r2.json()
            token = data2.get("access_token") or data2.get("token") or data2.get("accessToken")
        print(f"Registered user: showcase_{uid}, token: {token[:20]}..." if token else "NO TOKEN")
        return token, uid

async def capture_screenshots():
    token, uid = await register_and_login()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )

        # Set auth token before navigating to protected pages
        if token:
            await context.add_cookies([{
                "name": "token",
                "value": token,
                "domain": "localhost",
                "path": "/",
            }])

        page = await context.new_page()

        # 1. Landing page
        print("Capturing landing page...")
        await page.goto(f"{BASE}/", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{OUT}/01-landing.png", full_page=True)

        # 2. Register page
        print("Capturing register page...")
        await page.goto(f"{BASE}/register", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{OUT}/02-register.png", full_page=True)

        # 3. Login page
        print("Capturing login page...")
        await page.goto(f"{BASE}/login", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{OUT}/03-login.png", full_page=True)

        # 4. Chat page - with welcome modal
        print("Capturing chat page with welcome modal...")
        # Set token in localStorage before navigating
        await page.goto(f"{BASE}/", wait_until="networkidle", timeout=15000)
        if token:
            await page.evaluate(f"""() => {{ localStorage.setItem('token', '{token}'); }}""")
        await page.goto(f"{BASE}/chat", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)
        # Check if welcome modal is visible
        modal_visible = await page.locator('input[type="number"], input[placeholder*="分数"]').count() > 0
        if modal_visible:
            await page.screenshot(path=f"{OUT}/04-chat-welcome.png", full_page=True)
            # Fill welcome modal
            print("Filling welcome modal...")
            try:
                # Fill score
                score_input = page.locator('input[type="number"]').first
                if await score_input.count() > 0:
                    await score_input.fill("620")
                # Fill subjects
                subject_select = page.locator('select').first
                if await subject_select.count() > 0:
                    await subject_select.select_option("物理+化学+生物")
                # Fill region
                region_select = page.locator('select').last
                if await region_select.count() > 0:
                    await region_select.select_option("广东")
                # Click submit button
                submit_btn = page.locator('button').filter(has_text="开始对话").first
                if await submit_btn.count() == 0:
                    submit_btn = page.locator('button').filter(has_text="提交").first
                if await submit_btn.count() == 0:
                    submit_btn = page.locator('button').filter(has_text="确认").first
                if await submit_btn.count() == 0:
                    # Try any primary button in modal
                    submit_btn = page.locator('[role="dialog"] button, .modal button, [class*="modal"] button').last
                if await submit_btn.count() > 0:
                    await submit_btn.click()
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"  Warning: Could not fill welcome modal: {e}")

        # 5. Chat page after welcome modal (conversation started)
        print("Capturing chat page with conversation...")
        await page.screenshot(path=f"{OUT}/05-chat-started.png", full_page=True)

        # 6. Send a message and get AI response
        print("Sending message and capturing conversation...")
        try:
            textarea = page.locator('textarea, input[type="text"], [contenteditable]').first
            if await textarea.count() > 0:
                await textarea.fill("我平时比较喜欢自己研究数学题，也喜欢帮助同学解答问题，但不太喜欢死记硬背的东西")
                # Try to find send button
                send_btn = page.locator('button').filter(has_text="发送").first
                if await send_btn.count() == 0:
                    send_btn = page.locator('button[type="submit"]').first
                if await send_btn.count() > 0:
                    await send_btn.click()
                    await page.wait_for_timeout(5000)  # Wait for AI response
                else:
                    await textarea.press("Enter")
                    await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  Warning sending message: {e}")

        await page.screenshot(path=f"{OUT}/06-chat-conversation.png", full_page=True)

        # Send another message
        try:
            textarea = page.locator('textarea, input[type="text"], [contenteditable]').first
            if await textarea.count() > 0:
                await textarea.fill("我爸妈想让我学计算机，但我自己对生物更感兴趣，不知道该怎么选")
                send_btn = page.locator('button').filter(has_text="发送").first
                if await send_btn.count() > 0:
                    await send_btn.click()
                    await page.wait_for_timeout(5000)
                else:
                    await textarea.press("Enter")
                    await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  Warning sending 2nd message: {e}")

        await page.screenshot(path=f"{OUT}/07-chat-mid-conversation.png", full_page=True)

        # 7. Recommendations page
        print("Capturing recommendations page...")
        await page.goto(f"{BASE}/recommendations", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        # Check if loading spinner is gone
        try:
            await page.wait_for_selector('.animate-spin', state='detached', timeout=20000)
        except:
            pass
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{OUT}/08-recommendations.png", full_page=True)

        await browser.close()

    # Convert to base64 for embedding
    screenshots = {}
    for f in sorted(os.listdir(OUT)):
        if f.endswith('.png'):
            path = os.path.join(OUT, f)
            with open(path, 'rb') as img:
                screenshots[f] = base64.b64encode(img.read()).decode()

    # Write JSON mapping
    with open(f"{OUT}/screenshots.json", "w") as f:
        json.dump({"files": list(screenshots.keys()), "count": len(screenshots)}, f)

    print(f"\nDone! {len(screenshots)} screenshots captured to {OUT}/")
    for name in screenshots:
        print(f"  - {name} ({len(screenshots[name])} chars base64)")

if __name__ == "__main__":
    asyncio.run(capture_screenshots())
