from playwright.sync_api import sync_playwright
URL = "http://localhost:8502"
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    inp = page.locator('input[placeholder="Search your photos"]')
    inp.click()
    page.wait_for_timeout(300)
    inp.fill("zzzqqq")
    page.wait_for_timeout(2500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(9000)
    r = page.evaluate("""() => {
      const hits = [];
      document.querySelectorAll('*').forEach(el => {
        if (el.children.length === 0 && (el.textContent || '').includes('Something went wrong')) {
          const r = el.getBoundingClientRect();
          const cs = getComputedStyle(el);
          hits.push({tag: el.tagName, cls: (el.className||'').toString().slice(0,80),
                     vis: cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0,
                     x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width)});
        }
      });
      const body = document.body.innerText;
      return {
        searchView: !!document.querySelector('.st-key-gpsearchview'),
        hasPhrase: body.includes('Something went wrong'),
        hits: hits.slice(0, 5),
        results: document.querySelectorAll('[class*="st-key-pcell_"] img').length
      };
    }""")
    print(r)
    page.screenshot(path="figures/screens/_dbg_zero2.png", full_page=False, animations="disabled")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1500)
    page.screenshot(path="figures/screens/_dbg_zero2_bottom.png", full_page=False, animations="disabled")
    b.close()
