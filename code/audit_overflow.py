"""Audit horizontal overflow at multiple widths; report offending elements."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"
W = [(1440, 900), (1280, 800), (1150, 800), (1024, 768), (900, 800), (768, 1024), (390, 844)]

JS = """
() => {
  const out = {sw: document.documentElement.scrollWidth, iw: window.innerWidth, bad: []};
  const iw = window.innerWidth;
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > iw + 2 && r.left < iw) {
      const cs = getComputedStyle(el);
      if (cs.overflowX === 'auto' || cs.overflowX === 'scroll') return; // its own scroller
      out.bad.push({
        tag: el.tagName, cls: (el.className && el.className.baseVal !== undefined) ? 'svg' : String(el.className).slice(0, 90),
        left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width),
        txt: (el.innerText || '').trim().slice(0, 40)
      });
    }
  });
  // keep only the deepest offenders
  out.bad.sort((a, b) => b.right - a.right);
  out.bad = out.bad.slice(0, 12);
  return out;
}
"""

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h in W:
        ctx = b.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(14000)
        r = page.evaluate(JS)
        flag = "OVERFLOW" if r["sw"] > r["iw"] else "ok"
        print(f"== {w}x{h} scrollWidth={r['sw']} innerWidth={r['iw']} -> {flag}")
        for e in r["bad"][:8]:
            print(f"   {e['tag']:6s} L={e['left']:5d} R={e['right']:5d} W={e['w']:5d}  {e['cls'][:70]}  {e['txt'][:30]!r}")
        ctx.close()
    b.close()
