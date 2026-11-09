from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(15000)
    r = page.evaluate("""
    () => {
      const grid = document.querySelector('.gpmem-grid');
      const out = {gridKids: 0, gridParent: null};
      if (grid) {
        out.gridKids = grid.children.length;
        out.gridHTML = grid.outerHTML.slice(0, 200);
        out.gridParent = grid.parentElement ? grid.parentElement.className.slice(0, 80) : null;
      }
      const card = document.querySelector('[class*="st-key-memcard_"]');
      if (card) {
        out.cardParent = card.parentElement.className.slice(0, 80);
        out.cardGrand = card.parentElement.parentElement.className.slice(0, 80);
      }
      // where is the closing </div> markdown?
      const mds = [...document.querySelectorAll('[data-testid="stMarkdown"]')].map(m => m.innerText.slice(0, 30));
      out.mdSample = mds.slice(0, 10);
      return out;
    }
    """)
    print(r)
    b.close()
