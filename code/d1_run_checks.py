"""
Purpose: D1 checkpoint runner: (1) smoke test - JSON {"ok": true, "model_says": ...}
         via pydantic schema, plus an identical second call proving the disk-cache
         hit; (2) autotune_workers() saving llm_workers; (3) speed_test(10) with
         projections for 1,000 / 3,000 / 6,000 calls; (4) check_context demo.
Inputs:  BASE/.env (local LLM profile), BASE layout.
Outputs: printed checkpoint evidence (tee to logs/d1_run.log);
         data/pipeline_counts.json (llm_workers); cache/llm_cache.jsonl growth.
"""
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
import llm_helper  # noqa: E402
from pydantic import BaseModel  # noqa: E402


class SmokeOut(BaseModel):
    ok: bool
    model_says: str


def main():
    print("== D1 smoke test ==")
    sysp = "You are a JSON assistant. Return ONLY valid JSON."
    user = 'Return JSON {"ok": true, "model_says": <one short sentence>}'
    r1 = llm_helper.llm_json(sysp, user, schema_model=SmokeOut)
    print("call1:", json.dumps(r1))
    assert isinstance(r1, dict) and r1.get("ok") is True \
        and isinstance(r1.get("model_says"), str) and "_error" not in r1, \
        f"smoke call1 failed: {r1}"
    hits_before = llm_helper.stats()["cache_hits"]
    t0 = time.time()
    r2 = llm_helper.llm_json(sysp, user, schema_model=SmokeOut)
    dt2 = time.time() - t0
    hits_after = llm_helper.stats()["cache_hits"]
    is_hit = hits_after == hits_before + 1
    print(f"call2 identical: {json.dumps(r2)} dt={dt2 * 1000:.1f}ms cache_hit={is_hit}")
    assert r2 == r1 and is_hit, "second identical call did not hit the cache"
    print("SMOKE PASS: ok=true and second call is a cache hit")

    print("== D1 autotune ==")
    llm_helper.autotune_workers("local")

    print("== D1 speed test ==")
    llm_helper.speed_test(10, profile="local")

    print("== D1 context check ==")
    llm_helper.check_context("short prompt, well within limits")

    print("== D1 final stats ==")
    print("stats:", json.dumps(llm_helper.stats()))
    print("D1 RUN COMPLETE")


if __name__ == "__main__":
    main()
