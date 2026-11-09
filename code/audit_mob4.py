from playwright.sync_api import sync_playwright
import json
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
      const kid = h.children[0];
      const out = {kidStyleAttr: kid.getAttribute('style')};
      const rules = [];
      for (const ss of document.styleSheets) {
        try {
          for (const rule of ss.cssRules) {
            if (!rule.selectorText || !rule.style) continue;
            let m = false;
            try { m = kid.matches(rule.selectorText); } catch(e) { continue; }
            if (m) {
              const props = ['flex','flex-basis','flex-grow','flex-shrink','width','min-width','display'];
              const rel = props.filter(p => rule.style.getPropertyValue(p));
              if (rel.length) {
                const o = {sel: rule.selectorText.slice(0, 100)};
                rel.forEach(p => { o[p] = rule.style.getPropertyValue(p); });
                rules.push(o);
              }
            }
          }
        } catch(e) {}
      }
      out.rules = rules;
      return out;
    }
    """)
    print(json.dumps(r, indent=1))
    b.close()
