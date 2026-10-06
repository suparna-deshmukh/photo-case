"""Trace the ancestor chain of gpmain at a given width + find width-forcing descendants."""
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"
w = int(sys.argv[1]) if len(sys.argv) > 1 else 1440

JS = """
() => {
  const gp = document.querySelector('.st-key-gpmain');
  if (!gp) return {err: 'no gpmain'};
  const chain = [];
  let el = gp;
  while (el && el.tagName !== 'HTML') {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    chain.push({
      tag: el.tagName,
      cls: String(el.className).replace(/st-emotion-cache-\\w+/g, '').slice(0, 60),
      w: Math.round(r.width), left: Math.round(r.left),
      pos: cs.position, minW: cs.minWidth, width: cs.width,
      overflow: cs.overflow, overflowX: cs.overflowX,
      marginL: cs.marginLeft, padL: cs.paddingLeft, disp: cs.display
    });
    el = el.parentElement;
  }
  // descendants of gpmain with explicit large widths / min-widths
  const big = [];
  gp.querySelectorAll('*').forEach(d => {
    const cs = getComputedStyle(d);
    if (parseFloat(cs.minWidth) >= 200 || (cs.width !== 'auto' && parseFloat(cs.width) >= 1000)) {
      big.push({tag: d.tagName, cls: String(d.className).replace(/st-emotion-cache-\\w+/g,'').slice(0,70),
                minW: cs.minWidth, w: cs.width, rW: Math.round(d.getBoundingClientRect().width)});
    }
  });
  return {chain, big: big.slice(0, 25)};
}
"""

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": w, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    r = page.evaluate(JS)
    print(f"--- {w}px chain (gpmain -> body) ---")
    for c in r["chain"]:
        print(f"{c['tag']:6s} w={c['w']:5d} L={c['left']:5d} pos={c['pos']:9s} minW={c['minW']:8s} width={c['width']:10s} oX={c['overflowX']:8s} mL={c['marginL']:8s} {c['cls'][:55]}")
    print("--- descendants forcing width ---")
    for d in r["big"]:
        print(f"{d['tag']:6s} minW={d['minW']:8s} w={d['w']:10s} rW={d['rW']:5d}  {d['cls']}")
    b.close()
