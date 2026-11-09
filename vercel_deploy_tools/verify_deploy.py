import asyncio
import json
import re
import sys

from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://space-jog.vercel.app"
OUT = "/tmp/jog_verify"

import os
os.makedirs(OUT, exist_ok=True)

EXAMPLE = "A caf\u00e9 in Goa, before the beach"

async def wait_home(page, timeout_ms):
    await page.wait_for_selector(
        'button:has-text("Collections"), button:has-text("Photos")',
        timeout=timeout_ms,
    )
    await page.wait_for_timeout(2500)

async def main():
    result = {"url": URL, "console_errors": [], "page_errors": [], "steps": {}}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ---------- desktop 1440x900: home + full Ask flow ----------
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        page.on("console", lambda m: result["console_errors"].append(m.text[:300]) if m.type == "error" else None)
        page.on("pageerror", lambda e: result["page_errors"].append(str(e)[:300]))

        await page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        try:
            await wait_home(page, 300000)  # cold start may download CLIP model
            result["steps"]["home_1440"] = "ok"
            imgs = await page.locator("img").count()
            result["steps"]["home_1440_imgs"] = imgs
            await page.screenshot(path=f"{OUT}/home_1440.png")
        except Exception as e:
            result["steps"]["home_1440"] = f"FAIL: {str(e)[:200]}"
            await page.screenshot(path=f"{OUT}/home_1440_fail.png")

        # Ask Photos flow
        try:
            ask_btn = page.get_by_role("button", name="Ask Photos", exact=True)
            await ask_btn.wait_for(timeout=30000)
            await ask_btn.click()
            chip = page.get_by_role("button", name=EXAMPLE, exact=True)
            await chip.wait_for(timeout=30000)
            privacy = await page.locator(".gpasskprivacy").inner_text(timeout=10000)
            result["mode_line"] = privacy.strip()
            await page.screenshot(path=f"{OUT}/ask_view.png")
            await chip.click()
            result["steps"]["ask_example_clicked"] = "ok"
            open_btn = page.get_by_role("button", name=re.compile(r"^Open photo from"))
            await open_btn.wait_for(timeout=180000)
            result["steps"]["ask_results"] = f"ok ({await open_btn.count()} photos)"
            await page.screenshot(path=f"{OUT}/ask_results.png")
            await open_btn.first.click()
            await page.wait_for_selector(".gplb", timeout=60000)
            result["steps"]["lightbox"] = "ok"
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"{OUT}/lightbox.png")
        except Exception as e:
            result["steps"]["ask_flow"] = f"FAIL: {str(e)[:200]}"
            await page.screenshot(path=f"{OUT}/ask_flow_fail.png")
        await ctx.close()

        # ---------- mobile 390x844: home ----------
        ctx = await browser.new_context(viewport={"width": 390, "height": 844})
        page = await ctx.new_page()
        page.on("console", lambda m: result["console_errors"].append(m.text[:300]) if m.type == "error" else None)
        page.on("pageerror", lambda e: result["page_errors"].append(str(e)[:300]))
        await page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        try:
            await wait_home(page, 120000)
            result["steps"]["home_390"] = "ok"
            await page.screenshot(path=f"{OUT}/home_390.png")
        except Exception as e:
            result["steps"]["home_390"] = f"FAIL: {str(e)[:200]}"
            await page.screenshot(path=f"{OUT}/home_390_fail.png")
        await ctx.close()

        await browser.close()

    print(json.dumps(result, indent=2, ensure_ascii=False))

asyncio.run(main())
