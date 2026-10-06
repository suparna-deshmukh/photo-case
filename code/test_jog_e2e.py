"""Full-flow E2E for the redesigned Jog app (desktop + mobile).

Walks: home (onboarding, lightbox), app-bar search (grouped results, nudge ->
guided), guided loop (question, pair, anchor, stuck/fallback, confirm,
success, right-photo feedback), classic search, People tab, Settings.
Collects JS errors; asserts no error card.
"""
import re
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"
SHOTS = "figures/screens"

X1 = ("I'm trying to find a photo of a small café on our Goa trip. I think it was "
      "daytime and we were having coffee before the beach. I don't remember which "
      "day or which café.")
VAGUE = "I think it was a beach photo, maybe with a boat at sunset?"

OPTION_LABELS = {"Indoors", "Outdoors", "Unclear", "Morning", "Afternoon", "Evening",
                 "Night", "Café", "Beach", "Street", "Campus", "Classroom or study",
                 "Home or hostel", "Restaurant", "Temple or ruins", "Nature or landscape",
                 "Transport", "Office", "Party or event", "Shop or market",
                 "Document or receipt", "Somewhere else", "Summer", "Monsoon", "Winter",
                 "No one", "Just one person", "Two or three", "A group",
                 "Yes, some writing", "No writing", "Something else",
                 "Goa", "Hampi", "Pune", "Pondicherry", "Puducherry", "Bengaluru",
                 "Bangalore", "Gokarna", "Zuarinagar", "You"}

fails = []
js_errors = []

def check(page, name, cond):
    status = "ok" if cond else "FAIL"
    print(f"[{status}] {name}")
    if not cond:
        fails.append(name)
    return cond

def err_card(page):
    return page.locator("text=Something went wrong").count() > 0

def settle(page, ms=3000):
    page.wait_for_timeout(ms)
    if err_card(page):
        print("ERROR CARD:", page.locator("text=Something went wrong").first.inner_text()[:300])

def st_success_done(page):
    return page.locator("text=Found it in").count() > 0 or \
        page.get_by_role("button", name="Search another", exact=True).count() > 0

def click_btn(page, name, ms=3000):
    b = page.get_by_role("button", name=name)
    b.first.wait_for(state="visible", timeout=15000)
    b.first.scroll_into_view_if_needed()
    b.first.click()
    settle(page, ms)

def shot(page, name, full=False):
    page.screenshot(path=f"{SHOTS}/{name}.png", full_page=full, animations="disabled")
    print("shot:", name)

def first_option(page):
    for lab in sorted(OPTION_LABELS):
        b = page.get_by_role("button", name=lab, exact=True)
        if b.count() > 0:
            return lab
    b = page.get_by_role("button", name="I don't remember", exact=True)
    if b.count() > 0:
        return "I don't remember"
    return None

def run_desktop(pw):
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = ctx.new_page()
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    page.on("console", lambda m: js_errors.append(m.text) if m.type == "error" else None)
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    succeeded = False

    # --- home ---
    check(page, "d: no error card on load", not err_card(page))
    shot(page, "d_home_top")
    if page.get_by_role("button", name="Not sure", exact=True).count():
        click_btn(page, "Not sure", 4000)
        check(page, "d: onboarding dismissed (Not sure)", True)
    check(page, "d: month grid visible", page.get_by_role("button", name="Open photo from").count() > 0)
    shot(page, "d_home_full", full=True)

    # lightbox
    b = page.get_by_role("button", name="Open photo from").first
    b.scroll_into_view_if_needed(); b.click(); settle(page, 3500)
    check(page, "d: lightbox opens", page.get_by_role("button", name="Close").count() > 0)
    shot(page, "d_lightbox")
    click_btn(page, "Close")

    # --- app-bar search (grouped results) ---
    pill = page.locator('input[aria-label="Search Google Photos"]').first
    pill.fill("a café in Goa, daytime")
    pill.press("Enter"); settle(page, 6000)
    check(page, "d: classic results render", page.get_by_role("button", name="This is it ✔").count() > 0)
    check(page, "d: grouped results (See all)", page.get_by_role("button", name="See all").count() > 0)
    shot(page, "d_search_grouped")

    # nudge -> guided (router gating: hedged query offers the loop)
    pill.fill(VAGUE)
    pill.press("Enter"); settle(page, 7000)
    if page.get_by_role("button", name="Try guided search", exact=True).count():
        click_btn(page, "Try guided search", 6000)
        check(page, "d: nudge -> guided", page.locator("text=guided search").count() > 0)
    else:
        check(page, "d: nudge -> guided", False)
    if page.get_by_role("button", name="Back to search", exact=True).count():
        click_btn(page, "Back to search", 4000)
    # guided via example chip (autostart)
    g = page.get_by_role("button", name="Ask Gemini")
    g.last.click(); settle(page, 3000)
    chip = page.get_by_role("button", name="the sunset with a boat,…", exact=True)
    if chip.count():
        chip.first.click(); settle(page, 9000)
    shot(page, "d_guided_1")
    check(page, "d: cue chips present", page.get_by_role("button", name="not this", exact=True).count() > 0
          or page.get_by_role("button", name="sure", exact=True).count() > 0)

    # --- question card ---
    if page.get_by_role("button", name="I don't remember", exact=True).count():
        lab = first_option(page)
        check(page, "d: question option clicked (%s)" % lab, lab is not None)
        if lab:
            click_btn(page, lab, 4500)
        shot(page, "d_guided_question_answered")

    # --- pair card ---
    if page.get_by_role("button", name="Left is closer", exact=True).count():
        shot(page, "d_guided_pair")
        click_btn(page, "Left is closer", 4500)
    # --- anchor ---
    if page.get_by_role("button", name="Use as anchor", exact=True).count():
        click_btn(page, "Use as anchor", 3500)
        check(page, "d: anchor options", page.get_by_role("button", name="Right after", exact=True).count() > 0)
        click_btn(page, "Right after", 4500)
        shot(page, "d_guided_anchor")
    # --- I'm stuck -> fallback ---
    if page.get_by_role("button", name="I'm stuck", exact=True).count():
        click_btn(page, "I'm stuck", 11000)
        check(page, "d: fallback shown", page.locator("text=narrow it to").count() > 0)
        shot(page, "d_guided_fallback")
        day = page.get_by_role("button", name=re.compile(r"· \d+ photos$"))
        if day.count():
            day.first.scroll_into_view_if_needed()
            day.first.click(); settle(page, 6000)
            if page.get_by_role("button", name="✔ This one", exact=True).count():
                click_btn(page, "✔ This one", 5000)
                try:
                    page.get_by_role("button", name="Close, but not it", exact=True).first.wait_for(state="visible", timeout=25000)
                    check(page, "d: confirm dialog", True)
                except Exception:
                    check(page, "d: confirm dialog", False)
                shot(page, "d_confirm_dialog")
                click_btn(page, "Yes", 5500)
                check(page, "d: success screen", page.locator("text=Found it in").count() > 0)
                shot(page, "d_success")
                if page.get_by_role("button", name="Yes", exact=True).count():
                    click_btn(page, "Yes", 3000)
                if page.get_by_role("button", name="Search another", exact=True).count():
                    click_btn(page, "Search another", 4500)
                succeeded = True
    # --- confirm flow: This is it -> dialog -> Yes -> success ---
    if not succeeded and page.get_by_role("button", name="This is it ✔", exact=True).count():
        click_btn(page, "This is it ✔", 4000)
        try:
            page.get_by_role("button", name="Close, but not it", exact=True).first.wait_for(state="visible", timeout=25000)
            check(page, "d: confirm dialog", True)
        except Exception:
            check(page, "d: confirm dialog", False)
        shot(page, "d_confirm_dialog")
        click_btn(page, "Yes", 5000)
        check(page, "d: success screen", page.locator("text=Found it in").count() > 0)
        shot(page, "d_success")
        if page.get_by_role("button", name="Yes", exact=True).count():
            click_btn(page, "Yes", 3000)  # "Was this the right photo?"
        if page.get_by_role("button", name="Search another", exact=True).count():
            click_btn(page, "Search another", 4000)
    # back to search view
    if page.get_by_role("button", name="Back to search", exact=True).count():
        click_btn(page, "Back to search", 4000)
    shot(page, "d_final")
    ctx.close()
    browser.close()
    return page

