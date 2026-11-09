from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    page.screenshot(path="figures/screens/_pre_search.png", full_page=False, animations="disabled")
    page.click('input[placeholder="Search your photos"]', timeout=5000)
    page.wait_for_timeout(500)
    page.fill('input[placeholder="Search your photos"]', "sunset boat")
    page.keyboard.press("Enter")
    page.wait_for_timeout(8000)
    page.screenshot(path="figures/screens/_post_search.png", full_page=False, animations="disabled")
    r = page.evaluate("""
    () => ({
      err: document.body.innerText.includes('Something went wrong'),
      seg: !!document.querySelector('.st-key-gpseg'),
      searchView: !!document.querySelector('.st-key-gpsearchview'),
      btns: [...document.querySelectorAll('button')].map(b => b.innerText.trim()).filter(Boolean).slice(0, 25)
    })
    """)
    print(r)
    b.close()
