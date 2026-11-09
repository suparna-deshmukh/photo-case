from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(15000)
    r = page.evaluate("""
    () => {
      const out = {};
      const card = document.querySelector('[class*="st-key-memcard_"]');
      let h = card.parentElement;
      while (h && h.getAttribute('data-testid') !== 'stHorizontalBlock') h = h.parentElement;
      out.before = [...h.children].map(c => Math.round(c.getBoundingClientRect().width));
      h.style.width = '100%';
      out.afterWidth100 = [...h.children].map(c => Math.round(c.getBoundingClientRect().width));
      // also test: what does the top bar horizontal block look like?
      const tb = document.querySelector('.st-key-gptopm');
      if (tb) {
        const h2 = tb.querySelector('[data-testid="stHorizontalBlock"]');
        if (h2) {
          const cs = getComputedStyle(h2);
          out.topbar = {w: Math.round(h2.getBoundingClientRect().width),
            csW: cs.width, csFlex: cs.flex, csAlignSelf: cs.alignSelf,
            kids: [...h2.children].map(c => Math.round(c.getBoundingClientRect().width))};
        }
      }
      const csh = getComputedStyle(h);
      out.hCS = {w: csh.width, flex: csh.flex, alignSelf: csh.alignSelf,
                 minWidth: csh.minWidth, maxWidth: csh.maxWidth};
      return out;
    }
    """)
    print(r)
    b.close()
