"""
Run this ONCE on your PC to save LinkedIn session cookies.
After this, GitHub Actions will use cookies instead of logging in fresh.
"""
import asyncio
import json
from playwright.async_api import async_playwright

LINKEDIN_EMAIL = "anshumish0606@gmail.com"
LINKEDIN_PASSWORD = "#Linkedin2026!"

async def save_linkedin_cookies():
    print("🍪 LinkedIn Cookie Saver")
    print("="*40)
    print("This will open a VISIBLE browser.")
    print("Login to LinkedIn, then cookies will be saved automatically.")
    print("="*40)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("\n📌 Opening LinkedIn login...")
        await page.goto("https://www.linkedin.com/login")
        await asyncio.sleep(3)

        # Check page type
        content = await page.content()

        if "Welcome back" in content:
            print("📋 Welcome back page — entering password...")
            await page.fill("input[type='password']", LINKEDIN_PASSWORD)
        else:
            print("📧 Normal login page — entering credentials...")
            await page.fill("#username", LINKEDIN_EMAIL)
            await asyncio.sleep(1)
            await page.fill("#password", LINKEDIN_PASSWORD)

        await asyncio.sleep(1)
        await page.click("button[type='submit']")
        await asyncio.sleep(5)

        current_url = page.url

        # Check if verification needed
        if "checkpoint" in current_url or "challenge" in current_url:
            print("\n⚠️ LinkedIn wants verification!")
            print("Please complete the verification in the browser window...")
            print("Waiting 60 seconds for you to complete it...")
            await asyncio.sleep(60)

        # Check login success
        current_url = page.url
        if "feed" in current_url or "mynetwork" in current_url or "jobs" in current_url:
            print("✅ Login successful!")
        else:
            print(f"⚠️ Current URL: {current_url}")
            print("If you're logged in, press Enter to save cookies anyway...")
            input()

        # Save cookies
        cookies = await context.cookies()
        with open("config/linkedin_cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)

        print(f"✅ Saved {len(cookies)} cookies to config/linkedin_cookies.json")
        print("🎉 Done! GitHub Actions will now use these cookies!")

        await browser.close()

asyncio.run(save_linkedin_cookies())
