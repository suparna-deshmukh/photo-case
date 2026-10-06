"""
Purpose: D1B checkpoint tests for code/live_llm.py. Five tests:
         (1) no env vars -> not_configured, live_json None in <0.1 s;
         (2) wrong base URL -> None within ~4 s, no exception, breaker opens
             after 2 consecutive failures;
         (3) real .env hosted layer -> parsed JSON for a trivial prompt and the
             second identical call is a cache hit (SKIPPED if hosted key empty);
         (4) PER_SESSION_CAP=2 -> third distinct call returns None (mock server);
         (5) LIVE_DAILY_CAP=2 -> third call returns None (mock server).
Inputs:  BASE/.env for test 3 only (values loaded in-process, never printed).
Outputs: one PASS/FAIL line per test; exit code 0 iff all non-skipped pass.
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "code"))
import live_llm  # noqa: E402

_RESULTS = []


def report(num, ok, detail=""):
    _RESULTS.append((num, ok, detail))
    print(f"TEST {num}: {'PASS' if ok else 'FAIL'} | {detail}")


def _clear_live_env():
    for k in ("LIVE_LLM_BASE_URL", "LIVE_LLM_API_KEY", "LIVE_LLM_MODEL", "LIVE_DAILY_CAP"):
        os.environ.pop(k, None)


class _MockHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send({"data": [{"id": "mock-model"}]})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self.rfile.read(n)
        self._send({"choices": [{"message": {"content": '{"ok": true, "echo": "mock"}'}}]})


def _start_mock():
    srv = HTTPServer(("127.0.0.1", 0), _MockHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/v1"


def test1():
    _clear_live_env()
    live_llm.reset_for_tests()
    st = live_llm.live_status()
    t0 = time.time()
    out = live_llm.live_json("sys", "user")
    dt = time.time() - t0
    report(1, st["reason"] == "not_configured" and out is None and dt < 0.1,
           f"reason={st['reason']} out={out} dt={dt * 1000:.1f}ms")


def test2():
    _clear_live_env()
    live_llm.reset_for_tests()
    os.environ.update({"LIVE_LLM_BASE_URL": "http://127.0.0.1:9/v1",
                       "LIVE_LLM_API_KEY": "not-a-real-key",
                       "LIVE_LLM_MODEL": "mock-model"})
    t0 = time.time()
    r1 = live_llm.live_json("sys", "q1")
    r2 = live_llm.live_json("sys", "q2")
    dt2 = time.time() - t0
    with live_llm._lock:
        paused = time.time() < live_llm._state["breaker"]["paused_until"]
    r3 = live_llm.live_json("sys", "q3")
    report(2, r1 is None and r2 is None and paused and r3 is None and dt2 < 4.0,
           f"r1={r1} r2={r2} breaker_paused={paused} r3={r3} 2 failures in {dt2:.2f}s (no exception)")


def _load_env_file(path):
    vals = {}
    try:
        for l in open(path):
            s = l.strip()
            if "=" in s and not s.startswith("#"):
                k, v = s.split("=", 1)
                vals[k] = v
    except Exception:
        pass
    return vals


def test3():
    vals = _load_env_file(os.path.join(BASE, ".env"))
    if not vals.get("LIVE_LLM_API_KEY") or not vals.get("LIVE_LLM_MODEL"):
        report(3, True, "SKIPPED (hosted layer skipped: no LIVE_LLM key/model in .env)")
        return
    detail = ""
    passed = False
    for rnd in range(1, 4):
        _clear_live_env()
        os.environ.update({k: vals[k] for k in
                           ("LIVE_LLM_BASE_URL", "LIVE_LLM_API_KEY", "LIVE_LLM_MODEL")
                           if vals.get(k)})
        live_llm.reset_for_tests()
        st = live_llm.live_status()
        r1 = live_llm.live_json("You are a JSON assistant. Return ONLY valid JSON.",
                                'Return JSON {"ok": true}')
        detail = f"round{rnd} status={st['reason']} r1={r1}"
        if isinstance(r1, dict) and r1.get("ok") is True:
            hits_before = live_llm.stats()["cache_hits"]
            r2 = live_llm.live_json("You are a JSON assistant. Return ONLY valid JSON.",
                                    'Return JSON {"ok": true}')
            hit = live_llm.stats()["cache_hits"] == hits_before + 1
            detail += f" | r2={r2} cache_hit={hit}"
            if r2 == r1 and hit:
                passed = True
            break
    report(3, passed, detail)


def test4():
    srv, base = _start_mock()
    try:
        _clear_live_env()
        live_llm.reset_for_tests()
        os.environ.update({"LIVE_LLM_BASE_URL": base,
                           "LIVE_LLM_API_KEY": "mock-key",
                           "LIVE_LLM_MODEL": "mock-model"})
        live_llm.PER_SESSION_CAP = 2
        session = {}
        a = live_llm.live_json("s", "alpha", session=session)
        b = live_llm.live_json("s", "beta", session=session)
        c = live_llm.live_json("s", "gamma", session=session)
        report(4, a is not None and b is not None and c is None,
               f"a={a} b={b} c={c} session={session}")
    finally:
        live_llm.PER_SESSION_CAP = 10
        srv.shutdown()


def test5():
    srv, base = _start_mock()
    try:
        _clear_live_env()
        live_llm.reset_for_tests()
        os.environ.update({"LIVE_LLM_BASE_URL": base,
                           "LIVE_LLM_API_KEY": "mock-key",
                           "LIVE_LLM_MODEL": "mock-model",
                           "LIVE_DAILY_CAP": "2"})
        a = live_llm.live_json("s", "d1")
        b = live_llm.live_json("s", "d2")
        c = live_llm.live_json("s", "d3")
        st = live_llm.live_status()
        report(5, a is not None and b is not None and c is None
               and st["reason"] == "daily_cap_reached",
               f"a={a} b={b} c={c} status_reason={st['reason']}")
    finally:
        srv.shutdown()


def main():
    print("== D1B test_live_llm ==")
    test1()
    test2()
    test3()
    test4()
    test5()
    n_pass = sum(1 for _, ok, _ in _RESULTS if ok)
    print(f"D1B SUMMARY: {n_pass}/{len(_RESULTS)} PASS")
    sys.exit(0 if n_pass == len(_RESULTS) else 1)


if __name__ == "__main__":
    main()
