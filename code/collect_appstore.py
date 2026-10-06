"""
Purpose: D3 - collect Google Photos App Store reviews from Apple's public
         customer-reviews RSS/JSON feed for 10 countries x up to 10 pages,
         with resume support (part files under data/appstore_parts/).
Inputs: app id 962194608 (verified at runtime via itunes lookup, search fallback);
        network access to itunes.apple.com.
Outputs: data/appstore_parts/{country}.parquet; data/appstore_raw.parquet;
         logs/collect_appstore.log; data/pipeline_counts.json key n_appstore.
Privacy: author names are NOT stored (author field never copied).
Usage: .venv/bin/python code/collect_appstore.py [--limit N]
       --limit N: cap on total rows fetched in this run (pilots).
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent
PARTS_DIR = BASE / "data" / "appstore_parts"
OUT_PARQUET = BASE / "data" / "appstore_raw.parquet"
LOG_PATH = BASE / "logs" / "collect_appstore.log"
# D6 checkpoint remedy: countries extended 2026-10-06 (episodes 175 < 400)
COUNTRIES = ["us", "in", "gb", "au", "ca", "sg", "za", "ie", "nz", "ph",
            "de", "fr", "es", "mx", "br", "my", "id", "ae", "sa", "jp"]
MAX_PAGES = 10
HEADERS = {"User-Agent": "student-research/0.1"}
COLUMNS = ["source", "doc_id", "date", "rating", "text", "app_version", "country", "url"]


def log(msg):
    line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def resolve_app_id():
    try:
        r = requests.get("https://itunes.apple.com/lookup?id=962194608&country=us",
                         headers=HEADERS, timeout=20)
        if r.status_code == 200:
            data = r.json()
            if data.get("results"):
                name = data["results"][0].get("trackName", "")
                if "Google Photos" in name:
                    log(f"app id verified: 962194608 trackName={name!r}")
                    return 962194608
                log(f"lookup 962194608 returned {name!r} - falling back to search")
            else:
                log(f"lookup empty results, status {r.status_code}: {r.text[:300]}")
        else:
            log(f"lookup status {r.status_code}: {r.text[:300]}")
    except Exception as e:
        log(f"lookup error: {type(e).__name__}: {str(e)[:200]}")
    try:
        r = requests.get("https://itunes.apple.com/search?term=google+photos&entity=software&country=us",
                         headers=HEADERS, timeout=20)
        if r.status_code == 200:
            for item in r.json().get("results", []):
                if item.get("trackName", "").strip() == "Google Photos":
                    log(f"search found trackId={item['trackId']} {item.get('trackName')!r}")
                    return int(item["trackId"])
        else:
            log(f"search status {r.status_code}: {r.text[:300]}")
    except Exception as e:
        log(f"search error: {type(e).__name__}: {str(e)[:200]}")
    raise SystemExit("BLOCKED: could not verify the Google Photos app id")


def fetch_country(app_id, country, limit_left):
    path = PARTS_DIR / f"{country}.parquet"
    have_df = None
    if path.exists():
        try:
            have_df = pd.read_parquet(path)
        except Exception:
            have_df = None
    seen = set(have_df["doc_id"].astype(str)) if have_df is not None and len(have_df) else set()
    rows = []
    for page in range(1, MAX_PAGES + 1):
        if limit_left is not None and limit_left <= 0:
            break
        url = (f"https://itunes.apple.com/{country}/rss/customerreviews/"
               f"page={page}/id={app_id}/sortby=mostrecent/json")
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                log(f"ERROR {country} page {page}: HTTP {r.status_code} {r.text[:300]}")
                time.sleep(3)
                continue
            feed = r.json()
        except Exception as e:
            log(f"ERROR {country} page {page}: {type(e).__name__}: {str(e)[:200]}")
            time.sleep(3)
            continue
        entries = feed.get("feed", {}).get("entry", [])
        if isinstance(entries, dict):
            entries = [entries]
        if not entries:
            log(f"STOP {country} page {page}: no entries (feed exhausted)")
            break
        added = 0
        for e in entries:
            rating = (e.get("im:rating") or {}).get("label")
            if not rating:
                continue
            rid = str((e.get("id") or {}).get("label", ""))
            if not rid or rid in seen:
                continue
            title = (e.get("title") or {}).get("label", "") or ""
            content = (e.get("content") or {}).get("label", "") or ""
            updated = (e.get("updated") or {}).get("label", "") or ""
            version = (e.get("im:version") or {}).get("label", "") or ""
            link = ""
            links = e.get("link") or []
            if isinstance(links, dict):
                links = [links]
            for l in links:
                href = l.get("href") if isinstance(l, dict) else None
                if href:
                    link = href
                    break
            if not link:
                link = f"https://apps.apple.com/{country}/app/id{app_id}/#review-{rid}"
            text = (title + ". " + content) if title else content
            rows.append({
                "source": "appstore",
                "doc_id": rid,
                "date": updated,
                "rating": int(rating),
                "text": text,
                "app_version": version,
                "country": country,
                "url": link,
            })
            added += 1
        running = len(rows) + (len(have_df) if have_df is not None else 0)
        log(f"PROGRESS {country} page {page}: +{added} (running total {running})")
        time.sleep(1)
        if limit_left is not None:
            limit_left = max(0, limit_left - added)
    if rows or (have_df is not None and len(have_df)):
        PARTS_DIR.mkdir(parents=True, exist_ok=True)
        if have_df is not None and len(have_df):
            df = pd.concat([have_df, pd.DataFrame(rows, columns=COLUMNS)], ignore_index=True)
        else:
            df = pd.DataFrame(rows, columns=COLUMNS)
        df = df.drop_duplicates(subset="doc_id", keep="last")
        df.to_parquet(path, index=False)
        log(f"SAVED {country}: {len(df)} rows")
        return len(df)
    log(f"EMPTY {country}: 0 rows collected")
    return 0


def merge_and_report():
    frames = [pd.read_parquet(p) for p in sorted(PARTS_DIR.glob("*.parquet")) if p.exists()]
    if not frames:
        log("MERGE: no part files found")
        return 0
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset="doc_id", keep="last")
    df = df[COLUMNS]
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    per_country = df.groupby("country")["doc_id"].count().to_dict()
    log(f"MERGE total={len(df)} per_country={json.dumps(per_country)}")
    sample = df.sample(min(5, len(df)), random_state=42)
    for _, r in sample.iterrows():
        log(f"SAMPLE [{r['country']} {r['date']} rating={r['rating']}] {r['text'][:150]!r}")
    sys_path = str(BASE / "code")
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    from pipeline_counts import update_counts
    update_counts(n_appstore=int(len(df)))
    return len(df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="cap rows fetched this run (pilot)")
    args = ap.parse_args()
    log(f"START collect_appstore limit={args.limit}")
    app_id = resolve_app_id()
    limit_left = args.limit
    for country in COUNTRIES:
        if limit_left is not None and limit_left <= 0:
            break
        fetch_country(app_id, country, limit_left)
    total = merge_and_report()
    log(f"DONE collect_appstore total={total}")


if __name__ == "__main__":
    import sys
    main()
