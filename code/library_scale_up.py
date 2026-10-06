"""Scale the demo library to 2000+ non-deleted images. Chains:
1 build_library --append  2 tag_images (local, resume)  3 build_meta (append-safe)
4 embed_images  5 sync_space_jog  6 verification.
Stop on first failure. Log: logs/library_scale_up.log (tee by the launcher).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
PY = str(BASE / ".venv" / "bin" / "python")
LIB = BASE / "library"

def run_step(name, cmd):
    print(f"\n=== [{time.strftime('%H:%M:%S')}] STEP: {name} ===", flush=True)
    print(f"    $ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    p = subprocess.run(cmd, cwd=BASE)
    dt = time.time() - t0
    print(f"=== [{time.strftime('%H:%M:%S')}] {name}: rc={p.returncode} after {dt/60:.1f} min ===", flush=True)
    if p.returncode != 0:
        print(f"FAILED: {name} (rc={p.returncode}) — stopping scale-up", flush=True)
        sys.exit(p.returncode)

def verify():
    print(f"\n=== [{time.strftime('%H:%M:%S')}] STEP: verification ===", flush=True)
    raw = pd.read_csv(LIB / "images_raw.csv")
    kept = raw[~raw["deleted"].fillna(False).astype(bool)]
    ev = pd.read_csv(LIB / "events.csv")
    g = kept.groupby("event_id").size()
    ev["kept"] = ev["event_id"].map(g).fillna(0).astype(int)
    print(ev[["event_id", "target_count", "kept"]].to_string(index=False), flush=True)
    total_mb = sum(f.stat().st_size for f in LIB.glob("images/img_*.jpg")) / 1e6
    print(f"TOTAL non-deleted: {len(kept)}  (rows {len(raw)}, deleted {len(raw)-len(kept)}), {total_mb:.1f} MB", flush=True)
    low = ev[ev["kept"] < 0.6 * ev["target_count"]]
    if len(low):
        print(f"WARN events below 60%: {list(low['event_id'])}", flush=True)
    meta = pd.read_parquet(LIB / "meta.parquet")
    tags = pd.read_parquet(LIB / "tags.parquet")
    idx = json.loads((LIB / "emb_index.json").read_text())
    print(f"meta rows: {len(meta)} | tags rows: {len(tags)} | emb rows: {len(idx)}", flush=True)
    assert len(meta) == len(kept) == len(idx), "row count mismatch across meta/tags/emb"
    import numpy as np
    emb = np.load(LIB / "image_emb.npy")
    assert emb.shape == (len(idx), 512), f"emb shape {emb.shape}"
    missing = set(meta["img_id"]) - set(tags["img_id"])
    assert not missing, f"untagged: {sorted(missing)[:5]}"
    keys = {
        "medicine e07": kept[(kept["event_id"] == "e07") & kept["query"].str.contains("medicine|tablet|pill|blister|prescription", case=False, na=False)],
        "notes e05": kept[kept["event_id"] == "e05"],
        "sunset-boat e10": kept[(kept["event_id"] == "e10") & kept["query"].str.contains("sunset boat|boat sea sunset", case=False, na=False)],
        "ruins e06": kept[(kept["event_id"] == "e06") & kept["query"].str.contains("ruins|chariot|temple", case=False, na=False)],
        "rooftop e08": kept[(kept["event_id"] == "e08") & kept["query"].str.contains("rooftop", case=False, na=False)],
        "cafes e04/06/08": kept[kept["event_id"].isin(["e04", "e06", "e08"]) & kept["query"].str.contains("cafe", case=False, na=False)],
    }
    for k, v in keys.items():
        print(f"M5-key {k}: {len(v)}", flush=True)
        assert len(v) >= 1, f"missing M5-critical: {k}"
    print("VERIFICATION PASS", flush=True)

def main():
    run_step("build_library --append", [PY, "code/build_library.py", "--append"])
    run_step("tag_images local --resume", [PY, "code/tag_images.py", "--provider", "local", "--resume", "--workers", "8"])
    run_step("build_meta (append-safe)", [PY, "code/build_meta.py"])
    run_step("embed_images (CLIP)", [PY, "code/embed_images.py"])
    run_step("sync_space_jog", [PY, "code/sync_space_jog.py"])
    verify()
    print(f"\n=== [{time.strftime('%H:%M:%S')}] SCALE-UP COMPLETE ===", flush=True)

if __name__ == "__main__":
    main()
