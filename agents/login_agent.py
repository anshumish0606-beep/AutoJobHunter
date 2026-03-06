import asyncio
import logging
from agents.browser_agent import BrowserAgent

logger = logging.getLogger(__name__)


class LoginAgent:
    """
    Smart Login Agent — logs into any job portal intelligently.
    Uses Gemini Vision to find login fields on ANY website.
    No hardcoded selectors!
    """

    # Fallback selectors per portal (backup if Gemini fails)
    FALLBACK_SELECTORS = {
        "Naukri": {
            "username": "input[placeholder*='Email']",
            "password": "input[type='password']",
            "submit": "button[type='submit']"
        },
        "LinkedIn": {
            "username": "#username",
            "password": "#password",
            "submit": "button[type='submit']"
        },
        "Indeed": {
            "username": "input[name='__email']",
            "password": "input[name='__password']",
            "submit": "button[type='submit']"
        },
        "Glassdoor": {
            "username": "input[name='username']",
            "password": "input[name='password']",
            "submit": "button[type='submit']"
        }
    }

    def __init__(self, browser_agent: BrowserAgent):
        self.browser = browser_agent

    async def login(self, portal_name: str, portal_url: str, username: str, password: str) -> bool:
        """
        Login to a job portal smartly.
        Returns True if login successful, False otherwise.
        """
        print(f"\n🔐 Logging into {portal_name}...")
        fallbacks = self.FALLBACK_SELECTORS.get(portal_name, {})

        try:
            # Go to login page
            await self.browser.goto(portal_url)
            await self.browser.wait_for_page_load()

            # Check for CAPTCHA before login
            screenshot = await self.browser.screenshot()
            if self.browser.gemini.check_captcha(screenshot):
                print(f"⚠️ CAPTCHA detected on {portal_name}! Manual intervention needed.")
                return False

            # Step 1: Find and fill username/email
            print(f"   📧 Entering username...")
            username_typed = await self.browser.smart_type(
                "Email, Username, Mobile or User ID input field",
                username,
                fallback_selector=fallbacks.get("username")
            )

            if not username_typed:
                print(f"   ❌ Could not find username field on {portal_name}")
                return False

            await self.browser.human_delay(0.5, 1.5)

            # Some portals (LinkedIn) have a "Continue" button after email
            screenshot = await self.browser.screenshot()
            result = self.browser.gemini.analyze_screenshot(
                screenshot,
                "Is there a CONTINUE or NEXT button visible after entering email? Not the final login button."
            )
            if result.get("found"):
                await self.browser.smart_click("Continue or Next button", "button[type='submit']")
                await self.browser.human_delay(1, 2)

            # Step 2: Find and fill password
            print(f"   🔑 Entering password...")
            password_typed = await self.browser.smart_type(
                "Password input field",
                password,
                fallback_selector=fallbacks.get("password")
            )

            if not password_typed:
                print(f"   ❌ Could not find password field on {portal_name}")
                return False

            await self.browser.human_delay(0.5, 1.5)

            # Step 3: Click login button
            print(f"   🖱️ Clicking login button...")
            clicked = await self.browser.smart_click(
                "Login, Sign In or Submit button",
                fallback_selector=fallbacks.get("submit")
            )

            if not clicked:
                # Try pressing Enter as last resort
                await self.browser.page.keyboard.press("Enter")

            # Wait for page to load after login
            await self.browser.wait_for_page_load(timeout=15)
            await self.browser.human_delay(2, 4)

            # Step 4: Verify login success
            screenshot = await self.browser.screenshot()

            # Check for CAPTCHA after login attempt
            if self.browser.gemini.check_captcha(screenshot):
                print(f"⚠️ CAPTCHA appeared after login on {portal_name}!")
                return False

            success = self.browser.gemini.is_login_successful(screenshot)

            if success:
                print(f"✅ Successfully logged into {portal_name}!")
                return True
            else:
                print(f"❌ Login failed for {portal_name}. Check credentials.")
                return False

        except Exception as e:
            print(f"❌ Error during {portal_name} login: {str(e)}")
            logger.error(f"Login error for {portal_name}: {e}", exc_info=True)
            return False
