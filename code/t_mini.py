from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto("http://localhost:8599", wait_until="domcontentloaded")
    page.wait_for_timeout(10000)
    page.locator("textarea").fill("hello world test")
    page.wait_for_timeout(2500)
    r = page.evaluate("""() => {
      const d = document.querySelector('#dbglen');
      const btn = document.querySelector('button');
      return {dbg: d ? d.textContent : 'NO', disabled: btn ? btn.disabled : 'NO', val: document.querySelector('textarea').value};
    }""")
    print("mini fill:", r)
    b.close()
