from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(20000)
    r = page.evaluate("""
    () => {
      const out = {};
      const pcs = [...document.querySelectorAll('[class*="st-key-pcell_"]')].slice(0, 9).map(p => {
        const r = p.getBoundingClientRect();
        const col = p.closest('[data-testid="stColumn"]');
        const cr = col ? col.getBoundingClientRect() : null;
        return {px: Math.round(r.x), py: Math.round(r.y), pw: Math.round(r.width),
                cx: cr ? Math.round(cr.x) : null, cw: cr ? Math.round(cr.width) : null,
                cy: cr ? Math.round(cr.y) : null};
      });
      out.pcs = pcs;
      const mcs = [...document.querySelectorAll('[class*="st-key-memcard_"]')].slice(0, 6).map(p => {
        const r = p.getBoundingClientRect();
        const col = p.closest('[data-testid="stColumn"]');
        const cr = col ? col.getBoundingClientRect() : null;
        return {mx: Math.round(r.x), my: Math.round(r.y), mw: Math.round(r.width),
                cx: cr ? Math.round(cr.x) : null, cw: cr ? Math.round(cr.width) : null,
                cy: cr ? Math.round(cr.y) : null};
      });
      out.mcs = mcs;
      return out;
    }
    """)
    print(json.dumps(r, indent=1))
    b.close()
