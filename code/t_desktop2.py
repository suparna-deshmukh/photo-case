from playwright.sync_api import sync_playwright
import json, os, time
URL = "http://localhost:8502"
SH = "figures/screens"
EF = "space_jog/logs_ui_error.txt"
def err():
    if os.path.exists(EF) and os.path.getmtime(EF) > time.time() - 90:
        return open(EF).read().splitlines()[0]
    return None
BACK = ".st-key-ic_searchback button"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(16000)

    def search(q):
        if page.locator(BACK).count():
            page.locator(BACK).click(timeout=8000)
            page.wait_for_timeout(1500)
        inp = page.locator('input[placeholder="Search your photos"]')
        inp.click(); inp.fill(q)
        page.wait_for_timeout(1500); page.keyboard.press("Enter")
        page.wait_for_timeout(9000)

    # nudge
    search("somewhere with lights I think")
    r = page.evaluate("""() => ({
      nudge: document.body.innerText.includes('Not quite right?'),
      askBtn: !!document.querySelector('.st-key-nudge_ask'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("NUDGE:", json.dumps(r), "| e:", err())
    page.screenshot(path=f"{SH}/d_nudge.png", animations="disabled")

    # zero
    search("zzzqqq")
    r = page.evaluate("""() => ({
      zero: document.body.innerText.includes('No close matches'),
      askBtn: !!document.querySelector('.st-key-zero_ask'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("ZERO:", json.dumps(r), "| e:", err())
    page.screenshot(path=f"{SH}/d_zero.png", animations="disabled")

    # collections via sidebar
    page.locator(BACK).click(timeout=8000)
    page.wait_for_timeout(1500)
    page.locator('.st-key-gpsidebar button:has-text("Collections")').first.click(timeout=8000)
    page.wait_for_timeout(5000)
    r = page.evaluate("""() => ({
      coll: !!document.querySelector('.st-key-gpcollections'),
      you: document.body.innerText.includes('Which one is you?'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("COLLECTIONS:", json.dumps(r), "| e:", err())
    page.screenshot(path=f"{SH}/d_collections.png", animations="disabled")
    b.close()
