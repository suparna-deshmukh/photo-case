from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(15000)
    r = page.evaluate("""
    () => {
      const card = document.querySelector('[class*="st-key-memcard_"]');
      if (!card) return {err: 'no memcard'};
      const anc = [];
      let p = card, d = 0;
      while (p && d < 8) {
        const r2 = p.getBoundingClientRect();
        anc.push({t: p.getAttribute('data-testid') || p.tagName,
                  cls: String(p.className).replace(/st-emotion-cache-\\w+/g,'').slice(0,40),
                  w: Math.round(r2.width)});
        p = p.parentElement; d++;
      }
      return anc;
    }
    """)
    for a in r:
        print(a)
    b.close()
