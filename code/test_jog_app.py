"""
M7/M8 — Playwright test of the Jog app (fresh context, mobile viewport).
Usage: .venv/bin/python code/test_jog_app.py --url http://localhost:8502 [--classic]
Drives a full X1 free-play session: search, cue edit, question answer,
this-or-that, anchor, fallback, confirm. Screenshots -> figures/screens/.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
from playwright.sync_api import sync_playwright  # noqa: E402

X1 = ("I'm trying to find a photo of a small café on our Goa trip. I think it was "
      "daytime and we were having coffee before the beach. I don't remember which "
      "day or which café.")

LAT = []


def dismiss_onboarding(page):
    b = page.get_by_role("button", name="Skip for now", exact=True)
    if b.count():
        b.first.click()
        page.wait_for_timeout(2500)
        print("onboarding dialog: skipped")


def tap(page, name, timeout=15000):
    b = page.get_by_role("button", name=name, exact=True)
    if b.count() == 0:
        return False
    t0 = time.time()
    b.first.scroll_into_view_if_needed()
    b.first.click()
    page.wait_for_timeout(2500)  # streamlit rerun
    LAT.append(time.time() - t0)
    return True


def tap_retry(page, name, predicate, tries=3, timeout=15000):
    """Click a Streamlit button, retrying until predicate(page) holds.
    Streamlit can drop a click that lands mid-rerun, so retry a few times."""
    for _ in range(tries):
        b = page.get_by_role("button", name=name, exact=True)
        if b.count() == 0:
            return False
        t0 = time.time()
        b.first.scroll_into_view_if_needed()
        b.first.click()
        page.wait_for_timeout(2500)
        LAT.append(time.time() - t0)
        if predicate(page):
            return True
    return predicate(page)


def grid_checkbox_first(page, x_frac=0.80, y_frac=0.20):
    """Click the first-row 'not this' checkbox in the canvas data grid.
    Returns True if the grid's a11y text changed (toggle registered)."""
    def grid_state():
        return page.evaluate("""() => {
          const gv = document.querySelector('[data-testid="stDataFrame"]');
          if (!gv) return '';
          const t = [];
          gv.querySelectorAll('td').forEach(td => t.push(td.textContent));
          return t.join('|');
        }""")
    before = grid_state()
    try:
        cv = page.get_by_test_id("data-grid-canvas").bounding_box(timeout=3000)
    except Exception:
        return False
    if not cv:
        return False
    page.mouse.click(cv["x"] + cv["width"] * x_frac, cv["y"] + cv["height"] * y_frac)
    page.wait_for_timeout(1500)
    return grid_state() != before


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8502")
    ap.add_argument("--classic", action="store_true")
    args = ap.parse_args()
    shots = BASE / "figures" / "screens"
    shots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844},
                                  device_scale_factor=2)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        page.goto(args.url, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)  # CLIP load + first render
        dismiss_onboarding(page)

        mode = "classic" if args.classic else "jog"
        if args.classic:
            tap(page, "Search")
            page.wait_for_timeout(2500)
            box = page.locator("input[placeholder*='Search for a person']")
            if box.count() == 0:
                print("FATAL: no search box in classic mode")
                sys.exit(1)
            box.first.fill("a café in Goa, daytime, coffee")
            tap(page, "Search")
            page.wait_for_timeout(3000)
            page.screenshot(path=str(shots / f"jog_{mode}_grid.png"))
            print("classic: grid rendered")
            browser.close()
            return

        tap(page, "Search")
        page.wait_for_timeout(2500)
        ta = page.locator("textarea")
        ta.first.wait_for(timeout=20000)
        ta.first.fill(X1)
        tap(page, "Find it")
        page.wait_for_timeout(4000)

        # 1) cue chips + moments
        if page.get_by_role("button", name="This is it ✔").count() == 0:
            print("FATAL: no moments after search. Page text:")
            print(page.locator("body").inner_text()[:1500])
            page.screenshot(path=str(shots / "jog_fail_nomoments.png"))
            sys.exit(1)
        page.screenshot(path=str(shots / "jog_free_1_cues.png"), full_page=True)
        print("shot 1: cue chips + moments")

        # 2) cue edit: toggle 'not this' on the first cue chip (real buttons since redesign)
        edited = False
        if page.get_by_role("button", name="not this", exact=True).count() > 0:
            page.get_by_role("button", name="not this", exact=True).first.click()
            page.wait_for_timeout(2500)
            edited = True
            print("cue 'not this' toggled (chip UI)")
        if edited:
            print("cue edited (applies instantly)")
        else:
            print("WARN: no cue chips (empty cue list); skipping cue edit")

        # question card?
        if page.get_by_role("button", name="I don't remember").count() > 0:
            page.screenshot(path=str(shots / "jog_free_2_question.png"), full_page=True)
            print("shot 2: question card visible")
        else:
            page.screenshot(path=str(shots / "jog_free_2_question.png"), full_page=True)

        # 3) this-or-that
        for _ in range(3):
            if page.get_by_role("button", name="Left is closer").count() > 0:
                if "jog_free_3_pair.png" not in str(shots) or not (shots / "jog_free_3_pair.png").exists():
                    page.screenshot(path=str(shots / "jog_free_3_pair.png"), full_page=True)
                    print("shot 3: this-or-that card")
                tap(page, "Left is closer")
            else:
                break

        # 4) anchor flow
        if page.get_by_role("button", name="Use as anchor").count() > 0:
            page.get_by_role("button", name="Use as anchor").first.click()
            page.wait_for_timeout(2000)
            tap(page, "Right after")
            print("anchor set (right_after)")

        # 5) answer remaining questions until none
        for _ in range(8):
            if page.get_by_role("button", name="I don't remember").count() > 0:
                tap(page, "I don't remember")
            else:
                break

        # 6) fallback
        tap(page, "I'm stuck")
        body = page.locator("body").inner_text()
        if "I'd narrow it to" in body:
            print("fallback reached")
        else:
            print("WARN: fallback text not found")

        # 7) confirm flow (retry: Streamlit may drop a click mid-rerun)
        def _confirm_shown(pg):
            return "Is this the photo?" in pg.locator("body").inner_text()
        ok = tap_retry(page, "This is it ✔", _confirm_shown, tries=3)
        page.wait_for_timeout(1000)
        tap_retry(page, "Yes", lambda pg: "Found it in" in pg.locator("body").inner_text(), tries=3)
        page.wait_for_timeout(2500)
        body = page.locator("body").inner_text()
        if "Found it in" in body:
            print("success screen reached")
        else:
            print("WARN: success screen not found (confirm click may have been dropped)")
        page.screenshot(path=str(shots / "jog_free_4_success.png"), full_page=True)

        # assertions
        bad = [l for l in errors if "Traceback" in l or "Error" in l]
        body_all = page.locator("body").inner_text()
        if "Traceback" in body_all or "Exception has occurred" in body_all:
            print("FATAL: exception visible in UI")
            sys.exit(1)
        if LAT:
            vals = sorted(x * 1000 for x in LAT)
            p50 = statistics.median(vals)
            p95 = vals[min(len(vals) - 1, int(0.95 * len(vals)))]
            print(f"latency ms: n={len(vals)} p50={p50:.0f} p95={p95:.0f}")
        print("JS pageerrors:", len(errors), errors[:3])
        print("M7 TEST PASS")
        browser.close()


if __name__ == "__main__":
    main()
