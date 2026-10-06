"""Revamp probe: load app at a viewport, report console errors + leaks + screenshots."""
import sys, re
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"
SHOT = "figures/screens"

def run(viewport, name, steps=None, url=""):
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport=viewport)
        page = ctx.new_page()
        errs = []
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(URL + url, wait_until="domcontentloaded")
        page.wait_for_timeout(16000)  # first script run + CLIP warm
        txt = page.inner_text("body")
        err_card = page.locator("text=Something went wrong").count() > 0
        if err_card:
            print("ERROR CARD TEXT:", page.locator("text=Something went wrong").first.inner_text()[:400])
        if steps:
            steps(page)
            page.wait_for_timeout(1200)
            txt = page.inner_text("body")
        page.screenshot(path=f"{SHOT}/{name}.png", full_page=False, animations="disabled")
        print(f"== {name} {viewport} == err_card={err_card}")
        print("js errors:", errs[:8] if errs else "none")
        # quick visible-text sanity
        for bad in ["<", "st-key", "stButton", "None", "img_0"]:
            if bad in txt:
                print(f"  TEXT-CHECK found {bad!r}")
        b.close()
    return

W = {"d": {"width": 1440, "height": 900},
     "t": {"width": 768, "height": 1024},
     "m": {"width": 390, "height": 844}}
which = sys.argv[1] if len(sys.argv) > 1 else "d"
url = "?admin=1" if (len(sys.argv) > 2 and sys.argv[2] == "admin") else ""
run(W[which], f"revamp_{which}_home", url=url)
