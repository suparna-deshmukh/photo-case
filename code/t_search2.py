from playwright.sync_api import sync_playwright
URL = "http://localhost:8502"
def run(query, tag, ask=False):
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        console = []
        page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(16000)
        if ask:
            page.locator('button:text-is("Ask")').click()
            page.wait_for_timeout(1500)
            page.locator('textarea').first.fill(query)
            page.wait_for_timeout(500)
            page.locator('button:text-is("Find it")').click()
        else:
            inp = page.locator('input[placeholder="Search your photos"]')
            inp.click()
            page.wait_for_timeout(300)
            inp.fill(query)
            page.wait_for_timeout(2500)
            page.keyboard.press("Enter")
        page.wait_for_timeout(9000)
        r = page.evaluate("""() => {
          const body = document.body.innerText;
          const ec = document.querySelector('[data-testid="stException"]');
          return {
            searchView: !!document.querySelector('.st-key-gpsearchview'),
            askView: !!document.querySelector('.st-key-gpaske'),
            seg: !!document.querySelector('.st-key-gpseg'),
            err: body.includes('Something went wrong'),
            ecText: ec ? ec.innerText.slice(0, 400) : null,
            results: document.querySelectorAll('[class*="st-key-pcell_"] img').length
          };
        }""")
        r["js"] = errs[:3]
        r["console"] = console[:3]
        print(tag, r)
        page.screenshot(path=f"figures/screens/_dbg_{tag}.png", full_page=False, animations="disabled")
        b.close()
run("sunset boat", "search")
run("zzzqqq", "zerores")
run("a cafe somewhere in Goa, daytime I think", "ask_hedge")
