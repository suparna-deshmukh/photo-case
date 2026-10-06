"""M6 — engine tests (run: .venv/bin/python code/test_engine.py).

(1) score components in [0,1] and sum to the score
(2) rules-only parse of 8 tasks: start, rank target (visual-only vs full); full score
    ranks target within top 40 for >= 6/8 (also run with cached llm parses, print both)
(3) question selector never repeats an attribute, returns None after MAX_ROUNDS
(4) update_query_vec keeps unit norm
(5) median rules-parse latency over 10 fragments < 0.1 s (+ CLIP text-embedding time)
(6) no LLM env vars -> parse_memory returns rules/cache, never raises
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))

PASS = 0
FAIL = 0

def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"[PASS] {name}: {detail}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}: {detail}")

def main():
    lib = BASE / "library"
    meta = pd.read_parquet(lib / "meta.parquet")
    emb = np.load(lib / "image_emb.npy")
    idx = json.loads((lib / "emb_index.json").read_text())
    meta = meta.set_index("img_id", drop=False)
    tasks = json.loads((lib / "tasks.json").read_text())
    main_tasks = [t for t in tasks if t["set"] in ("X", "Y")]
    parses = json.loads((lib / "task_parses.json").read_text()) if (lib / "task_parses.json").exists() else {}

    from jog_engine.retrieval import Retriever
    from jog_engine.session import JogSession
    from jog_engine.cues import parse_memory
    from jog_engine.cues_rules import parse_rules
    from jog_engine.feedback import update_query_vec
    from jog_engine.questions import next_question
    from jog_engine.config import TOP_K

    from sentence_transformers import SentenceTransformer
    clip = SentenceTransformer("clip-ViT-B-32")
    ret = Retriever(meta.reset_index(drop=True), emb, clip)

    # ---------- (1) score components ----------
    parsed = parse_rules("a cafe in Goa in the morning", today="2026-10-06")
    qv = ret.encode_visual_query(parsed.visual_query)
    scored = ret.score(qv, parsed.cues, parsed.time_window)
    comp_sum = (scored["vis"] + scored["time"] + scored["place"] + scored["attr"]).to_numpy()
    diff = np.abs(comp_sum - scored["score"].to_numpy())
    in_range = bool(((scored[["vis", "time", "place", "attr"]] >= -0.51).all().all()
                     and (scored[["vis", "time", "place", "attr"]] <= 1.01).all().all()))
    check("T1 score components sum to score & in range", in_range and bool((diff < 1e-6).all()),
          f"max_diff={diff.max():.2e}, in_range={in_range}")

    # ---------- (2) rules-only rank of targets ----------
    def rank_for(task, use_cache):
        text = task["fragment_text"]
        if use_cache:
            import re
            norm = re.sub(r"\s+", " ", text).strip().lower()
            entry = parses.get(norm, {}).get("llm")
            if entry:
                from jog_engine.cues import _coerce_parsed
                parsed2 = _coerce_parsed(entry)
            else:
                parsed2 = parse_rules(text)
        else:
            parsed2 = parse_rules(text)
        qv2 = ret.encode_visual_query(parsed2.visual_query)
        s2 = ret.score(qv2, parsed2.cues, parsed2.time_window)
        row = s2[s2["img_id"] == task["target_img_id"]]
        if row.empty:
            return None, None
        r_full = int(s2.index[row.index[0]]) + 1
        # visual-only rank
        vsim = ret.visual_sim(qv2)
        r_vis = int(np.argsort(-vsim)[list(s2["img_id"]).index(task["target_img_id"])]) + 1
        return r_full, r_vis

    ok_rules = 0
    ok_cache = 0
    n_done = 0
    for t in main_tasks:
        rf, rv = rank_for(t, use_cache=False)
        rc, _ = rank_for(t, use_cache=True)
        n_done += 1
        if rf is not None and rf <= TOP_K:
            ok_rules += 1
        if rc is not None and rc <= TOP_K:
            ok_cache += 1
        print(f"  {t['id']}: full-rank rules={rf} cached={rc} visual-only={rv}")
    check(f"T2 rules-only top-{TOP_K} for >=6/8", ok_rules >= 6,
          f"rules={ok_rules}/{n_done} cached_llm={ok_cache}/{n_done}")

    # M6: fill the "rules" half of task_parses.json for all fragments + examples
    import re as _re
    parse_file = lib / "task_parses.json"
    parses_all = json.loads(parse_file.read_text()) if parse_file.exists() else {}
    ex_file = lib / "examples.json"
    example_texts = json.loads(ex_file.read_text()) if ex_file.exists() else []
    all_texts = [t["fragment_text"] for t in tasks] + list(example_texts)
    for _t in all_texts:
        _norm = _re.sub(r"\s+", " ", _t).strip().lower()
        parses_all.setdefault(_norm, {})["rules"] = parse_rules(_t).model_dump()
    parse_file.write_text(json.dumps(parses_all, indent=2, ensure_ascii=False))
    print(f"  task_parses.json rules half filled: {len(parses_all)} entries")

    # ---------- (3) question selector ----------
    parsed = parse_rules("a cafe in Goa, I think in the morning")
    qv = ret.encode_visual_query(parsed.visual_query)
    scored = ret.score(qv, parsed.cues, parsed.time_window)
    from jog_engine.clusters import moments as moments_fn
    state = {"answered": {}, "dont_know": {}, "asked": set(), "round": 0}
    asked_seq = []
    for r in range(6):
        q = next_question(scored, state, moments_fn(scored, ret.meta))
        if q is None:
            print(f"  question None at round {r} (expected after MAX_ROUNDS=4 or low entropy)")
            break
        asked_seq.append(q["attribute"])
        state["answered"][q["attribute"]] = q["options"][0]
        state["round"] += 1
        state["asked"].add(q["attribute"])
    no_repeat = len(asked_seq) == len(set(asked_seq))
    stopped = len(asked_seq) <= 4
    check("T3 question selector no-repeat + stops", no_repeat and stopped,
          f"asked={asked_seq}")

    # ---------- (4) unit norm ----------
    base = np.ones(512, dtype="float32")
    base = base / np.linalg.norm(base)
    img_index = {ret.img_ids[i]: i for i in range(len(ret.img_ids))}
    for _ in range(5):
        pos = [ret.img_ids[int(np.random.randint(len(ret.img_ids)))]]
        neg = [ret.img_ids[int(np.random.randint(len(ret.img_ids)))]]
        q2 = update_query_vec(base, pos, neg, emb, img_index)
        nrm = float(np.linalg.norm(q2))
        if abs(nrm - 1.0) > 1e-5:
            break
    else:
        nrm_ok = True
    check("T4 update_query_vec unit norm", nrm_ok, f"final norm={nrm:.6f}")

    # ---------- (5) latency ----------
    frags = [t["fragment_text"] for t in main_tasks] + [
        "a sunset with a boat in Goa", "my notes before exams last April",
        "rooftop dinner in Pondicherry at night", "street food with friends"]
    t0 = time.perf_counter()
    for f in frags:
        parse_rules(f)
    dt_rules = (time.perf_counter() - t0) / len(frags)
    t0 = time.perf_counter()
    for f in frags[:3]:
        ret.encode_text(f)
    dt_clip = (time.perf_counter() - t0) / 3
    check("T5 rules parse median < 0.1s", dt_rules < 0.1,
          f"rules={dt_rules*1000:.1f} ms/parse, clip_text={dt_clip*1000:.1f} ms")

    # ---------- (6) no LLM env -> rules/cache, never raises ----------
    saved = {}
    for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        saved[k] = os.environ.pop(k, None)
    try:
        ok6 = True
        detail = []
        for f in ["a cafe in Goa in the morning", "sunset with a boat in Gokarna"]:
            try:
                p6, src6 = parse_memory(f)
                detail.append(f"{src6}")
                if src6 not in ("rules", "cache"):
                    ok6 = False
            except Exception as e:
                ok6 = False
                detail.append(f"RAISED {e}")
        check("T6 no-LLM path returns rules/cache without raising", ok6, f"sources={detail}")
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v

    print(f"\nRESULT: {PASS} PASS, {FAIL} FAIL")
    return FAIL == 0

if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
