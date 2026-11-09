from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    page.locator(".st-key-pill_ask_chip button").click(timeout=15000)
    page.wait_for_timeout(2500)
    r = page.evaluate("""() => {
      const ta = document.querySelector('textarea');
      const chain = [];
      let cur = ta, d = 0;
      while (cur && d < 8) {
        chain.push(cur.tagName + (cur.getAttribute('data-testid') ? '['+cur.getAttribute('data-testid')+']' : '') + (cur.id ? '#'+cur.id : '') + (cur.className && typeof cur.className === 'string' ? '.'+cur.className.split(' ')[0] : ''));
        cur = cur.parentElement; d++;
      }
      // find the streamlit root
      const root = document.querySelector('#root > div, [data-testid="stMain"]');
      const inMain = !!ta.closest('[data-testid="stMain"]');
      const shadow = (() => { let p = ta.parentElement; while (p) { if (p instanceof HTMLIFrameElement) return true; p = p.parentElement; } return false; })();
      return {chain, inMain, shadow, html: ta.outerHTML.slice(0, 200)};
    }""")
    import json; print(json.dumps(r, indent=1))
    b.close()
