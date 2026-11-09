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
      const out = {hstyle: h.getAttribute('style'), hcls: h.className};
      out.kids = [...h.children].slice(0, 3).map(c => ({
        style: c.getAttribute('style'), w: Math.round(c.getBoundingClientRect().width),
        disp: getComputedStyle(c).display, flexB: getComputedStyle(c).flexBasis,
        maxW: getComputedStyle(c).maxWidth}));
      // is h inside any gpgrid/gpmem-grid div?
      out.ancestors = [];
      let p = h.parentElement, d = 0;
      while (p && d < 5) { out.ancestors.push((p.getAttribute('data-testid')||'') + '.' + String(p.className).replace(/st-emotion-cache-\\w+/g,'').slice(0,40)); p = p.parentElement; d++; }
      return out;
    }
    """)
    print(r)
    b.close()
