import asyncio
import re
import logging
from bs4 import BeautifulSoup
from agents.browser_agent import BrowserAgent
from llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class ScraperAgent:

    def __init__(self, browser_agent: BrowserAgent, gemini_client: GeminiClient, target_roles: list):
        self.browser = browser_agent
        self.gemini = gemini_client
        self.target_roles = target_roles
        self.exclude_keywords = ["5+ years", "3+ years", "2+ years", "senior", "lead", "manager", "director"]

    async def scrape_jobs(self, portal_name: str, max_pages: int = 3) -> list:
        all_jobs = []

        for page_num in range(1, max_pages + 1):
            print(f"   📄 Scraping page {page_num} on {portal_name}...")
            await self.browser.scroll_down(times=8)
            await asyncio.sleep(3)

            if portal_name == "LinkedIn":
                jobs = await self._scrape_linkedin_js()
            else:
                html = await self.browser.get_page_content()
                jobs = self._parse_jobs_html(html, portal_name)

            print(f"   📋 Found {len(jobs)} jobs on page {page_num}")
            all_jobs.extend(jobs)

            if not jobs or page_num >= max_pages:
                break

            next_clicked = await self._click_next_page(portal_name)
            if not next_clicked:
                print(f"   ℹ️ No more pages on {portal_name}")
                break
            await asyncio.sleep(3)

        print(f"   🤖 Checking relevance of {len(all_jobs)} jobs...")
        relevant = await self._filter_relevant_jobs(all_jobs)
        print(f"   ✅ {len(relevant)} relevant jobs found on {portal_name}")
        return relevant

    async def _scrape_linkedin_js(self) -> list:
        """Use JavaScript to extract LinkedIn jobs — works in headless mode."""
        try:
            jobs = await self.browser.page.evaluate("""
                () => {
                    const results = [];
                    
                    // Try multiple container selectors
                    const selectors = [
                        '.jobs-search-results__list-item',
                        '.scaffold-layout__list-item',
                        'li[class*="jobs-search-results"]',
                        '.job-card-container',
                        '[data-job-id]',
                        'li[class*="result"]'
                    ];
                    
                    let cards = [];
                    for (const sel of selectors) {
                        cards = document.querySelectorAll(sel);
                        if (cards.length > 0) break;
                    }
                    
                    // If still no cards, try getting all li elements in jobs list
                    if (cards.length === 0) {
                        const list = document.querySelector('ul.jobs-search-results__list, ul[class*="jobs-search"]');
                        if (list) cards = list.querySelectorAll('li');
                    }
                    
                    cards.forEach(card => {
                        try {
                            // Get title
                            const titleEl = card.querySelector(
                                'a.job-card-list__title, .job-card-list__title--link, ' +
                                'a[class*="job-card-list__title"], h3[class*="base-search-card__title"], ' +
                                '.artdeco-entity-lockup__title a, a[class*="title"]'
                            );
                            const title = titleEl ? titleEl.innerText.trim() : '';
                            if (!title) return;
                            
                            // Get company
                            const compEl = card.querySelector(
                                '.job-card-container__company-name, span[class*="company"], ' +
                                'h4[class*="subtitle"], .artdeco-entity-lockup__subtitle span, ' +
                                'a[class*="company"]'
                            );
                            const company = compEl ? compEl.innerText.trim() : '';
                            
                            // Get location
                            const locEl = card.querySelector(
                                '.job-card-container__metadata-item, span[class*="location"], ' +
                                'li[class*="metadata"], .artdeco-entity-lockup__caption span'
                            );
                            const location = locEl ? locEl.innerText.trim() : 'India';
                            
                            // Get link
                            const linkEl = card.querySelector('a[href*="/jobs/view/"], a[href*="linkedin.com/jobs"]');
                            let link = linkEl ? linkEl.href : '';
                            if (!link && titleEl) link = titleEl.href || '';
                            
                            // Get date
                            const dateEl = card.querySelector('time, span[class*="time"], .job-card-container__listed-status');
                            const date = dateEl ? (dateEl.getAttribute('datetime') || dateEl.innerText.trim()) : '';
                            
                            if (title) {
                                results.push({ title, company, location, date, link });
                            }
                        } catch(e) {}
                    });
                    
                    return results;
                }
            """)

            formatted = []
            for j in jobs:
                title_lower = j.get("title", "").lower()
                if not any(exc in title_lower for exc in self.exclude_keywords):
                    formatted.append({
                        "title": j.get("title", ""),
                        "company": j.get("company", ""),
                        "location": j.get("location", "India"),
                        "experience": "",
                        "salary": "",
                        "date_posted": j.get("date", ""),
                        "apply_link": j.get("link", ""),
                        "portal": "LinkedIn",
                        "relevance": "pending"
                    })
            return formatted

        except Exception as e:
            print(f"   ⚠️ JS scraping error: {e}")
            # Fallback to HTML parsing
            html = await self.browser.get_page_content()
            return self._parse_jobs_html(html, "LinkedIn")

    def _parse_jobs_html(self, html: str, portal_name: str) -> list:
        """Parse jobs from HTML using BeautifulSoup."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        SELECTORS = {
            "Naukri": {
                "container": ["article.jobTupleHeader", ".jobTuple", "div[class*='job-tuple']", "article[class*='job']"],
                "title": ["a.title", ".title a", "h2 a", "a[class*='title']"],
                "company": [".companyInfo .subTitle", ".comp-name", "span[class*='comp']"],
                "location": [".locWdth", ".location", "span[class*='loc']"],
                "link": ["a.title", "a[class*='title']"]
            },
            "Indeed": {
                "container": ["div.job_seen_beacon", "td.resultContent", "div[class*='job_seen']"],
                "title": ["h2.jobTitle a", "span[title]", ".jobTitle span"],
                "company": ["span.companyName", "[data-testid='company-name']"],
                "location": ["div.companyLocation", "[data-testid='text-location']"],
                "link": ["h2.jobTitle a", "a.jcs-JobTitle"]
            },
            "Glassdoor": {
                "container": ["li[data-test='jobListing']", "article[class*='job-listing']", "li[class*='JobsList']"],
                "title": ["a[data-test='job-title']", ".job-title a", "[class*='JobCard_jobTitle']"],
                "company": ["[data-test='employer-name']", ".employer-name"],
                "location": ["[data-test='emp-location']", ".location"],
                "link": ["a[data-test='job-title']", "a[class*='jobLink']"]
            }
        }

        selectors = SELECTORS.get(portal_name, {})
        containers = selectors.get("container", [])

        cards = []
        for sel in containers:
            cards = soup.select(sel)
            if cards:
                break

        if not cards:
            cards = soup.find_all(["article", "li"], class_=re.compile(r'job|result', re.I))[:20]

        base_urls = {
            "Naukri": "https://www.naukri.com",
            "LinkedIn": "https://www.linkedin.com",
            "Indeed": "https://in.indeed.com",
            "Glassdoor": "https://www.glassdoor.co.in"
        }

        for card in cards[:20]:
            try:
                def get_text(sels):
                    for s in sels:
                        el = card.select_one(s)
                        if el:
                            return el.get_text(strip=True)
                    return ""

                def get_link(sels):
                    for s in sels:
                        el = card.select_one(s)
                        if el:
                            href = el.get("href", "")
                            if href.startswith("http"):
                                return href
                            elif href.startswith("/"):
                                return base_urls.get(portal_name, "") + href
                    return ""

                title = get_text(selectors.get("title", []))
                if not title:
                    continue

                title_lower = title.lower()
                if any(exc in title_lower for exc in self.exclude_keywords):
                    continue

                jobs.append({
                    "title": title,
                    "company": get_text(selectors.get("company", [])),
                    "location": get_text(selectors.get("location", [])),
                    "experience": get_text(selectors.get("experience", [])),
                    "salary": get_text(selectors.get("salary", [])),
                    "date_posted": get_text(selectors.get("date", [])),
                    "apply_link": get_link(selectors.get("link", [])),
                    "portal": portal_name,
                    "relevance": "pending"
                })
            except Exception:
                continue

        return jobs

    async def _filter_relevant_jobs(self, jobs: list) -> list:
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