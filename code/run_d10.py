"""
Purpose: D10 - build the 6 preset cached answers for the Discovery app using
         the LOCAL profile (unlimited local usage) through evidence_engine.
         Also prints each answer side-by-side with its tables for QA review.
Inputs : BASE/data/app bundle (D9), BASE/.env (LLM_* local profile),
         code/evidence_engine.py, code/llm_helper.py.
Outputs: BASE/data/app/cached_answers.json; printed review block.
Usage  : .venv/bin/python code/run_d10.py
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
from llm_helper import llm_json  # noqa: E402
import evidence_engine as ee  # noqa: E402

APP = BASE / "data" / "app"


def live_call_local(system: str, user: str):
    res = llm_json(system, user, schema_model=None, profile="local", max_tokens=1400)
    if not isinstance(res, dict) or "_error" in res:
        return None
    return res


def main():
    out = ee.build_cached_answers(APP, live_call_local)
    print("\n================ QA REVIEW: cached answers vs tables ================")
    for q, entry in out.items():
        print(f"\n### Q: {q}")
        print(f"method: {entry['method']}  n={entry['n']}")
        print(entry["answer_markdown"])
        for t in entry["tables"][:2]:
            print(f"  table: {t['title']} (rows={len(t['rows'])})")
            for r in t["rows"][:5]:
                print("   ", r)
    (APP / "cached_answers.json").exists()
    print("\nrun_d10 done")


if __name__ == "__main__":
    main()
