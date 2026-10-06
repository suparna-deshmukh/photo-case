"""
Purpose: D7 - build the human/second-model validation blind set.
         Samples 55 docs from docs_for_llm (seed 42):
         DEV  = 15 docs the model extracted as retrieval episodes
         TEST = 30 episode docs (random across sources) + 10 stage-1-not-relevant docs.
         "Not relevant" for the 10 is interpreted as stage-1 relevant == False.
Inputs : data/docs_for_llm.parquet, data/stage1.parquet, data/stage2_v1.parquet.
Outputs: research/validation_blind.csv  (id, text + 4 EMPTY label columns, shuffled)
         research/validation_key.parquet (id, split, source, model_is_episode, model_gate, model_photo_type, model_outcome, prompt_version)
Usage  : .venv/bin/python code/prepare_validation.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))


def main():
    forl = pd.read_parquet(BASE / "data" / "docs_for_llm.parquet")
    stage1 = pd.read_parquet(BASE / "data" / "stage1.parquet")
    stage2 = pd.read_parquet(BASE / "data" / "stage2_v1.parquet")

    try:
        counts = json.loads((BASE / "data" / "pipeline_counts.json").read_text())
    except Exception:
        counts = {}
    prompt_version = counts.get("stage2_prompt_version", "v1")

    ep_ids = set(stage2.loc[stage2["is_retrieval_episode"] == True, "doc_id"].astype(str))  # noqa: E712
    notrel = stage1[stage1["relevant"] == False]  # noqa: E712

    m = forl.merge(stage1[["doc_id", "relevant"]], on="doc_id", how="left")
    m["doc_id"] = m["doc_id"].astype(str)
    episodes_pool = m[m["doc_id"].isin(ep_ids)].copy()
    notrel_pool = notrel[notrel["doc_id"].isin(set(m["doc_id"]))].copy()

    rng = pd.np.random.default_rng(42) if hasattr(pd, "np") else __import__("numpy").random.default_rng(42)

    # DEV: 15 episode docs, stratified across sources for diversity
    n_dev = min(15, len(episodes_pool))
    dev_idx = _stratified(episodes_pool, n_dev, 42)
    dev = episodes_pool.loc[dev_idx]

    # TEST: 30 more episode docs (not in DEV) + 10 not-relevant
    rest = episodes_pool[~episodes_pool.index.isin(dev.index)]
    n_test_ep = min(30, len(rest))
    test_ep_idx = _stratified(rest, n_test_ep, 42)
    test_ep = rest.loc[test_ep_idx]
    n_test_nr = min(10, len(notrel_pool))
    test_nr = notrel_pool.sample(n=n_test_nr, random_state=42)

    key_rows = []
    for _, r in dev.iterrows():
        key_rows.append({"id": r["doc_id"], "split": "DEV", "source": r["source"], "model_is_episode": True})
    for _, r in test_ep.iterrows():
        key_rows.append({"id": r["doc_id"], "split": "TEST", "source": r["source"], "model_is_episode": True})
    for _, r in test_nr.iterrows():
        key_rows.append({"id": r["doc_id"], "split": "TEST", "source": "n/a", "model_is_episode": False})
    key = pd.DataFrame(key_rows)

    # model labels for the episode docs (from stage2)
    s2 = stage2.copy()
    s2["doc_id"] = s2["doc_id"].astype(str)
    s2m = s2.set_index("doc_id")
    parsed = s2["episode_json"].map(lambda x: _safe_json(x))
    key["model_gate"] = key["id"].map(lambda i: _get(s2m, i, "failure_gate"))
    key["model_photo_type"] = key["id"].map(lambda i: _get(s2m, i, "photo_type"))
    key["model_outcome"] = key["id"].map(lambda i: _get(s2m, i, "outcome"))
    key["prompt_version"] = prompt_version
    key.to_parquet(BASE / "research" / "validation_key.parquet", index=False)

    # blind file: only id + full text + 4 empty columns; shuffled so split invisible
    all_ids = list(dev["doc_id"]) + list(test_ep["doc_id"]) + list(test_nr["doc_id"])
    text_map = dict(zip(m["doc_id"], m["text"]))
    blind = pd.DataFrame({"id": all_ids, "text": [text_map[i] for i in all_ids]})
    blind["human_is_retrieval"] = ""
    blind["human_photo_type"] = ""
    blind["human_failure_gate"] = ""
    blind["human_outcome"] = ""
    blind = blind.sample(frac=1.0, random_state=42).reset_index(drop=True)
    out = BASE / "research" / "validation_blind.csv"
    blind.to_csv(out, index=False)
    print(f"saved {out} ({len(blind)} rows) and research/validation_key.parquet ({len(key)} rows)")
    print(f"DEV={n_dev} TEST={n_test_ep + n_test_nr} (ep={n_test_ep}, notrel={n_test_nr})")


def _stratified(df: pd.DataFrame, n: int, seed: int):
    import numpy as np
    rng = np.random.default_rng(seed)
    sizes = df.groupby("source", dropna=False).size()
    total = sizes.sum()
    alloc = (sizes * n / total).round().astype(int)
    alloc = alloc.clip(lower=0)
    if alloc.sum() > n:
        order = alloc.sort_values(ascending=False).index
        excess = alloc.sum() - n
        for i in order:
            cut = min(excess, alloc[i])
            alloc[i] -= cut
            excess -= cut
            if excess == 0:
                break
    elif alloc.sum() < n:
        shortfall = n - int(alloc.sum())
        order = alloc.sort_values(ascending=False).index
        for i in order:
            room = int(sizes[i]) - int(alloc[i])
            give = min(shortfall, max(0, room))
            alloc[i] += give
            shortfall -= give
            if shortfall == 0:
                break
    pick = []
    for name, idx in df.groupby("source", dropna=False).groups.items():
        a = int(alloc.get(name, 0))
        if a > 0:
            pick.append(rng.choice(np.asarray(list(idx)), size=min(a, len(idx)), replace=False))
    pick = np.concatenate(pick) if pick else np.array([], dtype=object)
    return np.sort(pick)



def _safe_json(x):
    try:
        return json.loads(x)
    except Exception:
        return {}


def _get(s2m, i, col):
    try:
        ep = _safe_json(s2m.loc[i, "episode_json"])
        return ep.get(col)
    except Exception:
        return None


if __name__ == "__main__":
    main()
