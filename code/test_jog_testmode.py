"""M8 — Playwright dummy test-mode sessions (P1, P2) + admin log export.

Drives ?test=1 end to end (2 practice + 8 tasks, minimal interaction:
jog = Find it + give up; classic = one search + give up), downloads the
per-session log and the full admin log, then verifies:
  * task_start + task_end exist for every task (and practice)
  * jog tasks carry cues_parsed with parse_source in {cache, llm, rules}
  * classic tasks carry results_shown
  * counterbalancing queue matches the formula for P1..P6
Prints the first 15 lines of the admin log. Exit 0 = PASS.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "research" / "test_logs"
X = ["X1", "X2", "X3", "X4"]
Y = ["Y1", "Y2", "Y3", "Y4"]


def expected_queue(idx: int):
    mode_x = "classic" if idx % 2 == 0 else "jog"
    mode_y = "jog" if mode_x == "classic" else "classic"
    first_is_x = (idx // 2) % 2 == 0
    first = X if first_is_x else Y
    second = Y if first_is_x else X
    mm = {t: mode_x for t in X}
    mm.update({t: mode_y for t in Y})
    q = [("P1", "classic", True), ("P2", "jog", True)]
    q += [(t, mm[t], False) for t in first + second]
    return q


def _body(page):
    return page.locator("body").inner_text()


def wait_stable(page, timeout=30000, quiet_ms=1600):
    """Wait until the page text stops changing (no rerun in flight)."""
    t0 = time.time()
    last = object()
    last_change = time.time()
    while (time.time() - t0) * 1000 < timeout:
        try:
            cur = page.locator("body").inner_text()
        except Exception:
            cur = ""
        if cur != last:
            last = cur
            last_change = time.time()
        elif (time.time() - last_change) * 1000 >= quiet_ms:
            return True
        time.sleep(0.35)
    return True


def click_until(page, name, predicate, tries=6, wait=2500):
    """Streamlit drops button clicks that land mid-rerun; retry until predicate."""
    for _ in range(tries):
        wait_stable(page)
        b = page.get_by_role("button", name=name, exact=True)
        if b.count() == 0:
            page.wait_for_timeout(wait)
            continue
        b.first.scroll_into_view_if_needed()
        b.first.click()
        page.wait_for_timeout(wait)
        wait_stable(page)
        if predicate(page):
            return True
    return predicate(page)


def dismiss_onboarding(page):
    b = page.get_by_role("button", name="Skip for now", exact=True)
    if b.count():
        b.first.click()
        page.wait_for_timeout(2500)
        print("onboarding dialog: skipped")


def drive(page, url: str, code: str):
    idx = int(code[1:]) - 1
    page.goto(url + "/?test=1", wait_until="domcontentloaded")
    dismiss_onboarding(page)
    page.get_by_label("Your participant code (e.g. P1)").wait_for(timeout=30000)
    page.get_by_label("Your participant code (e.g. P1)").fill(code)
    ok = click_until(page, "Start session", lambda pg: "practice" in _body(pg) or "task 1 of 8" in _body(pg))
    if not ok:
        raise RuntimeError("Start session not confirmed")
    for tid, mode, practice in expected_queue(idx):
        ok = click_until(page, "Start task", lambda pg: "I give up" in _body(pg))
        if not ok:
            raise RuntimeError(f"{tid}: task never entered running phase")
        if mode == "jog":
            ok = click_until(page, "Find it",
                             lambda pg: pg.get_by_role("button", name="This is it ✔").count() > 0)
            if not ok:
                raise RuntimeError(f"{tid}: jog moments never rendered")
        else:
            box = page.locator("input[placeholder*='café']").first
            box.wait_for(state="visible", timeout=30000)
            box.fill("a photo from a trip")
            ok = click_until(page, "Search",
                             lambda pg: pg.get_by_role("button", name="This is it ✔").count() > 0)
            if not ok:
                raise RuntimeError(f"{tid}: classic results never rendered")
        ok = click_until(page, "I give up",
                         lambda pg: pg.get_by_role("button", name="Continue", exact=True).count() > 0)
        if not ok:
            raise RuntimeError(f"{tid}: give-up did not reach post phase")
        last = (tid, mode, practice) == expected_queue(idx)[-1]
        ok = click_until(page, "Continue",
                         lambda pg: ("Start task" in _body(pg)) or ("Session complete" in _body(pg)))
        if not ok:
            raise RuntimeError(f"{tid}: continue did not advance")
        if last:
            break
    dl = page.get_by_role("button", name="Download my session log")
    dl.wait_for(state="visible", timeout=45000)
    with page.expect_download() as dinfo:
        dl.click()
    dinfo.value.save_as(OUT / f"session_{code}.jsonl")
    page.goto(url + "/?admin=1", wait_until="domcontentloaded")
    page.get_by_role("button", name="Download all events (events.jsonl)").wait_for(timeout=30000)
    page.get_by_role("button", name="Download all events (events.jsonl)").click()
    page.wait_for_timeout(1000)
    with page.expect_download() as dinfo2:
        page.get_by_role("button", name="Download events.jsonl").click()
    dinfo2.value.save_as(OUT / f"events_{code}.jsonl")


def verify(code: str) -> list:
    idx = int(code[1:]) - 1
    lines = [json.loads(l) for l in (OUT / f"session_{code}.jsonl").read_text().splitlines() if l.strip()]
    events = [e for e in lines if e.get("event")]
    probs = []
    ss = [e for e in events if e["event"] == "session_start"]
    if not ss:
        probs.append("missing session_start")
    else:
        q = [(t, m, bool(p)) for t, m, p in ss[0]["payload"]["queue"]]
        exp = expected_queue(idx)
        if q != exp:
            probs.append(f"counterbalance mismatch: {q} != {exp}")
    for tid, mode, practice in expected_queue(idx):
        starts = [e for e in events if e["event"] == "task_start" and e["task_id"] == tid]
        ends = [e for e in events if e["event"] == "task_end" and e["task_id"] == f"test_{tid}"]
        if not starts:
            probs.append(f"{tid}: missing task_start")
        if not ends:
            probs.append(f"{tid}: missing task_end")
        else:
            print(f"  {tid} ({mode}, {'practice' if practice else 'task'}): "
                  f"outcome={ends[0]['payload'].get('outcome')} "
                  f"{ends[0]['payload'].get('seconds')}s q={ends[0]['payload'].get('n_queries')}")
        if mode == "jog":
            cp = [e for e in events if e["event"] == "cues_parsed" and e["task_id"] == f"test_{tid}"]
            if not cp or cp[0]["payload"].get("parse_source") not in ("cache", "llm", "rules"):
                probs.append(f"{tid}: missing/invalid cues_parsed {cp[:1]}")
        else:
            rs = [e for e in events if e["event"] == "results_shown" and e["task_id"] == f"test_{tid}"]
            if not rs:
                probs.append(f"{tid}: missing results_shown")
    post = [e for e in events if e["event"] == "post_task"]
    if len(post) != 10:
        probs.append(f"post_task count {len(post)} != 10")
    return probs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8502")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    failures = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for code in ("P1", "P2"):
            ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
            pg = ctx.new_page()
            print(f"--- driving {code} ---")
            try:
                drive(pg, args.url, code)
            finally:
                ctx.close()
            print(f"--- verifying {code} ---")
            probs = verify(code)
            for x in probs:
                print("  PROBLEM:", x)
            failures += [f"{code}: {x}" for x in probs]
        # counterbalancing table P1..P6 (computed; P1/P2 also observed above)
        print("--- counterbalance table P1..P6 ---")
        for i in range(6):
            q = expected_queue(i)
            xmode = next(m for t, m, _ in q if t == "X1")
            order = "X..Y.." if q[2][0] == "X1" else "Y..X.."
            print(f"  P{i+1}: X={xmode.upper():7s} first_set={order}")
        b.close()
    admin = (OUT / "events_P2.jsonl").read_text().splitlines()
    print("--- first 15 lines of events_P2.jsonl ---")
    for l in admin[:15]:
        print(l[:200])
    if failures:
        print("M8 TEST FAIL")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("M8 TEST PASS")


if __name__ == "__main__":
    main()
