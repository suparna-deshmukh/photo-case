from playwright.sync_api import sync_playwright
import os, time
URL = "http://localhost:8502"
EF = "space_jog/logs_ui_error.txt"

def err_log():
    if os.path.exists(EF):
        t = open(EF).read()
        if os.path.getmtime(EF) > time.time() - 120:
            return t.splitlines()[0]
    return None

def flow(tag, ask):
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(16000)
        if ask:
            page.locator('button:text-is("Ask")').click()
            page.wait_for_timeout(1200)
            page.locator('textarea').first.fill("a cafe somewhere in Goa, daytime I think")
            page.wait_for_timeout(400)
            page.locator('button:text-is("Find it")').click()
            q = "ask"
        else:
            inp = page.locator('input[placeholder="Search your photos"]')
            inp.click(); page.wait_for_timeout(300)
            inp.fill(tag); page.wait_for_timeout(2000)
            page.keyboard.press("Enter")
            q = tag
        page.wait_for_timeout(10000)
        r = page.evaluate("""() => ({
            hasPhrase: document.body.innerText.includes('Something went wrong'),
            results: document.querySelectorAll('[class*="st-key-pcell_"] img').length,
            ok: document.querySelectorAll('[class*="st-key-pcell_"] img').length === 0 ||
                 [...document.querySelectorAll('[class*="st-key-pcell_"] img')].every(i=>i.naturalWidth>0)
        })""")
        r["efile"] = err_log()
        print(tag, r)
        page.screenshot(path=f"figures/screens/_v3_{tag if len(tag)<12 else 'ask'}.png",
                        full_page=False, animations="disabled")
        b.close()

flow("sunset boat", False)
flow("zzzqqq", False)
flow("ask", True)
