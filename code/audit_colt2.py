from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (480, 600, 768):
        ctx = b.new_context(viewport={"width": w, "height": 844})
        page = ctx.new_page()
        page.goto("http://localhost:8599", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        r = page.evaluate("""
        () => {
          const h = document.querySelector('[data-testid="stHorizontalBlock"]');
          const cs = getComputedStyle(h);
          const kid = h.children[0];
          const kc = getComputedStyle(kid);
          return {hW: Math.round(h.getBoundingClientRect().width),
                  hCSSW: cs.width, gap: cs.gap, wrap: cs.flexWrap,
                  kidW: Math.round(kid.getBoundingClientRect().width),
                  kidFlexBasis: kc.flexBasis, kidWcss: kc.width};
        }
        """)
        print(w, r)
        ctx.close()
    b.close()
