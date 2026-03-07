"""
Debug Naukri login page — finds exact selectors.
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded")
        await asyncio.sleep(5)

        inputs = await page.query_selector_all("input:not([type='hidden'])")
        print(f"\n📋 Naukri Input fields ({len(inputs)}):")
        for i, inp in enumerate(inputs):
            t = await inp.get_attribute("type") or "text"
            id_ = await inp.get_attribute("id") or ""
            name_ = await inp.get_attribute("name") or ""
            ph = await inp.get_attribute("placeholder") or ""
            cls = await inp.get_attribute("class") or ""
            print(f"  [{i}] type={t} | id={id_} | name={name_} | placeholder={ph} | class={cls[:40]}")

        await browser.close()

asyncio.run(main())