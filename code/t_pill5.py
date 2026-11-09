from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    el = page.locator('.st-key-gpsearchpill [data-testid="stHorizontalBlock"]').first
    h0 = el.evaluate("e => getComputedStyle(e).height")
    page.add_style_tag(content=".st-key-gpsearchpill [data-testid='stHorizontalBlock'] { height: 48px !important; }")
    page.wait_for_timeout(500)
    h1 = el.evaluate("e => getComputedStyle(e).height")
    # also test directly on the element
    el.evaluate("e => e.style.height = '48px'")
    page.wait_for_timeout(300)
    h2 = el.evaluate("e => getComputedStyle(e).height")
    # check parent chain
    chain = el.evaluate("""e => {
      const out = [];
      let p = e.parentElement;
      for (let i = 0; i < 4 && p; i++) {
        const cs = getComputedStyle(p);
        out.push({tag: p.tagName, testid: p.getAttribute('data-testid')||'',
                  h: Math.round(p.getBoundingClientRect().height), disp: cs.display,
                  flexDir: cs.flexDirection, grow: cs.flexGrow, shrink: cs.flexShrink,
                  selfAlign: cs.alignSelf});
        p = p.parentElement;
      }
      return out;
    }""")
    print("h0:", h0, "h1(+important):", h1, "h2(inline):", h2)
    print(json.dumps(chain, indent=1))
    b.close()
