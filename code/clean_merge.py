"""
Purpose: D5 - merge all raw feedback sources (play/appstore/reddit/manual),
         clean them, tag era + keyword hit, and build the LLM input set.
Inputs : data/play_raw.parquet, data/appstore_raw.parquet, data/reddit_raw.parquet,
         data/manual_posts.csv (whichever exist).
Outputs: data/docs_clean.parquet
         data/docs_for_llm.parquet (kw_hit rows + control sample, seed 42)
         data/pipeline_counts.json keys: n_clean, n_kw_hit, n_for_llm, control_rate
Notes  : columns aligned to source, doc_id, date, rating, text, url, country,
         app_version, score (+ subreddit kept for reddit rows, used by D9 as
         country_or_subreddit). Era boundaries per locked context (working
         assumption, verify before deck). Username fields are absent from all
         raw sources by construction (D2/D3/D4).
Usage  : .venv/bin/python code/clean_merge.py
"""
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
from pipeline_counts import update_counts  # noqa: E402

# ---- era boundaries (locked context; D0 fact check found no contradiction) ----
ERA_EARLY = datetime(2024, 10, 1, tzinfo=timezone.utc)
ERA_WIDER = datetime(2025, 6, 1, tzinfo=timezone.utc)

# ---- keyword regex (module D5 list, word-boundary aware) ----
_FULL = [  # full-word alternatives: \b on both sides
    r"search", r"find", r"lost", r"missing", r"disappear", r"vanish", r"album",
    r"date", r"results", r"scroll", r"timeline", r"screenshot", r"document",
    r"receipt", r"face", r"people", r"sort", r"finding",
]
_STEM = [  # stem alternatives: leading \b only (match retrieval, memory, remember)
    r"memor", r"retriev",
]
_PHRASE = [  # multi-word / special forms: \b on both sides
    r"can'?t find", r"cannot find", r"couldn'?t find",
    r"old\s+photos?\b", r"old\s+pictures?\b", r"old\s+videos?\b",
    r"years\s+ago", r"where\s+is", r"locate", r"ask\s+photos", r"ask\s+tab",
]
KW_REGEX = re.compile(
    "|".join(
        [r"\b" + a + r"\b" for a in _FULL]
        + [r"\b" + a for a in _STEM]
        + [r"\b" + a + r"\b" for a in _PHRASE]
    ),
    re.IGNORECASE,
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s\-()]{7,}\d)(?!\d)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
# curly quotes -> straight, via escapes (file-safe)
REPLACEMENTS = [
    ("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("&nbsp;", " "),
]


def strip_html(t: str) -> str:
    t = HTML_TAG_RE.sub(" ", t or "")
    for a, b in REPLACEMENTS:
        t = t.replace(a, b)
    return t


def clean_text(t: str) -> str:
    t = strip_html(str(t))
    t = EMAIL_RE.sub(" [email removed] ", t)
    t = PHONE_RE.sub(" [phone removed] ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_date(v):
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def era_of(dt):
    if dt is None:
        return None
    if dt < ERA_EARLY:
        return "pre_ask"
    if dt < ERA_WIDER:
        return "early_access"
    return "wider_rollout"


def load_sources():
    frames = []
    play = BASE / "data" / "play_raw.parquet"
    if play.exists():
        df = pd.read_parquet(play)
        keep = ["doc_id", "date", "rating", "text", "country", "app_version"]
        out = df[keep].assign(source="play", score=None)
        out["url"] = df["url"] if "url" in df else None
        frames.append(out)
    app = BASE / "data" / "appstore_raw.parquet"
    if app.exists():
        df = pd.read_parquet(app)
        keep = ["doc_id", "date", "rating", "text", "country", "app_version"]
        out = df[keep].assign(source="appstore", score=None)
        out["url"] = df["url"] if "url" in df else None
        frames.append(out)
    red = BASE / "data" / "reddit_raw.parquet"
    if red.exists():
        df = pd.read_parquet(red)
        out = df[["doc_id", "date", "rating", "text", "url", "score"]].assign(
            source="reddit", country=None, app_version=None, subreddit=df["subreddit"])
        frames.append(out)
    man = BASE / "data" / "manual_posts.csv"
    if man.exists():
        df = pd.read_csv(man)
        cols = {}
        for c in ("doc_id", "date", "rating", "text", "url", "score"):
            if c in df:
                cols[c] = df[c]
        out = pd.DataFrame(cols)
        out = out.assign(source="community", country=None, app_version=None, subreddit=None)
        frames.append(out)
    return frames


def main():
    frames = load_sources()
    if not frames:
        print("BLOCKED: no raw sources found")
        return
    df = pd.concat(frames, ignore_index=True)
    df = df.reindex(columns=["source", "doc_id", "date", "rating", "text", "url",
                             "country", "app_version", "score", "subreddit"])
    n0 = len(df)
    print(f"loaded: {n0} rows  per_source={df['source'].value_counts().to_dict()}")

    df["text"] = df["text"].map(clean_text)
    print(f"after html/email/phone/whitespace clean: {len(df)}")

    wc = df["text"].str.split().str.len().fillna(0)
    mask = wc >= 8
    print(f"dropped <8 words: {int((~mask).sum())}  -> {int(mask.sum())}")
    df = df[mask].copy()

    df["_norm"] = df["text"].str.lower().str.strip()
    mask = ~df["_norm"].duplicated(keep="first")
    print(f"dropped exact dups: {int((~mask).sum())}  -> {int(mask.sum())}")
    df = df[mask].copy()

    df["_first120"] = df["_norm"].str[:120]
    mask = ~df["_first120"].duplicated(keep="first")
    print(f"dropped near-dups (same first 120 chars): {int((~mask).sum())}  -> {int(mask.sum())}")
    df = df[mask].copy()

    from langdetect import detect
    t0 = time.time()
    langs = []
    for i, t in enumerate(df["text"]):
        try:
            langs.append(detect(t[:500]))
        except Exception:
            langs.append(None)
        if (i + 1) % 2000 == 0:
            print(f"  langdetect {i+1}/{len(df)} ({time.time()-t0:.0f}s)")
    df["_lang"] = langs
    mask = df["_lang"].isna() | (df["_lang"] == "en")
    print(f"dropped non-English: {int((~mask).sum())} {df.loc[~mask, '_lang'].value_counts().to_dict()}  -> {int(mask.sum())}")
    df = df[mask].copy()

    dts = df["date"].map(parse_date)
    df["era"] = dts.map(era_of)
    print(f"era: {df['era'].value_counts(dropna=False).to_dict()}  (unparseable dates: {int(dts.isna().sum())})")

    df["kw_hit"] = df["_norm"].map(lambda s: bool(KW_REGEX.search(s)))
    n_kw = int(df["kw_hit"].sum())
    print(f"kw_hit rows: {n_kw}")
    g = df.groupby("source").agg(n=("doc_id", "size"), kw=("kw_hit", "sum"))
    g["share_pct"] = (100 * g["kw"] / g["n"]).round(1)
    print("kw_hit share per source:\n" + g.to_string())

    kept = df.drop(columns=["_norm", "_first120", "_lang"])

    # ---- control sample first (seed 42) so docs_clean carries the control flag ----
    rng = np.random.default_rng(42)
    nonkw_idx = kept.index[~kept["kw_hit"]]
    ctrl_rate = 0.05
    n_ctrl = int(round(len(nonkw_idx) * ctrl_rate))
    if n_ctrl < 1500:
        ctrl_rate = 0.10
        n_ctrl = int(round(len(nonkw_idx) * ctrl_rate))
    ctrl_idx = rng.choice(nonkw_idx, size=min(n_ctrl, len(nonkw_idx)), replace=False)
    kept["control"] = kept.index.isin(ctrl_idx)

    out = BASE / "data" / "docs_clean.parquet"
    kept.to_parquet(out, index=False)
    print(f"saved {out} ({len(kept)} rows)")

    # ---- docs_for_llm: kw_hit + control sample ----
    kw = kept[kept["kw_hit"]].copy()
    ctrl = kept[kept["control"]].copy()
    forl = pd.concat([kw, ctrl], ignore_index=True)
    forl = forl.sample(frac=1.0, random_state=42).reset_index(drop=True)
    out2 = BASE / "data" / "docs_for_llm.parquet"
    forl.to_parquet(out2, index=False)
    print(f"saved {out2} ({len(forl)} rows; kw_hit={len(kw)}, controls={len(ctrl)}, control_rate={ctrl_rate})")

    update_counts(n_clean=len(kept), n_kw_hit=n_kw, n_for_llm=len(forl), control_rate=ctrl_rate)
    print("done")


if __name__ == "__main__":
    main()
