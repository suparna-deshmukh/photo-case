from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    r = page.evaluate("""() => {
      const card = document.querySelector('[class*="st-key-memcard_"]');
      const img = card.querySelector('img');
      const chain = [];
      let el = img;
      while (el) {
        const cs = getComputedStyle(el);
        const rc = el.getBoundingClientRect();
        chain.push({
          tag: el.tagName, testid: el.getAttribute('data-testid') || '',
          cls: (el.className && typeof el.className === 'string') ? el.className.slice(0, 50) : '',
          h: Math.round(rc.height), hCSS: cs.height, disp: cs.display,
          inline: el.getAttribute('style') ? el.getAttribute('style').slice(0, 90) : ''
        });
        if (el === card) break;
        el = el.parentElement;
      }
      return chain.reverse();
    }""")
    print(json.dumps(r, indent=1))
    b.close()
