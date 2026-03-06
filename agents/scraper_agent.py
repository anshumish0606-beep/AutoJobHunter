import asyncio
import re
import logging
from bs4 import BeautifulSoup
from agents.browser_agent import BrowserAgent
from llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class ScraperAgent:
    """
    Smart Scraper Agent — collects job listings from search results.
    Parses HTML intelligently and uses Gemini to check relevance.
    """

    # Selectors per portal for job cards
    JOB_CARD_SELECTORS = {
        "Naukri": {
            "container": ".jobTuple, .job-tuple, article.jobTupleHeader",
            "title": ".title, .jobTitle, h2 a",
            "company": ".companyInfo .subTitle, .comp-name",
            "location": ".locWdth, .job-location",
            "experience": ".experience, .expwdth",
            "salary": ".salary, .sal-wrap",
            "date": ".freshness, span[class*='date']",
            "link": "a.title, a.jobTitle"
        },
        "LinkedIn": {
            "container": ".job-card-container, .jobs-search-results__list-item",
            "title": ".job-card-list__title, h3.base-search-card__title",
            "company": ".job-card-container__company-name, h4.base-search-card__subtitle",
            "location": ".job-card-container__metadata-item, span.job-search-card__location",
            "date": "time",
            "link": "a.job-card-list__title, a.base-card__full-link"
        },
        "Indeed": {
            "container": ".job_seen_beacon, .jobsearch-ResultsList > li",
            "title": "h2.jobTitle span, .jobTitle a",
            "company": ".companyName, [data-testid='company-name']",
            "location": ".companyLocation, [data-testid='text-location']",
            "salary": ".salary-snippet, .estimated-salary",
            "date": ".date, [data-testid='myJobsStateDate']",
            "link": "h2.jobTitle a, .jobTitle a"
        },
        "Glassdoor": {
            "container": "li.react-job-listing, article[data-test='jobListing']",
            "title": "[data-test='job-title'], .job-title",
            "company": "[data-test='employer-name'], .employer-name",
            "location": "[data-test='emp-location'], .location",
            "salary": "[data-test='detailSalary'], .salary-estimate",
            "date": ".listing-age, [data-test='job-age']",
            "link": "a[data-test='job-title'], a.jobLink"
        }
    }

    def __init__(self, browser_agent: BrowserAgent, gemini_client: GeminiClient, target_roles: list):
        self.browser = browser_agent
        self.gemini = gemini_client
        self.target_roles = target_roles
        self.exclude_keywords = ["5+ years", "3+ years", "2+ years", "senior", "lead", "manager", "director", "principal"]

    async def scrape_jobs(self, portal_name: str, max_pages: int = 3) -> list:
        """
        Scrape all job listings from current search results page.
        Returns list of job dicts.
        """
        all_jobs = []
        selectors = self.JOB_CARD_SELECTORS.get(portal_name, {})

        for page_num in range(1, max_pages + 1):
            print(f"   📄 Scraping page {page_num} on {portal_name}...")

            # Scroll to load all jobs on page
            await self.browser.scroll_down(times=5)
            await self.browser.human_delay(2, 3)

            # Get page HTML
            html = await self.browser.get_page_content()
            jobs = self._parse_jobs_from_html(html, portal_name, selectors)

            print(f"   📋 Found {len(jobs)} jobs on page {page_num}")
            all_jobs.extend(jobs)

            # Try to go to next page
            if page_num < max_pages:
                next_clicked = await self._click_next_page(portal_name)
                if not next_clicked:
                    print(f"   ℹ️ No more pages on {portal_name}")
                    break
                await self.browser.wait_for_page_load()
                await self.browser.human_delay(2, 4)

        # Filter relevant jobs using Gemini
        print(f"   🤖 Checking relevance of {len(all_jobs)} jobs...")
        relevant_jobs = await self._filter_relevant_jobs(all_jobs, portal_name)
        print(f"   ✅ {len(relevant_jobs)} relevant jobs found on {portal_name}")

        return relevant_jobs

    def _parse_jobs_from_html(self, html: str, portal_name: str, selectors: dict) -> list:
        """Parse job listings from HTML using BeautifulSoup."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        container_selector = selectors.get("container", "")
        if not container_selector:
            return jobs

        job_cards = soup.select(container_selector)

        for card in job_cards[:20]:  # Max 20 per page
            try:
                job = self._extract_job_data(card, selectors, portal_name)
                if job and job.get("title"):
                    # Quick pre-filter — exclude senior roles
                    title_lower = job["title"].lower()
                    if not any(exc in title_lower for exc in self.exclude_keywords):
                        jobs.append(job)
            except Exception as e:
                continue

        return jobs

    def _extract_job_data(self, card, selectors: dict, portal_name: str) -> dict:
        """Extract job details from a single job card."""

        def get_text(selector):
            if not selector:
                return ""
            el = card.select_one(selector)
            return el.get_text(strip=True) if el else ""

        def get_link(selector):
            if not selector:
                return ""
            el = card.select_one(selector)
            if el:
                href = el.get("href", "")
                if href.startswith("http"):
                    return href
                elif href.startswith("/"):
                    base_urls = {
                        "Naukri": "https://www.naukri.com",
                        "LinkedIn": "https://www.linkedin.com",
                        "Indeed": "https://in.indeed.com",
                        "Glassdoor": "https://www.glassdoor.co.in"
                    }
                    return base_urls.get(portal_name, "") + href
            return ""

        return {
            "title": get_text(selectors.get("title")),
            "company": get_text(selectors.get("company")),
            "location": get_text(selectors.get("location")),
            "experience": get_text(selectors.get("experience")),
            "salary": get_text(selectors.get("salary")),
            "date_posted": get_text(selectors.get("date")),
            "apply_link": get_link(selectors.get("link")),
            "portal": portal_name,
            "relevance": "pending"
        }

    async def _filter_relevant_jobs(self, jobs: list, portal_name: str) -> list:
        """Use Gemini to check relevance of each job."""
        relevant = []
        for job in jobs:
            try:
                result = self.gemini.is_job_relevant(
                    job["title"],
                    f"Company: {job['company']}, Location: {job['location']}, Experience: {job['experience']}",
                    self.target_roles
                )
                if result.get("relevant") and not result.get("requires_experience"):
                    job["relevance"] = result.get("relevance_score", "medium")
                    job["relevance_reason"] = result.get("reason", "")
                    relevant.append(job)
            except Exception:
                job["relevance"] = "medium"
                relevant.append(job)

        # Sort by relevance: high > medium > low
        order = {"high": 0, "medium": 1, "low": 2}
        relevant.sort(key=lambda x: order.get(x.get("relevance", "low"), 2))
        return relevant

    async def _click_next_page(self, portal_name: str) -> bool:
        """Click the next page button."""
        next_selectors = {
            "Naukri": "a[title='Next']",
            "LinkedIn": "button[aria-label='View next page']",
            "Indeed": "a[data-testid='pagination-page-next']",
            "Glassdoor": "button[alt='Next']"
        }

        selector = next_selectors.get(portal_name)
        if selector:
            try:
                await self.browser.page.click(selector, timeout=5000)
                return True
            except Exception:
                pass

        # Smart click fallback
        return await self.browser.smart_click("Next page button or arrow")
