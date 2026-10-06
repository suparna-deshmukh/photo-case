"""
Purpose: single LLM client helper for offline jobs (module D1). Reads a local or
         hosted profile from env, calls the OpenAI-compatible chat API, and always
         returns a dict ({"_error": msg} on final failure - never raises into callers).
         Implements the D0 probe defaults: JSON mode ON (retry once without if the
         proxy rejects it), Qwen3 thinking-off via extra_body + "/no_think" (retry
         without if rejected), think-block + markdown-fence stripping, first-{ to
         last-} extraction, pydantic validation, disk cache, 2/4/8/16 s backoff on
         429/5xx, autotuned worker count, prompt context check, batch runner.
Inputs:  env LLM_BASE_URL/LLM_API_KEY/LLM_MODEL (profile "local") or
         LIVE_LLM_BASE_URL/LIVE_LLM_API_KEY/LIVE_LLM_MODEL (profile "hosted"),
         loaded from BASE/.env (python-dotenv, guarded) plus os.environ;
         prompt strings; optional pydantic BaseModel; optional image path.
Outputs: parsed + validated JSON dict (or {"_error": msg});
         BASE/cache/llm_cache.jsonl (append-only disk cache);
         llm_workers saved via pipeline_counts.update_counts;
         printed tables for autotune_workers / speed_test / check_context.
D0 probe basis (research/llm_probe.json, 2026-10-06): JSON mode supported;
         no think-block leak at default; both thinking switches accepted by the
         proxy; needle verified at ~6526 tokens (context limit = 6526 - 1000);
         4-parallel burst all 200 with no rate-limit headers.
"""
import base64
import copy
import hashlib
import io
import json
import os
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CACHE_PATH = BASE / "cache" / "llm_cache.jsonl"
COUNTS_PATH = BASE / "data" / "pipeline_counts.json"
CONTEXT_LIMIT_TOKENS = 5526  # D0: needle OK at ~6526 tokens; minus 1000 safety margin

try:
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
except Exception:
    pass

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from pydantic import ValidationError
except Exception:
    ValidationError = None

try:
    from PIL import Image, ImageOps
except Exception:
    Image = ImageOps = None

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline_counts import update_counts  # noqa: E402

_cache = {}
_cache_lock = threading.Lock()
_stats = {"calls": 0, "cache_hits": 0, "errors": 0}
_stats_lock = threading.Lock()


class _RetryWithoutFlag(Exception):
    pass


class _FatalHTTP(Exception):
    pass


def _bump(name, n=1):
    with _stats_lock:
        _stats[name] += n


def stats():
    with _stats_lock:
        return dict(_stats)


def _load_cache():
    if not CACHE_PATH.exists():
        return
    try:
        for line in CACHE_PATH.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                _cache[rec["key"]] = rec["value"]
            except Exception:
                continue
    except Exception:
        pass


def _append_cache(key, value):
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _cache_lock:
            with open(CACHE_PATH, "a") as f:
                f.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")
    except Exception:
        pass


_load_cache()


def _env_triple(profile):
    if profile == "local":
        return (os.environ.get("LLM_BASE_URL", "").strip(),
                os.environ.get("LLM_API_KEY", "").strip(),
                os.environ.get("LLM_MODEL", "").strip())
    if profile == "hosted":
        return (os.environ.get("LIVE_LLM_BASE_URL", "").strip(),
                os.environ.get("LIVE_LLM_API_KEY", "").strip(),
                os.environ.get("LIVE_LLM_MODEL", "").strip())
    raise ValueError(f"unknown profile: {profile!r}")


def get_client(profile="local"):
    base, key, model = _env_triple(profile)
    if not base or not key or not model:
        return None
    if OpenAI is None:
        return None
    return OpenAI(base_url=base, api_key=key, timeout=180.0)


_THINK_RE = re.compile(r"<think[^>]*>.*?</think[^>]*>", re.DOTALL | re.I)


def _strip_think(text):
    text = _THINK_RE.sub("", text)
    low = text.lower()
    idx = low.rfind("<think")
    if idx != -1 and "</think" not in low[idx:]:
        text = text[:idx]
    return text


def _strip_fences(text):
    keep = [line for line in text.splitlines() if not line.strip().startswith("```")]
    return "\n".join(keep)


def _extract_json(text):
    text = _strip_fences(_strip_think(text or ""))
    if "{" not in text:
        raise ValueError("no JSON object found in model response")
    sub = text[text.index("{"): text.rindex("}") + 1]
    return json.loads(sub)


