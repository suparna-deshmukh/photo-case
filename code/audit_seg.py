from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(15000)
    page.click('input[placeholder="Search your photos"]')
    page.wait_for_timeout(300)
    page.fill('input[placeholder="Search your photos"]', "sunset boat")
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)
    r = page.evaluate("""
    () => {
      const seg = document.querySelector('.st-key-gpseg');
      const btns = [...document.querySelectorAll('button')].map(b => b.innerText.trim()).filter(Boolean).slice(0, 20);
      return {seg: seg ? {html: seg.innerHTML.slice(0, 200), r: (() => { const x = seg.getBoundingClientRect(); return [Math.round(x.x), Math.round(x.y), Math.round(x.width)]; })()} : null,
              btns, hasSearchBack: !!document.querySelector('.st-key-icb_searchback')};
    }
    """)
    print(r)
    b.close()
