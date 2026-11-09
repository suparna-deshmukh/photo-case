from playwright.sync_api import sync_playwright
URL = "http://localhost:8502"
SH = "figures/screens"
W = [(1440, 900, "w_d"), (1280, 800, "w_l1280"), (1150, 800, "w_l1150"),
     (1024, 768, "w_t1024"), (900, 800, "w_t900"), (768, 1024, "w_t"), (390, 844, "w_m")]
JS = """
() => {
  const stMain = document.querySelector('[data-testid="stMain"]');
  const out = {docSW: document.documentElement.scrollWidth, iw: window.innerWidth,
               mainSW: stMain ? stMain.scrollWidth : -1, mainCW: stMain ? stMain.clientWidth : -1};
  const g = document.querySelector('.st-key-gpmain');
  out.gm = g ? Math.round(g.getBoundingClientRect().right) : null;
  const cards = [...document.querySelectorAll('[class*="st-key-memcard_"]')].map(c => {
    const r = c.getBoundingClientRect();
    return {w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.left), y: Math.round(r.top)};
  });
  out.cards = cards;
  out.rows = {};
  cards.forEach(c => { const k = Math.round(c.y / 40); out.rows[k] = (out.rows[k] || 0) + 1; });
  const sub = document.querySelector('.gpmem-sub');
  if (sub) { const r = sub.getBoundingClientRect();
    out.sub = {w: Math.round(r.width), lines: Math.round(r.height / 16), text: sub.innerText}; }
  const imgs = [...document.querySelectorAll('[class*="st-key-pcell_"] img')];
  out.cells = {n: imgs.length, ok: imgs.filter(i => i.naturalWidth > 0 && i.getBoundingClientRect().width > 5).length};
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
        hor = "HORIZ!" if (r["docSW"] > r["iw"] or r["mainSW"] > r["mainCW"] + 1) else "lock"
        gm = "n/a" if r["gm"] is None else ("ok" if r["gm"] <= w + 2 else f"OVER {r['gm']}>{w}")
        print(f"{tag} {w}x{h}: {hor} gpmainR {gm} | memcard rows {r['rows']} | card0 {r['cards'][0] if r['cards'] else None} | sub {r.get('sub')} | cells {r['cells']} | err={r['err']} js={errs[:2]}")
        page.screenshot(path=f"{SH}/{tag}_home.png", full_page=False, animations="disabled")
        ctx.close()
    b.close()
print("done")