def _cache_key(profile, model, system, user, image_hash=None):
    material = json.dumps([profile, model, system or "", user, image_hash], ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _send(client, model, system, user_content, state, max_tokens, temperature):
    def attempt():
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system or ""},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
        }
        if state["max_tokens_flag"]:
            kwargs["max_tokens"] = max_tokens
        if state["json_mode"]:
            kwargs["response_format"] = {"type": "json_object"}
        if state["thinking_off"]:
            kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
        return client.chat.completions.create(**kwargs)

    last = None
    for delay in (0, 2, 4, 8, 16):
        if delay:
            time.sleep(delay)
        try:
            return attempt()
        except Exception as e:
            last = e
            msg = str(e)
            status = getattr(e, "status_code", None)
            if status == 400:
                low = msg.lower()
                if "response_format" in low and state["json_mode"]:
                    state["json_mode"] = False
                    raise _RetryWithoutFlag("response_format rejected by proxy")
                if any(tok in low for tok in ("thinking", "chat_template_kwargs", "enable_thinking")) and state["thinking_off"]:
                    state["thinking_off"] = False
                    raise _RetryWithoutFlag("thinking switch rejected by proxy")
                if "max_tokens" in low and state["max_tokens_flag"]:
                    state["max_tokens_flag"] = False
                    raise _RetryWithoutFlag("max_tokens rejected by proxy")
                raise _FatalHTTP(f"HTTP 400: {msg[:200]}")
            if status == 404:
                raise _FatalHTTP(f"HTTP 404 (model alias not found?): {msg[:200]}")
            if status is None or status == 429 or status >= 500:
                continue
            raise _FatalHTTP(f"HTTP {status}: {msg[:200]}")
    raise _FatalHTTP(f"retries exhausted (last: {str(last)[:200]})")


def _llm_json_core(system, user_content, schema_model, profile, max_retries,
                   temperature, max_tokens, image_hash=None, key_user=None):
    base, key, model = _env_triple(profile)
    if not base or not key or not model:
        _bump("errors")
        names = ("LLM_BASE_URL/LLM_API_KEY/LLM_MODEL" if profile == "local"
                 else "LIVE_LLM_BASE_URL/LIVE_LLM_API_KEY/LIVE_LLM_MODEL")
        return {"_error": f"profile '{profile}' not configured: set {names}"}
    client = get_client(profile)
    if client is None:
        _bump("errors")
        return {"_error": f"profile '{profile}' unavailable (openai package missing or env incomplete)"}

    is_qwen = "qwen" in model.lower()
    if isinstance(user_content, str) and is_qwen:
        user_content = user_content + " /no_think"
    key_material = key_user if key_user is not None else (
        user_content if isinstance(user_content, str) else json.dumps(user_content, ensure_ascii=False))
    ckey = _cache_key(profile, model, system, key_material, image_hash)
    with _cache_lock:
        if ckey in _cache:
            _bump("cache_hits")
            return copy.deepcopy(_cache[ckey])

    state = {"json_mode": True, "thinking_off": is_qwen, "max_tokens_flag": True}
    last_error = "unknown error"
    prompt = user_content
    for attempt in range(1, max_retries + 1):
        try:
            resp = _send(client, model, system, prompt, state, max_tokens, temperature)
            text = resp.choices[0].message.content
            obj = _extract_json(text)
            if schema_model is not None:
                obj = schema_model.model_validate(obj).model_dump()
            with _cache_lock:
                _cache[ckey] = obj
            _append_cache(ckey, obj)
            _bump("calls")
            return obj
        except _RetryWithoutFlag:
            continue
        except _FatalHTTP as e:
            last_error = str(e)
            break
        except Exception as e:
            name = type(e).__name__
            last_error = f"{name}: {str(e)[:200]}"
            is_json_problem = (issubclass(type(e), (json.JSONDecodeError, ValueError))
                               or (ValidationError is not None and isinstance(e, ValidationError)))
            if is_json_problem and attempt < max_retries:
                if isinstance(prompt, str):
                    prompt = prompt + "\nReturn ONLY valid JSON, no markdown, no explanation."
                continue
            break
    _bump("errors")
    return {"_error": last_error}


def llm_json(system, user, schema_model=None, profile="local",
             max_retries=3, temperature=0.0, max_tokens=1200):
    return _llm_json_core(system, user, schema_model, profile, max_retries,
                          temperature, max_tokens)


