from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h in ((2000, 1100), (1853, 1080)):
        ctx = b.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        page.goto("http://localhost:8502", wait_until="domcontentloaded")
        page.wait_for_timeout(14000)
        r = page.evaluate("""() => {
          const pill = document.querySelector('.st-key-gpsearchpill [data-testid="stHorizontalBlock"]');
          const cs = pill ? getComputedStyle(pill) : null;
          const inp = document.querySelector('.st-key-gpsearchpill input');
          const mic = document.querySelector('.st-key-icb_pill_mic [data-testid="stButton"] > button');
          const memcard = document.querySelector('[class*="st-key-memcard_"]');
          const mcs = memcard ? getComputedStyle(memcard) : null;
          const memimg = memcard ? memcard.querySelector('img') : null;
          const gptop = document.querySelector('.st-key-gptop');
          return {
            pill: cs ? {w: cs.width, h: cs.height, maxw: cs.maxWidth, radius: cs.borderRadius, bg: cs.backgroundColor} : null,
            inpBg: inp ? getComputedStyle(inp).backgroundColor : null,
            micBg: mic ? getComputedStyle(mic).backgroundColor : null,
            micSz: mic ? getComputedStyle(mic).width + 'x' + getComputedStyle(mic).height : null,
            memcard: mcs ? {w: mcs.width, h: mcs.height, ar: mcs.aspectRatio, bg: mcs.backgroundColor} : null,
            memimgSz: memimg ? Math.round(memimg.getBoundingClientRect().width) + 'x' + Math.round(memimg.getBoundingClientRect().height) : null,
            gptopPos: gptop ? getComputedStyle(gptop).position : null
          };
        }""")
        print(w, ":", json.dumps(r))
        page.screenshot(path=f"figures/screens/wide_{w}.png", animations="disabled")
        ctx.close()
    b.close()
