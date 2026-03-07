import asyncio
import logging
from agents.browser_agent import BrowserAgent

logger = logging.getLogger(__name__)


class LoginAgent:

    FALLBACK_SELECTORS = {
        "Naukri": {
            "username": ["#usernameField"],
            "password": ["#passwordField"],
            "submit": ["button[type='submit']"]
        },
        "LinkedIn": {
            "username": ["#username", "input[name='session_key']", "input[type='email']"],
            "password": ["#password", "input[name='session_password']", "input[type='password']"],
            "submit": ["button.btn__primary--large", "button[type='submit']"]
        },
        "Indeed": {
            "username": ["input[name='__email']", "input[type='email']"],
            "password": ["input[name='__password']", "input[type='password']"],
            "submit": ["button[type='submit']"]
        },
        "Glassdoor": {
            "username": ["input[name='username']", "input[type='email']", "#inlineUserEmail"],
            "password": ["input[name='password']", "input[type='password']"],
            "submit": ["button[type='submit']"]
        }
    }

    def __init__(self, browser_agent: BrowserAgent):
        self.browser = browser_agent

    async def _wait_and_fill(self, selectors: list, value: str, timeout: int = 15000) -> bool:
        """Wait for field to appear then fill it — handles delayed loading."""
        for selector in selectors:
            try:
                # Wait longer for element to appear
                await self.browser.page.wait_for_selector(
                    selector,
                    state="visible",
                    timeout=timeout
                )
                await asyncio.sleep(0.5)
                await self.browser.page.click(selector)
                await asyncio.sleep(0.3)
                await self.browser.page.fill(selector, "")
                await self.browser.page.type(selector, value, delay=80)
                await asyncio.sleep(0.5)
                print(f"      ✅ Filled: {selector}")
                return True
            except Exception:
                continue
        return False

    async def _try_click(self, selectors: list) -> bool:
        for selector in selectors:
            try:
                await self.browser.page.click(selector, timeout=5000)
                await asyncio.sleep(0.5)
                print(f"      ✅ Clicked: {selector}")
                return True
            except Exception:
                continue
        return False

    async def login(self, portal_name: str, portal_url: str, username: str, password: str) -> bool:
        print(f"\n🔐 Logging into {portal_name}...")
        fallbacks = self.FALLBACK_SELECTORS.get(portal_name, {})

        try:
            await self.browser.goto(portal_url)
            # Wait longer for page to fully load
            await asyncio.sleep(5)

            if portal_name == "LinkedIn":
                return await self._login_linkedin(username, password, fallbacks)

            # Standard login
            print(f"   📧 Entering username...")
            filled = await self._wait_and_fill(fallbacks.get("username", []), username)
            if not filled:
                print(f"   ❌ Could not find username field on {portal_name}")
                return False

            await asyncio.sleep(1)

            print(f"   🔑 Entering password...")
            filled = await self._wait_and_fill(fallbacks.get("password", []), password)
            if not filled:
                print(f"   ❌ Could not find password field on {portal_name}")
                return False

            await asyncio.sleep(1)

            print(f"   🖱️ Clicking login button...")
            clicked = await self._try_click(fallbacks.get("submit", []))
            if not clicked:
                await self.browser.page.keyboard.press("Enter")

            await asyncio.sleep(5)

            current_url = await self.browser.get_current_url()
            login_urls = ["login", "signin", "sign-in", "nlogin"]
            still_on_login = any(l in current_url.lower() for l in login_urls)

            if still_on_login:
                print(f"   ❌ Login failed for {portal_name}")
                return False

            print(f"✅ Successfully logged into {portal_name}!")
            return True

        except Exception as e:
            print(f"❌ Error during {portal_name} login: {str(e)}")
            logger.error(f"Login error for {portal_name}: {e}", exc_info=True)
            return False

    async def _login_linkedin(self, username: str, password: str, fallbacks: dict) -> bool:
        """LinkedIn login — handles Welcome back page and normal login."""
        try:
            current_url = await self.browser.get_current_url()

            if "checkpoint" in current_url or "otp" in current_url.lower():
                print(f"   ⚠️ LinkedIn requires OTP verification!")
                return False

            page_content = await self.browser.get_page_content()
            is_welcome_back = "Welcome back" in page_content

            if is_welcome_back:
                print(f"   📋 'Welcome back' page — filling password only...")
                filled = await self._wait_and_fill(
                    ["input[type='password']", "#password", "input[name='session_password']"],
                    password
                )
            else:
                print(f"   📧 Entering username...")
                filled = await self._wait_and_fill(fallbacks.get("username", []), username)
                if not filled:
                    return False
                await asyncio.sleep(1)
                print(f"   🔑 Entering password...")
                filled = await self._wait_and_fill(fallbacks.get("password", []), password)

            if not filled:
                print(f"   ❌ Could not fill password")
                return False

            await asyncio.sleep(1)

            print(f"   🖱️ Clicking Sign In...")
            clicked = await self._try_click([
                "button[type='submit']",
                "button.btn__primary--large"
            ])
            if not clicked:
                await self.browser.page.keyboard.press("Enter")

            await asyncio.sleep(6)

            current_url = await self.browser.get_current_url()

            if "checkpoint" in current_url or "challenge" in current_url:
                print(f"   ⚠️ LinkedIn asking for verification — solve it manually once!")
                return False

            if "login" in current_url or "signin" in current_url:
                print(f"   ❌ LinkedIn login failed — wrong password?")
                return False

            print(f"✅ Successfully logged into LinkedIn!")
            return True

        except Exception as e:
            print(f"❌ LinkedIn error: {str(e)}")
            return False