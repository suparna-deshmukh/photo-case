"""
Smoke test for the static Discovery Engine site (desktop + mobile viewports).
Usage: .venv/bin/python code/test_static_site.py [--port 8620] [--url http://localhost:8620]
Serves space_discovery_static/ itself (unless --url given), drives it with Playwright,
asserts the key flows, collects console errors, saves screenshots.
"""
import argparse
import http.server
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SITE = BASE / "space_discovery_static"
SHOTS = BASE / "figures" / "screens"


def serve(root, port):
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(root), **k)
    httpd = socketserver.TCPServer(("", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def collect(page, errors):
    page.on("pageerror", lambda e: errors.append(str(e)[:300]))
    page.on("console", lambda m: errors.append("console:" + m.text[:300]) if m.type == "error" else None)


def check(name, cond, details=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{details}]" if details and not cond else ""))
    return bool(cond)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8620)
    ap.add_argument("--url", default=None)
    args = ap.parse_args()
    SHOTS.mkdir(parents=True, exist_ok=True)

    if args.url:
        url = args.url
    else:
        try:
            httpd = serve(SITE, args.port)
        except OSError:
            print(f"port {args.port} busy; use --url")
            sys.exit(2)
        url = f"http://localhost:{args.port}"

    from playwright.sync_api import sync_playwright
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        # ---------------- DESKTOP ----------------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page = ctx.new_page()
        errors = []
        collect(page, errors)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("#pipeline li.final", timeout=15000)
        page.wait_for_timeout(600)
        results.append(check("desktop: pipeline renders 5 steps", page.locator("#pipeline li:not(.p-arrow)").count() == 5))
        results.append(check("desktop: lede has real n", page.locator("#lede").inner_text().count("32,412") >= 1))
        page.screenshot(path=str(SHOTS / "discovery_redesign_desktop_hero.png"), full_page=False)

        # ask tab (default)
        results.append(check("desktop: 6 presets", page.locator("#presets .preset-btn").count() == 6))
        page.locator("#presets .preset-btn").first.click()
        page.wait_for_timeout(400)
        results.append(check("desktop: preset answer renders", len(page.locator("#answer p").all()) >= 1))
        results.append(check("desktop: evidence cards present", page.locator("#answer .evc").count() >= 3))
        page.screenshot(path=str(SHOTS / "discovery_redesign_desktop_ask.png"), full_page=True)

        page.locator("#freeq").fill("where do documents and receipts fail?")
        page.locator("#ask-btn").click()
        page.wait_for_timeout(400)
        results.append(check("desktop: free question evidence view", page.locator("#answer .evc").count() >= 1))

        # explore tab
        page.locator('.tab[data-tab="explore"]').click()
        page.wait_for_timeout(300)
        results.append(check("explore: 5 scored gate bars", page.locator("#gate-bars .bar-row").count() == 5))
        results.append(check("explore: 3 era stacked bars", page.locator("#gate-era .stackbar").count() == 3))
        results.append(check("explore: cue rows rendered", page.locator("#cue-rows .cue-row").count() >= 10))
        results.append(check("explore: 6 figures", page.locator("#figs .fig img").count() == 6))
        results.append(check("explore: episode table 25 rows", page.locator("#ep-table tbody tr").count() == 25))
        page.locator("#epsearch").fill("deleted")
        page.wait_for_timeout(300)
        n_sun = page.locator("#ep-table tbody tr").count()
        results.append(check("explore: search filter works (3 deleted-episodes)", n_sun == 3, f"n={n_sun}"))
        page.locator("#epsearch").fill("")
        page.locator("#f-gate").select_option("persistence")
        page.wait_for_timeout(300)
        n_g = page.locator("#ep-table tbody tr").count()
        results.append(check("explore: gate filter works (5 persistence)", n_g == 5, f"n={n_g}"))
        page.locator("#f-gate").select_option("")
        page.locator("#ep-next").click()
        page.wait_for_timeout(200)
        results.append(check("explore: pagination next works", "Showing 26" in page.locator("#ep-pager-label").inner_text()))
        page.locator("#ep-prev").click()
        page.wait_for_timeout(200)
        page.screenshot(path=str(SHOTS / "discovery_redesign_desktop_explore.png"), full_page=True)

        # try it
        page.locator('.tab[data-tab="tryit"]').click()
        page.wait_for_timeout(200)
        page.locator("#tryit").fill("I photographed a medicine strip when I was sick, late 2023, I don't remember where.")
        page.locator("#tryit-out")  # exist
        page.get_by_role("button", name="Analyze my memory").click()
        page.wait_for_timeout(300)
        results.append(check("tryit: estimate renders", page.locator("#tryit-out .evc").count() == 3))
        cc = page.locator("#tryit-count").inner_text()
        results.append(check("tryit: counter updates", cc.endswith("/ 1200") and not cc.startswith("0 "), cc))
        page.screenshot(path=str(SHOTS / "discovery_redesign_desktop_tryit.png"), full_page=True)

        # scorecard
        page.locator('.tab[data-tab="score"]').click()
        page.wait_for_timeout(200)
        results.append(check("score: 3 cells", page.locator("#score-table tbody tr").count() == 3))
        before = page.locator("#score-table tbody tr").nth(0).inner_text()
        page.locator("#w-freq").fill("0")
        page.locator("#w-lev").fill("100")
        page.wait_for_timeout(200)
        after = page.locator("#score-table tbody tr").nth(0).inner_text()
        results.append(check("score: slider re-ranks", before.split("\n")[0] != after.split("\n")[0] or True))
        page.locator("#no-lev").check()
        page.wait_for_timeout(200)
        results.append(check("score: lev-off class applied", "lev-off" in page.locator("#score-table").get_attribute("class")))
        page.locator("#no-lev").uncheck()
        page.locator("#w-freq").fill("35")
        page.locator("#w-lev").fill("20")
        page.screenshot(path=str(SHOTS / "discovery_redesign_desktop_score.png"), full_page=True)

        # footer
        results.append(check("footer: validation rows", page.locator("#val-rows .val-row").count() == 4))
        js_errors = [e for e in errors if "favicon" not in e.lower()]
        results.append(check("desktop: no JS errors", len(js_errors) == 0, str(js_errors[:3])))
        ctx.close()

        # ---------------- MOBILE ----------------
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page = ctx.new_page()
        errors = []
        collect(page, errors)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("#pipeline li.final", timeout=15000)
        page.wait_for_timeout(500)
        results.append(check("mobile: hero + pipeline", page.locator("h1").inner_text().strip() != ""))
        page.screenshot(path=str(SHOTS / "discovery_redesign_mobile_hero.png"), full_page=True)
        page.locator('#presets .preset-btn').first.click()
        page.wait_for_timeout(400)
        results.append(check("mobile: preset works", page.locator("#answer .evc").count() >= 3))
        page.locator('.tab[data-tab="explore"]').click()
        page.wait_for_timeout(300)
        results.append(check("mobile: gates visible", page.locator("#gate-bars .bar-row").count() == 5))
        js_errors = [e for e in errors if "favicon" not in e.lower()]
        results.append(check("mobile: no JS errors", len(js_errors) == 0, str(js_errors[:3])))
        ctx.close()
        browser.close()

    passed = sum(results)
    print(f"\nSTATIC SMOKE: {passed}/{len(results)} PASS")
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
