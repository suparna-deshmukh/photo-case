"""
M9 (optional) — offline scripted-user benchmark, DIRECTIONAL ONLY.
Not a replacement for real users; labeled as such everywhere.

- up to 100 target images (stratified across events incl. utility/cafe/sunset/event)
- vague fragment per target via one local llm_json call (place_keep ~ Bernoulli(0.6),
  time_keep ~ Bernoulli(0.5), seed 42)
- Classic simulation: fragment as query, rank of target
- Jog simulation: rules-only parse, answer questions truthfully from tags w.p.
  answerability prior, pick this-or-that by CLIP closeness, stop at MAX_ROUNDS
- report: success @1 / @4 rounds (Jog) vs top-5 / top-20 (Classic); bootstrap 95% CIs
  (1000 resamples); breakdown by task type; figures/sim_eval.png
"""
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
LIB = BASE / "library"
FIG = BASE / "figures"

N_TARGETS = 100
SEED = 42
N_BOOT = 1000

FRAG_PROMPT = (
    "Write what a person would vaguely remember about this photo in 1-2 first-person sentences "
    "using ONLY the given tags. Include the place only if place_keep is true; include a rough time "
    "only if time_keep is true; always include at most two visual details; hedge with 'I think' or "
    "'maybe' on one detail. Return JSON: {\"fragment\": string}."
)


