"""Build the STATIC Discovery Engine (free HF static Space) from the data/app bundle.
Outputs: space_discovery_static/{index.html,app.js,style.css,README.md,ATTRIBUTION.md,data.json,figures/*}
data.json = episodes (182), cached answers, T1/T2/T4/T5/T7, validation, pipeline counts,
and sparse TF-IDF (vocab + per-episode [idx,val]) for client-side search.
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

BASE = Path(__file__).resolve().parents[1]
APP = BASE / "data" / "app"
OUT = BASE / "space_discovery_static"
MAX_TERMS = 3000

def clean(v):
    if isinstance(v, float) and v != v:
        return None
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    return v

def main():
    OUT.mkdir(exist_ok=True)
    ep = pd.read_parquet(APP / "episodes_public.parquet")
    cached = json.loads((APP / "cached_answers.json").read_text())
    validation = json.loads((APP / "validation_report.json").read_text())
    counts = json.loads((APP / "pipeline_counts.json").read_text())
    t7 = pd.read_csv(APP / "T7_scorecard.csv")

    episodes = []
    for _, r in ep.iterrows():
        episodes.append({
            "id": str(r["doc_id"]), "source": r["source"], "date": str(r["date"])[:10],
            "era": r["era"], "country": r.get("country_or_subreddit"), "url": r["url"],
            "snippet": r["snippet"], "gate": r["failure_gate"], "gc": bool(r.get("gate_consistent")),
            "mech": r.get("failure_mechanism"), "work": r.get("workaround"),
            "ptype": r.get("photo_type"), "qstyle": r.get("query_style"),
            "stakes": r.get("stakes"), "outcome": r.get("outcome"),
            "quote": r.get("evidence_quote"), "conf": float(r["confidence"]) if pd.notna(r.get("confidence")) else None,
            "cluster": r.get("mechanism_cluster_label"),
        })

    def rows_of(name, keep=("scope",), only_overall=True):
        t = pd.read_csv(APP / f"{name}.csv")
        out = []
        for _, r in t.iterrows():
            if only_overall and str(r.get("scope", "overall")) not in ("overall", "scored", "era_wider_rollout", "era_pre_ask", "era_early_access", "gate_" + str(r.get("scope", ""))[5:]):
                continue
            out.append({k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for k, v in r.items()})
        return out

    data = clean({
        "episodes": episodes,
        "cached_answers": cached,
        "validation": validation,
        "counts": counts,
        "t1": rows_of("T1_gate_distribution"),
        "t2": rows_of("T2_cue_matrix", only_overall=False),
        "t4": rows_of("T4_query_style"),
        "t5": rows_of("T5_workarounds"),
        "t7": t7.to_dict(orient="records"),
        "generated": "2026-10-06",
    })

    # sparse TF-IDF (same params as evidence_engine)
    txt = (ep["snippet"].fillna("") + ". " + ep["failure_mechanism"].fillna("")).tolist()
    vec = TfidfVectorizer(stop_words="english", max_features=MAX_TERMS, token_pattern=r"(?u)\b\w+\b")
    X = vec.fit_transform(txt)
    vocab = vec.get_feature_names_out().tolist()
    Xc = X.tocsr()
    docs = []
    for i in range(Xc.shape[0]):
        nz = Xc.indices[Xc.indptr[i]:Xc.indptr[i + 1]].tolist()
        vv = Xc.data[Xc.indptr[i]:Xc.indptr[i + 1]].astype("float32").tolist()
        docs.append([[int(a), round(float(b), 4)] for a, b in zip(nz, vv)])
    data["tfidf"] = {"vocab": vocab, "docs": docs}

    (OUT / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"data.json: {len(episodes)} episodes, vocab={len(vocab)}, size={OUT.joinpath('data.json').stat().st_size/1e6:.2f} MB")

    for f in ["F1_gate_distribution.png", "F2_remembered_vs_missing.png", "F3_phototype_gate_heatmap.png",
              "F4_query_styles_and_workarounds.png", "F5_mechanism_clusters.png", "F6_scorecard_top10.png"]:
        src = BASE / "figures" / f
        if src.exists():
            dst = OUT / "figures"
            dst.mkdir(exist_ok=True)
            shutil.copy(src, dst / f)
    print("static bundle data + figures copied")

if __name__ == "__main__":
    main()
