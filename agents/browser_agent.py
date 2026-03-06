import asyncio
import random
import time
from playwright.async_api import async_playwright, Page, Browser
from llm.gemini_client import GeminiClient
import logging

logger = logging.getLogger(__name__)


class BrowserAgent:
    """
    Smart Browser Agent — controls Chrome using Playwright.
    Uses Gemini Vision to understand pages intelligently.
    No hardcoded selectors — works on ANY website!
    """

    def __init__(self, gemini_client: GeminiClient, headless: bool = True):
        self.gemini = gemini_client
        self.headless = headless
        self.browser: Browser = None
        self.page: Page = None
        self.playwright = None

    async def start(self):
        """Launch browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ]
        )
        context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = await context.new_page()
        print("✅ Browser launched!")

    async def stop(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def screenshot(self) -> bytes:
        """Take screenshot of current page."""
        return await self.page.screenshot(full_page=False)

    async def human_delay(self, min_sec=1.0, max_sec=3.0):
        """Random human-like delay between actions."""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def goto(self, url: str):
        """Navigate to URL."""
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await self.human_delay(2, 4)
        print(f"📌 Navigated to: {url}")

    async def smart_click(self, description: str, fallback_selector: str = None) -> bool:
        """
        Smartly click an element using Gemini Vision.
        Falls back to selector if provided.
        """
        screenshot = await self.screenshot()
        result = self.gemini.analyze_screenshot(screenshot, f"Find and locate: {description}")

        if result.get("found"):
            text_near = result.get("text_near_element", "")
            if text_near:
                try:
                    await self.page.get_by_text(text_near, exact=False).first.click(timeout=5000)
                    await self.human_delay()
                    print(f"✅ Smart clicked: {description}")
                    return True
                except Exception:
                    pass

        if fallback_selector:
            try:
                await self.page.click(fallback_selector, timeout=5000)
                await self.human_delay()
                print(f"✅ Fallback clicked: {fallback_selector}")
                return True
            except Exception:
                pass

        print(f"❌ Could not click: {description}")
        return False

    async def smart_type(self, description: str, text: str, fallback_selector: str = None) -> bool:
        """
        Smartly type into an input field using Gemini Vision.
        """
        screenshot = await self.screenshot()
        result = self.gemini.analyze_screenshot(screenshot, f"Find input field: {description}")

        async def type_with_human_speed(selector_or_element, text):
            """Type text character by character like a human."""
            for char in text:
                await self.page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

        if result.get("found"):
            text_near = result.get("text_near_element", "")
            if text_near:
                try:
                    element = self.page.get_by_label(text_near, exact=False).first
                    await element.click(timeout=5000)
                    await element.clear()
                    await type_with_human_speed(element, text)
                    await self.human_delay()
                    print(f"✅ Smart typed in: {description}")
                    return True
                except Exception:
                    pass

        if fallback_selector:
            try:
                await self.page.click(fallback_selector, timeout=5000)
                await self.page.fill(fallback_selector, "")
                await self.page.type(fallback_selector, text, delay=random.randint(50, 150))
                await self.human_delay()
                print(f"✅ Fallback typed in: {fallback_selector}")
                return True
            except Exception:
                pass

        print(f"❌ Could not type in: {description}")
        return False

    async def wait_for_page_load(self, timeout=10):
        """Wait for page to fully load."""
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout * 1000)
        except Exception:
            await asyncio.sleep(3)

    async def scroll_down(self, times=3):
        """Scroll down to load more content."""
        for _ in range(times):
            await self.page.keyboard.press("End")
            await self.human_delay(1, 2)

    async def get_page_content(self) -> str:
        """Get full page HTML content."""
        return await self.page.content()

    async def get_current_url(self) -> str:
        """Get current page URL."""
        return self.page.url
