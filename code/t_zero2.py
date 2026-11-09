from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    inp = page.locator('input[placeholder="Search your photos"]')
    inp.click(); page.wait_for_timeout(300)
    inp.fill("zzzqqq"); page.wait_for_timeout(2500)
    page.keyboard.press("Enter"); page.wait_for_timeout(9000)
    r = page.evaluate("""() => {
      let el = null;
      document.querySelectorAll('p').forEach(p => { if ((p.textContent||'').includes('Something went wrong')) el = p; });
      if (!el) return null;
      const chain = [];
      let cur = el, depth = 0;
      while (cur && depth < 10) {
        const cs = getComputedStyle(cur);
        chain.push({tag: cur.tagName, testid: cur.getAttribute('data-testid')||'',
          key: (cur.className||'').toString().slice(0,60),
          disp: cs.display, vis: cs.visibility, op: cs.opacity,
          y: Math.round(cur.getBoundingClientRect().y), h: Math.round(cur.getBoundingClientRect().height)});
        cur = cur.parentElement; depth++;
      }
      return {text: el.textContent.slice(0,120), chain};
    }""")
    import json
    print(json.dumps(r, indent=1))
    b.close()
