from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(20000)
    # viewport shot of memories (top of page)
    page.screenshot(path="figures/screens/_vp_top.png", full_page=False, animations="disabled")
    # scroll stMain to the Feb 2026 grid (find its date header)
    page.evaluate("""
    () => {
      const heads = [...document.querySelectorAll('.gpdatehead')];
      const h = heads.find(e => e.innerText.includes('Feb 2026'));
      if (h) h.scrollIntoView({block: 'start'});
    }
    """)
    page.wait_for_timeout(500)
    page.screenshot(path="figures/screens/_vp_feb.png", full_page=False, animations="disabled")
    # now the full-page shot
    page.screenshot(path="figures/screens/_vp_full.png", full_page=True, animations="disabled")
    # after full-page shot, re-measure
    r = page.evaluate("""
    () => {
      const m = document.querySelector('[class*="st-key-memcard_"]');
      const p = document.querySelector('[class*="st-key-pcell_"]');
      const mr = m.getBoundingClientRect(); const pr = p.getBoundingClientRect();
      return {memW: Math.round(mr.width), pcellW: Math.round(pr.width),
              vw: window.innerWidth, vh: window.innerHeight};
    }
    """)
    print("after-fullpage:", r)
    b.close()
