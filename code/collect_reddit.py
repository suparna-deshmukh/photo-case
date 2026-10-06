"""
Purpose: D4 Part A - collect public Reddit discussions about finding/searching
         photos in Google Photos: 5 subreddits x 12 queries, plus comments for a
         subset of posts. Two engines:
         - engine=json (module default): www.reddit.com .json search endpoint +
           /comments/{id}.json. (Currently 403-blocked from this network.)
         - engine=rss (working fallback found 2026-10-06): www.reddit.com
           search.rss (25 newest posts per query, single page) + per-post
           .rss comment feed. Score is not exposed by RSS (stored as None).
         Resume support: completed (subreddit, query) pairs are saved as part
         files under data/reddit_parts/ and skipped on re-run. Defensive
         handling of 403/429 (block-streak breaker for json engine; 429
         backoff-then-skip for rss engine).
Inputs: public reddit endpoints; locked query/subreddit table; existing part
        files (resume); network access to reddit.com.
Outputs: data/reddit_parts/{sub}__{qhash}.parquet per pair;
         data/reddit_raw.parquet (merged, deduped by doc_id);
         logs/collect_reddit.log (progress, statuses, first 300 chars of failures);
         data/pipeline_counts.json key n_reddit.
Privacy: usernames (author/user fields and "/u/..." strings) are NEVER stored,
         printed or logged. Posts/comments whose text is [deleted]/[removed]
         are skipped.
Usage: .venv/bin/python code/collect_reddit.py [--engine json|rss] [--limit N]
       [--max-comment-posts N]
       --limit N: cap on total requests this run (pilots).
"""
import argparse
import hashlib
import html as html_mod
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent
PARTS_DIR = BASE / "data" / "reddit_parts"
OUT_PARQUET = BASE / "data" / "reddit_raw.parquet"
LOG_PATH = BASE / "logs" / "collect_reddit.log"
UA = "photo-retrieval-research/0.1 (student research project)"
SLEEP_S = 2
RSS_SLEEP_S = 10
BLOCK_STREAK_LIMIT = 6
MAX_PAGES = 3
ATOM = {"a": "http://www.w3.org/2005/Atom"}

SUBS = ["GooglePhotos", "google", "GooglePixel", "Android", "androidapps"]
QUERIES = [
    "can't find photo",
    "cannot find old photos",
    "search old photos",
    "find photo from years ago",
    "search not working google photos",
    "ask photos",
    "ask photos can't find",
    "search by date google photos",
    "find screenshot google photos",
    "lost photo google photos search",
    "search results wrong google photos",
    "remember photo can't find",
]
COLUMNS = ["source", "doc_id", "date", "rating", "text", "score", "subreddit", "url"]
_DELETES = {"[deleted]", "[removed]"}


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


def iso_rss(s):
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ""


_SUBMITTED_RE = re.compile(r"submitted by /u/\w+", re.IGNORECASE)
_INLINE_USER_RE = re.compile(r"(?<![\w/])u/[A-Za-z0-9_]{2,}")


def html_to_text(h):
    h = _SUBMITTED_RE.sub("", h or "")
    h = _INLINE_USER_RE.sub("[user]", h)
    h = re.sub(r"<br\s*/?>", "\n", h or "")
    h = re.sub(r"</p>", "\n", h)
    text = re.sub(r"<[^>]+>", " ", h)
    text = html_mod.unescape(text)
    return re.sub(r"[ \t]+", " ", text).strip()


def part_path(sub, query):
    h = hashlib.sha256(query.encode("utf-8")).hexdigest()[:10]
    return PARTS_DIR / f"{sub}__{h}.parquet"


class StopAll(Exception):
    pass


def get_json(url, state):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    except Exception as e:
        log(f"ERROR {url[:90]} {type(e).__name__}: {str(e)[:200]}")
        return None, 0
    if r.status_code in (403, 429):
        state["block_streak"] += 1
        log(f"BLOCKED status={r.status_code} streak={state['block_streak']}/{BLOCK_STREAK_LIMIT} {r.text[:300]}")
        if state["block_streak"] >= BLOCK_STREAK_LIMIT:
            raise StopAll(f"reddit blocking: {BLOCK_STREAK_LIMIT} consecutive 403/429")
        time.sleep(15)
        return None, r.status_code
    state["block_streak"] = 0
    if r.status_code != 200:
        log(f"ERROR status={r.status_code} {url[:90]} {r.text[:300]}")
        return None, r.status_code
    try:
        return r.json(), 200
    except Exception as e:
        log(f"ERROR bad-json {url[:90]} {str(e)[:200]} {r.text[:200]}")
        return None, 200


