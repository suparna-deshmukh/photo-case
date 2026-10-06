"""Sequential D-track runner (post-Reddit): D4 ckpt -> D5 -> orphans -> stage1 ->
stage2 v1/v1b -> finalize -> D6 checkpoint print. Each step is a subprocess; any
failure stops the chain (inspect logs). Run as a persistent session."""
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PY = str(BASE / ".venv" / "bin" / "python")

STEPS = [
    ("D4 checkpoint", ["code/d4_checkpoint.py"]),
    ("D5 clean_merge", ["code/clean_merge.py"]),
    ("D5 checkpoint", ["code/d5_checkpoint.py"]),
    ("filter stage2 orphans (pre-stage1)", ["code/filter_stage2_orphans.py"]),
    ("D6 stage1 (resume)", ["code/run_stage1.py"]),
    ("filter stage2 orphans (post-stage1)", ["code/filter_stage2_orphans.py"]),
    ("D6 stage2 v1 (resume)", ["code/run_stage2.py", "--pass", "v1"]),
    ("D6 stage2 v1b (resume)", ["code/run_stage2.py", "--pass", "v1b"]),
    ("D6 finalize_stage2", ["code/finalize_stage2.py"]),
]


def log(msg):
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {msg}", flush=True)


def main():
    for name, cmd in STEPS:
        log(f"=== START {name}: {' '.join(cmd)}")
        r = subprocess.run([PY] + cmd, cwd=BASE)
        if r.returncode != 0:
            log(f"=== FAILED {name} (rc={r.returncode}) — chain stopped")
            sys.exit(1)
        log(f"=== DONE {name}")
    import pandas as pd
    ep = pd.read_parquet(BASE / "data" / "episodes_full.parquet")
    import json
    counts = json.loads((BASE / "data" / "pipeline_counts.json").read_text())
    log("D6 SUMMARY: " + json.dumps({k: counts.get(k) for k in
        ("n_reddit", "n_clean", "n_kw_hit", "n_for_llm", "n_relevant", "kw_recall_est",
         "n_extracted_attempted", "n_episodes", "quote_verified_pct", "error_pct",
         "gate_pass_agreement")}, indent=1))
    log("episodes_full rows: " + str(len(ep)) + " (checkpoint target >= 400, else report shortfall)")
    log("D CHAIN DONE")


if __name__ == "__main__":
    main()
