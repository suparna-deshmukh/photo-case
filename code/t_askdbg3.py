from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(18000)
    page.locator(".st-key-pill_ask_chip button").click(timeout=15000)
    page.wait_for_timeout(2500)
    tas = page.locator("textarea")
    print("n textareas:", tas.count())
    tas.first.fill("a cafe somewhere in Goa, daytime I think")
    for w in (500, 1500, 3000, 5000):
        page.wait_for_timeout(w)
        r = page.evaluate("""() => {
          const ta = document.querySelector('textarea');
          const btn = document.querySelector('.st-key-ask_go button');
          return {val: ta ? ta.value : null, disabled: btn ? btn.disabled : null};
        }""")
        print("after", w, r)
        if r["disabled"] is False:
            break
    b.close()
