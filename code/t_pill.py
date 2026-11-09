from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h in ((1440, 900), (1600, 1000), (1800, 1000), (2000, 1100)):
        ctx = b.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        page.goto("http://localhost:8502", wait_until="domcontentloaded")
        page.wait_for_timeout(12000)
        r = page.evaluate("""() => {
          const pill = document.querySelector('.st-key-gpsearchpill [data-testid="stHorizontalBlock"]');
          const cs = pill ? getComputedStyle(pill) : null;
          const inner = document.querySelector('.st-key-wr_02 [data-testid="stHorizontalBlock"]');
          const ics = inner ? getComputedStyle(inner) : null;
          const memimg = document.querySelector('[class*="st-key-memcard_"] img');
          const mcs = memimg ? getComputedStyle(memimg) : null;
          return {
            pillH: cs ? cs.height : null, pillW: cs ? cs.width : null,
            innerW: ics ? ics.width : null, innerH: ics ? ics.height : null,
            imgW: mcs ? mcs.width : null, imgH: mcs ? mcs.height : null, imgPos: mcs ? mcs.objectFit : null
          };
        }""")
        print(w, json.dumps(r))
        ctx.close()
    b.close()
