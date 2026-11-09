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
      let h = card.parentElement;
      while (h && h.getAttribute('data-testid') !== 'stHorizontalBlock') h = h.parentElement;
      const cs = getComputedStyle(h);
      const kids = [...h.children].map(c => Math.round(c.getBoundingClientRect().width));
      const out = {hW: Math.round(h.getBoundingClientRect().width), wrap: cs.flexWrap, kids};
      // check the memcard's column wrapper chain for extra containers
      const anc = [];
      let p = card.parentElement, d = 0;
      while (p && d < 5) {
        anc.push({t: p.getAttribute('data-testid') || '-', cls: String(p.className).replace(/st-emotion-cache-\\w+/g,'').slice(0,50),
                  w: Math.round(p.getBoundingClientRect().width)});
        p = p.parentElement; d++;
      }
      out.anc = anc;
      return out;
    }
    """)
    print(json.dumps(r, indent=1))
    b.close()
