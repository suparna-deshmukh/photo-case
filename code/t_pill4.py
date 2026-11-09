from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto("http://localhost:8502", wait_until="domcontentloaded")
    page.wait_for_timeout(14000)
    r = page.evaluate("""() => {
      const el = document.querySelector('.st-key-gpsearchpill [data-testid="stHorizontalBlock"]');
      const out = [];
      for (const sheet of document.styleSheets) {
        let rules;
        try { rules = sheet.cssRules; } catch (e) { continue; }
        if (!rules) continue;
        for (const rule of rules) {
          if (!rule.selectorText || !rule.style) continue;
          if (!/height/.test(rule.style.cssText)) continue;
          let m = false;
          try { m = el.matches(rule.selectorText); } catch (e) {}
          if (m) out.push({sel: rule.selectorText.slice(0, 90),
                           decl: rule.style.cssText.split(';').filter(d => /height/i.test(d)).join('; ').slice(0, 120),
                           sheet: (sheet.href || 'inline').slice(-30)});
        }
      }
      return out;
    }""")
    print(json.dumps(r, indent=1))
    b.close()
