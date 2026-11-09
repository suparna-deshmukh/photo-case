from playwright.sync_api import sync_playwright
import time
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    inp = page.locator('input[placeholder="Search your photos"]')
    inp.click()
    page.wait_for_timeout(400)
    inp.type("sunset boat", delay=60)
    page.wait_for_timeout(1000)
    print("after type, view search?", page.evaluate("() => !!document.querySelector('.st-key-gpsearchview')"))
    page.keyboard.press("Enter")
    for t in (2, 5, 9):
        page.wait_for_timeout(3000 if t == 2 else 3000)
        r = page.evaluate("""() => ({
          searchView: !!document.querySelector('.st-key-gpsearchview'),
          seg: !!document.querySelector('.st-key-gpseg'),
          val: document.querySelector('input[placeholder="Search your photos"]').value,
          err: document.body.innerText.includes('Something went wrong')
        })""")
        print(f"t+{t}s:", r)
    page.screenshot(path="figures/screens/_seg3.png", full_page=False, animations="disabled")
    b.close()
