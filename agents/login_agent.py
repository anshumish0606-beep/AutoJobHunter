import asyncio
import logging
from agents.browser_agent import BrowserAgent

logger = logging.getLogger(__name__)


class LoginAgent:
    """
    Smart Login Agent — logs into any job portal.
    Uses updated fallback selectors for each portal.
    """

    FALLBACK_SELECTORS = {
        "Naukri": {
            "username": [
                "input[type='text']",
                "input[placeholder*='Email']",
                "input[placeholder*='email']",
                "input[name='username']",
                "#usernameField"
            ],
            "password": [
                "input[type='password']",
                "input[placeholder*='Password']",
                "input[placeholder*='password']"
            ],
            "submit": [
                "button[type='submit']",
                "button.loginButton",
                "input[type='submit']",
                "button:has-text('Login')",
                "button:has-text('Sign in')"
            ]
        },
        "LinkedIn": {
            "username": ["#username", "input[name='session_key']"],
            "password": ["#password", "input[name='session_password']"],
            "submit": ["button[type='submit']", ".login__form_action_container button"]
        },
        "Indeed": {
            "username": ["input[name='__email']", "input[type='email']", "#ifl-InputFormField-3"],
            "password": ["input[name='__password']", "input[type='password']", "#ifl-InputFormField-7"],
            "submit": ["button[type='submit']", "#signin-submit"]
        },
        "Glassdoor": {
            "username": [
                "input[name='username']",
                "input[type='email']",
                "input[placeholder*='Email']",
                "#inlineUserEmail",
                "input[autocomplete='email']"
            ],
            "password": [
                "input[name='password']",
                "input[type='password']",
                "#inlineUserPassword"
            ],
            "submit": [
                "button[type='submit']",
                "button:has-text('Sign In')",
                "button:has-text('Continue')"
            ]
        }
    }

    def __init__(self, browser_agent: BrowserAgent):
        self.browser = browser_agent

    async def _try_fill(self, selectors: list, value: str) -> bool:
        """Try multiple selectors until one works."""
        for selector in selectors:
            try:
                await self.browser.page.wait_for_selector(selector, timeout=3000)
                await self.browser.page.fill(selector, value)
                await asyncio.sleep(0.5)
                print(f"      ✅ Filled: {selector}")
                return True
            except Exception:
                continue
        return False

    async def _try_click(self, selectors: list) -> bool:
        """Try multiple selectors to click."""
        for selector in selectors:
            try:
                await self.browser.page.click(selector, timeout=3000)
                await asyncio.sleep(0.5)
                print(f"      ✅ Clicked: {selector}")
                return True
            except Exception:
                continue
        return False

    async def login(self, portal_name: str, portal_url: str, username: str, password: str) -> bool:
        """Login to a job portal using fallback selectors."""
        print(f"\n🔐 Logging into {portal_name}...")
        fallbacks = self.FALLBACK_SELECTORS.get(portal_name, {})

        try:
            await self.browser.goto(portal_url)
            await self.browser.wait_for_page_load()
            await asyncio.sleep(2)

            # Step 1: Fill username
            print(f"   📧 Entering username...")
            filled = await self._try_fill(fallbacks.get("username", []), username)
            if not filled:
                print(f"   ❌ Could not find username field on {portal_name}")
                return False

            await asyncio.sleep(1)

            # Step 2: Handle "Continue" button (LinkedIn style)
            for cont_selector in ["button:has-text('Continue')", "#login-submit"]:
                try:
                    btn = await self.browser.page.query_selector(cont_selector)
                    if btn and portal_name != "LinkedIn":
                        await btn.click()
                        await asyncio.sleep(2)
                        break
                except Exception:
                    pass

            # Step 3: Fill password
            print(f"   🔑 Entering password...")
            filled = await self._try_fill(fallbacks.get("password", []), password)
            if not filled:
                print(f"   ❌ Could not find password field on {portal_name}")
                return False

            await asyncio.sleep(1)

            # Step 4: Click submit
            print(f"   🖱️ Clicking login button...")
            clicked = await self._try_click(fallbacks.get("submit", []))
            if not clicked:
                await self.browser.page.keyboard.press("Enter")

            await self.browser.wait_for_page_load(timeout=15)
            await asyncio.sleep(3)

            # Step 5: Verify login by checking URL changed
            current_url = await self.browser.get_current_url()
            login_urls = ["login", "signin", "sign-in", "nlogin"]
            still_on_login = any(l in current_url.lower() for l in login_urls)

            if still_on_login:
                print(f"   ❌ Login failed for {portal_name} — still on login page")
                return False

            print(f"✅ Successfully logged into {portal_name}!")
            return True

        except Exception as e:
            print(f"❌ Error during {portal_name} login: {str(e)}")
            logger.error(f"Login error for {portal_name}: {e}", exc_info=True)
            return False
