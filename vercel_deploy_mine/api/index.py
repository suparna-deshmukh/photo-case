"""Vercel entrypoint for the Jog MVP (Streamlit).

Vercel's Python runtime loads a top-level ASGI app as the function handler.
This module is an ASGI proxy that:

1. Serves Streamlit's HTML shell, client JS/CSS, favicon and the app's own
   static files (fonts) directly from the bundle, so the page skeleton
   loads in seconds even on a cold instance.
2. Serves the deterministic /_stcore/host-config locally.
3. Restores the baked CLIP model from Vercel Blob into the largest writable
   filesystem (Fluid Compute: /var/tmp; /tmp is a 512 MiB tmpfs).
4. Starts the real Streamlit server (app.py) as a child process and proxies
   everything else (WebSocket session channel, media files, uploads).
"""

import asyncio
import contextlib
import mimetypes
import os
import resource
import shutil
import socket
import subprocess
import sys
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(_HERE)

_HF_REPO = "sentence-transformers/clip-ViT-B-32"
_HF_BASE = f"https://huggingface.co/{_HF_REPO}/resolve/main"
_HF_MODEL_FILE = "model.safetensors"
_MODEL_SIZE = 605157884


def _raise_fd_limit():
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        if soft < hard:
            resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
    except Exception:  # noqa: BLE001
        pass


_raise_fd_limit()


def _disk_free(path):
    try:
        return shutil.disk_usage(path).free
    except Exception:  # noqa: BLE001
        return -1


def _pick_hf_home():
    for base in sorted(("/var/tmp", "/tmp", "/dev/shm"), key=_disk_free, reverse=True):
        cand = os.path.join(base, "hf_cache")
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".jog_probe")
            with open(probe, "wb") as fh:
                fh.write(b"\0" * (8 * 1024 * 1024))
            os.remove(probe)
        except Exception as exc:  # noqa: BLE001
            print(f"jog: candidate {cand} not usable: {exc}", flush=True)
            continue
        print(f"jog: using HF cache dir {cand} (fs free: {_disk_free(base)} bytes)", flush=True)
        return cand
    return "/var/tmp/hf_cache"


HF_HOME = _pick_hf_home()
os.environ["HF_HOME"] = HF_HOME
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
# Vercel vendors streamlit outside site-packages, which auto-enables a hidden
# development mode (conflicts with server.port); pin it off.
os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")


def _restore_model():
    """Materialize the CLIP model into the HF cache under HF_HOME.

    Fetched via huggingface_hub.snapshot_download from the public Hugging
    Face repo (the previous Vercel Blob public URL is dead - 403). Restored
    state lives in /var/tmp and survives freeze/resume, so this runs once
    per instance; subsequent cold thaws are metadata checks only.
    """
    from huggingface_hub import snapshot_download

    hub_dir = os.path.join(HF_HOME, "hub")
    print("jog: ensuring CLIP model via huggingface_hub.snapshot_download", flush=True)
    snap_dir = snapshot_download(
        repo_id=_HF_REPO, cache_dir=hub_dir,
        # skip the legacy .bin duplicate of the weights (~600 MB)
        ignore_patterns=["0_CLIPModel/pytorch_model.bin", "*pytorch_model.bin", "README.md", ".gitattributes"],
    )
    # repo layout keeps the weights under 0_CLIPModel/
    target = os.path.join(snap_dir, "0_CLIPModel", _HF_MODEL_FILE)
    if not (os.path.exists(target) and os.path.getsize(target) == _MODEL_SIZE):
        for root, _dirs, names in os.walk(snap_dir):
            if _HF_MODEL_FILE in names:
                cand = os.path.join(root, _HF_MODEL_FILE)
                if os.path.getsize(cand) == _MODEL_SIZE:
                    target = cand
                    break
        else:
            raise RuntimeError("CLIP model missing or wrong size after snapshot_download")
    print(f"jog: CLIP model ready at {snap_dir}", flush=True)
    return True


# ---------------- static media map (instance-independent /media serving) ----------------
# Streamlit's media manager keeps file-id -> bytes mappings in per-process memory,
# so a /media/<id> request load-balanced to a different Fluid Compute instance
# than the one that rendered the view would 404. All bundled photos pass through
# streamlit's image pipeline unchanged (<= MAXIMUM_CONTENT_WIDTH, already JPEG),
# and face avatars are re-encoded deterministically (BILINEAR, q90), so every
# media id can be precomputed from the bundle. The proxy then serves /media/
# directly from the bundle on any instance.
_MEDIA_MAP = None  # type: dict | None


