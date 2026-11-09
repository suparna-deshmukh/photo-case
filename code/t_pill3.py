from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    r = page.evaluate("""() => {
      const blocks = [...document.querySelectorAll('.st-key-gpsearchpill [data-testid="stHorizontalBlock"]')];
      return blocks.map(el => {
        const cs = getComputedStyle(el);
        const rc = el.getBoundingClientRect();
        return {n: el.children.length, inline: el.getAttribute('style'),
                h: Math.round(rc.height), hCSS: cs.height, minH: cs.minHeight,
                alignItems: cs.alignItems, pad: cs.padding, box: cs.boxSizing};
      });
    }""")
    print(json.dumps(r, indent=1))
    b.close()
