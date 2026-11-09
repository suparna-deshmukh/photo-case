from playwright.sync_api import sync_playwright
import subprocess, time, urllib.request, json
BASE = "/Users/apple/photo_case"; PY = f"{BASE}/.venv/bin/python"
subprocess.run(["pkill", "-f", "streamlit run /tmp/coltest/app.py"], capture_output=True)
time.sleep(2)
logf = open("/tmp/coltest/log.txt", "a")
proc = subprocess.Popen([PY, "-m", "streamlit", "run", "/tmp/coltest/app.py",
                         "--server.headless", "true", "--server.port", "8599"],
                        cwd=BASE, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
for _ in range(30):
    time.sleep(1)
    try:
        urllib.request.urlopen("http://localhost:8599", timeout=3); break
    except Exception: pass

JS = """
() => {
  const kid = document.querySelector('[data-testid="stColumn"]');
  const out = [];
  for (const ss of document.styleSheets) {
    try {
      for (const rule of ss.cssRules) {
        const collect = (r, media) => {
          if (r.type === CSSRule.MEDIA_RULE) { r.cssRules.forEach(x => collect(x, r.conditionText)); return; }
          if (r.selectorText) {
            try { if (kid.matches(r.selectorText)) out.push({m: media || 'root', s: r.selectorText.slice(0, 60),
              css: r.style.cssText.slice(0, 150)}); } catch(e) {}
          }
        };
        collect(rule, null);
      }
    } catch(e) {}
  }
  return out;
}
"""
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (390, 768):
        ctx = b.new_context(viewport={"width": w, "height": 844})
        page = ctx.new_page()
        page.goto("http://localhost:8599", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        r = page.evaluate(JS)
        print(f"===== {w}px =====")
        for x in r:
            print(f"[{x['m']}] {x['s']}\n    {x['css']}")
        ctx.close()
    b.close()
proc.terminate()
