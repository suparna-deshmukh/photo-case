from playwright.sync_api import sync_playwright
import json, os, time
URL = "http://localhost:8502"
SH = "figures/screens"

def snap(page, name):
    page.screenshot(path=f"{SH}/j_{name}.png", full_page=False, animations="disabled")

def err(page):
    e = "space_jog/logs_ui_error.txt"
    if os.path.exists(e) and os.path.getmtime(e) > time.time() - 60:
        return open(e).read().splitlines()[0]
    return None

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    cons = []
    page.on("console", lambda m: cons.append(m.text[:200]) if m.type == "error" else None)
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(16000)

    page.locator(".st-key-pill_ask_chip button").click(timeout=15000)
    page.wait_for_timeout(2500)
    snap(page, "01_ask_idle")
    # type and immediately click Find it (real user path)
    page.locator("textarea").first.type("a cafe somewhere in Goa, daytime I think", delay=25)
    page.wait_for_timeout(300)
    page.locator(".st-key-ask_go button").click(timeout=10000)
    page.wait_for_timeout(12000)
    r = page.evaluate("""() => ({
      chips: [...document.querySelectorAll('.st-key-gpassk ~ * [class*="gpchip"], [class*="chip"]')].map(e=>e.innerText.trim()).filter(Boolean).slice(0,10),
      status: (document.body.innerText.match(/\\d+ likely matches[\\s\\S]{0,50}/)||[''])[0].replace(/\\n/g,' | '),
      question: (document.body.innerText.match(/(indoors or outdoors|time of day|kind of place)[^\\n]{0,60}/i)||[''])[0],
      pairs: document.querySelectorAll('[class*="st-key-pcell_"] img').length,
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("S1 after Find it:", json.dumps(r)[:400], "| efile:", err(page))
    snap(page, "02_session_top")
    # answer a question if present
    qbtn = page.locator("button:has-text('Outdoors'), button:has-text('Indoors')").first
    if qbtn.count():
        qbtn.click(timeout=8000)
        page.wait_for_timeout(8000)
        print("S2 answered question")
        snap(page, "03_after_answer")
    # open first result -> lightbox (click the overlay button on the tile)
    first = page.locator('[class*="st-key-pcellb_"] button').first
    first.scroll_into_view_if_needed()
    first.click(timeout=8000)
    page.wait_for_timeout(3000)
    r2 = page.evaluate("""() => ({
      lb: !!document.querySelector('[class*="gplbimgwrap"], [data-testid="stDialog"]'),
      thatsit: !!document.querySelector('.st-key-lb_thatsit')
    })""")
    print("S3 lightbox:", r2)
    snap(page, "04_lightbox")
    # That's it -> success
    if r2["thatsit"]:
        page.locator(".st-key-lb_thatsit button").click(timeout=8000)
        page.wait_for_timeout(4000)
        r3 = page.evaluate("""() => ({
          success: !!document.querySelector('[class*="gpsucc"]') || document.body.innerText.includes('Found it in'),
        })""")
        print("S4 success:", r3)
        snap(page, "05_success")
    print("font console errors:", [c for c in cons if 'font' in c.lower() or 'sfnt' in c.lower()][:3])
    print("ALL console errors:", cons[:5])
    print("efile final:", err(page))
    b.close()
