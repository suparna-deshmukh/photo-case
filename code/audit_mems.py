from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(15000)
    r = page.evaluate("""
    () => {
      const out = {rules: 0, totalRules: 0, mem: null};
      for (const ss of document.styleSheets) {
        try { out.totalRules += ss.cssRules.length; } catch(e) { out.rules = -1; }
      }
      const sub = document.querySelector('.gpmem-sub');
      if (sub) {
        const cs = getComputedStyle(sub);
        const meta = sub.parentElement;
        out.mem = {
          whiteSpace: cs.whiteSpace, overflow: cs.overflow, textOverflow: cs.textOverflow,
          fontSize: cs.fontSize, parentW: Math.round(meta.getBoundingClientRect().width),
          subW: Math.round(sub.getBoundingClientRect().width),
          text: sub.innerText, cls: sub.className
        };
      }
      const title = document.querySelector('.gpmem-title');
      if (title) {
        const cs = getComputedStyle(title);
        out.title = {whiteSpace: cs.whiteSpace, text: title.innerText,
                     w: Math.round(title.getBoundingClientRect().width)};
      }
      const card = document.querySelector('[class*="st-key-memcard_"]');
      if (card) {
        const cs = getComputedStyle(card);
        out.card = {w: Math.round(card.getBoundingClientRect().width),
                    h: Math.round(card.getBoundingClientRect().height),
                    aspect: cs.aspectRatio, overflow: cs.overflow,
                    cls: String(card.className).slice(0, 80)};
      }
      return out;
    }
    """)
    print(r)
    b.close()
