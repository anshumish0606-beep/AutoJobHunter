import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/autojobhunter.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.browser_agent import BrowserAgent
from agents.login_agent import LoginAgent
from agents.search_agent import SearchAgent
from agents.scraper_agent import ScraperAgent
from llm.gemini_client import GeminiClient
from output.report_generator import ReportGenerator
from output.notifier import EmailNotifier


def load_config():
    """Load all config files."""
    config_dir = Path("config")

    with open(config_dir / "credentials.json") as f:
        credentials = json.load(f)

    with open(config_dir / "job_roles.json") as f:
        job_config = json.load(f)

    with open(config_dir / "portals.json") as f:
        portals_config = json.load(f)

    return credentials, job_config, portals_config


async def run_portal(portal: dict, credentials: dict, job_config: dict,
                     gemini: GeminiClient, all_jobs: list):
    """Run full job search flow for one portal."""
    portal_name = portal["name"]
    portal_creds = credentials["portals"].get(portal_name, {})

    if not portal_creds.get("username") or portal_creds["username"].startswith("YOUR_"):
        print(f"⚠️ Skipping {portal_name} — credentials not configured")
        return

    # Initialize agents
    browser = BrowserAgent(gemini_client=gemini, headless=True)
    login_agent = LoginAgent(browser_agent=browser)
    search_agent = SearchAgent(browser_agent=browser)
    scraper = ScraperAgent(
        browser_agent=browser,
        gemini_client=gemini,
        target_roles=job_config["roles"]
    )

    try:
        print(f"\n{'='*50}")
        print(f"🚀 Starting {portal_name}...")
        print(f"{'='*50}")

        await browser.start()

        # Step 1: Login
        login_success = await login_agent.login(
            portal_name=portal_name,
            portal_url=portal["login_url"],
            username=portal_creds["username"],
            password=portal_creds["password"]
        )

        if not login_success:
            print(f"❌ Skipping {portal_name} due to login failure")
            return

        # Step 2: Search each job role
        portal_jobs = []

        for role in job_config["roles"][:4]:  # Search top 4 roles
            print(f"\n🔍 Searching: {role}")

            # Search
            search_success = await search_agent.search_jobs(
                portal_name=portal_name,
                keyword=role,
                location="India"
            )

            if not search_success:
                continue

            # Apply filters
            await search_agent.apply_filters(
                portal_name=portal_name,
                filters=job_config["filters"]
            )

            # Scrape results
            jobs = await scraper.scrape_jobs(
                portal_name=portal_name,
                max_pages=2
            )

            portal_jobs.extend(jobs)
            print(f"✅ Found {len(jobs)} relevant jobs for '{role}'")

        # Remove duplicates by title+company
        seen = set()
        unique_jobs = []
        for job in portal_jobs:
            key = f"{job.get('title', '').lower()}_{job.get('company', '').lower()}"
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)

        all_jobs.extend(unique_jobs)
        print(f"\n✅ {portal_name} complete — {len(unique_jobs)} unique jobs collected!")

    except Exception as e:
        logger.error(f"Error on {portal_name}: {e}", exc_info=True)
        print(f"❌ Error on {portal_name}: {str(e)}")

    finally:
        await browser.stop()


async def main():
    """Main orchestrator — runs all portals and generates report."""
    start_time = datetime.now()
    print("\n" + "="*60)
    print("🤖 AutoJobHunter Starting...")
    print(f"⏰ {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Load configs
    try:
        credentials, job_config, portals_config = load_config()
    except FileNotFoundError as e:
        print(f"❌ Config file missing: {e}")
        print("📝 Please fill in config/credentials.json with your details")
        return

    # Check Gemini API key
    gemini_key = credentials.get("gemini_api_key", "")
    if not gemini_key or gemini_key.startswith("YOUR_"):
        print("❌ Please add your Gemini API key to config/credentials.json")
        print("💡 Get free key at: https://aistudio.google.com/app/apikey")
        return

    # Initialize Gemini AI Brain
    gemini = GeminiClient(api_key=gemini_key)

    # Run all portals
    all_jobs = []
    enabled_portals = [p for p in portals_config["portals"] if p.get("enabled")]

    for portal in enabled_portals:
        try:
            await run_portal(portal, credentials, job_config, gemini, all_jobs)
        except Exception as e:
            print(f"❌ Portal {portal['name']} crashed: {e}")
            continue

    if not all_jobs:
        print("\n⚠️ No jobs found. Check your credentials and try again.")
        return

    print(f"\n{'='*60}")
    print(f"📊 TOTAL JOBS COLLECTED: {len(all_jobs)}")
    print(f"{'='*60}")

    # Generate reports
    reporter = ReportGenerator()
    html_path = reporter.generate_html_report(all_jobs)
    excel_path = reporter.generate_excel_report(all_jobs)
    reporter.generate_json_report(all_jobs)

    # Send email
    email_config = credentials.get("email_notification", {})
    if (email_config.get("sender_email") and
            not email_config["sender_email"].startswith("YOUR_")):

        notifier = EmailNotifier(
            sender_email=email_config["sender_email"],
            sender_app_password=email_config["sender_app_password"],
            recipient_email=email_config["recipient"]
        )
        notifier.send_report(all_jobs, html_path, excel_path)
    else:
        print("\n⚠️ Email not configured — report saved locally only")
        print(f"📁 HTML Report: {html_path}")
        print(f"📊 Excel Report: {excel_path}")

    elapsed = (datetime.now() - start_time).seconds // 60
    print(f"\n✅ AutoJobHunter completed in {elapsed} minutes!")
    print(f"📧 Results sent to: anshumish0606@gmail.com")


if __name__ == "__main__":
    asyncio.run(main())
