from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(20000)
    r = page.evaluate("""
    () => {
      const cards = [...document.querySelectorAll('[class*="st-key-memcard_"]')].map(c => {
        const r = c.getBoundingClientRect();
        return {x: Math.round(r.x), y: Math.round(r.y + window.scrollY), w: Math.round(r.width)};
      });
      return {cards, scrollY: window.scrollY, docH: document.body.scrollHeight};
    }
    """)
    print(r)
    page.screenshot(path="figures/screens/_mob_now.png", full_page=True, animations="disabled")
    b.close()
