from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    def dbg():
        r = page.evaluate("""() => {
          const d = document.querySelector('#dbgasklen');
          const btn = document.querySelector('.st-key-ask_go button');
          return {dbg: d ? d.textContent : 'NOELEM', disabled: btn ? btn.disabled : 'NOBTN'};
        }""")
        return r
    print("idle:", dbg())
    page.locator(".st-key-pill_ask_chip button").click(timeout=15000)
    page.wait_for_timeout(2500)
    print("ask idle:", dbg())
    page.locator("textarea").first.fill("a cafe somewhere in Goa")
    for w in (1000, 2000, 3000):
        page.wait_for_timeout(w)
        print("after fill", w, dbg())
    b.close()
