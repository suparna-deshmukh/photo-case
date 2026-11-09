from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(20000)
    r = page.evaluate("""
    () => {
      const probe = (h) => {
        if (!h) return null;
        const cs = getComputedStyle(h);
        return {w: Math.round(h.getBoundingClientRect().width), disp: cs.display,
                wrap: cs.flexWrap, dir: cs.flexDirection, gap: cs.gap,
                wCSS: cs.width, minW: cs.minWidth, maxW: cs.maxWidth,
                kids: [...h.children].slice(0,4).map(c => Math.round(c.getBoundingClientRect().width))};
      };
      const out = {};
      // memory columns
      const mc = document.querySelector('[class*="st-key-memcard_"]');
      let h1 = mc.parentElement;
      while (h1 && h1.getAttribute('data-testid') !== 'stHorizontalBlock') h1 = h1.parentElement;
      out.memory = probe(h1);
      // photo grid columns (find a pcell, walk up to stHorizontalBlock)
      const pc = document.querySelector('[class*="st-key-pcell_"]');
      let h2 = pc.parentElement;
      while (h2 && h2.getAttribute('data-testid') !== 'stHorizontalBlock') h2 = h2.parentElement;
      out.photo = probe(h2);
      // ancestors of each
      const anc = (h, n) => {
        const a = [];
        let p = h.parentElement, d = 0;
        while (p && d < n) {
          const cs = getComputedStyle(p);
          a.push({t: p.getAttribute('data-testid') || '-',
            w: Math.round(p.getBoundingClientRect().width),
            disp: cs.display, flex: cs.flex, alignSelf: cs.alignSelf, overflow: cs.overflow});
          p = p.parentElement; d++;
        }
        return a;
      };
      out.memoryAnc = anc(h1, 4);
      out.photoAnc = anc(h2, 4);
      return out;
    }
    """)
    print(json.dumps(r, indent=1))
    b.close()
