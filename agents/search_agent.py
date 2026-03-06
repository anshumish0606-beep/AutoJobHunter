import asyncio
import logging
from agents.browser_agent import BrowserAgent

logger = logging.getLogger(__name__)


class SearchAgent:
    """
    Smart Search Agent — searches for jobs and applies filters.
    Uses Gemini Vision to find search bars and filter options on ANY portal.
    """

    # Fallback search URLs per portal (direct search URL approach)
    SEARCH_URL_TEMPLATES = {
        "Naukri": "https://www.naukri.com/{keyword}-jobs?experience=0&jobAge=7",
        "LinkedIn": "https://www.linkedin.com/jobs/search/?keywords={keyword}&location=India&f_E=1&f_JT=I%2CF%2CP%2CC&sortBy=DD",
        "Indeed": "https://in.indeed.com/jobs?q={keyword}&l=India&fromage=7&explvl=entry_level",
        "Glassdoor": "https://www.glassdoor.co.in/Job/india-{keyword}-jobs-SRCH_IL.0,5_IN115_KO6,{end}.htm"
    }

    def __init__(self, browser_agent: BrowserAgent):
        self.browser = browser_agent

    async def search_jobs(self, portal_name: str, keyword: str, location: str = "India") -> bool:
        """
        Search for jobs on a portal using smart vision.
        Returns True if search results loaded successfully.
        """
        print(f"\n🔍 Searching '{keyword}' on {portal_name}...")

        try:
            # Method 1: Try direct search URL (faster)
            search_url = self._build_search_url(portal_name, keyword)
            if search_url:
                await self.browser.goto(search_url)
                await self.browser.wait_for_page_load()
                screenshot = await self.browser.screenshot()
                result = self.browser.gemini.extract_job_listings(screenshot)
                if result.get("found"):
                    print(f"✅ Job results loaded via direct URL on {portal_name}")
                    return True

            # Method 2: Use search bar (smart vision)
            print(f"   🔎 Finding search bar on {portal_name}...")
            typed = await self.browser.smart_type(
                "Job search bar, keyword input, job title search field",
                keyword
            )

            if typed:
                await self.browser.page.keyboard.press("Enter")
                await self.browser.wait_for_page_load()
                await self.browser.human_delay(2, 3)

                screenshot = await self.browser.screenshot()
                result = self.browser.gemini.extract_job_listings(screenshot)
                if result.get("found"):
                    print(f"✅ Job results found on {portal_name}")
                    return True

            print(f"⚠️ Could not get search results on {portal_name}")
            return False

        except Exception as e:
            print(f"❌ Search error on {portal_name}: {str(e)}")
            return False

    async def apply_filters(self, portal_name: str, filters: dict) -> None:
        """
        Apply job filters smartly using Gemini Vision.
        Filters: experience, job_type, date_posted, work_mode
        """
        print(f"   🎛️ Applying filters on {portal_name}...")

        filter_actions = [
            ("Fresher or Entry Level or 0 years experience filter", "experience"),
            ("Date posted filter - Last 7 days or Last week", "date"),
            ("Job type filter - Internship or Full Time", "job_type"),
            ("Work mode filter - Remote or Hybrid", "work_mode"),
        ]

        for filter_desc, filter_key in filter_actions:
            try:
                screenshot = await self.browser.screenshot()
                result = self.browser.gemini.find_filter_option(screenshot, filter_desc)

                if result.get("found"):
                    text_near = result.get("text_near_element", "")
                    if text_near:
                        await self.browser.smart_click(filter_desc)
                        await self.browser.human_delay(1, 2)
                        print(f"   ✅ Applied filter: {filter_key}")
                else:
                    print(f"   ⚠️ Filter not found: {filter_key} (skipping)")

            except Exception as e:
                print(f"   ⚠️ Could not apply filter {filter_key}: {str(e)}")
                continue

        await self.browser.wait_for_page_load()
        print(f"   ✅ Filters applied on {portal_name}")

    def _build_search_url(self, portal_name: str, keyword: str) -> str:
        """Build direct search URL for a portal."""
        template = self.SEARCH_URL_TEMPLATES.get(portal_name)
        if not template:
            return None

        keyword_slug = keyword.lower().replace(" ", "-")
        keyword_encoded = keyword.replace(" ", "+")

        if portal_name == "Naukri":
            return template.format(keyword=keyword_slug)
        elif portal_name == "LinkedIn":
            return template.format(keyword=keyword_encoded)
        elif portal_name == "Indeed":
            return template.format(keyword=keyword_encoded)
        elif portal_name == "Glassdoor":
            end = len(keyword) + 6
            return template.format(keyword=keyword_slug, end=end)

        return None
