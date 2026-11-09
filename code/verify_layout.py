"""Full layout+image verification at multiple widths."""
from playwright.sync_api import sync_playwright
URL = "http://localhost:8502"
SH = "figures/screens"
W = [(1440, 900, "v_d"), (1280, 800, "v_l1280"), (1150, 800, "v_l1150"),
     (1024, 768, "v_t1024"), (900, 800, "v_t900"), (768, 1024, "v_t"), (390, 844, "v_m")]
JS = """
() => {
  const stMain = document.querySelector('[data-testid="stMain"]');
  const out = {
    docSW: document.documentElement.scrollWidth, iw: window.innerWidth,
    mainSW: stMain ? stMain.scrollWidth : -1, mainCW: stMain ? stMain.clientWidth : -1,
    gpmain: null
  };
  const g = document.querySelector('.st-key-gpmain');
  if (g) { const r = g.getBoundingClientRect();
    out.gpmain = {l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width)}; }
  const pcellImgs = [...document.querySelectorAll('[class*="st-key-pcell_"] img')];
  out.cells = {n: pcellImgs.length,
    loaded: pcellImgs.filter(i => i.naturalWidth > 0 && i.getBoundingClientRect().width > 5).length,
    zero: pcellImgs.filter(i => i.getBoundingClientRect().width <= 5).length};
  const memImgs = [...document.querySelectorAll('[class*="st-key-memcard_"] img')];
  out.mems = {n: memImgs.length, loaded: memImgs.filter(i => i.naturalWidth > 0).length};
  out.err = document.body.innerText.includes('Something went wrong');
  return out;
}
"""
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h, tag in W:
        ctx = b.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(15000)
        r = page.evaluate(JS)
        hor = "HORIZ-SCROLL!" if (r["docSW"] > r["iw"] or r["mainSW"] > r["mainCW"] + 1) else "locked"
        gm = r["gpmain"]
        gmok = "n/a (mobile)" if gm is None else ("ok" if gm["r"] <= w + 2 else f"OVERFLOWS r={gm['r']}>{w}")
        print(f"{tag} {w}x{h}: {hor} | gpmain {gmok} {gm} | cells {r['cells']} | mems {r['mems']} | err={r['err']} js={errs[:2]}")
        page.screenshot(path=f"{SH}/{tag}_home.png", full_page=False, animations="disabled")
        ctx.close()
    b.close()
print("done")
