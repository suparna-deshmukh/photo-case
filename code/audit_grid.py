from playwright.sync_api import sync_playwright
URL = "http://localhost:8502"
JS = """
() => {
  const all = [...document.querySelectorAll('div')].filter(d => String(d.className).includes('st-key-pcell_'));
  const btns = all.slice(0, 40).map(d => d.querySelector('[data-testid="stButton"] > button'));
  const info = btns.filter(Boolean).slice(0, 5).map(b => {
    const cs = getComputedStyle(b);
    const r = b.getBoundingClientRect();
    return {bg: cs.backgroundImage.slice(0, 70), w: Math.round(r.width), h: Math.round(r.height),
            fs: cs.fontSize, txt: b.innerText.slice(0, 30)};
  });
  return {containers: all.length, info};
}
"""
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    r = page.evaluate(JS)
    print("pcell containers:", r["containers"])
    for x in r["info"]:
        print("  ", x)
    # element screenshot of the first grid
    g = page.locator('[class*="gpgrid"]').first
    if g.count():
        g.screenshot(path="figures/screens/_grid_zoom.png")
        print("grid shot saved")
    b.close()
