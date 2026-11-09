import subprocess, time, os, urllib.request
from playwright.sync_api import sync_playwright

BASE = "/Users/apple/photo_case"
PY = f"{BASE}/.venv/bin/python"
subprocess.run(["pkill", "-f", "streamlit run /tmp/coltest/app.py"], capture_output=True)
time.sleep(2)
logf = open("/tmp/coltest/log.txt", "a")
proc = subprocess.Popen([PY, "-m", "streamlit", "run", "/tmp/coltest/app.py",
                         "--server.headless", "true", "--server.port", "8599"],
                        cwd=BASE, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
for _ in range(30):
    time.sleep(1)
    try:
        urllib.request.urlopen("http://localhost:8599", timeout=3)
        break
    except Exception:
        pass

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w in (390, 480, 600, 768):
        ctx = b.new_context(viewport={"width": w, "height": 844})
        page = ctx.new_page()
        page.goto("http://localhost:8599", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        r = page.evaluate("""
        () => {
          const h = document.querySelector('[data-testid="stHorizontalBlock"]');
          const cs = getComputedStyle(h);
          const kid = h.children[0];
          const kc = getComputedStyle(kid);
          return {hW: Math.round(h.getBoundingClientRect().width), hCSSW: cs.width,
                  gap: cs.gap, wrap: cs.flexWrap,
                  kidW: Math.round(kid.getBoundingClientRect().width),
                  kidFlexBasis: kc.flexBasis, kidWcss: kc.width};
        }
        """)
        print(w, r)
        ctx.close()
    b.close()
proc.terminate()
