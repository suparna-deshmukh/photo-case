from playwright.sync_api import sync_playwright
import sys
URL = "http://localhost:8502"
w = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
JS = """
() => {
  const btns = [...document.querySelectorAll('.st-key-pcell_ [data-testid="stButton"] > button')].slice(0, 30);
  const res = btns.map(b => {
    const cs = getComputedStyle(b);
    return {bg: cs.backgroundImage.slice(0, 80), w: Math.round(b.getBoundingClientRect().width),
            h: Math.round(b.getBoundingClientRect().height), txt: b.innerText.slice(0, 20)};
  });
  const perf = performance.getEntriesByType('resource')
    .filter(r => r.name.includes('/images/')).slice(0, 8)
    .map(r => ({url: r.name.slice(0, 60), size: r.transferSize}));
  return {n: btns.length, res, perf,
          bodyImgs: document.images.length,
          imgsWithW: [...document.images].filter(i => i.naturalWidth > 0).length};
}
"""
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": w, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    r = page.evaluate(JS)
    print("pcell buttons:", r["n"])
    for x in r["res"][:6]:
        print("  ", x)
    print("resource /images/ entries:")
    for p in r["perf"]:
        print("   ", p)
    print("img tags:", r["bodyImgs"], "loaded:", r["imgsWithW"])
    b.close()
