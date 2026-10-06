"""
Purpose: D8 - analyze data/episodes_full.parquet: tables T1-T7, figures F1-F6,
         6 strongest findings with H1-H5 hypothesis verdicts.
         Every number computed from data; n shown everywhere; Okabe-Ito palette;
         gate colors per locked context.
Inputs : data/episodes_full.parquet, data/pipeline_counts.json,
         code/prompts + code/llm_helper.py (local profile, T6 cluster naming only).
Outputs: data/tables/T1..T7 CSVs; figures/F1..F6 PNGs;
         data/pipeline_counts.json key n_scored_cells; printed findings.
Usage  : .venv/bin/python code/analyze.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
from pipeline_counts import update_counts  # noqa: E402

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.stats.proportion import proportion_confint

PALETTE = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "vermillion": "#D55E00",
           "pink": "#CC79A7", "sky": "#56B4E9", "yellow": "#F0E442", "black": "#000000", "grey": "#999999"}
GATE_COLOR = {"expression": PALETTE["blue"], "interpretation": PALETTE["orange"], "evaluation": PALETTE["green"],
              "refinement": PALETTE["vermillion"], "persistence": PALETTE["pink"],
              "not_search_related": PALETTE["grey"], "unclear": PALETTE["sky"]}
GATES = ["expression", "interpretation", "evaluation", "refinement", "persistence"]
GATE_LABEL = {"expression": "expression\n(can't form query)", "interpretation": "interpretation\n(system misreads clues)",
              "evaluation": "evaluation\ncan't recognize/compare", "refinement": "refinement\nno way to adjust",
              "persistence": "persistence\ngave up", "not_search_related": "not_search_related", "unclear": "unclear"}
CUE_TYPES = ["person", "place", "time_when", "event_context", "anchor_relation", "visual_detail", "setting",
             "activity", "emotion_or_vibe", "purpose_or_reason", "text_in_image", "source", "device_or_app", "other"]
PHOTO_TYPES = ["trip_event", "people_social", "food_place", "scenery_pet", "document_utility", "screenshot", "video", "other_unspecified"]
ERAS = ["pre_ask", "early_access", "wider_rollout"]
FIG = dict(figsize=(10, 5.625), dpi=200)
plt.rcParams.update({"font.size": 16, "axes.titlesize": 18})

T6 = BASE / "data" / "tables"
FIGDIR = BASE / "figures"
T6.mkdir(parents=True, exist_ok=True)
FIGDIR.mkdir(parents=True, exist_ok=True)


def wilson(k, n, alpha=0.05):
    if n == 0:
        return (0.0, 0.0)
    lo, hi = proportion_confint(k, n, alpha=alpha, method="wilson")
    return (float(lo), float(hi))


def share_ci(counts: pd.Series):
    n = int(counts.sum())
    out = {}
    for k_, v_ in counts.items():
        lo, hi = wilson(int(v_), n)
        out[k_] = {"n": int(v_), "share_pct": round(100 * v_ / n, 1) if n else 0.0,
                   "ci_lo": round(100 * lo, 1), "ci_hi": round(100 * hi, 1)}
    return out, n


def main():
    ep = pd.read_parquet(BASE / "data" / "episodes_full.parquet")
    ep = ep[ep["failure_gate"].notna()].copy()
    n_ep = len(ep)
    print(f"episodes with a failure_gate: {n_ep}")
    scored = ep[~ep["failure_gate"].isin(["not_search_related", "unclear"])].copy()
    n_scored = len(scored)
    print(f"scored gates (excl. not_search_related/unclear): {n_scored}")
    findings = {}

    # ---------------- T1 gate distribution ----------------
    t1_rows = []
    for scope, sub in [("overall", ep), ("scored", scored)]:
        c = sub["failure_gate"].value_counts()
        stats, n = share_ci(c)
        for g in GATES + ["not_search_related", "unclear"]:
            s = stats.get(g, {"n": 0, "share_pct": 0.0, "ci_lo": 0.0, "ci_hi": 0.0})
            t1_rows.append({"scope": scope, "gate": g, **s, "denom_n": n})
    for era in ERAS:
        sub = scored[scored["era"] == era]
        c = sub["failure_gate"].value_counts()
        stats, n = share_ci(c)
        for g in GATES:
            s = stats.get(g, {"n": 0, "share_pct": 0.0, "ci_lo": 0.0, "ci_hi": 0.0})
            t1_rows.append({"scope": f"era_{era}", "gate": g, **s, "denom_n": n})
    for src in sorted(ep["source"].dropna().unique()):
        sub = scored[scored["source"] == src]
        c = sub["failure_gate"].value_counts()
        stats, n = share_ci(c)
        for g in GATES:
            s = stats.get(g, {"n": 0, "share_pct": 0.0, "ci_lo": 0.0, "ci_hi": 0.0})
            t1_rows.append({"scope": f"source_{src}", "gate": g, **s, "denom_n": n})
    t1 = pd.DataFrame(t1_rows)
    t1.to_csv(T6 / "T1_gate_distribution.csv", index=False)
    print("T1 saved")

    # ---------------- T2 cue matrix ----------------
    def cues_of(s, which):
        try:
            lst = json.loads(s) if s else []
            return [c["type"] if isinstance(c, dict) else c for c in lst]
        except Exception:
            return []

    scored["rem_cues"] = scored["remembered_cues"].map(lambda s: cues_of(s, "rem"))
    scored["miss_cues"] = scored["missing_cue_types"].map(lambda s: cues_of(s, "miss"))
    t2_rows = []
    for ct in CUE_TYPES:
        n_rem = int(scored["rem_cues"].map(lambda L: ct in L).sum())
        n_miss = int(scored["miss_cues"].map(lambda L: ct in L).sum())
        row = {"cue_type": ct, "n_remembered": n_rem, "pct_remembered": round(100 * n_rem / n_scored, 1),
               "n_missing": n_miss, "pct_missing": round(100 * n_miss / n_scored, 1),
               "ratio_missing_over_remembered": round(n_miss / n_rem, 2) if n_rem else None}
        t2_rows.append(row)
    t2 = pd.DataFrame(t2_rows)
    t2.to_csv(T6 / "T2_cue_matrix.csv", index=False)
    # certainty by cue_type + photo_type split (extra sheets appended as extra columns rows)
    cert = {"high": 0, "medium": 0, "low": 0}
    cert_by_type = {ct: {"high": 0, "medium": 0, "low": 0} for ct in CUE_TYPES}
    for s in scored["remembered_cues"]:
        try:
            for c in json.loads(s) if s else []:
                if isinstance(c, dict):
                    cert[c["certainty"]] = cert.get(c["certainty"], 0) + 1
                    cert_by_type[c["type"]][c["certainty"]] = cert_by_type[c["type"]].get(c["certainty"], 0) + 1
        except Exception:
            pass
    t2["cert_share_of_all_cues"] = ""
    t2.to_csv(T6 / "T2_cue_matrix.csv", index=False)
    pd.DataFrame([{"cue_type": k, "high": v["high"], "medium": v["medium"], "low": v["low"]} for k, v in cert_by_type.items()]).to_csv(T6 / "T2_cue_certainty.csv", index=False)
    split = {}
    for pt in PHOTO_TYPES:
        sub = scored[scored["photo_type"] == pt]
        n = len(sub)
        if n == 0:
            continue
        split[pt] = {ct: round(100 * sub["rem_cues"].map(lambda L: ct in L).sum() / n, 1) for ct in CUE_TYPES}
    pd.DataFrame(split).T.to_csv(T6 / "T2_cue_by_phototype.csv")
    print("T2 saved")

    # ---------------- T3 phototype x gate ----------------
    t3 = pd.crosstab(scored["photo_type"], scored["failure_gate"], margins=False)
    t3 = t3.reindex(index=[p for p in PHOTO_TYPES if p in t3.index], columns=[g for g in GATES if g in t3.columns], fill_value=0)
    t3.to_csv(T6 / "T3_phototype_by_gate.csv")
    t3_pct = t3.div(t3.sum(axis=1), axis=0) * 100
    t3_pct.round(1).to_csv(T6 / "T3_phototype_by_gate_pct.csv")
    print("T3 saved")

    # ---------------- T4 query style ----------------
    t4_rows = []
    c = ep["query_style"].fillna("none_stated").value_counts()
    stats, n = share_ci(c)
    for q in ["keyword", "natural_language", "date_or_filter", "people_or_face", "map_or_place", "browse_scroll", "ask_photos_chat", "none_stated"]:
        s = stats.get(q, {"n": 0, "share_pct": 0.0, "ci_lo": 0.0, "ci_hi": 0.0})
        t4_rows.append({"scope": "overall", "query_style": q, **s, "denom_n": n})
    for era in ERAS:
        sub = ep[ep["era"] == era]
        c = sub["query_style"].fillna("none_stated").value_counts()
        stats, n = share_ci(c)
        for q in ["keyword", "natural_language", "date_or_filter", "people_or_face", "map_or_place", "browse_scroll", "ask_photos_chat", "none_stated"]:
            s = stats.get(q, {"n": 0, "share_pct": 0.0, "ci_lo": 0.0, "ci_hi": 0.0})
            t4_rows.append({"scope": f"era_{era}", "query_style": q, **s, "denom_n": n})
    pd.DataFrame(t4_rows).to_csv(T6 / "T4_query_style.csv", index=False)
    print("T4 saved")

    # ---------------- T5 workarounds ----------------
    t5_rows = []
    c = ep["workaround"].fillna("none_stated").value_counts()
    stats, n = share_ci(c)
    for w in ["scroll_timeline", "search_other_app", "ask_other_person", "manual_albums_or_favorites",
              "rename_or_describe", "use_other_service", "switch_to_classic_search", "gave_up", "none_stated"]:
        s = stats.get(w, {"n": 0, "share_pct": 0.0, "ci_lo": 0.0, "ci_hi": 0.0})
        t5_rows.append({"scope": "overall", "workaround": w, **s, "denom_n": n})
    for g in GATES:
        sub = ep[ep["failure_gate"] == g]
        c = sub["workaround"].fillna("none_stated").value_counts()
        stats, n = share_ci(c)
        for w in ["scroll_timeline", "search_other_app", "ask_other_person", "manual_albums_or_favorites",
                  "rename_or_describe", "use_other_service", "switch_to_classic_search", "gave_up", "none_stated"]:
            s = stats.get(w, {"n": 0, "share_pct": 0.0, "ci_lo": 0.0, "ci_hi": 0.0})
            t5_rows.append({"scope": f"gate_{g}", "workaround": w, **s, "denom_n": n})
    pd.DataFrame(t5_rows).to_csv(T6 / "T5_workarounds.csv", index=False)
    print("T5 saved")

    part2(scored, ep, n_scored, t1, t2, t3, t3_pct, findings)
    update_counts(n_scored_cells=int(findings.get("n_scored_cells", 0)))
    print("D8 done")



# ============================== PART 2 ==============================
def part2(scored, ep, n_scored, t1, t2, t3, t3_pct, findings):
    n_ep = len(ep)
    # ---------------- T6 failure mechanism clusters ----------------
    mechs = scored[scored["failure_mechanism"].notna()].copy()
    mechs["mech_norm"] = mechs["failure_mechanism"].str.lower().str.strip()
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    X = model.encode(mechs["mech_norm"].tolist(), normalize_embeddings=True, show_progress_bar=False)
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    best = (None, -1)
    sil = {}
    for k in range(6, 15):
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
        s = silhouette_score(X, km.labels_)
        sil[k] = round(float(s), 3)
        if s > best[1]:
            best = (k, s)
    k = best[0]
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    mechs["cluster"] = km.labels_
    print(f"T6: silhouette by k = {sil}; chosen k={k} (sil={best[1]:.3f})")

    from llm_helper import llm_json
    import pydantic
    class ClusterName(pydantic.BaseModel):
        label: str
        definition: str
    t6_rows = []
    for cid in sorted(mechs["cluster"].unique()):
        sub = mechs[mechs["cluster"] == cid]
        examples = sub["failure_mechanism"].head(12).tolist()
        res = llm_json(
            "You name clusters of user-failure mechanisms. Given example mechanism descriptions (each <=15 words) from one cluster, return JSON {\"label\": \"<<=6 words>\", \"definition\": \"<<=20 words>\"} that captures the common cause.",
            "Example mechanisms:\n" + "\n".join(f"- {e}" for e in examples),
            schema_model=ClusterName)
        label = res.get("label", f"cluster_{cid}") if "_error" not in res else f"cluster_{cid}"
        definition = res.get("definition", "") if "_error" not in res else ""
        gm = sub["failure_gate"].value_counts()
        gate_mix = ", ".join(f"{g}:{int(c)}" for g, c in gm.items())
        ex3 = sub.head(3)
        t6_rows.append({
            "cluster": cid, "cluster_label": label, "definition": definition,
            "size": len(sub), "share_pct": round(100 * len(sub) / len(mechs), 1),
            "gate_mix": gate_mix,
            "example_doc_ids": ";".join(ex3["doc_id"].astype(str)),
            "example_quotes": " ||| ".join(str(q)[:120] for q in ex3["evidence_quote"].fillna("")),
        })
    t6 = pd.DataFrame(t6_rows).sort_values("size", ascending=False)
    t6.to_csv(T6 / "T6_mechanisms.csv", index=False)
    cmap = mechs[["doc_id", "cluster"]].copy()
    cmap["cluster_label"] = cmap["cluster"].map({int(r["cluster"]): r["cluster_label"] for _, r in t6.iterrows()})
    cmap[["doc_id", "cluster_label"]].to_csv(T6 / "T6_cluster_map.csv", index=False)
    print("T6 saved (+cluster map)")

    # ---------------- T7 opportunity scorecard ----------------
    LEV = {"expression": 0.8, "interpretation": 0.6, "evaluation": 0.8, "refinement": 1.0, "persistence": 0.5}
    STAKES_S = {"low": 0.33, "medium": 0.67, "high": 1.0}
    OUTCOME_S = {"found": 0.0, "partly_found": 0.5, "not_found": 1.0, "unknown": 0.5}
    cells = []
    for pt in PHOTO_TYPES:
        for g in GATES:
            cell = scored[(scored["photo_type"] == pt) & (scored["failure_gate"] == g)]
            n_cell = len(cell)
            if n_cell < 8:
                continue
            stakes_s = cell["stakes"].map(STAKES_S).fillna(0.5).mean()
            outcome_s = cell["outcome"].fillna("unknown").map(OUTCOME_S).mean()
            rating_s = cell["rating"].map(lambda r: (5 - r) / 4 if pd.notna(r) and r is not None else 0.5).mean()
            sev = 0.4 * stakes_s + 0.4 * outcome_s + 0.2 * rating_s
            wide = cell[cell["era"] == "wider_rollout"]
            fallback = False
            if len(wide) < 10:
                wide = cell[cell["era"].isin(["early_access", "wider_rollout"])]
                fallback = True
            gap = float((wide["outcome"].fillna("unknown") != "found").mean()) if len(wide) else 0.5
            gap_flag = bool(fallback or len(wide) < 10)
            cells.append({"photo_type": pt, "failure_gate": g, "n_cell": n_cell,
                          "sev": round(float(sev), 3), "gap": round(gap, 3), "gap_flag": gap_flag,
                          "lev": LEV[g]})
    t7 = pd.DataFrame(cells)
    if len(t7):
        max_freq = t7["n_cell"].max()
        tot = t7["n_cell"].sum()
        t7["freq"] = t7["n_cell"] / tot
        # score = 100*(0.35*freq/max_freq + 0.25*sev + 0.20*gap + 0.20*lev); max_freq = max cell share
        mf = max_freq / tot
        t7["score"] = 100 * (0.35 * t7["freq"] / mf + 0.25 * t7["sev"] + 0.20 * t7["gap"] + 0.20 * t7["lev"])
        # lev-free ranking (weights renormalized over freq/sev/gap)
        w = np.array([0.35, 0.25, 0.20])
        w = w / w.sum()
        t7["score_no_lev"] = 100 * (w[0] * t7["freq"] / mf + w[1] * t7["sev"] + w[2] * t7["gap"])
        # sensitivity: 1000 Dirichlet draws over [freq, sev, gap, lev]
        rng = np.random.default_rng(42)
        W = rng.dirichlet(20 * np.array([0.35, 0.25, 0.20, 0.20]), size=1000)
        base = np.column_stack([t7["freq"] / mf, t7["sev"], t7["gap"], t7["lev"]])
        S = base @ W.T  # (n_cells, 1000)
        order = np.argsort(-S, axis=0)
        rank = np.empty_like(order)
        for j in range(order.shape[1]):
            rank[order[:, j], j] = np.arange(order.shape[0])
        t7["p_top3"] = (rank < 3).mean(axis=1).round(3)
        t7["rank"] = t7["score"].rank(ascending=False).astype(int)
        t7["rank_no_lev"] = t7["score_no_lev"].rank(ascending=False).astype(int)
    t7 = t7.round(4)
    t7.to_csv(T6 / "T7_scorecard.csv", index=False)
    print(f"T7 saved ({len(t7)} scored cells, n>=8)")
    findings["n_scored_cells"] = len(t7)

    # robustness: gate tables restricted to gate_consistent episodes
    if "gate_consistent" in scored.columns and scored["gate_consistent"].notna().any():
        sc = scored[scored["gate_consistent"] == True]  # noqa: E712
        c = sc["failure_gate"].value_counts()
        stats, n = share_ci(c)
        rob = pd.DataFrame([{"gate": g, **stats.get(g, {"n": 0, "share_pct": 0.0, "ci_lo": 0.0, "ci_hi": 0.0}), "denom_n": n}
                            for g in GATES])
        rob.to_csv(T6 / "T1_robust_consistent_only.csv", index=False)
        print("T1 robustness (gate_consistent only) saved")

    # ---------------- figures ----------------
    fig1(t1, n_ep, n_scored)
    fig2(t2)
    fig3(t3, t3_pct, n_scored)
    fig4(t1, scored)
    fig5(t6)
    fig7 = t7 if len(t7) else None
    fig6(fig7)

    # ---------------- findings + hypothesis verdicts ----------------
    overall = t1[(t1["scope"] == "scored")]
    ov = {r["gate"]: r for _, r in overall.iterrows()}
    top2 = sorted(GATES, key=lambda g: -ov[g]["share_pct"])[:2]
    top2_share = sum(ov[g]["share_pct"] for g in top2)
    interp = ov["interpretation"]["share_pct"]
    findings["H1"] = (f"Top-2 gates {top2[0]}+{top2[1]} = {top2_share:.1f}% of {n_scored} scored episodes; "
                      f"interpretation = {interp:.1f}%. " +
                      ("H1 SUPPORTED (top gates are refinement/evaluation or evaluation/refinement)."
                       if set(top2) <= {"refinement", "evaluation"} else
                       "H1 NOT SUPPORTED as stated (top gates differ)."))
    rem_time = t2[t2["cue_type"] == "time_when"]["pct_remembered"].iloc[0]
    mis_time = t2[t2["cue_type"] == "time_when"]["pct_missing"].iloc[0]
    ctx_cues = ["event_context", "person", "place", "purpose_or_reason", "anchor_relation"]
    rem_ctx = t2[t2["cue_type"].isin(ctx_cues)]["pct_remembered"].mean()
    findings["H2"] = (f"time_when remembered in {rem_time:.1f}% but missing/forgotten in {mis_time:.1f}% of {n_scored} episodes; "
                      f"context cues (event/person/place/purpose/anchor) remembered on average in {rem_ctx:.1f}%. "
                      + ("H2 SUPPORTED." if mis_time > rem_time else "H2 MIXED/NOT SUPPORTED."))
    t4 = pd.read_csv(T6 / "T4_query_style.csv")
    ov4 = t4[t4["scope"] == "overall"].set_index("query_style")
    kw_share = ov4.loc["keyword", "share_pct"] if "keyword" in ov4.index else 0
    t5 = pd.read_csv(T6 / "T5_workarounds.csv")
    ov5 = t5[t5["scope"] == "overall"].set_index("workaround")
    scroll_share = ov5.loc["scroll_timeline", "share_pct"] if "scroll_timeline" in ov5.index else 0
    findings["H3"] = (f"keyword = {kw_share:.1f}% of stated query styles; scroll_timeline workaround = {scroll_share:.1f}% of {n_ep} episodes. "
                      + ("H3 directionally supported (keyword reliance + timeline-scroll fallback)." if (kw_share > 30 and scroll_share > 10) else "H3 NOT SUPPORTED quantitatively."))
    t2c = pd.read_csv(T6 / "T2_cue_by_phototype.csv", index_col=0)
    doc = t2c.loc["document_utility"] if "document_utility" in t2c.index else None
    trip = t2c.loc["trip_event"] if "trip_event" in t2c.index else None
    if doc is None or trip is None:
        findings["H4"] = "H4 NOT EVALUABLE: document_utility or trip_event absent from cue-by-phototype table."
    else:
        findings["H4"] = (f"document_utility: purpose_or_reason={doc['purpose_or_reason']:.1f}%, text_in_image={doc['text_in_image']:.1f}% remembered; "
                          f"trip_event: event_context={trip['event_context']:.1f}%, anchor_relation={trip['anchor_relation']:.1f}% remembered (of {n_scored}). "
                          + ("H4 SUPPORTED." if (doc["purpose_or_reason"] > trip["purpose_or_reason"] and doc["text_in_image"] > trip["text_in_image"]) else "H4 MIXED/NOT SUPPORTED."))
    findings["H5"] = ("H5 (success drop after 2 failed queries) CANNOT BE TESTED from cross-sectional feedback data: "
                      "single-attempt reviews/posts do not expose sequential query counts. Flag as not testable with this data.")

    for k_ in ["H1", "H2", "H3", "H4", "H5"]:
        print(f"FINDING {k_}: {findings[k_]}")
    (BASE / "data" / "tables" / "findings.json").write_text(json.dumps(findings, indent=2))
    print("findings saved to data/tables/findings.json")


def fig1(t1, n_ep, n_scored):
    ov = t1[t1["scope"] == "scored"].set_index("gate")
    fig, axes = plt.subplots(1, 2, figsize=(16, 5.625), dpi=200)
    ax = axes[0]
    gates = [g for g in GATES if g in ov.index]
    vals = [ov.loc[g, "share_pct"] for g in gates]
    los = [ov.loc[g, "share_pct"] - ov.loc[g, "ci_lo"] for g in gates]
    his = [ov.loc[g, "ci_hi"] - ov.loc[g, "share_pct"] for g in gates]
    y = np.arange(len(gates))
    ax.barh(y, vals, xerr=[los, his], color=[GATE_COLOR[g] for g in gates], ecolor="#333333", capsize=3, height=0.6)
    ax.set_yticks(y, [GATE_LABEL[g] for g in gates])
    for i, (g, v) in enumerate(zip(gates, vals)):
        ax.text(v + 0.5, i, f"{v:.1f}% (n={int(ov.loc[g,'n'])})", va="center", fontsize=14)
    ax.set_xlim(0, max(vals) * 1.35)
    ax.set_title(f"Failure gates among {n_scored} scored episodes (n total={n_ep})", fontsize=18)
    ax.set_xlabel("share of scored episodes (%)")
    ax.invert_yaxis()
    ax = axes[1]
    eras = [e for e in ERAS if f"era_{e}" in t1["scope"].values]
    width = 0.26
    for j, e in enumerate(eras):
        sub = t1[(t1["scope"] == f"era_{e}")].set_index("gate")
        gates_e = [g for g in GATES if g in sub.index]
        ax.barh(np.arange(len(gates_e)) + (j - 1) * width, [sub.loc[g, "share_pct"] for g in gates_e],
                height=width, color=[GATE_COLOR[g] for g in gates_e], label=e)
        for i, g in enumerate(gates_e):
            ax.text(sub.loc[g, "share_pct"] + 0.5, i + (j - 1) * width, f"{sub.loc[g,'share_pct']:.0f}%", va="center", fontsize=14)
    ax.set_yticks(np.arange(len(GATES)), [GATE_LABEL[g] for g in GATES])
    ax.set_title("By era (scored episodes per era; n per era in T1)", fontsize=18)
    ax.set_xlabel("share (%)")
    ax.legend(fontsize=14)
    fig.tight_layout()
    fig.savefig(FIGDIR / "F1_gate_distribution.png", dpi=200)
    plt.close(fig)
    print("F1 saved")


def fig2(t2):
    t2s = t2.sort_values("pct_remembered", ascending=False).iloc[:12]
    fig, ax = plt.subplots(figsize=(10, 5.625), dpi=200)
    y = np.arange(len(t2s))
    ax.barh(y + 0.19, t2s["pct_remembered"], height=0.38, color=PALETTE["blue"], label="remembered (%)")
    ax.barh(y - 0.19, -t2s["pct_missing"], height=0.38, color=PALETTE["vermillion"], label="forgotten/missing (%)")
    ax.set_yticks(y, t2s["cue_type"])
    for i, (_, r) in enumerate(t2s.iterrows()):
        ax.text(r["pct_remembered"] + 0.5, i + 0.19, f"{r['pct_remembered']:.0f}%", va="center", fontsize=14)
        ax.text(-r["pct_missing"] - 0.5, i - 0.19, f"{r['pct_missing']:.0f}%", va="center", ha="right", fontsize=14)
    ax.axvline(0, color="#333333", lw=1)
    ax.set_xlabel("% of episodes (n in T2)")
    ax.set_title("Cue types remembered vs forgotten", fontsize=18)
    ax.legend(fontsize=14)
    fig.tight_layout()
    fig.savefig(FIGDIR / "F2_remembered_vs_missing.png", dpi=200)
    plt.close(fig)
    print("F2 saved")


def fig3(t3, t3_pct, n_scored):
    fig, ax = plt.subplots(figsize=(10, 5.625), dpi=200)
    data = t3.to_numpy()
    im = ax.imshow(data, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(t3.columns)), [GATE_LABEL[g].split("\n")[0] for g in t3.columns], rotation=30, ha="right")
    ax.set_yticks(range(len(t3.index)), t3.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{int(data[i, j])}\n({t3_pct.iloc[i, j]:.0f}%)", ha="center", va="center", fontsize=14,
                    color="white" if data[i, j] > data.max() * 0.55 else "black")
    ax.set_title(f"Photo type x failure gate, n={n_scored} (count; row %)", fontsize=18)
    fig.colorbar(im, ax=ax, label="count")
    fig.tight_layout()
    fig.savefig(FIGDIR / "F3_phototype_gate_heatmap.png", dpi=200)
    plt.close(fig)
    print("F3 saved")


def fig4(t1, scored):
    t4 = pd.read_csv(T6 / "T4_query_style.csv")
    t5 = pd.read_csv(T6 / "T5_workarounds.csv")
    o4 = t4[t4["scope"] == "overall"].sort_values("share_pct", ascending=False)
    o5 = t5[t5["scope"] == "overall"].sort_values("share_pct", ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(16, 5.625), dpi=200)
    ax = axes[0]
    x = np.arange(len(o4))
    ax.bar(x, o4["share_pct"], color=PALETTE["blue"])
    ax.set_xticks(x, o4["query_style"], rotation=30, ha="right")
    for i, (_, r) in enumerate(o4.iterrows()):
        ax.text(i, r["share_pct"] + 0.5, f"{r['share_pct']:.0f}%\nn={int(r['n'])}", ha="center", fontsize=14)
    ax.set_title(f"Query style, n={int(o4['denom_n'].iloc[0])}", fontsize=18)
    ax.set_ylabel("share (%)")
    ax = axes[1]
    x = np.arange(len(o5))
    ax.bar(x, o5["share_pct"], color=PALETTE["orange"])
    ax.set_xticks(x, o5["workaround"], rotation=30, ha="right")
    for i, (_, r) in enumerate(o5.iterrows()):
        ax.text(i, r["share_pct"] + 0.5, f"{r['share_pct']:.0f}%\nn={int(r['n'])}", ha="center", fontsize=14)
    ax.set_title(f"Workarounds, n={int(o5['denom_n'].iloc[0])}", fontsize=18)
    ax.set_ylabel("share (%)")
    fig.tight_layout()
    fig.savefig(FIGDIR / "F4_query_styles_and_workarounds.png", dpi=200)
    plt.close(fig)
    print("F4 saved")


def fig5(t6):
    t6s = t6.sort_values("size", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5.625), dpi=200)
    y = np.arange(len(t6s))
    colors = [PALETTE["blue"], PALETTE["orange"], PALETTE["green"], PALETTE["vermillion"], PALETTE["pink"],
              PALETTE["sky"], PALETTE["yellow"], PALETTE["black"], PALETTE["grey"], PALETTE["blue"], PALETTE["orange"], PALETTE["green"]]
    ax.barh(y, t6s["size"], color=colors[:len(t6s)])
    ax.set_yticks(y, [f"{r.cluster_label}\n({r.share_pct:.0f}%)" for _, r in t6s.iterrows()])
    for i, (_, r) in enumerate(t6s.iterrows()):
        ax.text(r["size"] + max(t6s["size"]) * 0.01, i, f"n={int(r['size'])}", va="center", fontsize=14)
    ax.invert_yaxis()
    ax.set_xlabel("episodes (of those with a mechanism)")
    ax.set_title(f"Failure-mechanism clusters (k chosen by silhouette, n={int(t6s['size'].sum())})", fontsize=18)
    fig.tight_layout()
    fig.savefig(FIGDIR / "F5_mechanism_clusters.png", dpi=200)
    plt.close(fig)
    print("F5 saved")


def fig6(t7):
    if t7 is None or not len(t7):
        return
    t7s = t7.sort_values("score", ascending=False).head(10)
    fig, ax = plt.subplots(figsize=(10, 5.625), dpi=200)
    y = np.arange(len(t7s))
    ax.barh(y, t7s["score"], color=[GATE_COLOR[g] for g in t7s["failure_gate"]])
    labels = [f"{p} x {g}" for p, g in zip(t7s["photo_type"], t7s["failure_gate"])]
    ax.set_yticks(y, labels)
    for i, (_, r) in enumerate(t7s.iterrows()):
        ax.text(r["score"] + 0.5, i, f"score={r['score']:.0f}  P(top3)={r['p_top3']:.2f}  n={int(r['n_cell'])}", va="center", fontsize=14)
    ax.invert_yaxis()
    ax.set_xlim(0, t7s["score"].max() * 1.45)
    ax.set_xlabel("opportunity score (0-100)")
    ax.set_title(f"Top-10 opportunity cells (n={len(t7)} scored cells, cell n>=8)", fontsize=18)
    fig.tight_layout()
    fig.savefig(FIGDIR / "F6_scorecard_top10.png", dpi=200)
    plt.close(fig)
    print("F6 saved")


if __name__ == "__main__":
    main()
