
import asyncio
from playwright.async_api import async_playwright

async def take_screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            preview_url = "hello_world.html" or "http://localhost:8001/api/projects/1b2bb6b6-b13d-410e-8448-204450f5fda3/preview/index.html"
            await page.goto(preview_url, wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(2000)
            
            await page.screenshot(path="/tmp/screenshot.png")
            logger.info("✅ Screenshot saved to /tmp/screenshot.png")
        except Exception as e:
            logger.error(f"❌ Screenshot error: {e}")
        finally:
            await browser.close()

try:
    asyncio.run(take_screenshot())
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(take_screenshot())
    loop.close()
