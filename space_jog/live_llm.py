"""
Purpose: the ONLY code path through which the public Hugging Face Spaces call a
         hosted LLM (module D1B). Dependency-light: uses requests (not openai),
         no top-level import that can fail, and never raises into the UI - every
         failure path returns None / a status dict.
Inputs:  env vars LIVE_LLM_BASE_URL, LIVE_LLM_API_KEY, LIVE_LLM_MODEL (Space
         secrets or a local .env loaded by the app before calling), optional
         LIVE_DAILY_CAP (default 300); prompt strings; optional pydantic model
         passed in by the caller; optional plain-dict session from st.session_state.
Outputs: live_status() -> {available, reason, model}; mode_label() -> str;
         live_json(...) -> parsed dict | None; stats() -> counters (no inputs).
Caps and safety: PER_SESSION_CAP=10, DAILY_CAP=300 (env override), TIMEOUT_S=8,
         PROBE_TIMEOUT_S=3 (one-time /models probe cached 5 min), circuit breaker
         FAILS_BEFORE_PAUSE=2 consecutive failures -> PAUSE_S=120 s, input LRU
         cache of 500 (hits do not count against caps).
Privacy: never writes inputs or outputs to disk or logs; never prints the key
         or URL; exceptions are swallowed, never re-raised.
"""
import copy
import hashlib
import json
import os
import re
import threading
import time
from collections import OrderedDict

try:
    import requests as _requests
except Exception:  # dependency-light: module must import even without requests
    _requests = None

PER_SESSION_CAP = 10
TIMEOUT_S = 8
PROBE_TIMEOUT_S = 3
FAILS_BEFORE_PAUSE = 2
PAUSE_S = 120

_lock = threading.RLock()
_state = {
    "probe": {"ts": 0.0, "ok": False},
    "breaker": {"consec": 0, "paused_until": 0.0},
    "daily": {"date": "", "count": 0},
    "stats": {"calls": 0, "cache_hits": 0, "failures": 0,
              "caps_hit": {"session": 0, "daily": 0}},
}
_cache_lru = OrderedDict()
_CACHE_MAX = 500
_THINK_RE = re.compile(r"<think[^>]*>.*?</think[^>]*>", re.DOTALL | re.I)


def reset_for_tests():
    with _lock:
        _state["probe"] = {"ts": 0.0, "ok": False}
        _state["breaker"] = {"consec": 0, "paused_until": 0.0}
        _state["daily"] = {"date": "", "count": 0}
        _state["stats"] = {"calls": 0, "cache_hits": 0, "failures": 0,
                           "caps_hit": {"session": 0, "daily": 0}}
        _cache_lru.clear()


def stats():
    with _lock:
        return json.loads(json.dumps(_state["stats"]))


def _env():
    return (os.environ.get("LIVE_LLM_BASE_URL", "").strip(),
            os.environ.get("LIVE_LLM_API_KEY", "").strip(),
            os.environ.get("LIVE_LLM_MODEL", "").strip())


def _configured():
    base, key, model = _env()
    return bool(base and key and model and _requests is not None)


def _daily_cap():
    try:
        v = os.environ.get("LIVE_DAILY_CAP", "").strip()
        return int(v) if v else 300
    except Exception:
        return 300


def _utc_date():
    return time.strftime("%Y-%m-%d", time.gmtime())


def _strip_think(text):
    text = _THINK_RE.sub("", text)
    low = text.lower()
    idx = low.rfind("<think")
    if idx != -1 and "</think" not in low[idx:]:
        text = text[:idx]
    return text


def _extract_json(text):
    text = _strip_think(text or "")
    keep = [line for line in text.splitlines() if not line.strip().startswith("```")]
    text = "\n".join(keep)
    if "{" not in text:
        raise ValueError("no JSON object in response")
    sub = text[text.index("{"): text.rindex("}") + 1]
    return json.loads(sub)