def _st_image_encode(data, target_width):
    """Replicates streamlit 1.65 _ensure_image_size_and_format for local files."""
    import io as _io

    from PIL import Image

    pil = Image.open(_io.BytesIO(data))
    width, height = pil.size
    if target_width > 0 and width > target_width:
        new_height = int(1.0 * height * target_width / width)
        pil = pil.resize((target_width, new_height), resample=Image.BILINEAR)
        if pil.mode in {"RGBA", "LA", "P"}:
            pil = pil.convert("RGB")
        tmp = _io.BytesIO()
        pil.save(tmp, format="JPEG", quality=90)
        return tmp.getvalue()
    if pil.format != "JPEG":
        if pil.mode in {"RGBA", "LA", "P"}:
            pil = pil.convert("RGB")
        tmp = _io.BytesIO()
        pil.save(tmp, format="JPEG", quality=90)
        return tmp.getvalue()
    return data


def _st_media_id(data, mimetype):
    """Replicates streamlit 1.65 MemoryMediaFileStorage._calculate_file_id."""
    import hashlib

    filehash = hashlib.blake2b(digest_size=16, usedforsecurity=False)
    filehash.update(f"{len(data)}:".encode())
    if len(data) > 1048576:
        filehash.update(data[:65536])
        mid_start = (len(data) - 65536) // 2
        filehash.update(data[mid_start : mid_start + 65536])
        filehash.update(data[-65536:])
    else:
        filehash.update(data)
    filehash.update(mimetype.encode())
    return filehash.hexdigest()


def _build_media_map():
    """Map media id -> (abs_path | None, encoded_bytes | None) for bundled images."""
    media = {}
    sources = (
        (os.path.join(_HERE, "images"), 1460),  # MAXIMUM_CONTENT_WIDTH (stretch views)
        (os.path.join(_HERE, "data", "faces"), 56),
        (os.path.join(_HERE, "data", "faces"), 64),
    )
    for root, target_width in sources:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as fh:
                    data = fh.read()
                encoded = _st_image_encode(data, target_width)
                media_id = _st_media_id(encoded, "image/jpeg")
                if encoded is data:
                    media[media_id] = (path, None)
                else:
                    media[media_id] = (None, encoded)
            except Exception as exc:  # noqa: BLE001
                print(f"jog: media map: skipping {name}: {exc}", flush=True)
    return media


def _media_map():
    global _MEDIA_MAP
    if _MEDIA_MAP is None:
        _MEDIA_MAP = _build_media_map()
        print(f"jog: media map built ({len(_MEDIA_MAP)} ids)", flush=True)
    return _MEDIA_MAP


def _package_root():
    """Directory containing the bundled packages (streamlit, torch, ...)."""
    candidate = "/var/task/_vendor"
    if os.path.isdir(os.path.join(candidate, "streamlit")):
        return candidate
    try:
        import streamlit as _st_probe
        return os.path.dirname(os.path.dirname(os.path.abspath(_st_probe.__file__)))
    except Exception:  # noqa: BLE001
        return None


def _streamlit_static_dir():
    pkg = _package_root() or ""
    for base in (pkg, ""):
        cand = os.path.join(base, "streamlit", "static") if base else os.path.join(
            os.path.dirname(os.path.abspath(__import__("streamlit").__file__)), "static"
        )
        if os.path.isfile(os.path.join(cand, "index.html")):
            return cand
    return None


BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = int(os.environ.get("JOG_BACKEND_PORT", "8901"))
BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
_APP_RUN_DIR = None

_BACKEND_LOCK = threading.Lock()
_BACKEND_STARTED = False
_BACKEND_PID = None
_WARMUP_KICKED = False

_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "host",
    "sec-websocket-key", "sec-websocket-version", "sec-websocket-protocol",
    "sec-websocket-extensions",
}

_STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".txt": "text/plain; charset=utf-8",
}


def _fd_histogram(pid=None):
    try:
        fd_dir = f"/proc/{pid}/fd" if pid else "/proc/self/fd"
        counts = {}
        for name in os.listdir(fd_dir):
            try:
                target = os.readlink(os.path.join(fd_dir, name))
            except OSError:
                continue
            counts[target] = counts.get(target, 0) + 1
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:12]
        return {"total": sum(counts.values()), "top": top}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _backend_alive():
    try:
        with socket.create_connection((BACKEND_HOST, BACKEND_PORT), timeout=1):
            return True
    except OSError:
        return False


