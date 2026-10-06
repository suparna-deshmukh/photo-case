"""
Purpose: D6 STEP 2 - stage-1 relevance screening of docs_for_llm.parquet with
         the local LLM (batches of 12 docs per call, text truncated to 450 chars).
Inputs : data/docs_for_llm.parquet; existing data/stage1.parquet (resume);
         BASE/.env (LLM_* local profile); code/llm_helper.py; code/schemas.py.
Outputs: data/stage1.parquet (doc_id, relevant)
         logs/stage1.log (progress + ETA)
         data/pipeline_counts.json keys: n_relevant, kw_recall_est
Usage  : .venv/bin/python code/run_stage1.py [--limit N] [--workers auto]
"""
import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
from llm_helper import llm_json, check_context  # noqa: E402
from pipeline_counts import update_counts  # noqa: E402
from schemas import Stage1Screen  # noqa: E402

STAGE1 = BASE / "data" / "stage1.parquet"
LOG = BASE / "logs" / "stage1.log"
BATCH = 12
TRUNC = 450

SYSTEM = ('You screen user feedback about Google Photos. A document is RELEVANT if the writer '
          'describes trying to find, locate, search for, browse to, or retrieve existing photos or '
          'videos (including complaints about search, Ask Photos, results, dates, people/face search, '
          'or photos seeming to be missing when searched for). It is NOT relevant if it is only about '
          'storage pricing, editing tools, sharing UI, memories/highlights quality, or general praise. '
          'Return JSON: {"relevant_ids": [list of ids]} using only the ids given.')

_lock = threading.Lock()


def log(msg: str):
    line = time.strftime("%Y-%m-%dT%H:%M:%S%z") + " " + msg
    print(line, flush=True)
    with _lock:
        with open(LOG, "a") as f:
            f.write(line + "\n")


def user_msg(batch: pd.DataFrame) -> str:
    parts = []
    for _, r in batch.iterrows():
        t = str(r["text"])[:TRUNC]
        parts.append(f"{r['doc_id']} :: {t}")
    return "Decide which ids are relevant.\n" + "\n".join(parts)


def process_batch(batch: pd.DataFrame, profile="local"):
    ids = [str(x) for x in batch["doc_id"]]
    res = llm_json(SYSTEM, user_msg(batch), schema_model=Stage1Screen, profile=profile)
    if "_error" in res:
        res = llm_json(SYSTEM, user_msg(batch), schema_model=Stage1Screen, profile=profile)
    if "_error" in res:
        return {i: None for i in ids}
    rel = set(res.get("relevant_ids") or [])
    return {i: (i in rel) for i in ids}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="max batches this run (pilot)")
    ap.add_argument("--workers", default="auto")
    args = ap.parse_args()

    forl = pd.read_parquet(BASE / "data" / "docs_for_llm.parquet")
    done = set()
    partial = None
    if STAGE1.exists():
        partial = pd.read_parquet(STAGE1)
        done = set(partial["doc_id"])
        log(f"RESUME: {len(done)} docs already in stage1.parquet")
    todo = forl[~forl["doc_id"].isin(done)].reset_index(drop=True)
    log(f"START stage1: {len(forl)} total, {len(todo)} todo, batch={BATCH}, workers={args.workers}")

    n_batches = (len(todo) + BATCH - 1) // BATCH
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    if args.limit is not None:
        batches = batches[:args.limit]
        log(f"LIMIT: running {len(batches)} batches only")

    # context check on a full batch (worst case)
    if batches:
        sample = user_msg(batches[0])
        check_context(SYSTEM + "\n" + sample)

    import json as _json
    from concurrent.futures import as_completed
    if str(args.workers) == "auto":
        try:
            workers = int(_json.loads((BASE / "data" / "pipeline_counts.json").read_text()).get("llm_workers", 4))
        except Exception:
            workers = 4
    else:
        workers = int(args.workers)
    results = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = [ex.submit(process_batch, b) for b in batches]
        for i, fut in enumerate(as_completed(futs), 1):
            res = fut.result()
            results.update(res)
            if i % 25 == 0:
                dt = time.time() - t0
                rate = i / dt
                eta = (len(batches) - i) / rate if rate else 0
                log(f"PROGRESS {i}/{len(batches)} batches, err_batches_with_None={sum(1 for v in res.values() if v is None)}, rate={rate:.2f} batch/s, ETA={eta/60:.1f} min")
                flush_partial(partial, todo, results, i)
    flush_partial(partial, todo, results, len(batches))

    # assemble full stage1 table
    rows = []
    for _, r in forl.iterrows():
        did = str(r["doc_id"])
        rows.append({"doc_id": did, "relevant": results.get(did, None)})
    df = pd.DataFrame(rows, columns=["doc_id", "relevant"])
    # re-read persisted partials in case of earlier runs
    if STAGE1.exists():
        prev = pd.read_parquet(STAGE1)
        prev_map = dict(zip(prev["doc_id"].astype(str), prev["relevant"]))
        df["relevant"] = [prev_map.get(d, v) for d, v in zip(df["doc_id"].astype(str), df["relevant"])]
    df.to_parquet(STAGE1, index=False)

    rel = df["relevant"] == True  # noqa: E712
    n_rel = int(rel.sum())
    # keyword-filter recall estimate (positional: df is in docs_for_llm order)
    ctrl_rate = None
    try:
        import json as _j
        ctrl_rate = _j.loads((BASE / "data" / "pipeline_counts.json").read_text()).get("control_rate")
    except Exception:
        pass
    ctrl_arr = forl["control"].fillna(False).to_numpy() if "control" in forl.columns else None
    rel_arr = rel.to_numpy()
    rel_kw = rel_ctrl = 0
    if ctrl_arr is not None:
        rel_kw = int((rel_arr & ~ctrl_arr).sum())
        rel_ctrl = int((rel_arr & ctrl_arr).sum())
    est = None
    if ctrl_rate and (rel_kw or rel_ctrl):
        est = round(rel_kw / (rel_kw + rel_ctrl / ctrl_rate), 3)
    log(f"DONE stage1: n_total={len(df)} n_relevant={n_rel} (of {int(rel.notna().sum())} judged; "
        f"{int(rel.isna().sum())} unjudged/err) kw_recall_est={est}")
    update_counts(n_relevant=n_rel, kw_recall_est=est, n_stage1_unjudged=int(rel.isna().sum()))
    print(f"stage1: relevant={n_rel}/{len(df)} kw_recall_est={est}")


def flush_partial(partial, todo, results, n_batches_done):
    with _lock:
        if partial is None:
            base = pd.DataFrame(columns=["doc_id", "relevant"])
        else:
            base = partial.copy()
        have = set(base["doc_id"].astype(str))
        new = {d: v for d, v in results.items() if d not in have}
        if new:
            add = pd.DataFrame({"doc_id": list(new.keys()), "relevant": list(new.values())})
            base = pd.concat([base, add], ignore_index=True)
        base.to_parquet(STAGE1, index=False)


if __name__ == "__main__":
    main()
