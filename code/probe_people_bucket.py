"""Probe: does the People bucket appear after search, desktop + mobile?"""
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"

def people_info(page):
    txt = page.locator("body").inner_text()
    import re
    m = re.search(r"Results for[^\n]*", txt)
    header = m.group(0) if m else "NO RESULTS HEADER"
    # people section: header 'People' + chip counts
    has_people_header = page.locator('div.grp-head', has_text="People").count() > 0
    chips = [c.inner_text().replace("\n", " ") for c in page.locator("div.pc-cnt").all()]
    return header, has_people_header, chips

def search_pill(page, q):
    pill = page.locator('input[aria-label="Search Google Photos"]').first
    for attempt in range(3):
        pill.fill("")
        page.wait_for_timeout(700)
        pill.fill(q)
        page.wait_for_timeout(300)
        pill.press("Enter")
        try:
            page.get_by_text("Results for", exact=False).first.wait_for(timeout=12000)
            return
        except Exception:
            page.wait_for_timeout(2500)
    raise RuntimeError("results never appeared (desktop pill)")

def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        # desktop
        pg = b.new_context(viewport={"width": 1440, "height": 1000}).new_page()
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_timeout(15000)
        if pg.get_by_role("button", name="Not sure", exact=True).count():
            pg.get_by_role("button", name="Not sure").first.click(); pg.wait_for_timeout(3000)
        for q in ["goa", "sunset", "cafe", "my friends", "sachin", "zzzqqqxyzzy"]:
            search_pill(pg, q)
            pg.wait_for_timeout(1500)
            header, hp, chips = people_info(pg)
            print(f"DESKTOP q={q!r}: people_header={hp} chips={chips} | {header[:60]}")
            if q == "goa":
                pg.screenshot(path="figures/screens/qa_s5_desktop_people.png")
        pg.close()
        # mobile
        pg2 = b.new_context(viewport={"width": 390, "height": 844},
                            device_scale_factor=2, is_mobile=True, has_touch=True).new_page()
        pg2.goto(URL, wait_until="domcontentloaded")
        pg2.wait_for_timeout(15000)
        if pg2.get_by_role("button", name="Not sure", exact=True).count():
            pg2.get_by_role("button", name="Not sure").first.click(); pg2.wait_for_timeout(3000)
        nav = pg2.get_by_role("button", name="Search", exact=True)
        print("mobile Search nav buttons:", nav.count())
        nav.first.click(); pg2.wait_for_timeout(2500)
        box = pg2.locator('input[aria-label="Search your photos"], input[placeholder*="Search for a person"]').first
        box.click()
        for q in ["goa", "my friends"]:
            box.fill("")
            pg2.wait_for_timeout(400)
            box.fill(q)
            pg2.wait_for_timeout(300)
            pg2.get_by_role("button", name="Search", exact=True).last.click()
            try:
                pg2.get_by_text("Results for", exact=False).first.wait_for(timeout=12000)
            except Exception:
                print(f"MOBILE q={q!r}: NO RESULTS HEADER; body head:", pg2.locator("body").inner_text()[:200].replace("\n", " | "))
                continue
            pg2.wait_for_timeout(1500)
            header, hp, chips = people_info(pg2)
            print(f"MOBILE  q={q!r}: people_header={hp} chips={chips} | {header[:60]}")
            if q == "goa":
                pg2.screenshot(path="figures/screens/qa_s5_mobile_people.png")
        b.close()

if __name__ == "__main__":
    main()
