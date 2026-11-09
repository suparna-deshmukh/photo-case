from playwright.sync_api import sync_playwright
import subprocess, time, urllib.request
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
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto("http://localhost:8599", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    r = page.evaluate("""
    () => {
      const kid = document.querySelector('[data-testid="stColumn"]');
      const out = {cls: kid.className, nss: document.styleSheets.length, total: 0, err: ''};
      const matched = [];
      for (const ss of document.styleSheets) {
        try {
          out.total += ss.cssRules.length;
          for (const rule of ss.cssRules) {
            if (rule.selectorText && rule.style && rule.style.getPropertyValue('width')) {
              try { if (kid.matches(rule.selectorText)) matched.push({s: rule.selectorText.slice(0,60), w: rule.style.getPropertyValue('width'), flex: rule.style.getPropertyValue('flex')}); } catch(e) {}
            }
          }
        } catch(e) { out.err = String(e).slice(0, 60); }
      }
      out.matched = matched;
      const cs = getComputedStyle(kid);
      out.computed = {w: cs.width, flex: cs.flex, flexBasis: cs.flexBasis, disp: cs.display};
      return out;
    }
    """)
    print(r)
    b.close()
proc.terminate()