def get_rss(url, state, backoff_s=45):
    """GET an rss url. Returns (root|None, status). 429: one backoff retry, else None."""
    for attempt in (1, 2):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        except Exception as e:
            log(f"ERROR {url[:90]} {type(e).__name__}: {str(e)[:200]}")
            return None, 0
        if r.status_code == 429:
            log(f"RATE-LIMITED 429 {url[:90]} attempt={attempt} {r.text[:200]}")
            if attempt == 1:
                time.sleep(backoff_s)
                continue
            state["skipped_rate"] += 1
            return None, 429
        state["block_streak"] = 0
        if r.status_code != 200:
            log(f"ERROR status={r.status_code} {url[:90]} {r.text[:300]}")
            return None, r.status_code
        try:
            return ET.fromstring(r.content), 200
        except Exception as e:
            log(f"ERROR bad-xml {url[:90]} {str(e)[:200]} {r.text[:200]}")
            return None, 200
    return None, 429


def post_row_json(d, sub):
    title = (d.get("title") or "").strip()
    selftext = (d.get("selftext") or "").strip()
    if title in _DELETES and not selftext:
        return None
    text = (title + "\n\n" + selftext).strip() if selftext else title
    if not text or text in _DELETES:
        return None
    rid = str(d.get("id", ""))
    if not rid:
        return None
    return {
        "source": "reddit_post",
        "doc_id": rid,
        "date": iso(d.get("created_utc")),
        "rating": None,
        "text": text,
        "score": int(d.get("score", 0) or 0),
        "subreddit": sub,
        "url": "https://www.reddit.com" + (d.get("permalink") or f"/r/{sub}/comments/{rid}/"),
    }


def fetch_pair_json(sub, query, limit_box, state):
    try:
        _fetch_pair_json_inner(sub, query, limit_box, state)
    except StopAll:
        raise


def _fetch_pair_json_inner(sub, query, limit_box, state):
    q = query + ("" if sub == "GooglePhotos" else " google photos")
    rows = []
    post_targets = []
    base = f"https://www.reddit.com/r/{sub}/search.json?q={quote_plus(q)}&restrict_sr=1&sort=new&t=all&limit=100"
    url = base
    for page in range(1, MAX_PAGES + 1):
        if limit_box is not None and limit_box["left"] <= 0:
            break
        data, status = get_json(url, state)
        if limit_box is not None:
            limit_box["left"] -= 1
        if data is None:
            break
        children = (data.get("data") or {}).get("children") or []
        for child in children:
            if child.get("kind") != "t3":
                continue
            d = child.get("data") or {}
            row = post_row_json(d, sub)
            if row is None:
                continue
            rows.append(row)
            if int(d.get("num_comments", 0) or 0) >= 3:
                post_targets.append((str(d.get("id", "")), row["url"]))
        after = (data.get("data") or {}).get("after")
        if not after:
            break
        url = base + f"&after={quote_plus(after)}"
        time.sleep(SLEEP_S)
    for rid, parent_url in post_targets:
        if limit_box is not None and limit_box["left"] <= 0:
            break
        data, status = get_json(f"https://www.reddit.com/comments/{rid}.json?limit=50", state)
        if limit_box is not None:
            limit_box["left"] -= 1
        time.sleep(SLEEP_S)
        if data is None or not isinstance(data, list) or len(data) < 2:
            continue
        children = ((data[1].get("data") or {}).get("children")) or []
        kept = 0
        for child in children:
            if kept >= 15:
                break
            if child.get("kind") != "t1":
                continue
            d = child.get("data") or {}
            body = (d.get("body") or "").strip()
            if len(body) <= 60 or body in _DELETES:
                continue
            cid = str(d.get("id", ""))
            if not cid:
                continue
            rows.append({
                "source": "reddit_comment",
                "doc_id": f"{rid}_{cid}",
                "date": iso(d.get("created_utc")),
                "rating": None,
                "text": body,
                "score": int(d.get("score", 0) or 0),
                "subreddit": sub,
                "url": parent_url,
            })
            kept += 1
    save_pair(sub, query, rows)


def rss_entries(root):
    if root is None:
        return []
    return root.findall("a:entry", ATOM) or []


