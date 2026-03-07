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
    """

    JOB_CARD_SELECTORS = {
        "Naukri": {
            "container": "article.jobTupleHeader, .jobTuple, div[class*='job-tuple']",
            "title": "a.title, .title a, h2 a, a[class*='title']",
            "company": ".companyInfo .subTitle, .comp-name, span[class*='comp']",
            "location": ".locWdth, .location, span[class*='loc']",
            "experience": ".experience, .exp, span[class*='exp']",
            "salary": ".salary, span[class*='sal']",
            "date": ".freshness, span[class*='date'], span[class*='fresh']",
            "link": "a.title, a[class*='title']"
        },
        "LinkedIn": {
            "container": "li.jobs-search-results__list-item, div.job-card-container, li[class*='result']",
            "title": "a.job-card-list__title, h3.base-search-card__title, a[class*='title'], .job-card-list__title",
            "company": "span.job-card-container__company-name, h4.base-search-card__subtitle, [class*='company']",
            "location": "li.job-card-container__metadata-item, span[class*='location'], .job-search-card__location",
            "date": "time, span[class*='date'], .job-search-card__listdate",
            "link": "a.job-card-list__title, a[class*='title'], a.base-card__full-link"
        },
        "Indeed": {
            "container": "div.job_seen_beacon, td.resultContent, div[class*='job_seen']",
            "title": "h2.jobTitle a, span[title], .jobTitle span",
            "company": "span.companyName, [data-testid='company-name']",
            "location": "div.companyLocation, [data-testid='text-location']",
            "salary": "div.salary-snippet, .estimated-salary span",
            "date": "span.date, [data-testid='myJobsStateDate']",
            "link": "h2.jobTitle a, a.jcs-JobTitle"
        },
        "Glassdoor": {
            "container": "li[data-test='jobListing'], article[class*='job-listing'], li[class*='JobsList']",
            "title": "a[data-test='job-title'], .job-title a, [class*='JobCard_jobTitle']",
            "company": "[data-test='employer-name'], [class*='EmployerProfile'], .employer-name",
            "location": "[data-test='emp-location'], .location, [class*='location']",
            "salary": "[data-test='detailSalary'], .salary-estimate",
            "date": ".listing-age, [data-test='job-age']",
            "link": "a[data-test='job-title'], a[class*='jobLink'], a[class*='JobCard']"
        }
    }

    def __init__(self, browser_agent: BrowserAgent, gemini_client: GeminiClient, target_roles: list):
        self.browser = browser_agent
        self.gemini = gemini_client
        self.target_roles = target_roles
        self.exclude_keywords = ["5+ years", "3+ years", "2+ years", "senior", "lead", "manager", "director"]

    async def scrape_jobs(self, portal_name: str, max_pages: int = 3) -> list:
        """Scrape all job listings from current search results page."""
        all_jobs = []
        selectors = self.JOB_CARD_SELECTORS.get(portal_name, {})

        for page_num in range(1, max_pages + 1):
            print(f"   📄 Scraping page {page_num} on {portal_name}...")

            await self.browser.scroll_down(times=5)
            await asyncio.sleep(2)

            html = await self.browser.get_page_content()
            jobs = self._parse_jobs_from_html(html, portal_name, selectors)

            print(f"   📋 Found {len(jobs)} jobs on page {page_num}")
            all_jobs.extend(jobs)

            if page_num < max_pages:
                next_clicked = await self._click_next_page(portal_name)
                if not next_clicked:
                    print(f"   ℹ️ No more pages on {portal_name}")
                    break
                await self.browser.wait_for_page_load()
                await asyncio.sleep(3)

        print(f"   🤖 Checking relevance of {len(all_jobs)} jobs...")
        relevant_jobs = await self._filter_relevant_jobs(all_jobs)
        print(f"   ✅ {len(relevant_jobs)} relevant jobs found on {portal_name}")
        return relevant_jobs

    def _parse_jobs_from_html(self, html: str, portal_name: str, selectors: dict) -> list:
        """Parse job listings from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        container_selectors = selectors.get("container", "").split(", ")

        job_cards = []
        for sel in container_selectors:
            cards = soup.select(sel.strip())
            if cards:
                job_cards = cards
                break

        if not job_cards:
            print(f"   ⚠️ No job cards found — trying generic search")
            job_cards = soup.find_all(["article", "li"], class_=re.compile(r'job|result', re.I))[:20]

        for card in job_cards[:20]:
            try:
                job = self._extract_job_data(card, selectors, portal_name)
                if job and job.get("title"):
                    title_lower = job["title"].lower()
                    if not any(exc in title_lower for exc in self.exclude_keywords):
                        jobs.append(job)
            except Exception:
                continue

        return jobs

    def _extract_job_data(self, card, selectors: dict, portal_name: str) -> dict:
        """Extract job details from a single job card."""
        base_urls = {
            "Naukri": "https://www.naukri.com",
            "LinkedIn": "https://www.linkedin.com",
            "Indeed": "https://in.indeed.com",
            "Glassdoor": "https://www.glassdoor.co.in"
        }

        def get_text(selector_str):
            if not selector_str:
                return ""
            for sel in selector_str.split(", "):
                el = card.select_one(sel.strip())
                if el:
                    return el.get_text(strip=True)
            return ""

        def get_link(selector_str):
            if not selector_str:
                return ""
            for sel in selector_str.split(", "):
                el = card.select_one(sel.strip())
                if el:
                    href = el.get("href", "")
                    if href.startswith("http"):
                        return href
                    elif href.startswith("/"):
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

    async def _filter_relevant_jobs(self, jobs: list) -> list:
        """Use Bytez AI to check relevance of each job."""
        relevant = []
        for job in jobs:
            try:
                result = self.gemini.is_job_relevant(
                    job["title"],
                    f"Company: {job['company']}, Location: {job['location']}",
                    self.target_roles
                )
                if result.get("relevant") and not result.get("requires_experience"):
                    job["relevance"] = result.get("relevance_score", "medium")
                    job["relevance_reason"] = result.get("reason", "")
                    relevant.append(job)
            except Exception:
                job["relevance"] = "medium"
                relevant.append(job)

        order = {"high": 0, "medium": 1, "low": 2}
        relevant.sort(key=lambda x: order.get(x.get("relevance", "low"), 2))
        return relevant

    async def _click_next_page(self, portal_name: str) -> bool:
        """Click the next page button."""
        next_selectors = {
            "Naukri": ["a[title='Next']", "button[aria-label='Next']"],
            "LinkedIn": ["button[aria-label='View next page']", ".artdeco-pagination__button--next"],
            "Indeed": ["a[data-testid='pagination-page-next']", "a[aria-label='Next Page']"],
            "Glassdoor": ["button[alt='Next']", "button[aria-label='Next page']"]
        }

        for selector in next_selectors.get(portal_name, []):
            try:
                await self.browser.page.click(selector, timeout=3000)
                return True
            except Exception:
                continue
        return False