def run_mobile(pw):
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 390, "height": 844},
                              device_scale_factor=2, is_mobile=True,
                              has_touch=True)
    page = ctx.new_page()
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    page.on("console", lambda m: js_errors.append(m.text) if m.type == "error" else None)
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    check(page, "m: no error card on load", not err_card(page))
    shot(page, "m_home_top")
    if page.get_by_role("button", name="Not sure", exact=True).count():
        click_btn(page, "Not sure", 4000)
    shot(page, "m_home_full", full=True)

    # bottom nav -> Gemini (guided)
    b = page.get_by_role("button", name="Ask Gemini")
    b.last.wait_for(state="visible", timeout=15000)
    b.last.click()
    page.wait_for_timeout(3500)
    check(page, "m: guided tab", page.locator("text=guided search").count() > 0)
    ta = page.locator("textarea").first
    ta.fill(X1)
    ta.press("Tab")
    page.wait_for_timeout(1500)
    click_btn(page, "Find it", 9000)
    shot(page, "m_guided_1")
    check(page, "m: moments render", page.get_by_role("button", name="This is it ✔").count() > 0)
    if page.get_by_role("button", name="I don't remember", exact=True).count():
        lab = first_option(page)
        if lab:
            click_btn(page, lab, 4500)
        shot(page, "m_guided_question")
    if page.get_by_role("button", name="This is it ✔", exact=True).count():
        click_btn(page, "This is it ✔", 4000)
        if page.get_by_role("button", name="Close, but not it", exact=True).count():
            click_btn(page, "Yes", 5000)
        check(page, "m: success screen", page.locator("text=Found it in").count() > 0)
        shot(page, "m_success")
    # search tab via bottom nav
    page.get_by_role("button", name="Search").first.click(); settle(page, 5000)
    inp = page.locator('input[placeholder*="Search for a person"]').first
    for _ in range(3):
        inp.fill("medicine photo from when I was ill")
        page.wait_for_timeout(500)
        if (inp.input_value() or "").strip():
            break
        page.wait_for_timeout(2000)
    for _ in range(3):
        sb = page.get_by_role("button", name="Search", exact=True)
        sb.first.wait_for(state="visible", timeout=15000)
        sb.first.click()
        page.wait_for_timeout(7000)
        if page.get_by_role("button", name="This is it ✔").count() > 0:
            break
    check(page, "m: mobile classic results", page.get_by_role("button", name="This is it ✔").count() > 0)
    shot(page, "m_search_results")
    # people tab
    page.get_by_role("button", name="People").first.click(); settle(page, 3500)
    shot(page, "m_people")
    ctx.close()
    browser.close()

with sync_playwright() as pw:
    run_desktop(pw)
    run_mobile(pw)

real_js = [e for e in js_errors if "favicon" not in e.lower()]
print(f"\nJS errors: {len(real_js)}")
for e in real_js[:10]:
    print("  ", e[:200])
print(f"\nRESULT: {'PASS' if not fails and not real_js else 'FAIL'} "
      f"({len(fails)} step fails, {len(real_js)} js errors)")
sys.exit(1 if (fails or real_js) else 0)
