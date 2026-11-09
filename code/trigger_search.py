from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    inp = page.locator('input[placeholder="Search your photos"]')
    inp.click()
    page.wait_for_timeout(300)
    inp.fill("sunset boat")
    page.wait_for_timeout(2500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(8000)
    r = page.evaluate("""() => ({
      searchView: !!document.querySelector('.st-key-gpsearchview'),
      seg: !!document.querySelector('.st-key-gpseg'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print(r)
    page.screenshot(path="figures/screens/_debug_search.png", full_page=False, animations="disabled")
    b.close()
