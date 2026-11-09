from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(20000)
    r = page.evaluate("""() => {
      const out = [];
      document.querySelectorAll('button').forEach(btn => {
        const t = (btn.innerText || '').trim();
        if (t && t.length < 30) {
          const rc = btn.getBoundingClientRect();
          out.push({t, x: Math.round(rc.x), y: Math.round(rc.y), w: Math.round(rc.width),
                    h: Math.round(rc.height), disp: getComputedStyle(btn).display,
                    vis: getComputedStyle(btn).visibility,
                    covered: (() => { const e = document.elementFromPoint(rc.x + rc.width/2, rc.y + rc.height/2); return e ? (e === btn || btn.contains(e) ? 'self' : e.tagName + '.' + (e.className||'').toString().slice(0,40)) : 'none'; })()});
        }
      });
      return {n: out.length, btns: out.slice(0, 25)};
    }""")
    import json; print(json.dumps(r, indent=1)[:2500])
    b.close()
