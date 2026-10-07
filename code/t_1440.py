from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(18000)
    r = page.evaluate("""() => {
      const stMain = document.querySelector('[data-testid="stMain"]');
      const g = document.querySelector('.st-key-gpmain');
      const imgs = [...document.querySelectorAll('[class*="st-key-pcell_"] img')];
      return {
        sw: document.documentElement.scrollWidth, iw: window.innerWidth,
        gm: g ? Math.round(g.getBoundingClientRect().right) : null,
        cells: {n: imgs.length, ok: imgs.filter(i => i.naturalWidth > 0 && i.getBoundingClientRect().width > 5).length},
        mem: document.querySelectorAll('[class*="st-key-memcard_"] img').length,
        fontOk: document.fonts ? document.fonts.status : 'n/a',
        err: document.body.innerText.includes('Something went wrong')
      };
    }""")
    print(r)
    # verify the Google Sans Flex font actually loaded
    f = page.evaluate("() => { try { return document.fonts.check('16px \"Google Sans Flex\"'); } catch(e) { return String(e); } }")
    print("GSF loaded:", f)
    page.screenshot(path="figures/screens/w_d_home_final.png", animations="disabled")
    b.close()
