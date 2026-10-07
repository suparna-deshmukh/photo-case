from playwright.sync_api import sync_playwright
import json, os, time
URL = "http://localhost:8502"
SH = "figures/screens"
EF = "space_jog/logs_ui_error.txt"

def err():
    if os.path.exists(EF) and os.path.getmtime(EF) > time.time() - 90:
        return open(EF).read().splitlines()[0]
    return None

def overflow(page):
    return page.evaluate("""() => {
      const bad = [];
      document.querySelectorAll('div, span, p, button, input, textarea, h1, h2, h3').forEach(el => {
        if (el.children.length > 2) return;
        const t = (el.innerText || '').trim();
        if (!t || t.length > 60) return;
        if (el.scrollHeight > el.clientHeight + 2 && getComputedStyle(el).overflow === 'visible')
          bad.push(t.slice(0, 40));
      });
      return bad.slice(0, 8);
    }""")

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(16000)

    # 1) search
    inp = page.locator('input[placeholder="Search your photos"]')
    inp.click(); inp.fill("sunset boat")
    page.wait_for_timeout(2000); page.keyboard.press("Enter")
    page.wait_for_timeout(9000)
    r = page.evaluate("""() => ({
      view: !!document.querySelector('.st-key-gpsearchview'),
      results: document.querySelectorAll('[class*="st-key-pcell_"] img').length,
      err: document.body.innerText.includes('Something went wrong'),
      overflow: 0
    })""")
    r["ovf"] = overflow(page)
    print("SEARCH:", json.dumps(r), "| e:", err())
    page.screenshot(path=f"{SH}/d_search.png", animations="disabled")

    # 2) nudge (hedged query) — go back home first
    page.locator(".st-key-searchback button").click(timeout=8000)
    page.wait_for_timeout(2000)
    inp = page.locator('input[placeholder="Search your photos"]')
    inp.click(); inp.fill("somewhere with lights I think")
    page.wait_for_timeout(2000); page.keyboard.press("Enter")
    page.wait_for_timeout(9000)
    r = page.evaluate("""() => ({
      nudge: document.body.innerText.includes('Not quite right?'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("NUDGE:", json.dumps(r), "| e:", err())
    page.screenshot(path=f"{SH}/d_nudge.png", animations="disabled")

    # 3) zero
    page.locator(".st-key-searchback button").click(timeout=8000)
    page.wait_for_timeout(2000)
    inp = page.locator('input[placeholder="Search your photos"]')
    inp.click(); inp.fill("zzzqqq")
    page.wait_for_timeout(2000); page.keyboard.press("Enter")
    page.wait_for_timeout(9000)
    r = page.evaluate("""() => ({
      zero: document.body.innerText.includes('No close matches'),
      askBtn: !!document.querySelector('.st-key-zero_ask'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("ZERO:", json.dumps(r), "| e:", err())
    page.screenshot(path=f"{SH}/d_zero.png", animations="disabled")

    # 4) collections
    page.locator(".st-key-searchback button").click(timeout=8000)
    page.wait_for_timeout(2000)
    page.locator('.st-key-gpsidebar >> text="Collections"').first.click(timeout=8000)
    page.wait_for_timeout(5000)
    r = page.evaluate("""() => ({
      people: (document.body.innerText.match(/People/g) || []).length,
      places: (document.body.innerText.match(/Places/g) || []).length,
      you: document.body.innerText.includes('Which one is you?'),
      err: document.body.innerText.includes('Something went wrong')
    })""")
    print("COLLECTIONS:", json.dumps(r), "| e:", err())
    page.screenshot(path=f"{SH}/d_collections.png", animations="disabled")
    b.close()
