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
      const all = [...document.querySelectorAll('[class*="st-key-memcard_"]')];
      const pcs = [...document.querySelectorAll('[class*="st-key-pcell_"]')];
      const out = {memN: all.length, pcellN: pcs.length};
      // for each memcard: visible? inside dialog?
      out.mems = all.map(c => {
        const r = c.getBoundingClientRect();
        let inDialog = false, p = c;
        while (p) { if (p.closest && p.closest('[role="dialog"]')) { inDialog = true; break; } p = p.parentElement; }
        const vis = c.offsetParent !== null;
        return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), vis, inDialog};
      });
      // pcells: group by x
      const byX = {};
      pcs.forEach(p => { const x = Math.round(p.getBoundingClientRect().x); byX[x] = (byX[x]||0)+1; });
      out.pcellByX = byX;
      // how many stMain? how many root vertical blocks?
      out.stMainN = document.querySelectorAll('[data-testid="stMain"]').length;
      return out;
    }
    """)
    print(json.dumps(r, indent=1))
    b.close()
