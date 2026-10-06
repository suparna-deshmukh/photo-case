"""
Purpose: D4 enrichment via Arctic Shift (public Reddit archive API, no key).
Why: www.reddit.com .json is IP-blocked (403) and per-post RSS comment feeds
     are IP rate-limited (sustained 429s observed 2026-10-06). Arctic Shift
     mirrors the same public data: posts/ids (batched metadata) and
     comments/search?link_id=t3_<id> (full comment JSON incl. score).
Phases:
  C) best-effort archive post search per (sub, query) pair -> older posts
     (RSS only reaches the 25 newest); file Arctic__{sub}__{qhash}.parquet.
     Aborts early if the search endpoint keeps timing out.
  A) batched posts/ids metadata for all unique posts -> __postmeta__.parquet
     (doc_id, score, num_comments, created_utc, subreddit)
  B) comments per post (limit=100, keep max 15 >60-char non-deleted bodies,
     same filters as the RSS phase) appended to __comments__.parquet
Then merges (reusing collect_reddit.merge_and_report) and patches `score`
into reddit_raw.parquet from __postmeta__.parquet.
Privacy: author/user fields are NEVER stored, printed or logged; u/ mentions
in bodies are stripped (same regex as collect_reddit).
Resume: posts already present in __comments__.parquet are skipped; existing
Arctic pair files and __postmeta__ entries are skipped.
Usage: .venv/bin/python code/collect_reddit_arctic.py [--no-search] [--sleep 3]
"""
import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent
PARTS_DIR = BASE / "data" / "reddit_parts"
LOG_PATH = BASE / "logs" / "d4_reddit_arctic.log"
API = "https://arctic-shift.photon-reddit.com/api"
UA = {"User-Agent": "photo-retrieval-research/0.1 (student research project)"}
COMMENT_PART = PARTS_DIR / "__comments__.parquet"
POSTMETA_PART = PARTS_DIR / "__postmeta__.parquet"
MAX_COMMENTS_PER_POST = 15
BATCH_IDS = 20
COLUMNS = ["source", "doc_id", "date", "rating", "text", "score", "subreddit", "url"]
sys.path.insert(0, str(BASE / "code"))
from collect_reddit import SUBS, QUERIES, part_path, html_to_text  # noqa: E402
from collect_reddit import _DELETES  # noqa: E402


def log(msg):
    line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def iso(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ""


def get_json(url, params, sleep_s):
    """GET with one retry on 422/429/timeout. Returns (data|None, ok)."""
    for attempt in (1, 2):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=45)
        except Exception as e:
            log(f"ERR {url.split('?')[0]} {type(e).__name__}: {str(e)[:150]}")
            time.sleep(30)
            continue
        if r.status_code in (422, 429, 503):
            log(f"THROTTLE status={r.status_code} {url.split('?')[0]} attempt={attempt} {r.text[:120]}")
            time.sleep(30)
            continue
        if r.status_code != 200:
            log(f"ERR status={r.status_code} {url.split('?')[0]} {r.text[:200]}")
            return None, False
        try:
            j = r.json()
        except Exception:
            log(f"ERR bad-json {url.split('?')[0]} {r.text[:200]}")
            return None, False
        if j.get("data") is None:
            log(f"ERR server {r.text[:200]} {url.split('?')[0]} attempt={attempt}")
            time.sleep(30)
            continue
        return j["data"], True
    return None, False


def all_posts():
    posts = {}
    for p in sorted(PARTS_DIR.glob("*.parquet")):
        if p.name in (COMMENT_PART.name, POSTMETA_PART.name):
            continue
        try:
            d = pd.read_parquet(p)
        except Exception:
            continue
        for _, r in d[d["source"] == "reddit_post"].iterrows():
            rid = str(r["doc_id"])
            if rid not in posts:
                posts[rid] = {"doc_id": rid, "sub": str(r["subreddit"]), "url": str(r["url"])}
    return posts


def phase_search(sleep_s, abort_after=3):
    log("PHASE C: archive post search (older posts beyond RSS's 25 newest)")
    failures = 0
    for sub in SUBS:
        for query in QUERIES:
            h = hashlib.sha256(query.encode("utf-8")).hexdigest()[:10]
            path = PARTS_DIR / f"Arctic__{sub}__{h}.parquet"
            if path.exists():
                continue
            q = query + ("" if sub == "GooglePhotos" else " google photos")
            rows = []
            data, ok = get_json(f"{API}/posts/search",
                                {"subreddit": sub, "title": q, "limit": 100, "sort": "desc"}, sleep_s)
            time.sleep(sleep_s)
            if not ok or data is None:
                failures += 1
                log(f"C-FAIL {sub} q={query!r} (endpoint throttled/timed out)")
                if failures >= abort_after:
                    log("C-ABORT: search endpoint persistently unavailable; continuing with RSS posts only")
                    return
                continue
            for d in data:
                rid = str(d.get("id", ""))
                title = (d.get("title") or "").strip()
                selftext = (d.get("selftext") or "").strip()
                if not rid or (title in _DELETES and not selftext):
                    continue
                text = (title + "\n\n" + selftext).strip() if selftext else title
                if not text or text in _DELETES:
                    continue
                rows.append({
                    "source": "reddit_post", "doc_id": rid,
                    "date": iso(d.get("created_utc")), "rating": None,
                    "text": text, "score": int(d.get("score", 0) or 0),
                    "subreddit": sub,
                    "url": f"https://www.reddit.com{d.get('permalink', '')}",
                })
            path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows, columns=COLUMNS).drop_duplicates("doc_id").to_parquet(path, index=False)
            log(f"C-SAVED {sub} q={query!r}: {len(rows)} posts")


