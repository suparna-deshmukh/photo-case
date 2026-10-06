"""
Purpose: D9 - build the public dataset + embeddings + app data bundle for the
         Discovery Engine Space (BASE/data/app/).
Inputs : data/episodes_full.parquet, data/tables/T1-T7 + T6_cluster_map,
         figures/F1-F6, data/validation_report.json, data/pipeline_counts.json.
Outputs: data/app/episodes_public.parquet (no usernames, snippet <=280 chars),
         data/app/episodes_emb.npy (float32, normalized), data/app/emb_ids.json,
         copies of tables/figures/validation/pipeline_counts, data/app/enums.json.
Usage  : .venv/bin/python code/build_app_data.py
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
APP = BASE / "data" / "app"
APP.mkdir(parents=True, exist_ok=True)


def snippet(t: str, n: int = 280) -> str:
    t = "" if t is None or (isinstance(t, float)) else str(t)
    if len(t) <= n:
        return t
    cut = t[:n]
    if " " in cut[200:]:
        cut = cut[:cut.rfind(" ", 200, n)]
    return cut.rstrip() + "…"


def main():
    ep = pd.read_parquet(BASE / "data" / "episodes_full.parquet")
    cmap = None
    mp = BASE / "data" / "tables" / "T6_cluster_map.csv"
    if mp.exists():
        cmap = pd.read_csv(mp)

    pub = ep.copy()
    pub["country_or_subreddit"] = np.where(pub["subreddit"].notna(), pub["subreddit"], pub["country"])
    pub["snippet"] = pub["text"].map(snippet)
    if cmap is not None:
        pub = pub.merge(cmap, on="doc_id", how="left")
        pub = pub.rename(columns={"cluster_label": "mechanism_cluster_label"})
    else:
        pub["mechanism_cluster_label"] = None
    keep = ["doc_id", "source", "date", "era", "rating", "country_or_subreddit", "url", "snippet",
            "retrieval_intent", "photo_type", "photo_age", "remembered_cues", "missing_cue_types",
            "query_attempted", "query_style", "failure_gate", "gate_consistent", "failure_mechanism",
            "workaround", "stakes", "outcome", "evidence_quote", "confidence", "mechanism_cluster_label"]
    pub = pub[keep]
    # safety: no username-like columns
    assert not [c for c in pub.columns if any(w in c.lower() for w in ("user", "author", "name", "avatar"))]
    pub.to_parquet(APP / "episodes_public.parquet", index=False)
    print(f"episodes_public.parquet: {len(pub)} rows")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    txt = (pub["snippet"].fillna("") + ". " + pub["failure_mechanism"].fillna("")).tolist()
    X = model.encode(txt, normalize_embeddings=True, show_progress_bar=False).astype("float32")
    np.save(APP / "episodes_emb.npy", X)
    (APP / "emb_ids.json").write_text(json.dumps(list(pub["doc_id"].astype(str))))
    print(f"embeddings: {X.shape}")

    for name in [f"T{i}_{n}" for i, n in [
        (1, "gate_distribution"), (1, "robust_consistent_only"), (2, "cue_matrix"), (2, "cue_certainty"),
        (2, "cue_by_phototype"), (3, "phototype_by_gate"), (3, "phototype_by_gate_pct"),
        (4, "query_style"), (5, "workarounds"), (6, "mechanisms"), (6, "cluster_map"), (7, "scorecard")]]:
        src = BASE / "data" / "tables" / f"{name}.csv"
        if src.exists():
            shutil.copy(src, APP / f"{name}.csv")
    for f in ["T7_scorecard.csv"]:
        src = BASE / "data" / "tables" / f
        if src.exists():
            shutil.copy(src, APP / f)
    for f in ["F1_gate_distribution.png", "F2_remembered_vs_missing.png", "F3_phototype_gate_heatmap.png",
              "F4_query_styles_and_workarounds.png", "F5_mechanism_clusters.png", "F6_scorecard_top10.png"]:
        src = BASE / "figures" / f
        if src.exists():
            shutil.copy(src, APP / f)
        else:
            print(f"WARNING missing figure {f}")
    vf = BASE / "data" / "validation_report.json"
    if vf.exists():
        shutil.copy(vf, APP / "validation_report.json")
    else:
        print("WARNING validation_report.json missing")
    pc = BASE / "data" / "pipeline_counts.json"
    if pc.exists():
        shutil.copy(pc, APP / "pipeline_counts.json")

    enums = {
        "photo_type": ["trip_event", "people_social", "food_place", "scenery_pet", "document_utility", "screenshot", "video", "other_unspecified"],
        "retrieval_intent": ["find_specific_photo", "find_set_or_moment", "find_info_inside_photo", "find_by_person", "other"],
        "photo_age": ["recent_lt_6m", "six_to_24m", "over_2y", "unspecified"],
        "cue_type": ["person", "place", "time_when", "event_context", "anchor_relation", "visual_detail", "setting",
                     "activity", "emotion_or_vibe", "purpose_or_reason", "text_in_image", "source", "device_or_app", "other"],
        "cue_certainty": ["high", "medium", "low"],
        "query_style": ["keyword", "natural_language", "date_or_filter", "people_or_face", "map_or_place",
                        "browse_scroll", "ask_photos_chat", "none_stated"],
        "workaround": ["scroll_timeline", "search_other_app", "ask_other_person", "manual_albums_or_favorites",
                       "rename_or_describe", "use_other_service", "switch_to_classic_search", "gave_up", "none_stated"],
        "outcome": ["found", "partly_found", "not_found", "unknown"],
        "stakes": ["low", "medium", "high"],
        "failure_gate": ["expression", "interpretation", "evaluation", "refinement", "persistence", "not_search_related", "unclear"],
        "era": ["pre_ask", "early_access", "wider_rollout"],
        "source": ["play", "appstore", "reddit", "community"],
    }
    (APP / "enums.json").write_text(json.dumps(enums, indent=2))

    total = sum(f.stat().st_size for f in APP.rglob("*") if f.is_file())
    print(f"data/app total size: {total/1e6:.1f} MB")


if __name__ == "__main__":
    main()
