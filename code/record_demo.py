"""90-second demo recording: one full vague-memory search in Jog mode.

Produces figures/demo_recording_90s.webm (Playwright WebM video).
Run: BASE/.venv/bin/python code/record_demo.py
"""
import os, sys, glob
from playwright.sync_api import sync_playwright

URL = "http://localhost:8502"
OUT = "figures"

X1 = ("I'm trying to find a photo of a small café on our Goa trip. I think it was "
      "daytime and we were having coffee before the beach. I don't remember which "
      "day or which café.")

def click(page, name):
    b = page.get_by_role("button", name=name)
    b.first.wait_for(state="visible", timeout=20000)
    b.first.scroll_into_view_if_needed()
    b.first.click()
    page.wait_for_timeout(2500)

def main():
    vdir = "/tmp/demo_video"
    os.makedirs(vdir, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844},
                                  device_scale_factor=2, is_mobile=True, has_touch=True,
                                  record_video_dir=vdir,
                                  record_video_size={"width": 390, "height": 844})
        page = ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(14000)  # CLIP cold start (kept in the video: honest loading)
        page.wait_for_timeout(2000)

        # dismiss onboarding if present
        if page.get_by_role("button", name="Not sure", exact=True).count():
            click(page, "Not sure")

        # guided flow via bottom nav Gemini
        g = page.get_by_role("button", name="Ask Gemini")
        g.last.click(); page.wait_for_timeout(2500)

        page.locator("textarea").first.type(X1, delay=28)  # typed, human-paced
        page.wait_for_timeout(1200)
        click(page, "Find it")
        page.wait_for_timeout(4000)  # let moments settle

        # answer one question if shown
        for lab in ("Morning", "Afternoon", "Goa", "Café", "Daytime",
                    "I don't remember"):
            if page.get_by_role("button", name=lab, exact=True).count():
                click(page, lab)
                break
        page.wait_for_timeout(2500)

        # this-or-that if shown
        if page.get_by_role("button", name="Left is closer", exact=True).count():
            click(page, "Left is closer")
            page.wait_for_timeout(2000)

        # confirm a moment
        if page.get_by_role("button", name="This is it ✔", exact=True).count():
            click(page, "This is it ✔")
            if page.get_by_role("button", name="Yes", exact=True).count():
                click(page, "Yes")
            page.wait_for_timeout(3500)  # linger on success screen

        page.wait_for_timeout(1500)
        video_path = page.video.path()
        ctx.close()
        browser.close()
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "demo_recording_90s.webm")
    os.replace(video_path, dst)
    print("video:", dst, os.path.getsize(dst), "bytes")

if __name__ == "__main__":
    main()
