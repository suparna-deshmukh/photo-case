from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    page.locator(".st-key-pill_ask_chip button").click(timeout=15000)
    page.wait_for_timeout(2000)
    page.locator("textarea").first.type("a cafe somewhere in Goa, daytime I think", delay=25)
    page.locator(".st-key-ask_go button").click(timeout=10000)
    page.wait_for_timeout(12000)
    r = page.evaluate("""() => {
      const imgs = [...document.querySelectorAll('img')];
      const bad = imgs.filter(i => i.naturalWidth === 0).map(i => i.src.slice(0, 90));
      return {total: imgs.length, bad: bad.slice(0, 6)};
    }""")
    print("ask session:", r)
    # home check
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(10000)
    r2 = page.evaluate("""() => {
      const imgs = [...document.querySelectorAll('img')];
      const bad = imgs.filter(i => i.naturalWidth === 0).map(i => i.src.slice(0, 90));
      return {total: imgs.length, bad: bad.slice(0, 6)};
    }""")
    print("home:", r2)
    b.close()
