from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    r = page.evaluate("""() => {
      const outer = document.querySelector('.st-key-gpsearchpill > [data-testid="stHorizontalBlock"], .st-key-gpsearchpill [data-testid="stHorizontalBlock"]');
      const out = {};
      function desc(el) {
        const cs = getComputedStyle(el);
        const rc = el.getBoundingClientRect();
        return {tag: el.tagName, testid: el.getAttribute('data-testid')||'',
          cls: (el.className||'').toString().slice(0, 60),
          disp: cs.display, dir: cs.flexDirection, wrap: cs.flexWrap,
          w: Math.round(rc.width), h: Math.round(rc.height),
          hCSS: cs.height, basis: cs.flexBasis};
      }
      out.outer = outer ? desc(outer) : null;
      out.children = outer ? [...outer.children].map(desc) : [];
      // find input
      const inp = document.querySelector('.st-key-gpsearchpill input');
      out.inp = inp ? {h: getComputedStyle(inp).height, w: getComputedStyle(inp).width,
                        box: Math.round(inp.getBoundingClientRect().width) + 'x' + Math.round(inp.getBoundingClientRect().height),
                        parentBox: Math.round(inp.parentElement.getBoundingClientRect().width) + 'x' + Math.round(inp.parentElement.getBoundingClientRect().height)} : null;
      return out;
    }""")
    print(json.dumps(r, indent=1)[:3000])
    b.close()
