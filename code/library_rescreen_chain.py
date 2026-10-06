"""Chain: rescreen_relaxed -> tag -> meta -> embed -> sync -> verify."""
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
    print(f"TOTAL non-deleted: {len(kept)}, {total_mb:.1f} MB", flush=True)
    low = ev[ev["kept"] < 0.6 * ev["target_count"]]
    if len(low):
        print(f"WARN events below 60%: {list(low['event_id'])}", flush=True)
    meta = pd.read_parquet(LIB / "meta.parquet")
    tags = pd.read_parquet(LIB / "tags.parquet")
    idx = json.loads((LIB / "emb_index.json").read_text())
    print(f"meta rows: {len(meta)} | tags rows: {len(tags)} | emb rows: {len(idx)}", flush=True)
    assert len(meta) == len(kept) == len(idx), "row count mismatch"
    import numpy as np
    emb = np.load(LIB / "image_emb.npy")
    assert emb.shape == (len(idx), 512), f"emb shape {emb.shape}"
    missing = set(meta["img_id"]) - set(tags["img_id"])
    assert not missing, f"untagged: {sorted(missing)[:5]}"
    print("VERIFICATION PASS", flush=True)

def main():
    run_step("rescreen_relaxed", [PY, "code/rescreen_relaxed.py"])
    run_step("tag_images local --resume", [PY, "code/tag_images.py", "--provider", "local", "--resume", "--workers", "8"])
    run_step("build_meta (append-safe)", [PY, "code/build_meta.py"])
    run_step("embed_images (CLIP)", [PY, "code/embed_images.py"])
    run_step("sync_space_jog", [PY, "code/sync_space_jog.py"])
    verify()
    print(f"\n=== [{time.strftime('%H:%M:%S')}] RESCREEN CHAIN COMPLETE ===", flush=True)

if __name__ == "__main__":
    main()