def phase_postmeta(posts, sleep_s):
    log(f"PHASE A: post metadata for {len(posts)} unique posts (batched posts/ids)")
    meta = {}
    if POSTMETA_PART.exists():
        try:
            m = pd.read_parquet(POSTMETA_PART)
            meta = {str(r.doc_id): r for r in m.itertuples(index=False)}
        except Exception:
            meta = {}
    todo = [rid for rid in posts if rid not in meta]
    ids = sorted(todo)
    for i in range(0, len(ids), BATCH_IDS):
        chunk = ids[i:i + BATCH_IDS]
        data, ok = get_json(f"{API}/posts/ids", {"ids": ",".join(chunk)}, sleep_s)
        time.sleep(sleep_s)
        if not ok or data is None:
            log(f"A-FAIL batch at {i} ({len(chunk)} ids)")
            continue
        for d in data:
            rid = str(d.get("id", ""))
            if rid:
                meta[rid] = {"doc_id": rid, "score": int(d.get("score", 0) or 0),
                             "num_comments": int(d.get("num_comments", 0) or 0),
                             "created_utc": iso(d.get("created_utc"))}
        if (i // BATCH_IDS) % 5 == 0:
            pd.DataFrame(list(meta.values())).to_parquet(POSTMETA_PART, index=False)
            log(f"A-progress {min(i + BATCH_IDS, len(ids))}/{len(ids)}")
    pd.DataFrame(list(meta.values())).to_parquet(POSTMETA_PART, index=False)
    log(f"A-DONE {len(meta)} posts with metadata")


def phase_comments(posts, sleep_s):
    done = set()
    if COMMENT_PART.exists():
        try:
            done = {str(d).split("_")[0] for d in pd.read_parquet(COMMENT_PART)["doc_id"].astype(str)}
        except Exception:
            pass
    todo = [rid for rid in sorted(posts) if rid not in done]
    log(f"PHASE B: comments for {len(todo)} posts (of {len(posts)}; {len(done)} already done)")
    n_rows = 0
    for n, rid in enumerate(todo):
        data, ok = get_json(f"{API}/comments/search",
                            {"link_id": f"t3_{rid}", "limit": 100}, sleep_s)
        time.sleep(sleep_s)
        if not ok or data is None:
            log(f"B-FAIL {rid}")
            continue
        kept = 0
        rows = []
        for d in data:
            if kept >= MAX_COMMENTS_PER_POST:
                break
            body = (d.get("body") or "").strip()
            if len(body) <= 60 or body in _DELETES:
                continue
            body = html_to_text(body)  # strips u/ handles, submitted-by lines
            cid = str(d.get("id", ""))
            if not cid:
                continue
            rows.append({
                "source": "reddit_comment", "doc_id": f"{rid}_{cid}",
                "date": iso(d.get("created_utc")) or posts[rid].get("date", ""),
                "rating": None, "text": body,
                "score": int(d.get("score", 0) or 0),
                "subreddit": posts[rid]["sub"], "url": posts[rid]["url"],
            })
            kept += 1
        if rows:
            df_new = pd.DataFrame(rows, columns=COLUMNS)
            if COMMENT_PART.exists():
                try:
                    df_all = pd.concat([pd.read_parquet(COMMENT_PART), df_new], ignore_index=True)
                except Exception:
                    df_all = df_new
            else:
                df_all = df_new
            df_all = df_all.drop_duplicates(subset="doc_id", keep="last")
            df_all.to_parquet(COMMENT_PART, index=False)
            n_rows += len(rows)
        if (n + 1) % 25 == 0:
            log(f"B-progress {n + 1}/{len(todo)} comment_rows={n_rows}")
    log(f"B-DONE new_comment_rows={n_rows}")


def merge_with_scores():
    from collect_reddit import merge_and_report
    total = merge_and_report()
    raw = pd.read_parquet(BASE / "data" / "reddit_raw.parquet")
    meta = pd.read_parquet(POSTMETA_PART)
    meta = meta.set_index("doc_id")["score"]
    mask = raw["score"].isna() & raw["doc_id"].isin(meta.index)
    raw.loc[mask, "score"] = raw.loc[mask, "doc_id"].map(meta).astype("Int64")
    raw.to_parquet(BASE / "data" / "reddit_raw.parquet", index=False)
    log(f"MERGE-SCORE patched {int(mask.sum())} post rows with archive scores; total={len(raw)}")
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-search", action="store_true", help="skip phase C (archive search)")
    ap.add_argument("--sleep", type=float, default=3.0)
    args = ap.parse_args()
    log(f"START arctic collector sleep={args.sleep} search={not args.no_search}")
    if not args.no_search:
        phase_search(args.sleep)
    posts = all_posts()
    log(f"posts discovered: {len(posts)}")
    phase_postmeta(posts, args.sleep)
    phase_comments(posts, args.sleep)
    total = merge_with_scores()
    log(f"DONE arctic collector total={total}")


if __name__ == "__main__":
    main()
