#!/usr/bin/env python3
"""
Purpose: Probe the local-LLM endpoint (LiteLLM proxy) and record capabilities in research/llm_probe.json.
Inputs: env var LITELLM_API_KEY (never printed); proxy base URL from ~/.codex/litellm.config.toml (hardcoded here after discovery).
Outputs: research/llm_probe.json (no secrets); human-readable summary on stdout.
Checks: (a) JSON mode, (b) vision, (c) think-leak + thinking switches, (d) context window needle, (e) latency, (f) rate-limit headers/concurrency.
"""
import base64, json, os, struct, time, zlib, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

BASE = "https://litellm-cw-tnc7knp4ba-uc.a.run.app/v1"
MODEL = "qwen38-27b"
KEY = os.environ.get("LITELLM_API_KEY", "")
OUT = os.path.join(os.path.dirname(__file__), "..", "research", "llm_probe.json")
probe = {"base_url": BASE, "model_alias": MODEL, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

def call(messages, extra=None, timeout=90):
    body = {"model": MODEL, "messages": messages}
    if extra: body.update(extra)
    req = urllib.request.Request(BASE + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(r.read().decode())
        dt = time.time() - t0
        headers = {k.lower(): v for k, v in r.headers.items() if "rate" in k.lower() or "retry" in k.lower() or "x-" in k.lower()}
        return {"ok": True, "status": r.status, "dt": round(dt, 2), "headers": headers, "data": data}
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", "replace")[:300]
        return {"ok": False, "status": e.code, "dt": round(time.time() - t0, 2), "headers": {k.lower(): v for k, v in e.headers.items() if "rate" in k.lower() or "retry" in k.lower()}, "error": body_txt}
    except Exception as e:
        return {"ok": False, "status": 0, "dt": round(time.time() - t0, 2), "error": str(e)[:300]}

def text_of(res):
    if not res.get("ok"): return None
    try:
        ch = res["data"]["choices"][0]["message"]
        parts = []
        if ch.get("content"): parts.append(ch["content"])
        if ch.get("reasoning"): parts.append("[REASONING:" + str(ch["reasoning"])[:200] + "]")
        return "\n".join(parts)
    except Exception:
        return None

# (0) model list
res = call([{"role": "user", "content": "Reply with the single word: pong"}])
probe["basic_chat"] = {"ok": res["ok"], "status": res["status"], "dt_s": res["dt"], "text": (text_of(res) or res.get("error"))[:200], "headers": res.get("headers", {})}

# (a) JSON mode
res = call([{"role": "user", "content": 'Reply ONLY with JSON: {"status": "ok"}'}],
           extra={"response_format": {"type": "json_object"}, "temperature": 0})
txt = text_of(res)
probe["json_mode"] = {"ok": res["ok"], "status": res["status"], "accepted": res["ok"],
                      "text": (txt or res.get("error"))[:200]}
probe["json_mode"]["parses"] = False
if txt:
    try:
        j = txt[txt.index("{"):txt.rindex("}")+1]
        probe["json_mode"]["parses"] = json.loads(j).get("status") == "ok"
    except Exception:
        pass

# (b) vision: tiny 64x64 solid red PNG
def make_png():
    w = h = 64
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * w for _ in range(h))
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    return base64.b64encode(png).decode()
res = call([{"role": "user", "content": [
    {"type": "text", "text": "What single color is this image? Reply with one word."},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + make_png()}}]}])
txt = text_of(res)
probe["vision"] = {"ok": res["ok"], "status": res["status"], "accepted": res["ok"],
                   "answer": (txt or res.get("error"))[:120],
                   "is_vision": bool(res["ok"] and txt and "red" in txt.lower())}

# (c) think leak + thinking switches
res = call([{"role": "user", "content": "What is 17*23? Show your reasoning, then give the final number."}])
txt = text_of(res)
leak = txt is not None and ("[REASONING:" in txt or "think" in txt.lower()[:400])
probe["think_leak_default"] = {"ok": res["ok"], "status": res["status"], "leaked": leak, "text": (txt or res.get("error"))[:250]}
res2 = call([{"role": "user", "content": "Reply with the single word: ok"}],
            extra={"chat_template_kwargs": {"enable_thinking": False}})
probe["switch_enable_thinking"] = {"accepted": res2["ok"], "status": res2["status"], "error": res2.get("error", "")[:200]}
res3 = call([{"role": "user", "content": "Reply with the single word: ok"}],
            extra={"extra_body": {"thinking": {"type": "disabled"}}})
probe["switch_thinking_param"] = {"accepted": res3["ok"], "status": res3["status"], "error": res3.get("error", "")[:200]}

# (d) context window: ~6,500-token prompt, needle at start
needle = "KX7F2Q9W"
filler_word = "photo"
n_words = 5200  # ~6.5k tokens for typical Qwen tokenizer on English
filler = (filler_word + " ") * n_words
prompt = f"At the very beginning of this text the code word {needle} appears. After reading everything, reply with ONLY that code word.\n\n{filler}"
approx_tokens = len(prompt.split()) * 1.25
res = call([{"role": "user", "content": prompt}], timeout=180)
txt = text_of(res)
probe["context_needle"] = {"ok": res["ok"], "status": res["status"], "approx_tokens_sent": int(approx_tokens),
                           "needle": needle, "got_needle": bool(txt and needle in txt),
                           "text": (txt or res.get("error"))[:200]}

# (e) latency: 5 short calls
times = []
for i in range(5):
    r = call([{"role": "user", "content": "Reply with the single word: ok"}])
    times.append(r["dt"] if r["ok"] else None)
probe["latency_s_5_calls"] = times
ok_times = [t for t in times if t]
probe["latency_median_s"] = sorted(ok_times)[len(ok_times)//2] if ok_times else None

# (f) concurrency burst: 4 parallel calls, look for 429 / rate headers
def one(_):
    return call([{"role": "user", "content": "Reply with the single word: ok"}])
with ThreadPoolExecutor(max_workers=4) as ex:
    burst = list(ex.map(one, range(4)))
probe["concurrency_burst"] = {"n": 4,
    "statuses": [b["status"] for b in burst],
    "any_429": any(b["status"] == 429 for b in burst),
    "headers_seen": sorted({h for b in burst for h in b.get("headers", {})})}

probe["secrets_included"] = False
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(probe, f, indent=2)
print(json.dumps(probe, indent=2)[:2500])
