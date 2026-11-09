import subprocess, time, urllib.request
from playwright.sync_api import sync_playwright
BASE = "/Users/apple/photo_case"; PY = f"{BASE}/.venv/bin/python"
subprocess.run(["pkill", "-f", "streamlit run /tmp/coltest/frag_test.py"], capture_output=True)
time.sleep(2)
logf = open("/tmp/coltest/dlg.log", "a")
proc = subprocess.Popen([PY, "-m", "streamlit", "run", "/tmp/coltest/frag_test.py",
                         "--server.headless", "true", "--server.port", "8599"],
                        cwd=BASE, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
for _ in range(30):
    time.sleep(1)
    try:
        urllib.request.urlopen("http://localhost:8599", timeout=3); break
    except Exception: pass
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 900, "height": 800})
    page = ctx.new_page()
    page.goto("http://localhost:8599", wait_until="domcontentloaded")
    page.wait_for_timeout(6000)
    txt = page.inner_text("body")
    print(txt[:400])
    b.close()
proc.terminate()
