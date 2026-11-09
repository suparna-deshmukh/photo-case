from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(15000)
    r = page.evaluate("""
    () => {
      const card = document.querySelector('[class*="st-key-memcard_"]');
      const out = {chain: []};
      let el = card, d = 0;
      while (el && d < 7) {
        const cs = getComputedStyle(el);
        const r2 = el.getBoundingClientRect();
        out.chain.push({tid: el.getAttribute('data-testid') || '-', w: Math.round(r2.width),
          disp: cs.display, flexWrap: cs.flexWrap, flexDir: cs.flexDirection,
          cls: String(el.className).replace(/st-emotion-cache-\\w+/g,'').slice(0,50)});
        el = el.parentElement; d++;
      }
      // find the columns container (stHorizontalBlock) ancestor
      let h = card.parentElement;
      while (h && h.getAttribute('data-testid') !== 'stHorizontalBlock') h = h.parentElement;
      if (h) {
        const cs = getComputedStyle(h);
        out.horiz = {w: Math.round(h.getBoundingClientRect().width), disp: cs.display,
                     flexWrap: cs.flexWrap, kids: h.children.length,
                     kidWs: [...h.children].slice(0,4).map(c => Math.round(c.getBoundingClientRect().width))};
      }
      return out;
    }
    """)
    print(r)
    b.close()
