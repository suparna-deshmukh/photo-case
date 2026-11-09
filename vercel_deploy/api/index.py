"""Vercel entrypoint for the Jog MVP (Streamlit).

Vercel's Python runtime loads a top-level ASGI app as the function handler,
so this module is a small ASGI proxy that:

1. Starts the real Streamlit server (app.py, same argv as local dev) as a
   child process on a localhost port.
2. Proxies every HTTP and WebSocket request to that backend.

The Hugging Face cache is pointed at the CLIP model baked into the function
bundle so no ~600MB download happens at runtime.
"""

import asyncio
import contextlib
import os
import socket
import subprocess
import sys
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))

# Must be set before streamlit / sentence_transformers import anything from HF.
os.environ["HF_HOME"] = os.path.join(_HERE, "hf_cache")
os.chdir(_HERE)

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = int(os.environ.get("JOG_BACKEND_PORT", "8901"))
BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

_BACKEND_LOCK = threading.Lock()
_BACKEND_STARTED = False

_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "host",
    "sec-websocket-key", "sec-websocket-version", "sec-websocket-protocol",
    "sec-websocket-extensions",
}


def _backend_alive():
    try:
        with socket.create_connection((BACKEND_HOST, BACKEND_PORT), timeout=2):
            return True
    except OSError:
        return False


def _wait_for_backend(timeout=180.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _backend_alive():
            return True
        time.sleep(0.5)
    return False


def _start_backend():
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.headless", "true",
        "--server.address", BACKEND_HOST,
        "--server.port", str(BACKEND_PORT),
        "--browser.gatherUsageStats", "false",
    ]
    subprocess.Popen(cmd, cwd=_HERE, env=os.environ.copy())


def _ensure_backend():
    global _BACKEND_STARTED
    with _BACKEND_LOCK:
        if not _BACKEND_STARTED:
            _BACKEND_STARTED = True
            _start_backend()
    if not _wait_for_backend(timeout=180.0):
        raise RuntimeError("streamlit backend did not become ready in time")


async def _ensure_backend_async():
    await asyncio.get_running_loop().run_in_executor(None, _ensure_backend)


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

    async with httpx.AsyncClient(timeout=httpx.Timeout(240.0, connect=10.0)) as client:
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

    await send({"type": "websocket.accept"})

    try:
        async with ws_connect(uri, open_timeout=60.0) as ws:
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
            for task in done:
                if task.exception() and not isinstance(task.exception(), asyncio.CancelledError):
                    raise task.exception()
    finally:
        with contextlib.suppress(Exception):
            await send({"type": "websocket.close", "code": 1000})


async def app(scope, receive, send):
    scope_type = scope.get("type")
    if scope_type == "lifespan":
        while True:
            message = await receive()
            if message.get("type") == "lifespan.startup":
                try:
                    await _ensure_backend_async()
                    await send({"type": "lifespan.startup.complete"})
                except Exception as exc:  # noqa: BLE001
                    await send({"type": "lifespan.startup.failed", "message": str(exc)})
                    return
            elif message.get("type") == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    elif scope_type == "http":
        await _proxy_http(scope, receive, send)
    elif scope_type == "websocket":
        await _proxy_websocket(scope, receive, send)
    else:
        raise RuntimeError(f"unsupported ASGI scope type: {scope_type}")
