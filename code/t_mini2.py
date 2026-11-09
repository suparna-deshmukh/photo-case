from playwright.sync_api import sync_playwright
import time
def state(page):
    return page.evaluate("""() => {
      const d = document.querySelector('#dbglen');
      const btns = [...document.querySelectorAll('button')].filter(b => (b.textContent||'').trim() === 'Go');
      return {dbg: d ? d.textContent : 'NO', go: btns[0] ? btns[0].disabled : 'NOBTN',
              val: document.querySelector('textarea').value};
    }""")
with sync_playwright() as pw:
    b = pw.chromium.launch()
    # A: fill + 6s
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto("http://localhost:8599", wait_until="domcontentloaded")
    page.wait_for_timeout(10000)
    page.locator("textarea").fill("hello world test")
    page.wait_for_timeout(6000)
    print("A fill+6s:", state(page))
    ctx.close()
    # B: type real keys + 4s
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto("http://localhost:8599", wait_until="domcontentloaded")
    page.wait_for_timeout(10000)
    page.locator("textarea").type("hello world test", delay=20)
    page.wait_for_timeout(4000)
    print("B type+4s:", state(page))
    ctx.close()
    # C: type + blur + 4s
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto("http://localhost:8599", wait_until="domcontentloaded")
    page.wait_for_timeout(10000)
    page.locator("textarea").type("hello world test", delay=20)
    page.keyboard.press("Tab")
    page.wait_for_timeout(4000)
    print("C type+blur+4s:", state(page))
    b.close()
