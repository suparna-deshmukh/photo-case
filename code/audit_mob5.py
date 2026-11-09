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
      out.hW = Math.round(h.getBoundingClientRect().width);
      out.hClientW = h.clientWidth;
      out.before = Math.round(h.children[0].getBoundingClientRect().width);
      // strip aspect-ratio from all memcards
      for (const c of document.querySelectorAll('[class*="st-key-memcard_"]')) {
        c.style.aspectRatio = 'auto';
      }
      out.after = Math.round(h.children[0].getBoundingClientRect().width);
      // now give an explicit height instead
      for (const c of document.querySelectorAll('[class*="st-key-memcard_"]')) {
        c.style.height = '150px';
      }
      out.afterH = Math.round(h.children[0].getBoundingClientRect().width);
      return out;
    }
    """)
    print(r)
    b.close()
