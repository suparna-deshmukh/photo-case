"""
Purpose: D11 - browser test for the Discovery Engine Streamlit app (local or
         live URL) using Playwright in a FRESH context (no logged-in profile).
         Walks all 4 tabs, one preset, one Try-it analysis; screenshots to a
         folder; reports PASS/FAIL per step.
Inputs : --url (default http://localhost:8501), --out (default
         BASE/figures/screens), --mobile (mobile viewport).
Outputs: <out>/discovery_01_ask.png ... discovery_05_scorecard.png; exit code.
Usage  : .venv/bin/python code/test_discovery_app.py [--url U] [--out DIR] [--mobile]
"""
import argparse
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

SAMPLE = ("I am looking for a photo from my trip to the mountains with my friends two summers ago. "
          "We were at a lake and I remember the sun setting. The search for 'mountains' shows nothing "
          "useful and I keep scrolling the timeline to find it.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8501")
    ap.add_argument("--out", default=str(BASE / "figures" / "screens"))
    ap.add_argument("--mobile", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright
    results = []

    def check(name, ok, detail=""):
        results.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 390, "height": 844} if args.mobile else {"width": 1440, "height": 900})
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_selector("h1, h2, h3, [data-testid='stAppViewContainer']", timeout=120000)
            time.sleep(6)
            ok = page.locator("text=Photo Retrieval Discovery Engine").count() > 0 or page.locator("text=retrieval episodes").count() > 0
            check("app loads", ok, page.title())
            page.screenshot(path=str(out / "discovery_01_ask.png"), full_page=False)

            btn = page.get_by_role("button", name="What kinds of old photos")
            ok = btn.count() > 0
            if ok:
                btn.first.click()
                time.sleep(4)
                ok = page.locator("text=Evidence view").count() > 0 or page.locator("text=Most common").count() > 0 or page.locator("text=n=").count() > 0
            check("preset answer renders", ok, "")
            page.screenshot(path=str(out / "discovery_02_preset.png"))

            tab = page.get_by_role("tab", name="Explore")
            ok = tab.count() > 0
            if ok:
                tab.first.click()
                time.sleep(5)
            check("explore tab opens", ok, "")
            page.screenshot(path=str(out / "discovery_03_explore.png"))

            tab = page.get_by_role("tab", name="Try it")
            ok = tab.count() > 0
            if ok:
                tab.first.click()
                time.sleep(2)
                ta = page.locator("textarea")
                ok = ta.count() > 0
                if ok:
                    ta.first.click()
                    page.keyboard.type(SAMPLE, delay=5)
                    time.sleep(2)
                    btn = page.get_by_role("button", name="Analyze").first
                    for _ in range(15):
                        if not btn.is_disabled():
                            break
                        time.sleep(1)
                    page.get_by_role("button", name="Analyze").first.click()
                    try:
                        page.wait_for_selector("text=Nearest-episode estimate", timeout=240000)
                    except Exception:
                        time.sleep(30)
                    time.sleep(4)
                    ok = page.locator("text=Nearest-episode estimate").count() > 0
            check("try-it nearest estimate", ok, "")
            page.screenshot(path=str(out / "discovery_04_tryit.png"), full_page=True)

            tab = page.get_by_role("tab", name="Opportunity scorecard")
            ok = tab.count() > 0
            if ok:
                tab.first.click()
                time.sleep(4)
                ok = page.locator("text=scorecard").count() > 0 or page.locator("text=Opportunity").count() > 0
            check("scorecard tab opens", ok, "")
            page.screenshot(path=str(out / "discovery_05_scorecard.png"))

            if errors:
                check("no page errors", False, "; ".join(errors)[:300])
            else:
                check("no page errors", True, "")
        except Exception as e:
            check("fatal", False, f"{type(e).__name__}: {str(e)[:300]}")
        finally:
            browser.close()
    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"BROWSER TEST: {len(results) - n_fail}/{len(results)} PASS, {n_fail} FAIL")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