def _encode_image(raw, max_side):
    if Image is not None:
        try:
            im = Image.open(io.BytesIO(raw))
            im = ImageOps.exif_transpose(im)
            im.thumbnail((max_side, max_side))
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=85)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            pass
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def llm_json_image(system, user_text, image_path, schema_model=None, profile="local",
                   max_side=640, max_retries=3, temperature=0.0, max_tokens=1200):
    image_path = Path(image_path)
    try:
        raw = image_path.read_bytes()
    except Exception as e:
        _bump("errors")
        return {"_error": f"cannot read image: {str(e)[:150]}"}
    image_hash = hashlib.sha256(raw).hexdigest()
    content = [
        {"type": "text", "text": user_text},
        {"type": "image_url", "image_url": {"url": _encode_image(raw, max_side)}},
    ]
    return _llm_json_core(system, content, schema_model, profile, max_retries,
                          temperature, max_tokens, image_hash=image_hash, key_user=user_text)


class _Pacer:
    def __init__(self, per_minute):
        self.min_interval = 60.0 / per_minute if per_minute else 0.0
        self.last = 0.0
        self.lock = threading.Lock()

    def wait(self):
        if not self.min_interval:
            return
        with self.lock:
            sleep_for = self.last + self.min_interval - time.time()
            if sleep_for > 0:
                time.sleep(sleep_for)
            self.last = time.time()


def llm_json_batch(items, fn, workers=None, max_per_minute=None):
    if workers is None:
        workers = 4
        try:
            data = json.loads(COUNTS_PATH.read_text())
            workers = int(data.get("llm_workers", 4))
        except Exception:
            pass
    results = [None] * len(items)
    pacer = _Pacer(max_per_minute)
    t0 = time.time()
    s0 = stats()
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as ex:
        futs = {}
        for i, it in enumerate(items):
            pacer.wait()
            futs[ex.submit(fn, it)] = i
        iterable = as_completed(futs)
        if tqdm is not None:
            iterable = tqdm(iterable, total=len(futs), desc="llm_json_batch")
        for fut in iterable:
            i = futs[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = {"_error": f"worker: {type(e).__name__}: {str(e)[:150]}"}
    dt = time.time() - t0
    s1 = stats()
    n_err = sum(1 for r in results if isinstance(r, dict) and "_error" in r)
    print(f"llm_json_batch: items={len(items)} workers={int(workers)} elapsed={dt:.1f}s "
          f"new_calls={s1['calls'] - s0['calls']} cache_hits={s1['cache_hits'] - s0['cache_hits']} "
          f"errors={n_err} sec_per_call={dt / max(len(items), 1):.2f}")
    return results


def autotune_workers(profile="local"):
    tiers = [1, 2, 4, 8]
    tier_results = {}
    print(f"autotune_workers(profile={profile!r}): 12 representative calls per tier (unique nonce per tier to bypass cache)")
    for w in tiers:
        nonce = uuid.uuid4().hex[:8]
        items = [f'Return JSON {{"ok": true, "i": {i}, "run": "{nonce}"}}' for i in range(12)]
        t0 = time.time()
        outs = llm_json_batch(
            items,
            lambda it: llm_json("You are a JSON assistant. Return ONLY valid JSON.",
                                it, profile=profile, max_tokens=60),
            workers=w)
        dt = time.time() - t0
        errs = sum(1 for o in outs if isinstance(o, dict) and "_error" in o)
        cpm = round(12 / dt, 1) if dt > 0 else 0.0
        tier_results[w] = {"seconds": round(dt, 1), "errors": errs, "calls_per_min": cpm}
        print(f"  workers={w}: {dt:.1f}s, errors={errs}, {cpm} calls/min")
    clean = {w: r for w, r in tier_results.items() if r["errors"] == 0}
    pool = clean if clean else tier_results
    best = max(pool, key=lambda w: pool[w]["calls_per_min"])
    update_counts(llm_workers=int(best))
    print(f"autotune: choosing workers={best} -> data/pipeline_counts.json (llm_workers)")
    return int(best)


def check_context(prompt, limit_tokens=CONTEXT_LIMIT_TOKENS):
    est = len(prompt or "") / 3.5
    if est > limit_tokens:
        print(f"WARNING: prompt is ~{int(est)} tokens, exceeds limit {limit_tokens} - trim before sending.")
        return False
    print(f"context ok: ~{int(est)} tokens <= limit {limit_tokens}")
    return True


def speed_test(n=10, profile="local", projections=(1000, 3000, 6000)):
    nonce = uuid.uuid4().hex[:8]
    t0 = time.time()
    for i in range(n):
        llm_json("You are a JSON assistant. Return ONLY valid JSON.",
                 f'Return JSON {{"ok": true, "i": {i}, "run": "{nonce}"}}',
                 profile=profile, max_tokens=60)
    dt = time.time() - t0
    sec_per = dt / max(n, 1)
    print(f"speed_test n={n} profile={profile!r}: {dt:.1f}s total, {sec_per:.2f}s per call")
    for p in projections:
        print(f"  projected {p} sequential calls: {p * sec_per / 60:.1f} minutes")
    return sec_per
