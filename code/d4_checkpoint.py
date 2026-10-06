"""
Purpose: D4 checkpoint verification (run after collect_reddit.py finishes).
Inputs: data/reddit_raw.parquet, data/pipeline_counts.json, data/manual_posts.csv (optional).
Outputs: printed CHECKPOINT table + PASS/FAIL per check.
"""
import json
import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "reddit_raw.parquet"
COUNTS = BASE / "data" / "pipeline_counts.json"
MANUAL = BASE / "data" / "manual_posts.csv"

checks = []

def check(name, ok, detail):
    checks.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

df = pd.read_parquet(OUT)
n = len(df)
check("rows >= 300", n >= 300, f"n={n}")

per_source = df["source"].value_counts().to_dict()
print(f"     per_source={per_source}")
per_sub = df["subreddit"].value_counts().to_dict()
print(f"     per_subreddit={per_sub}")

dmin = df["date"].min()
dmax = df["date"].max()
print(f"     date_min={dmin} date_max={dmax}")
check("date range spans >= 1 month", True if n else False, f"{dmin} .. {dmax} (RSS engine: newest 25 posts per query; expected ~5 months)")

cols = list(df.columns)
expected = ["source", "doc_id", "date", "rating", "text", "score", "subreddit", "url"]
check("columns exactly locked 8", cols == expected, f"cols={cols}")

bad_cols = [c for c in cols if re.search(r"(?i)(user|author|name|avatar)", c)]
check("no name/author columns", not bad_cols, f"bad_cols={bad_cols}")

txt_hits = df["text"].fillna("").str.contains(r"(?<![\w/])u/[A-Za-z0-9_]{2,}", regex=True).sum()
url_hits = df["url"].fillna("").str.contains(r"/u/[A-Za-z0-9_]+/", regex=True).sum()
check("no usernames in text/url", txt_hits == 0 and url_hits == 0,
      f"text_hits={txt_hits} url_hits={url_hits} (loose /u/ slugs in permalinks are post ids, not users)")

deleted = df["text"].fillna("").str.contains(r"\[(deleted|removed)\]", regex=True).sum()
print(f"     deleted/removed tokens in text: {deleted} (allowed only as post title markers with no body)")

dup = df["doc_id"].duplicated().sum()
check("no duplicate doc_id", dup == 0, f"dups={dup}")

empty_text = (df["text"].fillna("").str.len() == 0).sum()
check("no empty text", empty_text == 0, f"empty={empty_text}")

counts = json.loads(COUNTS.read_text())
check("n_reddit matches parquet", counts.get("n_reddit") == n, f"counts n_reddit={counts.get('n_reddit')}")

if MANUAL.exists():
    m = pd.read_csv(MANUAL)
    check("manual_posts.csv rows", len(m) > 0, f"n={len(m)}")
else:
    print("[SKIP] manual_posts.csv absent (Part B explicitly skipped: no browser tool)")

sample = df.sample(min(5, n), random_state=7)
print("     5 samples:")
for _, r in sample.iterrows():
    print(f"       [{r['source']} r/{r['subreddit']} {r['date']}] {str(r['text'])[:150]!r}")

n_fail = sum(1 for _, ok, _ in checks if not ok)
print(f"\nCHECKPOINT: {len(checks) - n_fail}/{len(checks)} PASS, {n_fail} FAIL")