def _wait_for_backend(timeout=240.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _backend_alive():
            return True
        time.sleep(0.5)
    return False


def _monitor_child(pid):
    time.sleep(25)
    try:
        with open(f"/proc/{pid}/limits") as fh:
            limits = [line for line in fh if "open files" in line]
        print(f"jogdiag: child pid={pid} limits={limits!r} fds={_fd_histogram(pid)}", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"jogdiag: child monitor failed: {exc}", flush=True)


def _stage_app():
    """Copy the app tree into a writable directory.

    Vercel Fluid Compute mounts the function code read-only, but app.py
    appends to BASE/"logs"/"events.jsonl" (BASE = the app directory).
    Running the Streamlit child from a writable staged copy keeps app.py
    untouched while making all of its file writes work. Locally this is
    a cheap no-op with identical behavior.
    """
    global _APP_RUN_DIR
    if _APP_RUN_DIR:
        return _APP_RUN_DIR
    for base in sorted(("/var/tmp", "/tmp"), key=_disk_free, reverse=True):
        cand = os.path.join(base, "jog_app")
        try:
            if os.path.isdir(cand):
                shutil.rmtree(cand)
            shutil.copytree(
                _HERE, cand,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            probe = os.path.join(cand, ".jog_probe")
            with open(probe, "wb") as fh:
                fh.write(b"0")
            os.remove(probe)
        except Exception as exc:  # noqa: BLE001
            print(f"jog: app stage dir {cand} not usable: {exc}", flush=True)
            continue
        _APP_RUN_DIR = cand
        print(f"jog: running app from writable dir {cand}", flush=True)
        return cand
    print("jog: no writable stage dir; running app in place", flush=True)
    return _HERE


def _start_backend():
    global _BACKEND_PID
    print(f"jog: starting streamlit backend on {BACKEND_HOST}:{BACKEND_PORT}", flush=True)
    env = os.environ.copy()
    pkg_root = _package_root()
    if pkg_root:
        env["PYTHONPATH"] = pkg_root + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [
        sys.executable, "-m", "jog_child",
        "run", "app.py",
        "--global.developmentMode", "false",
        "--server.headless", "true",
        "--server.address", BACKEND_HOST,
        "--server.port", str(BACKEND_PORT),
        "--browser.gatherUsageStats", "false",
    ]
    proc = subprocess.Popen(
        cmd, cwd=_stage_app(), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    _BACKEND_PID = proc.pid
    threading.Thread(target=_monitor_child, args=(proc.pid,), daemon=True).start()

    def _pump():
        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, b""):
            print(line.decode("utf-8", "replace").rstrip(), flush=True)

    threading.Thread(target=_pump, daemon=True).start()


def _ensure_backend():
    global _BACKEND_STARTED
    with _BACKEND_LOCK:
        if not _BACKEND_STARTED:
            _BACKEND_STARTED = True
            _restore_model()
            _start_backend()
    if not _wait_for_backend(timeout=240.0):
        raise RuntimeError("streamlit backend did not become ready in time")


def _kick_warmup():
    global _WARMUP_KICKED
    with _BACKEND_LOCK:
        if _WARMUP_KICKED:
            return
        _WARMUP_KICKED = True

    def _warmup():
        try:
            _ensure_backend()
            _media_map()
            print("jog: warmup backend ready", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"jog: warmup failed: {exc}", flush=True)

    threading.Thread(target=_warmup, daemon=True).start()


async def _ensure_backend_async():
    await asyncio.get_running_loop().run_in_executor(None, _ensure_backend)


def _safe_join(base, rel):
    base = os.path.realpath(base)
    full = os.path.realpath(os.path.join(base, rel))
    if not (full == base or full.startswith(base + os.sep)):
        return None
    return full


async def _serve_local_static(scope, receive, send):
    path = scope.get("path", "/")
    st_static = _streamlit_static_dir()

    if path == "/app/static/" or path.startswith("/app/static/"):
        base, rel = os.path.join(_HERE, "static"), path[len("/app/static/"):]
    elif st_static and (path.startswith("/static/") or path in ("/", "/index.html", "/favicon.png", "/manifest.json")):
        if path == "/" or path == "/index.html":
            return await _respond_file(send, os.path.join(st_static, "index.html"), no_cache=True)
        base, rel = st_static, path.lstrip("/")
    else:
        await send({"type": "http.response.start", "status": 404,
                    "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"not found", "more_body": False})
        return

    full = _safe_join(base, rel)
    if full is None or not os.path.isfile(full):
        if st_static and os.path.isfile(os.path.join(st_static, "index.html")):
            full = os.path.join(st_static, "index.html")
        else:
            await send({"type": "http.response.start", "status": 404,
                        "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": b"not found", "more_body": False})
            return
    no_cache = os.path.basename(full).endswith((".html",)) or full.endswith("manifest.json")
    await _respond_file(send, full, no_cache=no_cache)


async def _respond_file(send, full, no_cache=False):
    ctype = _STATIC_TYPES.get(os.path.splitext(full)[1].lower())
    if ctype is None:
        ctype, _ = mimetypes.guess_type(full)
        ctype = ctype or "application/octet-stream"
    size = os.path.getsize(full)
    headers = [
        (b"content-type", ctype.encode("latin-1")),
        (b"content-length", str(size).encode("latin-1")),
        (b"cache-control", b"no-cache" if no_cache else b"public, max-age=31536000, immutable"),
    ]
    await send({"type": "http.response.start", "status": 200, "headers": headers})
    with open(full, "rb") as fh:
        while True:
            chunk = fh.read(256 * 1024)
            if not chunk:
                break
            await send({"type": "http.response.body", "body": chunk, "more_body": True})
    await send({"type": "http.response.body", "body": b"", "more_body": False})


_HOST_CONFIG_BODY = (
    b'{"allowedOrigins": [], "useExternalAuthToken": false, '
    b'"enableCustomParentMessages": false, "enforceDownloadInNewTab": false, '
    b'"metricsUrl": "", "blockErrorDialogs": false, "resourceCrossOriginMode": null}'
)


async def _proxy_http(scope, receive, send):
    await _ensure_backend_async()

    import httpx

    chunks = []
    while True:
        message = await receive()
        if message.get("type") == "http.request":
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break

    headers = [
        (key, value)
        for key, value in scope.get("headers", [])
        if key.lower() not in _HOP_BY_HOP
    ]
    headers.append((b"accept-encoding", b"identity"))
    query = scope.get("query_string", b"")
    url = BASE_URL + scope.get("path", "/") + (
        "?" + query.decode("latin-1") if query else ""
    )

    async with httpx.AsyncClient(timeout=httpx.Timeout(280.0, connect=10.0)) as client:
        request = client.build_request(
            scope.get("method", "GET"),
            url,
            content=b"".join(chunks) or None,
            headers=headers,
        )
        response = await client.send(request, stream=True)
        out_headers = [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in response.headers.items()
            if key.lower() not in _HOP_BY_HOP and key.lower() != "content-encoding"
        ]
        await send({
            "type": "http.response.start",
            "status": response.status_code,
            "headers": out_headers,
        })
        async for chunk in response.aiter_bytes(64 * 1024):
            await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        await response.aclose()


async def _proxy_websocket(scope, receive, send):
    await _ensure_backend_async()

    try:
        from websockets.asyncio.client import connect as ws_connect
    except ImportError:
        from websockets import connect as ws_connect

    query = scope.get("query_string", b"")
    uri = f"ws://{BACKEND_HOST}:{BACKEND_PORT}{scope.get('path', '/')}" + (
        "?" + query.decode("latin-1") if query else ""
    )

    requested = []
    for k, v in scope.get("headers", []):
        if k.lower() == b"sec-websocket-protocol":
            requested = [p.strip().decode("latin-1") for p in v.split(b",") if p.strip()]
            break

    if requested:
        await send({"type": "websocket.accept", "subprotocol": requested[0]})
    else:
        await send({"type": "websocket.accept"})

    try:
        async with ws_connect(uri, open_timeout=60.0, subprotocols=requested or None) as ws:
            async def client_to_backend():
                try:
                    while True:
                        message = await receive()
                        if message.get("type") == "websocket.receive":
                            if message.get("text") is not None:
                                await ws.send(message["text"])
                            else:
                                await ws.send(message.get("bytes") or b"")
                        elif message.get("type") == "websocket.disconnect":
                            await ws.close(code=message.get("code", 1000))
                            return
                finally:
                    with contextlib.suppress(Exception):
                        await ws.close()

            async def backend_to_client():
                while True:
                    data = await ws.recv()
                    if isinstance(data, (bytes, bytearray, memoryview)):
                        await send({"type": "websocket.send", "bytes": bytes(data)})
                    else:
                        await send({"type": "websocket.send", "text": data})

            task_client = asyncio.create_task(client_to_backend())
            task_backend = asyncio.create_task(backend_to_client())
            done, pending = await asyncio.wait(
                {task_client, task_backend}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            for task in pending:
                with contextlib.suppress(BaseException):
                    await task
            try:
                from websockets import exceptions as ws_exc
            except ImportError:
                ws_exc = None
            for task in done:
                exc = task.exception()
                if exc and not isinstance(exc, asyncio.CancelledError):
                    if ws_exc is not None and isinstance(exc, ws_exc.ConnectionClosed):
                        continue  # backend went away; normal teardown
                    raise exc
    finally:
        with contextlib.suppress(Exception):
            await send({"type": "websocket.close", "code": 1000})


async def _diag(scope, receive, send):
    import json as _json

    report = {
        "rlimit_nofile": list(resource.getrlimit(resource.RLIMIT_NOFILE)),
        "self_fds": _fd_histogram(),
    }
    if _BACKEND_PID is not None:
        report["child"] = {"pid": _BACKEND_PID, "alive": _proc_alive(_BACKEND_PID),
                           "fds": _fd_histogram(_BACKEND_PID)}
    body = _json.dumps(report, indent=2, default=str).encode()
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body, "more_body": False})


def _proc_alive(pid):
    with contextlib.suppress(ProcessLookupError, OSError):
        os.kill(pid, 0)
        return True
    return False


async def app(scope, receive, send):
    scope_type = scope.get("type")
    path = scope.get("path", "")

    if scope_type == "lifespan":
        while True:
            message = await receive()
            if message.get("type") == "lifespan.startup":
                # No warmup here: the CLIP model download is ~600 MB of
                # bandwidth per instance, so the backend is started lazily
                # on the first request that actually needs it (WebSocket).
                await send({"type": "lifespan.startup.complete"})
            elif message.get("type") == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    elif scope_type == "http" and path == "/__jogdiag":
        await _diag(scope, receive, send)
    elif scope_type == "http" and path == "/_stcore/host-config":
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json"),
                                (b"cache-control", b"no-cache"),
                                (b"content-length", str(len(_HOST_CONFIG_BODY)).encode())]})
        await send({"type": "http.response.body", "body": _HOST_CONFIG_BODY, "more_body": False})
    elif scope_type == "http" and path == "/_stcore/health":
        # Always "ok": the real Streamlit runtime reports ready as soon as it
        # can accept browser connections. Here the WebSocket request that
        # follows is what (waits for and) completes the backend, so a 503
        # would deadlock the client.
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})
    elif scope_type == "http" and path == "/favicon.ico":
        # Browsers auto-request this; serve the bundle favicon locally so
        # cold instances never start a backend for it.
        _st_static = _streamlit_static_dir()
        if _st_static and os.path.isfile(os.path.join(_st_static, "favicon.png")):
            await _respond_file(send, os.path.join(_st_static, "favicon.png"), no_cache=False)
        else:
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
    elif scope_type == "http" and (
        path in ("/", "/index.html", "/favicon.png", "/manifest.json")
        or path.startswith("/static/")
        or path.startswith("/app/static/")
    ):
        if path in ("/", "/index.html") and scope.get("method") == "GET":
            _kick_warmup()
        await _serve_local_static(scope, receive, send)
    elif scope_type == "http" and path.startswith("/media/"):
        file_id = path[len("/media/"):].rsplit(".", 1)[0]
        hit = _media_map().get(file_id)
        if hit is not None:
            abs_path, encoded = hit
            headers = [
                (b"content-type", b"image/jpeg"),
                (b"content-length", str(len(encoded) if encoded is not None else os.path.getsize(abs_path)).encode()),
                (b"cache-control", b"public, max-age=31536000, immutable"),
            ]
            await send({"type": "http.response.start", "status": 200, "headers": headers})
            if encoded is not None:
                await send({"type": "http.response.body", "body": encoded, "more_body": False})
            else:
                with open(abs_path, "rb") as fh:
                    while True:
                        chunk = fh.read(256 * 1024)
                        if not chunk:
                            break
                        await send({"type": "http.response.body", "body": chunk, "more_body": True})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return
        # Unknown id on this instance: ask the local backend (serves it if this
        # instance rendered the view); other instances may 404, which is the
        # pre-existing best-effort behavior.
        await _proxy_http(scope, receive, send)
        return
    elif scope_type == "http":
        await _proxy_http(scope, receive, send)
    elif scope_type == "websocket":
        await _proxy_websocket(scope, receive, send)
    else:
        raise RuntimeError(f"unsupported ASGI scope type: {scope_type}")
