"""QA for the People feature: onboarding dialog, You-label, person filter, avatars.
Runs against http://localhost:8502 (desktop + mobile). Expects data/people.json
to exist (face pipeline output synced)."""
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"


def dismiss_or_pick(page, pick_first=True):
    """Return the dialog state: 'none' | 'skipped' | 'picked:<label>'."""
    dlg = page.get_by_role("dialog", name="Which one is you?")
    if dlg.count() == 0:
        return "none"
    labels = [t.strip() for t in
              page.get_by_role("button", name="This is me").all_inner_texts()]
    avatars = page.locator('dialog img, [role="dialog"] img').count()
    print(f"dialog visible: {dlg.is_visible()} | persons shown: {labels} | avatars: {avatars}")
    if pick_first:
        page.get_by_role("button", name="This is me").first.click()
        page.wait_for_timeout(3000)
        return "picked"
    page.get_by_role("button", name="Skip for now", exact=True).click()
    page.wait_for_timeout(3000)
    return "skipped"


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        # --- desktop: pick first person ---
        pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_timeout(12000)
        st = dismiss_or_pick(pg, pick_first=True)
        assert st in ("none", "picked"), f"onboarding state: {st}"
        pg.screenshot(path="figures/screens/qa_people_1_after_pick.png")
        # people row on home should show a 'You' card
        body = pg.inner_text("body")
        if st == "picked":
            assert "You" in body, "no 'You' label on home after pick"
            print("'You' label present on home")
        # open the person filter: click the You avatar card on home
        you_card = pg.get_by_text("You", exact=True).first
        if you_card.count():
            you_card.click()
            pg.wait_for_timeout(4000)
            pg.screenshot(path="figures/screens/qa_people_2_filter.png")
            body2 = pg.inner_text("body")
            assert "photos" in body2, "person filter view missing photo count"
            print("person filter view OK")
            # clear filter
            clr = pg.get_by_role("button", name="✕", exact=True)
            if clr.count():
                clr.first.click()
                pg.wait_for_timeout(2500)
        # tag panel People group
        pg.get_by_role("button", name="Search Google Photos", exact=True).click()
        pg.wait_for_timeout(3000)
        pg.locator("input[placeholder*='Search for a person']").click()
        pg.wait_for_timeout(2000)
        pg.screenshot(path="figures/screens/qa_people_3_tagpanel.png")
        print("JS errors (desktop):", errs)
        pg.close()

        # --- mobile: skip path ---
        pg2 = b.new_context(viewport={"width": 390, "height": 844},
                            device_scale_factor=2).new_page()
        errs2 = []
        pg2.on("pageerror", lambda e: errs2.append(str(e)[:150]))
        pg2.goto(URL, wait_until="domcontentloaded")
        pg2.wait_for_timeout(12000)
        st2 = dismiss_or_pick(pg2, pick_first=False)
        assert st2 in ("none", "skipped"), f"mobile onboarding state: {st2}"
        pg2.screenshot(path="figures/screens/qa_people_4_mobile_home.png")
        print("JS errors (mobile):", errs2)
        b.close()
    print("PEOPLE QA PASS")


if __name__ == "__main__":
    sys.exit(main())