def main():
    import llm_helper
    from sentence_transformers import SentenceTransformer
    from jog_engine.retrieval import Retriever
    from jog_engine.cues_rules import parse_rules
    from jog_engine.questions import next_question
    from jog_engine.clusters import moments as moments_fn
    from jog_engine.config import PRIORS, TOP_K, MAX_ROUNDS

    rng = np.random.default_rng(SEED)
    meta = pd.read_parquet(LIB / "meta.parquet").reset_index(drop=True)
    emb = np.load(LIB / "image_emb.npy").astype("float32")
    idx = {i: n for n, i in enumerate(json.loads((LIB / "emb_index.json").read_text()))}
    clip = SentenceTransformer("clip-ViT-B-32")
    ret = Retriever(meta, emb, clip)

    # stratified target selection
    meta["kind"] = "event"
    meta.loc[meta["setting_type"].isin(["document_or_utility"]), "kind"] = "utility"
    meta.loc[meta["setting_type"] == "cafe", "kind"] = "cafe"
    cap = meta["caption"].fillna("").str.lower()
    meta.loc[cap.str.contains("sunset") | cap.str.contains("boat"), "kind"] = "sunset"
    groups = {k: g["img_id"].tolist() for k, g in meta.groupby("kind")}
    picks = []
    for k in ("utility", "cafe", "sunset", "event"):
        want = 20 if k != "event" else 40
        pool = groups.get(k, [])
        picks += list(rng.choice(pool, size=min(want, len(pool)), replace=False))
    picks = list(dict.fromkeys(picks))[:N_TARGETS]
    log(f"targets: {len(picks)} (kinds: {pd.Series(picks).map(lambda i: meta.set_index('img_id').loc[i, 'kind']).value_counts().to_dict()})")

    # fragments
    meta_ix = meta.set_index("img_id")
    fragments = {}
    for img_id in picks:
        row = meta_ix.loc[img_id]
        place_keep = bool(rng.random() < 0.6)
        time_keep = bool(rng.random() < 0.5)
        tags = {
            "caption": row.get("caption"), "setting": row.get("setting_type"),
            "time_of_day": row.get("time_of_day"), "indoor_outdoor": row.get("indoor_outdoor"),
            "people": row.get("people_count_bucket"), "objects": row.get("objects"),
            "place_name": row.get("place_name"),
        }
        res = llm_helper.llm_json(
            FRAG_PROMPT,
            f"Tags: {json.dumps(tags, default=str)}\nplace_keep={place_keep}\ntime_keep={time_keep}",
            profile="local")
        if "_error" in res:
            fragments[img_id] = f"I remember a photo of {row.get('caption', 'something')}"
        else:
            fragments[img_id] = res.get("fragment", "")
        time.sleep(0.05)
    (LIB / "sim_fragments.json").write_text(json.dumps(fragments, indent=1))

    # simulations
    rows = []
    for n, img_id in enumerate(picks, 1):
        frag = fragments[img_id]
        # Classic
        v = clip.encode([frag], convert_to_numpy=True, normalize_embeddings=True)[0]
        sims = emb @ v.astype("float32")
        order = np.argsort(-sims)
        classic_rank = int(np.where(order == idx[img_id])[0][0]) + 1
        # Jog (rules-only)
        parsed = parse_rules(frag)
        qv = ret.encode_visual_query(parsed.visual_query)
        scored = ret.score(qv, parsed.cues, parsed.time_window)
        jog_rank_r1 = int(scored.index[scored["img_id"] == img_id][0]) + 1 if img_id in set(scored["img_id"]) else len(scored)
        in_top5_moments_r1 = any(img_id in m["img_ids"][:5] for m in moments_fn(scored.head(TOP_K), meta))
        # rounds: answer truthfully w.p. prior
        state = {"answered": {}, "dont_know": {}, "asked": set(), "round": 0}
        cur = scored
        found_round = None
        for r in range(1, MAX_ROUNDS + 1):
            q = next_question(cur, state, moments_fn(cur.head(TOP_K), meta))
            if q is None:
                break
            attr = q["attribute"]
            row = meta_ix.loc[img_id]
            truth = str(row.get({"indoor_outdoor": "indoor_outdoor", "time_of_day": "time_of_day",
                                 "place_name": "place_name", "setting_type": "setting_type",
                                 "season_hint": "season_hint", "people_count_bucket": "people_count_bucket",
                                 "has_text": "has_text", "dominant_color": "dominant_colors"}[attr], ""))
            if rng.random() < PRIORS.get(attr, 0.5) and truth:
                state["answered"][attr] = truth
            else:
                state["dont_know"][attr] = state["dont_know"].get(attr, 0) + 1
            state["asked"].add(attr)
            state["round"] = r
            cue_type = {"indoor_outdoor": "indoor_outdoor", "time_of_day": "time_of_day",
                        "place_name": "place", "setting_type": "setting_type",
                        "season_hint": "season"}.get(attr, "other")
            cues = [c for c in parsed.cues if c.type != cue_type]
            if state.get("answered", {}).get(attr):
                from jog_engine.cues import Cue
                cues.append(Cue(type=cue_type, value=state["answered"][attr], certainty="sure"))
            cur = ret.score(qv, cues, parsed.time_window)
            r_rank = int(cur.index[cur["img_id"] == img_id][0]) + 1 if img_id in set(cur["img_id"]) else len(cur)
            if r_rank <= 1:
                found_round = r
                break
        rows.append({
            "img_id": img_id, "kind": meta_ix.loc[img_id, "kind"],
            "classic_rank": classic_rank, "jog_rank_r1": jog_rank_r1,
            "jog_top5_moments_r1": int(in_top5_moments_r1),
            "jog_found_round": found_round if found_round else (1 if jog_rank_r1 == 1 else MAX_ROUNDS),
        })
        if n % 20 == 0:
            log(f"sim {n}/{len(picks)}")
    df = pd.DataFrame(rows)
    (BASE / "data" / "sim_eval_raw.csv").write_text(df.to_csv(index=False))

    # metrics
    def boot_ci(x, nboot=N_BOOT):
        x = np.asarray(x, dtype="float64")
        res = np.array([np.mean(rng.choice(x, size=len(x), replace=True)) for _ in range(nboot)])
        return float(np.percentile(res, 2.5)), float(np.percentile(res, 97.5))

    def succ_rate(x):
        lo, hi = boot_ci(x)
        return f"{x.mean()*100:.0f}% [{lo*100:.0f}-{hi*100:.0f}]"

    metrics = {}
    metrics["classic_top5"] = succ_rate((df["classic_rank"] <= 5).astype(int))
    metrics["classic_top20"] = succ_rate((df["classic_rank"] <= 20).astype(int))
    metrics["jog_r1_top1"] = succ_rate((df["jog_rank_r1"] <= 1).astype(int))
    metrics["jog_r1_top5"] = succ_rate((df["jog_rank_r1"] <= 5).astype(int))
    metrics["jog_r4_top1"] = succ_rate((df["jog_found_round"] <= MAX_ROUNDS).astype(int))
    log("METRICS: " + json.dumps(metrics, indent=1))
    by_kind = df.groupby("kind").agg(
        n=("img_id", "count"),
        classic_top5=("classic_rank", lambda s: (s <= 5).mean()),
        jog_r1_top5=("jog_rank_r1", lambda s: (s <= 5).mean()),
        jog_r4_top1=("jog_found_round", lambda s: (s <= MAX_ROUNDS).mean()))
    log("BY_KIND:\n" + by_kind.round(2).to_string())

    # figure
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    labels = ["Classic\n≤5", "Classic\n≤20", "Jog r1\n≤1", "Jog r1\n≤5", "Jog ≤4 r\n≤1"]
    vals = [
        (df["classic_rank"] <= 5).mean(), (df["classic_rank"] <= 20).mean(),
        (df["jog_rank_r1"] <= 1).mean(), (df["jog_rank_r1"] <= 5).mean(),
        (df["jog_found_round"] <= MAX_ROUNDS).mean(),
    ]
    errs = []
    for x in [(df["classic_rank"] <= 5).astype(int), (df["classic_rank"] <= 20).astype(int),
              (df["jog_rank_r1"] <= 1).astype(int), (df["jog_rank_r1"] <= 5).astype(int),
              (df["jog_found_round"] <= MAX_ROUNDS).astype(int)]:
        lo, hi = boot_ci(x)
        errs.append([x.mean() - lo, hi - x.mean()])
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    bars = ax.bar(labels, vals, color="#4f46e5", width=0.55)
    ax.errorbar(range(len(vals)), vals, yerr=np.array(errs).T, fmt="none", color="#1e1b4b", capsize=4)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v*100:.0f}%",
                ha="center", va="bottom", fontsize=14)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("success rate", fontsize=14)
    ax.set_title(f"Offline scripted-user simulation (n={len(df)}) — directional only", fontsize=14)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "sim_eval.png")
    log("wrote figures/sim_eval.png")
    log("DONE build_sim_eval")


def log(msg):
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {msg}", flush=True)


if __name__ == "__main__":
    main()
