"""
Purpose: D6 STEPS 2-4 - stage-2 episode extraction, one local-LLM call per
         relevant document. Runs pass v1 (primary label) and optionally pass
         v1b (equivalent re-wording, second opinion stored as gate_pass2).
         STEP 0 volume rule: if projected wall-clock > 120 min, caps to the
         largest source x era stratified sample (seed 42) that fits, min 500.
Inputs : data/stage1.parquet, data/docs_clean.parquet, code/prompts/stage2_v1.txt,
         code/prompts/stage2_v1b.txt, BASE/.env (local profile), code/llm_helper.py.
Outputs: data/stage2_v1.parquet / data/stage2_v1b.parquet
         (doc_id, episode_json, is_retrieval_episode, failure_gate, _error; partial saves every 25)
         logs/stage2.log (progress + ETA every 25 docs)
         data/pipeline_counts.json keys: stage2_prompt_version, stage2_prompt_sha,
         stage2_prompt_v1b_sha, stage2_capped, n_relevant_total, n_extracted_target
Usage  : .venv/bin/python code/run_stage2.py --pass v1 [--pilot 30] [--limit N] [--workers auto]
         .venv/bin/python code/run_stage2.py --pass v1b
"""
import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
from llm_helper import llm_json, check_context  # noqa: E402
from pipeline_counts import update_counts  # noqa: E402
from schemas import Episode  # noqa: E402

TRUNC = 900
SECONDS_PER_CALL = 0.25  # D1 autotune, 8 workers: 12 calls in 3.0 s
CAP_MIN = 120
MIN_CAP = 500

_lock = threading.Lock()


def log(msg: str):
    line = time.strftime("%Y-%m-%dT%H:%M:%S%z") + " " + msg
    print(line, flush=True)
    with _lock:
        with open(BASE / "logs" / "stage2.log", "a") as f:
            f.write(line + "\n")


def prompt_file(pass_name: str) -> str:
    p = BASE / "code" / "prompts" / f"stage2_{pass_name}.txt"
    return p.read_text().strip()


_EP_SCHEMA = json.dumps(Episode.model_json_schema(), ensure_ascii=False)


def user_msg(text: str) -> str:
    return (f"User feedback text:\n\"\"\"\n{text[:TRUNC]}\n\"\"\"\n\n"
            f"The JSON must exactly match this schema (every field name as given; "
            f"remembered_cues is a list of objects with keys type, value, certainty):\n"
            f"{_EP_SCHEMA}\n\nReturn the JSON object.")


