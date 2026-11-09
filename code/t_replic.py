from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    page.locator(".st-key-pill_ask_chip button").click(timeout=15000)
    page.wait_for_timeout(1500)
    page.locator('textarea').first.fill("a cafe somewhere in Goa, daytime I think")
    page.wait_for_timeout(500)
    try:
        page.locator(".st-key-ask_go button").click(timeout=8000)
        print("Find it clicked OK")
    except Exception as e:
        print("Find it FAILED:", str(e).split("\n")[0])
        # try blur then click
        page.keyboard.press("Tab")
        page.wait_for_timeout(1500)
        try:
            page.locator(".st-key-ask_go button").click(timeout=8000)
            print("after Tab: Find it clicked OK")
        except Exception as e2:
            print("after Tab FAILED:", str(e2).split("\n")[0])
    page.wait_for_timeout(8000)
    r = page.evaluate("""() => ({
      session: document.body.innerText.includes('what I picked up') || document.body.innerText.includes('likely matches'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print(r)
    b.close()
