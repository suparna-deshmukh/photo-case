"""
Vercel function: backend for the Discovery Engine "Discover more" tab
(public static HF Space). Fetches fresh public feedback for a user query
(Google Play Store, Apple App Store, Reddit) and analyzes it with the
hosted Gemini layer (live_llm) when available.

POST /feedback  {"query": str, "sources": ["play","appstore","reddit"], "per_source": 5-30}
  -> {"query","sources","errors","n","by_source","avg_rating","rows","ai",
      "basic_markdown","ai_available","model"}
GET  /          -> health JSON
Safety: CORS open (public static page caller); 10 req/min per IP
(per-instance, best effort); no stack traces in responses; LIVE_LLM_*
secrets come from Vercel env and are never echoed.
"""
import asyncio
import json
import os
import sys
import time
from collections import OrderedDict

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import live_feedback as lf
import live_llm

CORS = [
    (b"access-control-allow-origin", b"*"),
    (b"access-control-allow-methods", b"GET, POST, OPTIONS"),
    (b"access-control-allow-headers", b"content-type"),
    (b"access-control-max-age", b"86400"),
]
_RL_WINDOW = 60.0
_RL_MAX = 10
_rl = OrderedDict()


def _rate_ok(ip):
    now = time.time()
    win = _rl.setdefault(ip, [])
    while win and now - win[0] > _RL_WINDOW:
        win.pop(0)
    if len(win) >= _RL_MAX:
        return False
    win.append(now)
    if len(_rl) > 10000:
        _rl.popitem(last=False)
    return True


def _client_ip(scope):
    xff = (dict(scope.get("headers") or {})).get(b"x-forwarded-for", b"")
    if xff:
        return xff.split(b",")[0].strip().decode("latin1")
    client = scope.get("client") or ("", 0)
    return client[0] or "unknown"


def _handle(scope, body):
    method = scope.get("method", "GET")
    path = (scope.get("path") or "/").rstrip("/") or "/"
    if method == "OPTIONS":
        return 204, CORS, b""
    if path == "/":
        st = live_llm.live_status()
        return (200, CORS, json.dumps(
            {"ok": True, "service": "discovery-feedback-api",
             "ai_available": st["available"], "model": st.get("model")},
            ensure_ascii=False).encode("utf-8"))
    if path != "/feedback":
        return 404, CORS, json.dumps({"error": "not found"}).encode("utf-8")
    if method != "POST":
        return 405, CORS, json.dumps({"error": "use POST /feedback with a JSON body"}).encode("utf-8")
    if not _rate_ok(_client_ip(scope)):
        return 429, CORS, json.dumps({"error": "too many requests — please wait a minute"}).encode("utf-8")
    try:
        req = json.loads(body.decode("utf-8") or "{}") if body else {}
    except Exception:
        return 400, CORS, json.dumps({"error": "invalid JSON body"}).encode("utf-8")
    query = str(req.get("query") or "").strip()[:200]
    if not query:
        return 400, CORS, json.dumps({"error": "query is required"}).encode("utf-8")
    sources = [s for s in ("play", "appstore", "reddit") if s in (req.get("sources") or [])]
    if not sources:
        return 400, CORS, json.dumps({"error": "pick at least one source"}).encode("utf-8")
    try:
        per = int(req.get("per_source") or 10)
    except Exception:
        per = 10
    per = max(5, min(30, per))

    try:
        result = lf.run_search(query, sources, per)
    except Exception:
        return 502, CORS, json.dumps({"error": "live fetch failed — please try again in a minute"}).encode("utf-8")
    rows = result["rows"]
    st = live_llm.live_status()
    ai = None
    model = st.get("model") if rows and st["available"] else None
    if model:
        try:
            ai = lf.ai_analysis(query, rows, session={"live_calls": 0})
        except Exception:
            ai = None
    n_by, rated = {}, []
    for r in rows:
        n_by[r["source"]] = n_by.get(r["source"], 0) + 1
        if r.get("rating"):
            rated.append(r["rating"])
    resp = {
        "query": query,
        "sources": result["sources"],
        "errors": result["errors"],
        "n": len(rows),
        "by_source": n_by,
        "avg_rating": round(sum(rated) / len(rated), 2) if rated else None,
        "rows": rows,
        "ai": ai,
        "basic_markdown": lf.basic_analysis(query, rows) if rows else None,
        "ai_available": bool(st["available"]),
        "model": model,
    }
    return 200, CORS, json.dumps(resp, ensure_ascii=False).encode("utf-8")


async def app(scope, receive, send):
    t = scope.get("type")
    if t == "lifespan":
        while True:
            m = await receive()
            if m.get("type") == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif m.get("type") == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    elif t == "http":
        body = b""
        while True:
            m = await receive()
            body += m.get("body", b"")
            if m.get("more_body") is False:
                break
        status, headers, payload = await asyncio.get_running_loop().run_in_executor(
            None, _handle, scope, body)
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": payload})
    else:
        raise RuntimeError("unsupported ASGI scope type: " + str(t))
