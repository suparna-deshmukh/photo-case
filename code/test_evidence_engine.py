"""
Purpose: D10 - self-contained tests for code/evidence_engine.py (no pytest).
         Runs against BASE/data/app (built by D9).
Inputs : BASE/data/app bundle.
Outputs: printed PASS/FAIL per test; exit code 0 only if all pass.
Usage  : .venv/bin/python code/test_evidence_engine.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
import evidence_engine as ee  # noqa: E402

APP = BASE / "data" / "app"
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def main():
    df, emb, enums, counts, validation = ee.load_data(APP)
    emb_ids = ee.load_emb_ids(APP)
    mc = {}

    # (1) query_stats counts equal manual pandas counts for 3 queries
    q1 = ee.query_stats(df, ["failure_gate"], {}, "count", enums)
    manual1 = df["failure_gate"].value_counts()
    ok1 = all(int(q1[q1["failure_gate"] == g]["n"].iloc[0]) == int(manual1.get(g, 0)) for g in manual1.index)
    q2 = ee.query_stats(df, ["photo_type"], {"failure_gate": ["refinement"]}, "count", enums)
    manual2 = df[df["failure_gate"] == "refinement"]["photo_type"].value_counts()
    ok2 = all(int(q2[q2["photo_type"] == g]["n"].iloc[0]) == int(manual2.get(g, 0)) for g in manual2.index)
    q3 = ee.query_stats(df, ["cue_remembered"], {}, "count", enums)
    cnt = {}
    for s in df["remembered_cues"]:
        for t in ee._cue_types_of(s):
            cnt[t] = cnt.get(t, 0) + 1
    ok3 = all(int(q3[q3["cue_remembered"] == g]["n"].iloc[0]) == cnt.get(g, 0) for g in cnt)
    check("T1 query_stats vs manual counts (3 queries)", ok1 and ok2 and ok3,
          f"gate_ok={ok1} phototype_ok={ok2} cue_ok={ok3}")

    # (2) route_keywords returns valid plans for the 6 presets
    ok4 = True
    details = []
    for q in ee.PRESET_QUESTIONS:
        plan = ee.route_keywords(q, enums)
        valid = all(ee._validate_step(s, enums) for s in plan["steps"]) and 1 <= len(plan["steps"]) <= 3
        details.append(f"{q[:30]}..:{len(plan['steps'])}steps")
        ok4 = ok4 and valid
    check("T2 route_keywords valid plans for 6 presets", ok4, "; ".join(details))

    # (3) semantic_search works with MiniLM and with forced TF-IDF fallback
    r1, m1 = ee.semantic_search(df, emb, "search results wrong old photos", k=8, enums=enums, model_cache=mc, emb_ids=emb_ids)
    r2, m2 = ee.semantic_search(df, emb, "search results wrong old photos", k=8, enums=enums, model_cache=mc,
                                force_tfidf=True, emb_ids=emb_ids)
    ok5 = (len(r1) == 8 and m1 == "minilm" and len(r2) == 8 and m2 == "tfidf"
           and set(r1["doc_id"]) <= set(df["doc_id"].astype(str)))
    # simulate model load failure
    mc_bad = {"model": _Broken()}
    r3, m3 = ee.semantic_search(df, emb, "x", k=8, enums=enums, model_cache=mc_bad, emb_ids=emb_ids)
    ok6 = len(r3) == 8
    check("T3 semantic_search minilm + tfidf fallback", ok5 and ok6, f"m1={m1} m2={m2} fallback={ok6}")

    # (4) number checker rejects a deliberately wrong number
    plan = ee.route_keywords("Where in the retrieval journey does it break most?", enums)
    results_ = ee.run_plan(plan, df, emb, enums, model_cache=mc, emb_ids=emb_ids)
    allowed = ee._allowed_numbers(results_)
    real_num = sorted(allowed, key=lambda x: -x)[0]
    wrong_num = real_num + 37
    if results_["evidence_ids"]:
        ans_bad = f"The top gate has a share of {wrong_num}%. [ep:{results_['evidence_ids'][0]}]"
    else:
        ans_bad = f"The top gate has a share of {wrong_num}%."
    bad_detected = _numbers_outside(ans_bad, allowed)
    ans_good = f"The top gate has n={int(real_num)}."
    good_ok = not _numbers_outside(ans_good, allowed)
    check("T4 number checker rejects wrong number, accepts table number",
          bad_detected and good_ok, f"wrong={wrong_num} rejected={bad_detected}")

    # (5) nearest_estimate returns k=8 neighbours
    t7p = APP / "T7_scorecard.csv"
    t7 = pd.read_csv(t7p) if t7p.exists() else None
    ne = ee.nearest_estimate("I took a photo at my sister's wedding last summer and now the search won't find it",
                             df, emb, k=8, enums=enums, model_cache=mc, t7=t7)
    ok7 = (len(ne["most_similar"]) <= 8 and ne["label"].endswith("n=8 neighbours")
           and isinstance(ne["votes"], dict) and set(ne["votes"]) == {"failure_gate", "photo_type", "workaround"})
    check("T5 nearest_estimate k=8", ok7, f"votes={json.dumps(ne['votes'])[:100]}")

    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"\nTESTS: {len(results) - n_fail}/{len(results)} PASS, {n_fail} FAIL")
    return 0 if n_fail == 0 else 1


class _Broken:
    def encode(self, *a, **k):
        raise RuntimeError("simulated model failure")


def _numbers_outside(text, allowed):
    clean = re.sub(r"\[ep:[^\]]+\]", " ", text)
    bad = [n for n in _nums(clean) if n not in allowed]
    return len(bad) > 0


import re  # noqa: E402


def _nums(text):
    return {round(float(m), 1) for m in re.findall(r"\b(\d+(?:\.\d+)?)\b", text)}


if __name__ == "__main__":
    sys.exit(main())
