"""
Purpose: D6 STEPS 5-6 - verify evidence quotes, compute pass-2 gate agreement,
         join stage-2 output with docs_clean and write data/episodes_full.parquet
         (only is_retrieval_episode == True rows, stage-2 fields flattened,
         remembered_cues as JSON string).
Inputs : data/stage2_v1.parquet, data/stage2_v1b.parquet (optional),
         data/docs_clean.parquet, data/pipeline_counts.json.
Outputs: data/episodes_full.parquet
         data/pipeline_counts.json keys: n_extracted_attempted, n_episodes,
         quote_verified_pct, error_pct, gate_pass_agreement
Usage  : .venv/bin/python code/finalize_stage2.py
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
from pipeline_counts import update_counts  # noqa: E402


def norm(s) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def main():
    v1 = pd.read_parquet(BASE / "data" / "stage2_v1.parquet")
    v1b = None
    p = BASE / "data" / "stage2_v1b.parquet"
    if p.exists():
        v1b = pd.read_parquet(p)

    clean = pd.read_parquet(BASE / "data" / "docs_clean.parquet")[
        ["doc_id", "source", "date", "rating", "text", "url", "country", "app_version", "score", "subreddit", "era", "control"]]

    df = v1.merge(clean, on="doc_id", how="left", suffixes=("", "_doc"))
    n_attempted = len(df)
    n_err = int(df["_error"].notna().sum())

    # ---- STEP 5: quote verification ----
    def check_quote(row):
        q = row.get("evidence_quote")
        if q is None or (isinstance(q, float)):
            return (q, None)
        qn, tn = norm(q), norm(row["text"])
        ok = qn in tn
        return (q, ok)

    parsed = []
    for _, r in df.iterrows():
        try:
            ep = json.loads(r["episode_json"])
        except Exception:
            ep = {"_error": "bad episode_json"}
        parsed.append(ep)
    df["episode_json_parsed"] = parsed

    qv = []
    for _, r in df.iterrows():
        q = r["episode_json_parsed"].get("evidence_quote") if not str(r["episode_json_parsed"]).startswith('{"_error"') else None
        if q in (None, "", "null"):
            qv.append((q, None))
        else:
            ok = norm(q) in norm(r["text"])
            if not ok:
                q = None
            qv.append((q, ok))
    df["evidence_quote"] = [a for a, _ in qv]
    df["quote_verified"] = [b for _, b in qv]
    n_q = int(df["quote_verified"].notna().sum())
    n_qv = int(df["quote_verified"].fillna(False).sum())
    print(f"quotes present: {n_q}, verified substrings: {n_qv} ({100*n_qv/n_q:.1f}%)" if n_q else "no quotes")

    # flatten
    flat_cols = ["retrieval_intent", "photo_type", "photo_age", "query_attempted", "query_style",
                 "failure_gate", "failure_mechanism", "workaround", "stakes", "outcome", "confidence"]
    for c in flat_cols:
        df[c] = df["episode_json_parsed"].map(lambda ep: ep.get(c) if isinstance(ep, dict) and "_error" not in ep else None)
    df["missing_cue_types"] = df["episode_json_parsed"].map(
        lambda ep: json.dumps(ep.get("missing_cue_types") or [], ensure_ascii=False)
        if isinstance(ep, dict) and "_error" not in ep else None)
    df["remembered_cues"] = df["episode_json_parsed"].map(
        lambda ep: json.dumps([c if isinstance(c, dict) else c for c in (ep.get("remembered_cues") or [])], ensure_ascii=False)
        if isinstance(ep, dict) and "_error" not in ep else None)

    # ---- STEP 4b agreement ----
    if v1b is not None:
        m = df.merge(v1b[["doc_id", "failure_gate"]].rename(columns={"failure_gate": "gate_pass2"}),
                     on="doc_id", how="left")
        both = m["failure_gate"].notna() & m["gate_pass2"].notna()
        agree = (m.loc[both, "failure_gate"] == m.loc[both, "gate_pass2"])
        agreement = float(agree.mean()) if len(agree) else None
        df = df.merge(v1b[["doc_id", "failure_gate"]].rename(columns={"failure_gate": "gate_pass2"}), on="doc_id", how="left")
        df["gate_consistent"] = df.apply(
            lambda r: bool(r["failure_gate"] == r["gate_pass2"]) if pd.notna(r["failure_gate"]) and pd.notna(r["gate_pass2"]) else None, axis=1)
        print(f"pass-2 gate agreement: {agreement and round(100*agreement, 1)}% over {int(both.sum())} docs with both gates")
    else:
        df["gate_pass2"] = None
        df["gate_consistent"] = None
        agreement = None

    episodes = df[df["is_retrieval_episode"] == True].copy()  # noqa: E712
    keep = ["doc_id", "source", "date", "rating", "text", "url", "country", "app_version", "score",
            "subreddit", "era", "control",
            "is_retrieval_episode", "retrieval_intent", "photo_type", "photo_age", "remembered_cues",
            "missing_cue_types", "query_attempted", "query_style", "failure_gate", "gate_pass2",
            "gate_consistent", "failure_mechanism", "workaround", "stakes", "outcome",
            "evidence_quote", "quote_verified", "confidence", "_error"]
    episodes = episodes[keep]
    out = BASE / "data" / "episodes_full.parquet"
    episodes.to_parquet(out, index=False)
    print(f"saved {out}: {len(episodes)} episodes (of {n_attempted} attempted; errors={n_err})")

    update_counts(
        n_extracted_attempted=n_attempted,
        n_episodes=len(episodes),
        quote_verified_pct=round(100 * n_qv / n_q, 1) if n_q else None,
        error_pct=round(100 * n_err / n_attempted, 2) if n_attempted else None,
        gate_pass_agreement=round(agreement, 3) if agreement is not None else None,
    )
    print("update_counts done")


if __name__ == "__main__":
    main()