def rss_entry_fields(e):
    def g(tag):
        el = e.find("a:" + tag, ATOM)
        return (el.text or "").strip() if el is not None and el.text else ""
    l = e.find("a:link", ATOM)
    return {
        "title": g("title"),
        "id": g("id"),
        "published": g("published") or g("updated"),
        "link": l.attrib.get("href", "") if l is not None else "",
        "content": g("content"),
    }


def fetch_pair_rss(sub, query, limit_box, state, comment_candidates):
    """RSS engine: one search.rss per pair (25 newest posts, single page).
       comment_candidates: shared list of (doc_id, url, sub, date) fed by phase 1."""
    q = query + ("" if sub == "GooglePhotos" else " google photos")
    url = f"https://www.reddit.com/r/{sub}/search.rss?q={quote_plus(q)}&restrict_sr=on&sort=new&t=all"
    if limit_box is not None and limit_box["left"] <= 0:
        return
    root, status = get_rss(url, state)
    if limit_box is not None:
        limit_box["left"] -= 1
    if root is None:
        log(f"RSS-SEARCH-FAIL {sub} q={query!r} status={status} - will retry on next run")
        return
    rows = []
    if True:
        for e in rss_entries(root):
            f = rss_entry_fields(e)
            m = re.search(r"comments/([a-z0-9]+)", f["link"])
            if not m or not f["id"].startswith("t3_"):
                continue
            rid = m.group(1)
            title = f["title"].strip()
            selftext = html_to_text(f["content"])
            if title in _DELETES and not selftext:
                continue
            text = (title + "\n\n" + selftext).strip() if selftext else title
            if not text or text in _DELETES:
                continue
            date_iso = iso_rss(f["published"])
            rows.append({
                "source": "reddit_post",
                "doc_id": rid,
                "date": date_iso,
                "rating": None,
                "text": text,
                "score": None,
                "subreddit": sub,
                "url": f["link"],
            })
            comment_candidates.append((rid, f["link"], sub, date_iso))
        log(f"RSS-SEARCH {sub} q={query!r}: {len(rows)} posts (rss single page, 25 max)")
    time.sleep(RSS_SLEEP_S)
    save_pair(sub, query, rows)


def save_pair(sub, query, rows):
    path = part_path(sub, query)
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=COLUMNS)
    df = df.drop_duplicates(subset="doc_id", keep="last")
    df.to_parquet(path, index=False)
    n_posts = int((df["source"] == "reddit_post").sum()) if len(df) else 0
    log(f"SAVED {sub} q={query!r}: {len(df)} rows ({n_posts} posts, {len(df) - n_posts} comments)")


def fetch_rss_comments(candidates, max_posts, limit_box):
    """Phase 2 (rss engine): per-post .rss comment feeds for selected unique posts."""
    seen = set()
    unique = []
    for rid, url, sub, date_iso in candidates:
        if rid in seen:
            continue
        seen.add(rid)
        unique.append((rid, url, sub, date_iso))
    # newest first, then stable-sort r/GooglePhotos to the front
    unique.sort(key=lambda t: t[3], reverse=True)
    unique.sort(key=lambda t: t[2] != "GooglePhotos")
    picked = unique[:max_posts]
    # resume: skip posts that already have comment rows from a previous run
    done_rids = set()
    if _COMMENT_PART.exists():
        try:
            c = pd.read_parquet(_COMMENT_PART)
            done_rids = {str(d).split("_")[0] for d in c["doc_id"].astype(str)}
        except Exception:
            pass
    todo = [t for t in picked if t[0] not in done_rids]
    log(f"RSS-COMMENTS: {len(unique)} unique posts, {len(done_rids)} already done, "
        f"fetching comment feeds for {len(todo)} of {len(picked)}")
    state = {"skipped_rate": 0}
    for rid, url, sub, date_iso in todo:
        if limit_box is not None and limit_box["left"] <= 0:
            break
        root, status = get_rss(f"https://www.reddit.com/comments/{rid}.rss", state)
        if limit_box is not None:
            limit_box["left"] -= 1
        if root is None:
            time.sleep(RSS_SLEEP_S)
            continue
        kept = 0
        for e in rss_entries(root):
            if kept >= 15:
                break
            f = rss_entry_fields(e)
            if not f["id"].startswith("t1_"):
                continue
            body = html_to_text(f["content"])
            if len(body) <= 60 or body in _DELETES:
                continue
            cid = f["id"][3:]
            rows = [{
                "source": "reddit_comment",
                "doc_id": f"{rid}_{cid}",
                "date": iso_rss(f["published"]) or date_iso,
                "rating": None,
                "text": body,
                "score": None,
                "subreddit": sub,
                "url": url,
            }]
            # append into the pair part file of this sub? comments are keyed to post,
            # not to a pair - write to a shared comment part file instead.
            _append_comment_rows(rows, sub)
            kept += 1
        time.sleep(RSS_SLEEP_S)
    log(f"RSS-COMMENTS done, rate-limited-skipped posts: {state['skipped_rate']}")


