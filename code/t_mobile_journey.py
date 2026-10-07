from playwright.sync_api import sync_playwright
import json, os, time
URL = "http://localhost:8502"
SH = "figures/screens"
EF = "space_jog/logs_ui_error.txt"
def err():
    if os.path.exists(EF) and os.path.getmtime(EF) > time.time() - 120:
        return open(EF).read().splitlines()[0]
    return None
def locked(page):
    return page.evaluate("""() => {
      const sw = document.documentElement.scrollWidth;
      return {locked: sw <= window.innerWidth + 1, sw, iw: window.innerWidth};
    }""")
def imgs_ok(page):
    return page.evaluate("""() => {
      const imgs = [...document.querySelectorAll('img')];
      const bad = imgs.filter(i => i.naturalWidth === 0 && i.getBoundingClientRect().width > 5);
      return {n: imgs.length, bad: bad.length};
    }""")
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    print("M0 home:", locked(page), imgs_ok(page), "| e:", err())
    page.screenshot(path=f"{SH}/m_01_home.png", animations="disabled")

    # floating nav Ask
    page.locator(".st-key-fnav_ask button").click(timeout=10000)
    page.wait_for_timeout(3000)
    r = page.evaluate("""() => ({
      ask: document.body.innerText.includes('Ask Photos'),
      ta: !!document.querySelector('textarea')
    })""")
    print("M1 ask idle:", r, locked(page), "| e:", err())
    page.screenshot(path=f"{SH}/m_02_ask_idle.png", animations="disabled")

    # type + immediately Find it (real user path)
    page.locator("textarea").first.type("a cafe somewhere in Goa, daytime I think", delay=25)
    page.wait_for_timeout(300)
    page.locator(".st-key-ask_go button").click(timeout=10000)
    page.wait_for_timeout(12000)
    r = page.evaluate("""() => ({
      status: (document.body.innerText.match(/\\d+ likely matches[\\s\\S]{0,40}/)||[''])[0].replace(/\\n/g,' | '),
      cells: document.querySelectorAll('[class*="st-key-pcell_"] img').length,
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("M2 session:", json.dumps(r), locked(page), imgs_ok(page), "| e:", err())
    page.screenshot(path=f"{SH}/m_03_session.png", animations="disabled")

    # open first tile -> lightbox
    first = page.locator('[class*="st-key-pcellb_"] button').first
    first.scroll_into_view_if_needed()
    first.click(timeout=8000)
    page.wait_for_timeout(3000)
    r = page.evaluate("""() => ({
      dlg: !!document.querySelector('[data-testid="stDialog"] .gplb'),
      thatsit: !!document.querySelector('.st-key-lb_thatsit button')
    })""")
    print("M3 lightbox:", r, "| e:", err())
    page.screenshot(path=f"{SH}/m_04_lightbox.png", animations="disabled")

    # That's it -> success
    page.locator(".st-key-lb_thatsit button").click(timeout=8000)
    page.wait_for_timeout(4000)
    r = page.evaluate("""() => ({
      success: !!document.querySelector('[class*="gpsucc-chips"]')
    })""")
    print("M4 success:", r, "| e:", err())
    page.screenshot(path=f"{SH}/m_05_success.png", animations="disabled")
    b.close()
