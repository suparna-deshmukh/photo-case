"""Repro: walk every free-play branch of the Jog app; report the exact step
that triggers 'Something went wrong in the demo' (widget double-instantiation)."""
import sys
from playwright.sync_api import sync_playwright

X1 = ("I'm trying to find a photo of a small café on our Goa trip. I think it was "
      "daytime and we were having coffee before the beach. I don't remember which "
      "day or which café.")

URL = "http://localhost:8502"

def err_on(page):
    el = page.locator("text=Something went wrong in the demo")
    if el.count() > 0:
        tech = page.locator("text=technical note").first
        tech_txt = tech.inner_text() if tech.count() else "?"
        return True, tech_txt
    return False, ""

def step(page, name, fn):
    e, tech = err_on(page)
    if e:
        print(f"STOP: error before step '{name}': {tech}")
        page.screenshot(path="figures/screens/jog_repro_error.png", full_page=True)
        sys.exit(1)
    print(f"--- {name}")
    fn()
    page.wait_for_timeout(2500)
    e, tech = err_on(page)
    if e:
        print(f"FAIL at step '{name}': {tech}")
        page.screenshot(path="figures/screens/jog_repro_error.png", full_page=True)
        sys.exit(1)
    print(f"ok: {name}")

def dismiss_onboarding(page):
    b = page.get_by_role("button", name="Skip for now", exact=True)
    if b.count():
        b.first.click()
        page.wait_for_timeout(2500)
        print("onboarding dialog: skipped")

def btn(page, name):
    b = page.get_by_role("button", name=name, exact=True)
    if b.count() == 0:
        raise RuntimeError(f"button not found: {name}")
    b.first.scroll_into_view_if_needed()
    b.first.click()

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(10000)
    dismiss_onboarding(page)
    step(page, "open search (home pill)", lambda: btn(page, "Search Google Photos"))

    def start_search():
        page.locator("textarea").first.fill(X1)
        btn(page, "Find it")
    step(page, "find it", start_search)

    def cue_toggle():
        btn(page, "not this")
    if page.get_by_role("button", name="not this", exact=True).count():
        step(page, "cue 'not this'", cue_toggle)

    def answer_q():
        for opt in ["Indoors", "Outdoors", "Morning", "Afternoon", "Evening", "Night",
                    "Something else", "I don't remember"]:
            b = page.get_by_role("button", name=opt, exact=True)
            if b.count() > 0:
                b.first.click()
                return
        raise RuntimeError("no question options found")
    if page.get_by_role("button", name="I don't remember", exact=True).count():
        step(page, "answer question (I don't remember)", answer_q)

    def pair_left():
        btn(page, "Left is closer")
    if page.get_by_role("button", name="Left is closer", exact=True).count():
        step(page, "pair: left closer", pair_left)

    def use_anchor():
        btn(page, "Use as anchor")
    if page.get_by_role("button", name="Use as anchor", exact=True).count():
        step(page, "use as anchor", use_anchor)
        def same_day():
            btn(page, "Same day")
        step(page, "anchor: same day", same_day)

    def stuck():
        btn(page, "I'm stuck")
    step(page, "I'm stuck", stuck)

    def open_fallback_expander():
        exp = page.locator("[data-testid='stExpander']").last
        exp.locator("summary").click()
    step(page, "open fallback expander", open_fallback_expander)

    def fb_this_one():
        btn(page, "✔ This one")
    if page.get_by_role("button", name="✔ This one", exact=True).count():
        step(page, "fallback: this one", fb_this_one)
        def cfm_no():
            btn(page, "No")
        step(page, "confirm: No", cfm_no)

    def this_is_it():
        btn(page, "This is it ✔")
    if page.get_by_role("button", name="This is it ✔", exact=True).count():
        step(page, "moment: this is it", this_is_it)
        def cfm_yes():
            btn(page, "Yes")
        step(page, "confirm: Yes", cfm_yes)

    def find_another():
        btn(page, "Search another")
    step(page, "find another", find_another)
    step(page, "second search", start_search)

    def show_all():
        btn(page, "Show all in this moment")
    step(page, "show all in moment", show_all)
    step(page, "grid: this one", fb_this_one)
    step(page, "confirm: No", cfm_no)
    step(page, "start over (fallback)", lambda: btn(page, "Start over"))

    def to_search_view():
        btn(page, "Photos")
        page.get_by_role("button", name="Search Google Photos", exact=True) \
             .wait_for(state="visible", timeout=15000)
        btn(page, "Search Google Photos")
    step(page, "to search view", to_search_view)

    def classic_search():
        page.locator("input[placeholder*='Search for a person']").first.fill("a café in Goa, daytime")
        btn(page, "Search")
    step(page, "classic search", classic_search)
    step(page, "classic: this is it", this_is_it)
    step(page, "classic confirm: Yes", lambda: btn(page, "Yes"))
    step(page, "classic: search something else", lambda: btn(page, "Search something else"))

    def back_to_photos():
        btn(page, "Photos")
    step(page, "back to photos", back_to_photos)
    step(page, "search tab again", lambda: btn(page, "Search Google Photos"))
    step(page, "about page", lambda: btn(page, "About"))
    step(page, "reset all", lambda: btn(page, "Reset"))

    page.screenshot(path="figures/screens/jog_repro_final.png", full_page=True)
    print("REPRO COMPLETE: no widget error in free-play walk")
    browser.close()
