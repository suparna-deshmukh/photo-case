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
      let h = card.parentElement;
      while (h && h.getAttribute('data-testid') !== 'stHorizontalBlock') h = h.parentElement;
      const out = {};
      const cs = getComputedStyle(h);
      out.before = {wrap: cs.flexWrap, gap: cs.gap, dir: cs.flexDirection,
                    kidW: Math.round(h.children[0].getBoundingClientRect().width)};
      // which CSS rules set flex-wrap on h?
      const rules = [];
      for (const ss of document.styleSheets) {
        try {
          for (const rule of ss.cssRules) {
            if (rule.selectorText && rule.style && rule.style.flexWrap &&
                rule.style.flexWrap.includes('wrap') && h.matches(rule.selectorText)) {
              rules.push(rule.selectorText.slice(0, 90) + ' => ' + rule.style.flexWrap);
            }
          }
        } catch(e) {}
      }
      out.matchingWrapRules = rules;
      h.style.flexWrap = 'nowrap';
      out.afterNowrap = {kidW: Math.round(h.children[0].getBoundingClientRect().width),
                         kidW2: Math.round(h.children[1].getBoundingClientRect().width)};
      return out;
    }
    """)
    print(r)
    b.close()
