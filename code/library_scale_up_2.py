"""Round 2: fetch remaining shortfall with the expanded query set, then
tag -> meta -> embed -> sync -> verify. Stops a round loop on no progress."""
import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
PY = str(BASE / ".venv" / "bin" / "python")
LIB = BASE / "library"
TOTAL_GOAL = 2050

def run_step(name, cmd):
    print(f"\n=== [{time.strftime('%H:%M:%S')}] STEP: {name} ===", flush=True)
    print(f"    $ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    p = subprocess.run(cmd, cwd=BASE)
    dt = time.time() - t0
    print(f"=== [{time.strftime('%H:%M:%S')}] {name}: rc={p.returncode} after {dt/60:.1f} min ===", flush=True)
    return p.returncode

def counts():
    raw = pd.read_csv(LIB / "images_raw.csv")
    kept = raw[~raw["deleted"].fillna(False).astype(bool)]
    ev = pd.read_csv(LIB / "events.csv")
    g = kept.groupby("event_id").size()
    ev["kept"] = ev["event_id"].map(g).fillna(0).astype(int)
    ev["ok"] = ev["kept"] >= 0.6 * ev["target_count"]
    return len(kept), ev, len(kept) < TOTAL_GOAL or not ev["ok"].all()

def verify():
    print(f"\n=== [{time.strftime('%H:%M:%S')}] STEP: verification ===", flush=True)
    raw = pd.read_csv(LIB / "images_raw.csv")
    kept = raw[~raw["deleted"].fillna(False).astype(bool)]
    ev = pd.read_csv(LIB / "events.csv")
    g = kept.groupby("event_id").size()
    ev["kept"] = ev["event_id"].map(g).fillna(0).astype(int)
    print(ev[["event_id", "target_count", "kept"]].to_string(index=False), flush=True)
    total_mb = sum(f.stat().st_size for f in LIB.glob("images/img_*.jpg")) / 1e6
    print(f"TOTAL non-deleted: {len(kept)} (rows {len(raw)}, deleted {len(raw)-len(kept)}), {total_mb:.1f} MB", flush=True)
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
    print("VERIFICATION PASS", flush=True)

def main():
    prev = None
    for rnd in (1, 2, 3):
        n, ev, need_more = counts()
        print(f"\n=== [{time.strftime('%H:%M:%S')}] ROUND {rnd}: non-deleted={n}, need_more={need_more} ===", flush=True)
        if not need_more:
            print("target reached, no fetch round needed", flush=True)
            break
        rc = run_step(f"build_library --append (round {rnd})", [PY, "code/build_library.py", "--append"])
        if rc != 0:
            print(f"FAILED build_library round {rnd}", flush=True)
            sys.exit(rc)
        n2, ev2, need_more2 = counts()
        print(f"after round {rnd}: non-deleted={n2} (delta {n2-n})", flush=True)
        if n2 == n:
            print("NO PROGRESS — stopping fetch loop", flush=True)
            break
        if not need_more2:
            break
        prev = n2
    rc = run_step("tag_images local --resume", [PY, "code/tag_images.py", "--provider", "local", "--resume", "--workers", "8"])
    if rc != 0: sys.exit(rc)
    rc = run_step("build_meta (append-safe)", [PY, "code/build_meta.py"])
    if rc != 0: sys.exit(rc)
    rc = run_step("embed_images (CLIP)", [PY, "code/embed_images.py"])
    if rc != 0: sys.exit(rc)
    rc = run_step("sync_space_jog", [PY, "code/sync_space_jog.py"])
    if rc != 0: sys.exit(rc)
    verify()
    print(f"\n=== [{time.strftime('%H:%M:%S')}] SCALE-UP 2 COMPLETE ===", flush=True)

if __name__ == "__main__":
    main()
