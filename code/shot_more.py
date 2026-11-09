from playwright.sync_api import sync_playwright
URL = "http://localhost:8502"
SH = "figures/screens"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    # desktop 1440 (warm now)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(15000)
    r = page.evaluate("() => ({n: document.querySelectorAll('[class*=\"st-key-memcard_\"]').length, sw: document.documentElement.scrollWidth, iw: window.innerWidth})")
    print("1440:", r)
    page.screenshot(path=f"{SH}/final_d_home.png", full_page=False, animations="disabled")
    # desktop search view
    page.click('input[placeholder="Search your photos"]')
    page.wait_for_timeout(300)
    page.fill('input[placeholder="Search your photos"]', "sunset boat")
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)
    page.screenshot(path=f"{SH}/final_d_search.png", full_page=False, animations="disabled")
    # ask idle
    page.click('button:text-is("Ask")')
    page.wait_for_timeout(2500)
    page.screenshot(path=f"{SH}/final_d_askidle.png", full_page=False, animations="disabled")
    ctx.close()
    # mobile 390 full journey
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(15000)
    page.screenshot(path=f"{SH}/final_m_home.png", full_page=False, animations="disabled")
    # open ask via floating button
    page.click('button:text-is("Ask")')
    page.wait_for_timeout(3000)
    page.screenshot(path=f"{SH}/final_m_askidle.png", full_page=False, animations="disabled")
    # tap an example chip
    page.click("text=A café in Goa, before the beach")
    page.wait_for_timeout(12000)
    page.screenshot(path=f"{SH}/final_m_ask1.png", full_page=False, animations="disabled")
    print("mobile js errs:", errs[:4])
    ctx.close()
    b.close()
print("done")