_COMMENT_PART = PARTS_DIR / "__comments__.parquet"


def _append_comment_rows(rows, sub):
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    df_new = pd.DataFrame(rows, columns=COLUMNS)
    if _COMMENT_PART.exists():
        try:
            df_all = pd.concat([pd.read_parquet(_COMMENT_PART), df_new], ignore_index=True)
        except Exception:
            df_all = df_new
    else:
        df_all = df_new
    df_all = df_all.drop_duplicates(subset="doc_id", keep="last")
    df_all.to_parquet(_COMMENT_PART, index=False)


def merge_and_report():
    frames = [pd.read_parquet(p) for p in sorted(PARTS_DIR.glob("*.parquet"))]
    if not frames:
        log("MERGE: no part files found")
        return 0
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset="doc_id", keep="first")
    df = df[COLUMNS]
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    per_source = df.groupby("source")["doc_id"].count().to_dict()
    per_sub = df.groupby("subreddit")["doc_id"].count().to_dict()
    log(f"MERGE total={len(df)} per_source={json.dumps(per_source)} per_sub={json.dumps(per_sub)} "
        f"date_min={dates.min() if len(dates) else 'n/a'} date_max={dates.max() if len(dates) else 'n/a'}")
    sample = df.sample(min(5, len(df)), random_state=42)
    for _, r in sample.iterrows():
        log(f"SAMPLE [{r['source']} r/{r['subreddit']} {r['date']}] {str(r['text'])[:150]!r}")
    sys.path.insert(0, str(BASE / "code"))
    from pipeline_counts import update_counts
    update_counts(n_reddit=int(len(df)))
    return len(df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["json", "rss"], default="json")
    ap.add_argument("--limit", type=int, default=None, help="cap on total requests this run (pilot)")
    ap.add_argument("--rss-sleep", type=int, default=10, help="seconds between per-post rss fetches")
    ap.add_argument("--max-comment-posts", type=int, default=120,
                    help="rss engine: max unique posts to fetch comment feeds for")
    args = ap.parse_args()
    log(f"START collect_reddit engine={args.engine} limit={args.limit}")
    state = {"block_streak": 0, "skipped_rate": 0}
    global RSS_SLEEP_S
    RSS_SLEEP_S = int(args.rss_sleep)
    limit_box = {"left": args.limit} if args.limit is not None else None
    if args.engine == "json":
        stopped = False
        for sub in SUBS:
            for query in QUERIES:
                if limit_box is not None and limit_box["left"] <= 0:
                    break
                if part_path(sub, query).exists():
                    log(f"SKIP {sub} q={query!r}: part file exists")
                    continue
                try:
                    fetch_pair_json(sub, query, limit_box, state)
                except StopAll as e:
                    log(f"STOPPED: {e} - saving what was collected")
                    stopped = True
                    break
            if stopped:
                break
    else:
        candidates = []
        for sub in SUBS:
            for query in QUERIES:
                if limit_box is not None and limit_box["left"] <= 0:
                    break
                if part_path(sub, query).exists():
                    log(f"SKIP {sub} q={query!r}: part file exists")
                    continue
                fetch_pair_rss(sub, query, limit_box, state, candidates)
            if limit_box is not None and limit_box["left"] <= 0:
                break
        # re-harvest candidates from already-saved part files (resume case)
        if _COMMENT_PART.exists() or not candidates:
            for p in sorted(PARTS_DIR.glob("*.parquet")):
                if p.name == "__comments__.parquet":
                    continue
                try:
                    d = pd.read_parquet(p)
                except Exception:
                    continue
                for _, r in d[d["source"] == "reddit_post"].iterrows():
                    candidates.append((str(r["doc_id"]), str(r["url"]), str(r["subreddit"]),
                                       str(r["date"])))
        fetch_rss_comments(candidates, args.max_comment_posts, limit_box)
    total = merge_and_report()
    log(f"DONE collect_reddit total={total}")


if __name__ == "__main__":
    main()
