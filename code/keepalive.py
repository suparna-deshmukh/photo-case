"""
Purpose: M10 - keep both Hugging Face Spaces awake (free-tier sleep) by GETting
         the Space URLs every 10 minutes until 2026-10-07 16:00 IST.
Reads  : research/links.md (LINK_discovery / LINK_mvp URLs), or the two known
         space URLs as fallback.
Writes : logs/keepalive.log
Usage  : .venv/bin/python code/keepalive.py   (start detached)
"""
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
LOG = BASE / "logs/keepalive.log"
IST = timezone(timedelta(hours=5, minutes=30))
STOP = datetime(2026, 10, 7, 16, 0, tzinfo=IST)
FALLBACK = ["https://pm-ai-18.photo-retrieval-discovery.hf.space",
            "https://pm-ai-18.jog-memory-retrieval.hf.space"]
UA = {"User-Agent": "photo-retrieval-research/0.1 (student project)"}


def log(msg):
    line = f"{datetime.now(IST).isoformat()} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def urls():
    try:
        txt = (BASE / "research/links.md").read_text()
        found = re.findall(r"https://[a-z0-9\-]+\.hf\.space[^\s|)]*", txt)
        found = [u.rstrip("/") for u in dict.fromkeys(found)]
        if found:
            return found[:2]
    except Exception:
        pass
    return FALLBACK


def main():
    us = urls()
    log(f"KEEPALIVE start urls={us} stop={STOP.isoformat()}")
    while datetime.now(IST) < STOP:
        for u in us:
            try:
                r = requests.get(u, headers=UA, timeout=60, allow_redirects=True)
                log(f"GET {u} -> {r.status_code}")
            except Exception as e:
                log(f"GET {u} -> ERROR {type(e).__name__}: {str(e)[:120]}")
        for _ in range(600):
            if datetime.now(IST) >= STOP:
                break
            time.sleep(1)
    log("KEEPALIVE stopped (deadline reached)")


if __name__ == "__main__":
    main()
