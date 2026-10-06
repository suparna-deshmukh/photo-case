import time
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"
js_errors = []

def snap(page, tag):
    dlg = page.get_by_role("button", name="Close, but not it", exact=True).count()
    daybtn = page.get_by_role("button", name=__import__("re").compile(r"\u00b7 \d+ photos$")).count()
    thisone = page.get_by_role("button", name="\u2714 This one", exact=True).count()
    anchor = page.get_by_role("button", name="Same day", exact=True).count()
    err = page.locator("text=Something went wrong").count()
    print(f"[{tag}] dialog={dlg} daybtn={daybtn} thisone={thisone} anchorcard={anchor} errcard={err}", flush=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_context(viewport={"width":1440,"height":1000}).new_page()
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    if page.get_by_role("button", name="Not sure", exact=True).count():
        page.get_by_role("button", name="Not sure", exact=True).first.click()
        page.wait_for_timeout(5000)
    g = page.get_by_role("button", name="Ask Gemini")
    g.last.click(); page.wait_for_timeout(4000)
    chip = page.get_by_role("button", name="the sunset with a boat,\u2026", exact=True)
    if chip.count():
        chip.first.click(); page.wait_for_timeout(12000)
    snap(page, "after chip")
    # answer question if present
    for lab in ("Morning","Afternoon","Evening","Night","Indoors","Outdoors","Beach","Caf\u00e9"):
        b = page.get_by_role("button", name=lab, exact=True)
        if b.count():
            b.first.click(); page.wait_for_timeout(9000); break
    snap(page, "after question")
    if page.get_by_role("button", name="Left is closer", exact=True).count():
        page.get_by_role("button", name="Left is closer", exact=True).first.click()
        page.wait_for_timeout(9000)
    snap(page, "after pair")
    if page.get_by_role("button", name="Use as anchor", exact=True).count():
        page.get_by_role("button", name="Use as anchor", exact=True).first.click()
        page.wait_for_timeout(9000)
        snap(page, "after use-anchor")
        if page.get_by_role("button", name="Right after", exact=True).count():
            page.get_by_role("button", name="Right after", exact=True).first.click()
            page.wait_for_timeout(9000)
    snap(page, "after right-after")
    if page.get_by_role("button", name="I'm stuck", exact=True).count():
        page.get_by_role("button", name="I'm stuck", exact=True).first.click()
        page.wait_for_timeout(12000)
    snap(page, "after stuck")
    import re as _re
    day = page.get_by_role("button", name=_re.compile(r"\u00b7 \d+ photos$"))
    if day.count():
        day.first.click(); page.wait_for_timeout(10000)
    snap(page, "after day")
    t = page.get_by_role("button", name="\u2714 This one", exact=True)
    print("thisone count before click:", t.count(), flush=True)
    if t.count():
        t.first.click()
        for i in range(8):
            page.wait_for_timeout(5000)
            snap(page, f"postclick+{(i+1)*5}s")
            if page.get_by_role("button", name="Close, but not it", exact=True).count():
                break
    import pathlib
    e = pathlib.Path("space_jog/logs_ui_error.txt")
    print("UI ERROR FILE:", (e.read_text()[:500] if e.exists() else "none"), flush=True)
    print("JS ERRORS:", js_errors[:5], flush=True)
    browser.close()