def process_doc(did, text, system, profile="local"):
    res = llm_json(system, user_msg(text), schema_model=Episode, profile=profile, max_tokens=2048)
    if "_error" in res:
        return {"doc_id": did, "episode_json": json.dumps({"_error": res["_error"]}),
                "is_retrieval_episode": None, "failure_gate": None, "_error": res["_error"][:200]}
    ep = res["episode"] if isinstance(res, dict) and "episode" in res else res
    # llm_json returns the parsed dict itself when schema_model given
    return {
        "doc_id": did,
        "episode_json": json.dumps(res, ensure_ascii=False),
        "is_retrieval_episode": bool(res.get("is_retrieval_episode")),
        "failure_gate": res.get("failure_gate"),
        "_error": None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="pass_name", choices=["v1", "v1b", "v2"], required=True)
    ap.add_argument("--docfile", default=None, help="file of doc_ids restricting the pass (eval runs)")
    ap.add_argument("--pilot", type=int, default=None, help="process only this many (stratified, seed 42)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", default="auto")
    args = ap.parse_args()

    log_path = BASE / "logs" / "stage2.log"
    log_path.parent.mkdir(exist_ok=True)

    system = prompt_file(args.pass_name)
    sha = hashlib.sha256(system.encode()).hexdigest()
    if args.pass_name == "v1":
        update_counts(stage2_prompt_version="v1", stage2_prompt_sha=sha[:16])
    elif args.pass_name == "v1b":
        update_counts(stage2_prompt_v1b_sha=sha[:16])
    else:
        update_counts(stage2_prompt_v2_sha=sha[:16])

    stage1 = pd.read_parquet(BASE / "data" / "stage1.parquet")
    clean = pd.read_parquet(BASE / "data" / "docs_clean.parquet")
    rel = stage1[stage1["relevant"] == True].merge(  # noqa: E712
        clean[["doc_id", "source", "era", "text"]], on="doc_id", how="left")
    if args.docfile:
        ids = {ln.strip() for ln in Path(args.docfile).read_text().splitlines() if ln.strip()}
        rel = rel[rel["doc_id"].astype(str).isin(ids)]
        log(f"DOCFILTER: restricted to {len(rel)} docs from {args.docfile}")
    log(f"START stage2 pass={args.pass_name} prompt_sha={sha[:16]} n_relevant_total={len(rel)}")

    out = BASE / f"data/stage2_{args.pass_name}.parquet"
    done = set()
    if out.exists():
        prev = pd.read_parquet(out)
        done = set(prev["doc_id"].astype(str))
        log(f"RESUME: {len(done)} docs already done for pass {args.pass_name}")
    todo = rel[~rel["doc_id"].astype(str).isin(done)].reset_index(drop=True)

    # STEP 0 volume rule (v1 only; v1b mirrors whatever v1 did)
    capped = False
    n_target = len(todo)
    if args.pass_name == "v1" and args.pilot is None and args.limit is None:
        proj_min = len(todo) * SECONDS_PER_CALL / 60
        log(f"VOLUME PLAN: {len(todo)} docs x {SECONDS_PER_CALL}s = {proj_min:.1f} min projected")
        if proj_min > CAP_MIN:
            n_fit = max(MIN_CAP, int((CAP_MIN * 60) / SECONDS_PER_CALL))
            n_fit = min(n_fit, len(todo))
            rng = np.random.default_rng(42)
            grp = todo.groupby(["source", "era"], dropna=False)
            sizes = grp.size()
            total = sizes.sum()
            alloc = (sizes * n_fit / total).round().astype(int)
            pick = []
            for name, idx in grp.groups.items():
                n = min(int(alloc.get(name, 0)), len(idx))
                pick.append(rng.choice(np.asarray(list(idx)), size=n, replace=False))
            pick = np.concatenate(pick) if pick else np.array([], dtype=int)
            todo = todo.iloc[np.sort(pick)].reset_index(drop=True)
            capped = True
            log(f"CAP APPLIED: {len(todo)} docs (source x era stratified, seed 42)")
    if args.pilot is not None:
        # stratified pilot sample of the requested size
        n = min(args.pilot, len(todo))
        grp = todo.groupby(["source", "era"], dropna=False)
        sizes = grp.size()
        total = sizes.sum()
        alloc = (sizes * n / total).round().astype(int)
        alloc = alloc.clip(lower=1)
        alloc = (alloc / alloc.sum() * n).astype(int)
        rng = np.random.default_rng(42)
        pick = []
        for name, idx in grp.groups.items():
            nn = min(int(alloc.get(name, 0)), len(idx))
            if nn > 0:
                pick.append(rng.choice(np.asarray(list(idx)), size=nn, replace=False))
        pick = np.concatenate(pick) if pick else np.array([], dtype=int)
        todo = todo.iloc[np.sort(pick)].reset_index(drop=True)
        log(f"PILOT: processing {len(todo)} docs")
    if args.limit is not None:
        todo = todo.iloc[:args.limit].reset_index(drop=True)

    if len(todo) == 0:
        log("NOTHING TO DO (all done)")
        return

    check_context(system + "\n" + user_msg("x" * TRUNC))

    workers = 4
    if str(args.workers) == "auto":
        try:
            workers = int(json.loads((BASE / "data" / "pipeline_counts.json").read_text()).get("llm_workers", 4))
        except Exception:
            pass

    rows = []
    t0 = time.time()
    n_err = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(process_doc, str(r["doc_id"]), str(r["text"]), system): r["doc_id"]
                for _, r in todo.iterrows()}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            rows.append(r)
            if r["_error"]:
                n_err += 1
            if i % 25 == 0:
                dt = time.time() - t0
                rate = i / dt if dt else 0
                eta = (len(futs) - i) / rate if rate else 0
                log(f"PROGRESS pass={args.pass_name} {i}/{len(futs)} err={n_err} rate={rate:.2f}/s ETA={eta/60:.1f} min")
                _flush(out, rows)
    _flush(out, rows)

    if out.exists():
        df = pd.read_parquet(out)
    else:
        df = pd.DataFrame(rows)
    log(f"DONE pass={args.pass_name} total_rows={len(df)} err={int(df['_error'].notna().sum()) if '_error' in df else n_err} capped={capped}")
    if args.pass_name == "v1":
        update_counts(stage2_capped=capped, n_relevant_total=int((stage1['relevant'] == True).sum()),  # noqa: E712
                      n_extracted_target=len(df))


def _flush(out_path: Path, rows):
    with _lock:
        if not rows:
            return
        new = pd.DataFrame(rows)
        if out_path.exists():
            old = pd.read_parquet(out_path)
            df = pd.concat([old, new], ignore_index=True).drop_duplicates(subset="doc_id", keep="last")
        else:
            df = new
        df.to_parquet(out_path, index=False)


if __name__ == "__main__":
    main()