def live_status():
    """Reachability status; probe (GET <base>/models) cached for 5 minutes."""
    if not _configured():
        return {"available": False, "reason": "not_configured", "model": None}
    base, key, model = _env()
    now = time.time()
    with _lock:
        probe = _state["probe"]
        if probe["ts"] > 0 and now - probe["ts"] < 300:
            ok = probe["ok"]
        else:
            ok = False
            try:
                r = _requests.get(base.rstrip("/") + "/models",
                                  headers={"Authorization": "Bearer " + key},
                                  timeout=PROBE_TIMEOUT_S)
                ok = r.status_code == 200
            except Exception:
                ok = False
            probe["ts"] = now
            probe["ok"] = ok
        if _state["breaker"]["paused_until"] > now:
            return {"available": False, "reason": "paused", "model": model}
        d = _state["daily"]
        if d["date"] == _utc_date() and d["count"] >= _daily_cap():
            return {"available": False, "reason": "daily_cap_reached", "model": model}
    return {"available": bool(ok), "reason": "ok" if ok else "probe_failed", "model": model}


def mode_label():
    return "AI mode" if live_status()["available"] else "Basic mode (no live AI)"


def _post_json(base, key, payload):
    url = base.rstrip("/") + "/chat/completions"
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    try:
        r = _requests.post(url, headers=headers, json=payload, timeout=TIMEOUT_S)
    except Exception:
        return None, "transport"
    if r.status_code == 400 and "response_format" in payload:
        payload2 = {k: v for k, v in payload.items() if k != "response_format"}
        try:
            r = _requests.post(url, headers=headers, json=payload2, timeout=TIMEOUT_S)
        except Exception:
            return None, "transport"
    if r.status_code != 200:
        return None, "http_" + str(r.status_code)
    try:
        data = r.json()
        text = data["choices"][0]["message"]["content"]
    except Exception:
        return None, "bad_response"
    return text, "ok"


def live_json(system, user, schema_model=None, session=None, max_tokens=800):
    """Parse JSON from the hosted LLM, or None on any failure. Never raises."""
    if not _configured():
        return None
    base, key, model = _env()
    now = time.time()
    with _lock:
        if session is not None and int(session.get("live_calls", 0)) >= PER_SESSION_CAP:
            _state["stats"]["caps_hit"]["session"] += 1
            return None
        d = _state["daily"]
        if d["date"] != _utc_date():
            d["date"], d["count"] = _utc_date(), 0
        if d["count"] >= _daily_cap():
            _state["stats"]["caps_hit"]["daily"] += 1
            return None
        if _state["breaker"]["paused_until"] > now:
            return None
    norm = " ".join((user or "").split()).lower()
    ckey = hashlib.sha256("|".join([model, system or "", norm]).encode("utf-8")).hexdigest()
    with _lock:
        if ckey in _cache_lru:
            _cache_lru.move_to_end(ckey)
            _state["stats"]["cache_hits"] += 1
            return copy.deepcopy(_cache_lru[ckey])
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system or ""},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    text, status = _post_json(base, key, payload)
    obj = None
    if status == "ok":
        try:
            obj = _extract_json(text)
            if schema_model is not None:
                obj = schema_model.model_validate(obj).model_dump()
        except Exception:
            obj = None
    with _lock:
        st = _state["stats"]
        br = _state["breaker"]
        if obj is None:
            st["failures"] += 1
            br["consec"] += 1
            if br["consec"] >= FAILS_BEFORE_PAUSE:
                br["paused_until"] = time.time() + PAUSE_S
                br["consec"] = 0
        else:
            br["consec"] = 0
            st["calls"] += 1
            _state["daily"]["count"] += 1
            if session is not None:
                session["live_calls"] = int(session.get("live_calls", 0)) + 1
            if len(_cache_lru) >= _CACHE_MAX:
                _cache_lru.popitem(last=False)
            _cache_lru[ckey] = obj
    return obj
