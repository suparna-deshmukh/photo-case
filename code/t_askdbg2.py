from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(18000)
    r = page.evaluate("""() => {
      const btns = [...document.querySelectorAll('button')].filter(b => (b.innerText||'').trim() === 'Ask');
      return btns.map(b => b.outerHTML.slice(0, 300));
    }""")
    for h in r: print(h, "\n----")
    # try candidate selectors
    for sel in ['button[aria-label="Ask"]', '[data-testid="stButton"]:has(button:has-text("Ask"))']:
        try:
            n = page.locator(sel).count()
            print(sel, "count:", n)
        except Exception as e:
            print(sel, "ERR", str(e)[:80])
    b.close()
