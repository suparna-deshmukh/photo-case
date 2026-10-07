from playwright.sync_api import sync_playwright
import json, os, time
URL = "http://localhost:8502"
EF = "space_jog/logs_ui_error.txt"
def err():
    if os.path.exists(EF) and os.path.getmtime(EF) > time.time() - 120:
        return open(EF).read().splitlines()[0]
    return None
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(URL + "/?test=1", wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    r = page.evaluate("""() => ({
      join: document.body.innerText.includes('P1') || !!document.querySelector('.st-key-pcode'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("T0 join screen:", json.dumps(r), "| e:", err())
    page.locator(".st-key-pcode input").fill("P1")
    page.wait_for_timeout(800)
    page.keyboard.press("Tab")
    page.wait_for_timeout(800)
    page.locator(".st-key-pcode input").locator("..").locator("xpath=following-sibling::*").first  # noop
    start_btn = page.locator('button:has-text("Start session"), button:has-text("Start")').first
    start_btn.click(timeout=10000)
    page.wait_for_timeout(6000)
    r = page.evaluate("""() => ({
      card: !!document.querySelector('.st-key-gptaskcard'),
      practice: document.body.innerText.toLowerCase().includes('practice'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("T1 task card:", json.dumps(r), "| e:", err())
    page.screenshot(path="figures/screens/t_testmode.png", animations="disabled")
    # start the practice task
    sb = page.locator('button:has-text("Start task")')
    if sb.count():
        sb.first.click(timeout=8000)
        page.wait_for_timeout(8000)
        r = page.evaluate("""() => ({
          searchbox: !!document.querySelector('input') ,
          membox: !!document.querySelector('textarea'),
          err: document.body.innerText.includes('Something went wrong')
        })""")
        print("T2 task running:", json.dumps(r), "| e:", err())
        page.screenshot(path="figures/screens/t_testmode_run.png", animations="disabled")
    # admin
    page.goto(URL + "/?admin=1", wait_until="domcontentloaded")
    page.wait_for_timeout(12000)
    r = page.evaluate("""() => ({
      admin: !!document.querySelector('a[download]') || document.body.innerText.includes('events.jsonl'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("T3 admin:", json.dumps(r), "| e:", err())
    b.close()
