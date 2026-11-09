from playwright.sync_api import sync_playwright
import os, time
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(18000)
    page.locator(".st-key-pill_ask_chip button").click(timeout=15000)
    page.wait_for_timeout(2500)
    page.locator('textarea').first.fill("a cafe somewhere in Goa, daytime I think")
    page.wait_for_timeout(500)
    page.locator(".st-key-ask_go button").click(timeout=15000)
    page.wait_for_timeout(12000)
    r = page.evaluate("""() => ({
      askView: !!document.querySelector('[class*="st-key-gpask"], [class*="gpask"]'),
      hasPhrase: document.body.innerText.includes('Something went wrong'),
      results: document.querySelectorAll('[class*="st-key-pcell_"] img').length,
      chips: [...document.querySelectorAll('[class*="gpchip"], [class*="askchip"]')].map(e=>e.innerText.trim()).filter(Boolean).slice(0,8),
      status: (document.body.innerText.match(/\\d+ likely[\\s\\S]{0,40}/)||[''])[0].replace('\\n',' ')
    })""")
    efile = "space_jog/logs_ui_error.txt"
    r["efile"] = open(efile).read().splitlines()[0] if os.path.exists(efile) and os.path.getmtime(efile) > time.time()-120 else None
    print(r)
    page.screenshot(path="figures/screens/_v3_ask.png", full_page=False, animations="disabled")
    b.close()
