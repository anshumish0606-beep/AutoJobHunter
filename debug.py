"""
Debug script — opens browser visibly and prints all input fields found on login pages.
Run this to find correct selectors for each portal.
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_portal(name, url):
    print(f"\n{'='*50}")
    print(f"🔍 Debugging: {name}")
    print(f"{'='*50}")

    async with async_playwright() as p:
        # Run VISIBLE so you can see what's happening
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)  # Wait for page to fully load

        # Find ALL input fields on page
        inputs = await page.query_selector_all("input")
        print(f"\n📋 Found {len(inputs)} input fields:")
        for i, inp in enumerate(inputs):
            inp_type = await inp.get_attribute("type") or "text"
            inp_id = await inp.get_attribute("id") or ""
            inp_name = await inp.get_attribute("name") or ""
            inp_placeholder = await inp.get_attribute("placeholder") or ""
            inp_class = await inp.get_attribute("class") or ""
            print(f"  [{i}] type={inp_type} | id={inp_id} | name={inp_name} | placeholder={inp_placeholder} | class={inp_class[:40]}")

        # Find ALL buttons
        buttons = await page.query_selector_all("button, input[type='submit']")
        print(f"\n🖱️ Found {len(buttons)} buttons:")
        for i, btn in enumerate(buttons):
            btn_type = await btn.get_attribute("type") or ""
            btn_text = await btn.inner_text() or ""
            btn_class = await btn.get_attribute("class") or ""
            print(f"  [{i}] type={btn_type} | text={btn_text[:30]} | class={btn_class[:40]}")

        await browser.close()

async def main():
    portals = [
        ("Naukri", "https://www.naukri.com/nlogin/login"),
        ("LinkedIn", "https://www.linkedin.com/login"),
    ]

    for name, url in portals:
        await debug_portal(name, url)

asyncio.run(main())