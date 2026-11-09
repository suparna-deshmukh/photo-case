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
      const out = [];
      for (const ss of document.styleSheets) {
        try {
          const walk = (rules, media) => {
            for (const rule of rules) {
              if (rule.type === CSSRule.MEDIA_RULE) walk(rule.cssRules, rule.conditionText || rule.media.mediaText);
              else if (rule.selectorText && /stColumn|stHorizontalBlock/.test(rule.selectorText)
                       && (rule.style.width || rule.style.flex || rule.style.flexWrap)) {
                out.push({media: media || 'root', sel: rule.selectorText.slice(0, 80),
                          width: rule.style.width || '', flex: rule.style.flex || '',
                          flexBasis: rule.style.flexBasis || '', wrap: rule.style.flexWrap || ''});
              }
            }
          };
          walk(ss.cssRules, null);
        } catch(e) {}
      }
      return out;
    }
    """)
    for x in r:
        print(x)
    b.close()
proc.terminate()
