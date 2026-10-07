from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    cons = []
    page.on("console", lambda m: cons.append(m.text[:200]) if m.type == "error" else None)
    resp = []
    page.on("response", lambda r: resp.append((r.status, r.url)) if "woff2" in r.url else None)
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(15000)
    print("woff2 responses:", resp[:5])
    print("font errors:", [c for c in cons if "font" in c.lower() or "sfnt" in c.lower()][:4])
    print("GSF check:", page.evaluate("() => { try { return document.fonts.check('16px \"Google Sans Flex\"'); } catch(e) { return String(e); } }"))
    print("faces:", page.evaluate("() => [...document.fonts].map(f => f.family + ' ' + f.status).slice(0, 6)"))
    b.close()
