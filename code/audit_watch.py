from playwright.sync_api import sync_playwright
import time
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    t0 = time.time()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    while time.time() - t0 < 25:
        try:
            r = page.evaluate("""
            () => {
              const m = document.querySelector('[class*="st-key-memcard_"]');
              const p = document.querySelector('[class*="st-key-pcell_"]');
              if (!m && !p) return {phase: 'empty'};
              const mr = m ? m.getBoundingClientRect() : null;
              const pr = p ? p.getBoundingClientRect() : null;
              const bodyLen = document.body.innerText.length;
              return {mem: mr ? {x: Math.round(mr.x), w: Math.round(mr.width)} : null,
                      pcell: pr ? {x: Math.round(pr.x), w: Math.round(pr.width)} : null,
                      bodyLen,
                      runs: (document.querySelector('[data-testid="stStatusWidget"]') ? 'status' : 'none')};
            }
            """)
            t = time.time() - t0
            print(f"t={t:5.1f}s {r}")
        except Exception as e:
            print(f"t={time.time()-t0:5.1f}s ERR {str(e)[:80]}")
        time.sleep(1.0)
    b.close()
