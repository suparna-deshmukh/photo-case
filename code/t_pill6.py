from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    r = page.evaluate("""() => {
      const col2 = document.querySelectorAll('.st-key-gpsearchpill [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]')[1];
      const out = [col2];
      function dump(el, depth) {
        if (!el || depth > 6) return;
        const cs = getComputedStyle(el);
        const rc = el.getBoundingClientRect();
        out.push({d: depth, tag: el.tagName, testid: el.getAttribute('data-testid') || '',
                  h: Math.round(rc.height), disp: cs.display, vis: cs.visibility,
                  pos: cs.position, mt: cs.marginTop, mb: cs.marginBottom,
                  txt: (el.childElementCount === 0 ? (el.textContent || '').slice(0, 20) : '')});
        for (const c of el.children) dump(c, depth + 1);
      }
      dump(col2, 0);
      return out;
    }""")
    print(json.dumps(r, indent=1))
    b.close()
