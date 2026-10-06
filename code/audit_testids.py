from playwright.sync_api import sync_playwright
import sys
URL = "http://localhost:8502"
w = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
JS = """
() => {
  const out = [];
  const gp = document.querySelector('.st-key-gpmain');
  let el = gp;
  let depth = 0;
  while (el && depth < 8) {
    const cs = getComputedStyle(el);
    out.push({
      testid: el.getAttribute('data-testid') || '-',
      tag: el.tagName,
      w: Math.round(el.getBoundingClientRect().width),
      maxW: cs.maxWidth, disp: cs.display, flexB: cs.flexBasis,
      inlineStyle: el.getAttribute('style') || ''
    });
    el = el.parentElement; depth++;
  }
  return out;
}
"""
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": w, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    for c in page.evaluate(JS):
        print(f"{c['tag']:8s} testid={c['testid']:24s} w={c['w']:5d} maxW={c['maxW']:10s} disp={c['disp']:8s} flexB={c['flexB']:10s} style={c['inlineStyle'][:100]}")
    b.close()
