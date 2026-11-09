from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    # 1) pill text_input with fill
    page.locator('input[placeholder="Search your photos"]').fill("sunset boat")
    page.wait_for_timeout(2500)
    r = page.evaluate("() => !!document.querySelector('.st-key-gpsearchview')")
    print("pill fill -> search view:", r)
    # back home
    page.reload(); page.wait_for_timeout(12000)
    # 2) ask textarea with type()
    page.locator(".st-key-pill_ask_chip button").click(timeout=15000)
    page.wait_for_timeout(2500)
    ta = page.locator("textarea").first
    ta.click()
    ta.type("a cafe somewhere in Goa", delay=30)
    page.wait_for_timeout(3000)
    r = page.evaluate("""() => {
      const d = document.querySelector('#dbgasklen');
      const btn = document.querySelector('.st-key-ask_go button');
      return {dbg: d ? d.textContent : 'NOELEM', disabled: btn ? btn.disabled : 'NOBTN', val: document.querySelector('textarea').value};
    }""")
    print("textarea type ->", r)
    b.close()
