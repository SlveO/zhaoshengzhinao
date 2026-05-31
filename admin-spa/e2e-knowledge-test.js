const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  
  const errors = [];
  const failedRequests = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(`[console.error] ${msg.text()}`);
    }
  });
  
  page.on('response', resp => {
    if (!resp.ok() && resp.url().includes('/api/')) {
      failedRequests.push(`[API] ${resp.status()} ${resp.url()}`);
    }
  });

  console.log('--- STEP 1: Navigate to login ---');
  await page.goto('http://localhost/admin/?tenant=scnu');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '../.playwright-mcp/01-login-page.png', fullPage: true });
  console.log('Login page loaded');

  console.log('--- STEP 2: Login ---');
  await page.fill('input[type="text"], input[name="username"], #username', 'admin');
  await page.fill('input[type="password"], input[name="password"], #password', 'admin123');
  await page.click('button[type="submit"], button:has-text("登录"), button:has-text("Login")');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '../.playwright-mcp/02-dashboard.png', fullPage: true });
  console.log('Dashboard loaded');

  console.log('--- STEP 3: Navigate to knowledge ---');
  await page.goto('http://localhost/admin/knowledge?tenant=scnu');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '../.playwright-mcp/03-knowledge-page.png', fullPage: true });
  console.log('Knowledge page loaded');

  const textContent = await page.evaluate(() => document.body.innerText);
  
  console.log('--- CONSOLE ERRORS ---');
  console.log(errors.length ? errors.join('\n') : 'None');
  
  console.log('--- FAILED API REQUESTS ---');
  console.log(failedRequests.length ? failedRequests.join('\n') : 'None');
  
  console.log('--- PAGE TEXT (first 2000 chars) ---');
  console.log(textContent.slice(0, 2000));

  await browser.close();
})();
