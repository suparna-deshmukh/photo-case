"""
Purpose: D2 - collect Google Photos Google Play Store reviews for 8 countries x
         2 sort modes (newest + most_relevant) with resume support: combos whose
         part file under data/play_parts/ is complete are skipped, partial part
         files are continued (deduped by doc_id). 1 s sleep between API calls;
         defensive error handling with a 5-consecutive-error stop; progress log.
Inputs: app id com.google.android.apps.photos; locked country table; existing
        part files (resume); network access to the Play Store.
Outputs: data/play_parts/{country}_{sort}.parquet per combo;
         data/play_raw.parquet (merged, fixed columns, no PII columns);
         logs/collect_play.log (progress/errors, no names);
         data/pipeline_counts.json key n_play.
Privacy: userName and avatar (userImage) fields are dropped immediately and
         never written to any file.
Usage: .venv/bin/python code/collect_play.py [--limit N]
       --limit N: cap on total rows fetched in this run (pilots).
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from google_play_scraper import reviews as gp_reviews
from google_play_scraper import Sort

BASE = Path(__file__).resolve().parent.parent
PARTS_DIR = BASE / "data" / "play_parts"
OUT_PARQUET = BASE / "data" / "play_raw.parquet"
LOG_PATH = BASE / "logs" / "collect_play.log"
APP_ID = "com.google.android.apps.photos"

# locked table: (country, lang, newest_count, most_relevant_count)
# D6 checkpoint remedy: targets raised 2026-10-06 (episodes 175 < 400);
# module D6 allows "raise counts in D2-D4". Logged in STATE.md + deck notes.
TABLE = [
    ("in", "en", 5000, 3000),
    ("us", "en", 4000, 3000),
    ("gb", "en", 1600, 1000),
    ("au", "en", 1200, 600),
    ("ca", "en", 1200, 600),
    ("sg", "en", 600, 400),
    ("za", "en", 600, 400),
    ("ph", "en", 600, 400),
    ("de", "en", 800, 500),
    ("fr", "en", 800, 500),
    ("es", "en", 800, 500),
    ("br", "en", 800, 500),
    ("mx", "en", 800, 500),
    ("my", "en", 500, 300),
    ("id", "en", 500, 300),
    ("ae", "en", 500, 300),
    ("th", "en", 500, 300),
    ("vn", "en", 500, 300),
]
COLUMNS = ["source", "doc_id", "date", "rating", "text", "thumbs_up",
           "app_version", "country", "sort_mode", "url"]


def log(msg):
    line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def part_path(country, sort_name):
    return PARTS_DIR / f"{country}_{sort_name}.parquet"


def convert(rec, country, sort_name):
    at = rec.get("at")
    if isinstance(at, datetime):
        date_iso = at.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        try:
            date_iso = datetime.fromtimestamp(int(at), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            date_iso = ""
    rid = str(rec.get("reviewId", ""))
    return {
        "source": "play",
        "doc_id": rid,
        "date": date_iso,
        "rating": int(rec.get("score", 0) or 0),
        "text": rec.get("content") or "",
        "thumbs_up": int(rec.get("thumbsUpCount", 0) or 0),
        "app_version": str(rec.get("appVersion") or ""),
        "country": country,
        "sort_mode": sort_name,
        "url": f"https://play.google.com/store/apps/details?id={APP_ID}&reviewId={rid}",
    }


def fetch_combo(country, lang, sort_name, sort_const, target, limit_box):
    path = part_path(country, sort_name)
    have = 0
    seen = set()
    if path.exists():
        try:
            prev = pd.read_parquet(path)
            have = len(prev)
            seen = set(prev["doc_id"].astype(str))
            if have >= target:
                log(f"SKIP {country}/{sort_name}: already complete ({have} rows)")
                return
            log(f"RESUME {country}/{sort_name}: continuing from {have} rows")
        except Exception as e:
            log(f"WARN {country}/{sort_name}: unreadable part file ({str(e)[:120]}); refetching")
            have, seen = 0, set()
    rows = []
    token = None
    consecutive_errors = 0
    while have + len(rows) < target:
        remaining = target - have - len(rows)
        if limit_box is not None:
            if limit_box["left"] <= 0:
                log(f"LIMIT reached for {country}/{sort_name} at {have + len(rows)} rows")
                break
            remaining = min(remaining, limit_box["left"])
        want = min(200, remaining)
        try:
            result = gp_reviews(APP_ID, lang=lang, country=country,
                                sort=sort_const, count=want,
                                continuation_token=token)
            if isinstance(result, tuple):
                batch, token = result
            else:
                batch, token = result, None
        except Exception as e:
            consecutive_errors += 1
            log(f"ERROR {country}/{sort_name} @row {have + len(rows)}: {type(e).__name__}: {str(e)[:200]}")
            if consecutive_errors >= 5:
                log(f"STOP {country}/{sort_name} after 5 consecutive errors")
                break
            time.sleep(5)
            continue
        consecutive_errors = 0
        fresh = []
        for rec in batch:
            row = convert(rec, country, sort_name)
            if not row["doc_id"] or row["doc_id"] in seen:
                continue
            seen.add(row["doc_id"])
            fresh.append(row)
        rows.extend(fresh)
        if limit_box is not None:
            limit_box["left"] -= len(fresh)
        time.sleep(1)
        log(f"PROGRESS {country}/{sort_name}: {have + len(rows)}/{target} (token={'yes' if token else 'no'})")
        if not token:
            break
    if rows:
        PARTS_DIR.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                df_all = pd.concat([pd.read_parquet(path), pd.DataFrame(rows, columns=COLUMNS)],
                                   ignore_index=True)
            except Exception:
                df_all = pd.DataFrame(rows, columns=COLUMNS)
        else:
            df_all = pd.DataFrame(rows, columns=COLUMNS)
        df_all = df_all.drop_duplicates(subset="doc_id", keep="last")
        df_all.to_parquet(path, index=False)
        log(f"SAVED {country}/{sort_name}: {len(df_all)} rows")


TARGETS = {
    ("in", "newest"): 2500, ("in", "most_relevant"): 1500,
    ("us", "newest"): 2000, ("us", "most_relevant"): 1500,
    ("gb", "newest"): 800, ("gb", "most_relevant"): 500,
    ("au", "newest"): 600, ("au", "most_relevant"): 300,
    ("ca", "newest"): 600, ("ca", "most_relevant"): 300,
    ("sg", "newest"): 300, ("sg", "most_relevant"): 200,
    ("za", "newest"): 300, ("za", "most_relevant"): 200,
    ("ph", "newest"): 300, ("ph", "most_relevant"): 200,
}


def merge_and_report():
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    frames = [pd.read_parquet(p) for p in sorted(PARTS_DIR.glob("*.parquet"))]
    if not frames:
        log("MERGE: no part files found")
        return 0
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["doc_id", "country", "sort_mode"], keep="last")
    # The scraper returns full ~200-row batches, so part files can overshoot a
    # combo target. Truncate each (country, sort_mode) to its locked target here;
    # part files keep the full raw collection.
    parts = []
    for (country, sort_mode), target in TARGETS.items():
        g = df[(df["country"] == country) & (df["sort_mode"] == sort_mode)]
        if len(g) > target:
            log(f"TRUNCATE {country}/{sort_mode}: {len(g)} -> {target} (locked table target)")
        parts.append(g.head(target))
    for (country, sort_mode) in set(zip(df["country"], df["sort_mode"])) - set(TARGETS):
        log(f"WARN untabled combo in parts: {country}/{sort_mode} (kept as-is)")
        parts.append(df[(df["country"] == country) & (df["sort_mode"] == sort_mode)])
    df = pd.concat(parts, ignore_index=True)
    df = df[COLUMNS]
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    total = len(df)
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    dmin = str(dates.min()) if len(dates) else "n/a"
    dmax = str(dates.max()) if len(dates) else "n/a"
    per_country = df.groupby("country")["doc_id"].count().to_dict()
    log(f"MERGE total={total} date_min={dmin} date_max={dmax}")
    log("PER_COUNTRY " + json.dumps(per_country))
    sample = df.sample(min(5, len(df)), random_state=42)
    for _, r in sample.iterrows():
        log(f"SAMPLE [{r['country']}/{r['sort_mode']} {r['date']} rating={r['rating']}] {str(r['text'])[:150]!r}")
    sys.path.insert(0, str(BASE / "code"))
    from pipeline_counts import update_counts
    update_counts(n_play=int(total))
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="cap on total rows fetched this run (pilot)")
    args = ap.parse_args()
    log(f"START collect_play limit={args.limit}")
    limit_box = {"left": args.limit} if args.limit is not None else None
    for country, lang, newest_target, relevant_target in TABLE:
        fetch_combo(country, lang, "newest", Sort.NEWEST, newest_target, limit_box)
        fetch_combo(country, lang, "most_relevant", Sort.MOST_RELEVANT, relevant_target, limit_box)
    total = merge_and_report()
    log(f"DONE collect_play total={total}")


if __name__ == "__main__":
    main()
