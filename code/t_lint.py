from playwright.sync_api import sync_playwright
import re, json
URL = "http://localhost:8502"
PATTERN = re.compile(r"[A-Z]{3,}_[A-Z]{3,}|undefined|\bNaN\b|\bNone\b|img_\d+|\be\d{2}\b|\b1 photos\b|\bmixed\b|Ask Gemini|free tier|Voice search")
def lint(page, tag):
    r = page.evaluate("""() => document.body.innerText""")
    hits = {}
    for m in PATTERN.finditer(r):
        ctx = r[max(0, m.start()-40):m.end()+40].replace("\n", " | ")
        hits[m.group(0)] = hits.get(m.group(0), 0) + 1
        if hits[m.group(0)] == 1:
            hits["  ~" + m.group(0) + "~"] = ctx[:90]
    print(tag, "leaks:", json.dumps({k: v for k, v in hits.items() if not k.startswith("  ~")}) or "NONE")
    for k, v in hits.items():
        if k.startswith("  ~"):
            print("   ctx:", v)
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(16000)
    lint(page, "HOME")
    page.locator(".st-key-pill_ask_chip button").click(timeout=10000)
    page.wait_for_timeout(2500)
    lint(page, "ASK_IDLE")
    page.locator("textarea").first.type("a cafe somewhere in Goa, daytime I think", delay=20)
    page.locator(".st-key-ask_go button").click(timeout=10000)
    page.wait_for_timeout(12000)
    lint(page, "ASK_SESSION")
    # classic search
    page.locator(".st-key-ic_searchback button").click(timeout=8000)
    page.wait_for_timeout(2000)
    inp = page.locator('input[placeholder="Search your photos"]')
    inp.click(); inp.fill("sunset boat"); page.wait_for_timeout(1500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(9000)
    lint(page, "SEARCH")
    b.close()
