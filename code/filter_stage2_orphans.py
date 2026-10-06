"""Drop stage-2 rows whose doc is no longer stage-1-relevant (after D5 re-runs)."""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]


def main():
    stage1 = pd.read_parquet(BASE / "data" / "stage1.parquet")
    rel = set(stage1.loc[stage1["relevant"] == True, "doc_id"].astype(str))  # noqa: E712
    total = 0
    for pass_name in ("v1", "v1b"):
        p = BASE / f"data/stage2_{pass_name}.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        before = len(df)
        df = df[df["doc_id"].astype(str).isin(rel)].reset_index(drop=True)
        df.to_parquet(p, index=False)
        dropped = before - len(df)
        total += dropped
        print(f"{pass_name}: {before} -> {len(df)} (dropped {dropped} orphans)")
    print(f"stage1 relevant={len(rel)}; total orphans dropped={total}")


if __name__ == "__main__":
    main()
