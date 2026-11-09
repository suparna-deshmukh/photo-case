from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (390, 1440):
        ctx = b.new_context(viewport={"width": w, "height": 844})
        page = ctx.new_page()
        page.goto("http://localhost:8599", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        r = page.evaluate("""
        () => [...document.querySelectorAll('[data-testid="stColumn"]')].map(c => {
          const r = c.getBoundingClientRect();
          return {x: Math.round(r.x), w: Math.round(r.width)};
        })
        """)
        print(w, r)
        ctx.close()
    b.close()
