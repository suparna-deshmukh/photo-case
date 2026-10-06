from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_context(viewport={"width":390,"height":844}).new_page()
    p.goto("http://localhost:8502", wait_until="domcontentloaded")
    p.wait_for_timeout(14000)
    if p.get_by_role("button", name="Not sure", exact=True).count():
        p.get_by_role("button", name="Not sure", exact=True).first.click()
        p.wait_for_timeout(4000)
    p.get_by_role("button", name="Ask Gemini").last.click()
    p.wait_for_timeout(3500)
    chip = p.get_by_role("button", name="the sunset with a boat,\u2026", exact=True)
    if chip.count():
        chip.first.click()
        p.wait_for_timeout(14000)
    if p.get_by_role("button", name="This is it \u2714", exact=True).count():
        p.get_by_role("button", name="This is it \u2714", exact=True).first.click()
        p.wait_for_timeout(8000)
        if p.get_by_role("button", name="Close, but not it", exact=True).count():
            p.get_by_role("button", name="Yes", exact=True).first.click()
            p.wait_for_timeout(8000)
    print("success visible:", p.locator("text=Found it in").count(), flush=True)
    p.get_by_role("button", name="Search").first.click()
    p.wait_for_timeout(7000)
    print("on search tab:", p.locator('input[placeholder*="Search for a person"]').count(),
          " guided head:", p.locator("text=guided search").count(), flush=True)
    inp = p.locator('input[placeholder*="Search for a person"]').first
    inp.fill("medicine photo from when I was ill")
    p.wait_for_timeout(600)
    print("filled:", inp.input_value()[:40], flush=True)
    for attempt in range(3):
        p.get_by_role("button", name="Search", exact=True).nth(0).click()
        p.wait_for_timeout(8000)
        n = p.get_by_role("button", name="This is it \u2714").count()
        print(f"attempt {attempt+1}: thisone={n} warning={p.locator('text=Type a search first').count()}", flush=True)
        if n:
            break
    b.close()
