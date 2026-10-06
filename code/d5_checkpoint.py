"""
Purpose: D5 checkpoint verification.
Inputs : data/docs_clean.parquet, data/docs_for_llm.parquet, data/pipeline_counts.json.
Outputs: printed checkpoint (row counts, ranges, 5 kept / 5 dropped examples, PASS/FAIL).
Usage  : .venv/bin/python code/d5_checkpoint.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


clean = pd.read_parquet(BASE / "data" / "docs_clean.parquet")
forl = pd.read_parquet(BASE / "data" / "docs_for_llm.parquet")
counts = json.loads((BASE / "data" / "pipeline_counts.json").read_text())

print(f"docs_clean: {len(clean)} rows")
print("  per source:", clean["source"].value_counts().to_dict())
print("  per era:", clean["era"].value_counts(dropna=False).to_dict())
print("  kw_hit:", int(clean["kw_hit"].sum()), f"({100*clean['kw_hit'].mean():.1f}%)")
print("  kw_hit share per source:", clean.groupby("source")["kw_hit"].mean().round(3).to_dict())

n_min = 5000
check("docs_clean >= 5,000", len(clean) >= n_min, f"n={len(clean)}")
check("docs_for_llm between 1,200 and 8,000", 1200 <= len(forl) <= 8000, f"n={len(forl)}")
check("counts file consistent",
      counts.get("n_clean") == len(clean) and counts.get("n_for_llm") == len(forl),
      f"n_clean={counts.get('n_clean')} n_for_llm={counts.get('n_for_llm')}")
check("control column present", "control" in forl.columns and forl["control"].sum() > 0,
      f"controls={int(forl['control'].sum()) if 'control' in forl.columns else 'missing'}")

rng = pd.np.random.default_rng(1) if hasattr(pd, "np") else __import__("numpy").random.default_rng(1)
print("\n5 random KEPT (kw_hit=True):")
kept = clean[clean["kw_hit"]]
for _, r in kept.sample(min(5, len(kept)), random_state=1).iterrows():
    print(f"  [{r['source']} {str(r['date'])[:10]}] {str(r['text'])[:150]!r}")
print("\n5 random DROPPED-BY-KW (kw_hit=False, still in docs_clean):")
dropped = clean[~clean["kw_hit"]]
for _, r in dropped.sample(min(5, len(dropped)), random_state=1).iterrows():
    print(f"  [{r['source']} {str(r['date'])[:10]}] {str(r['text'])[:150]!r}")

n_fail = checks.count(False)
print(f"\nD5 CHECKPOINT: {len(checks) - n_fail}/{len(checks)} PASS, {n_fail} FAIL")
sys.exit(0 if not n_fail else 1)
