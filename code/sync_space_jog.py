"""Sync library/ -> space_jog/ (data files + non-deleted images). Idempotent, append-safe."""
import shutil
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
LIB = BASE / "library"
SPACE = BASE / "space_jog"

DATA_FILES = ["meta.parquet", "image_emb.npy", "emb_index.json", "gazetteer.json",
              "tasks.json", "task_parses.json", "examples.json"]

def main():
    raw = pd.read_csv(LIB / "images_raw.csv")
    kept = raw[~raw["deleted"].fillna(False).astype(bool)]
    (SPACE / "images").mkdir(parents=True, exist_ok=True)
    (SPACE / "data").mkdir(parents=True, exist_ok=True)

    copied = updated = 0
    for f in DATA_FILES:
        src = LIB / f
        dst = SPACE / "data" / f
        if not src.exists():
            print(f"  WARN missing {src}")
            continue
        if not dst.exists() or src.stat().st_size != dst.stat().st_size:
            shutil.copy2(src, dst)
            copied += 1
    print(f"data files: {copied} updated")

    img_dir = SPACE / "images"
    kept_names = set(kept["filename"].astype(str))
    added = 0
    for f in sorted(LIB.glob("images/img_*.jpg")):
        if f.name not in kept_names:
            continue
        dst = img_dir / f.name
        if not dst.exists() or dst.stat().st_size != f.stat().st_size:
            shutil.copy2(f, dst)
            added += 1
    removed = 0
    for f in img_dir.glob("img_*.jpg"):
        if f.name not in kept_names:
            f.unlink()
            removed += 1
    total_mb = sum(f.stat().st_size for f in img_dir.glob("img_*.jpg")) / 1e6
    print(f"images: {added} added, {removed} orphaned removed, "
          f"{len(list(img_dir.glob('img_*.jpg')))} present ({total_mb:.1f} MB)")

    # face-grouping data (People feature)
    pj = LIB / "people.json"
    if pj.exists():
        import json as _json
        _ppl = _json.loads(pj.read_text())
        for _p in _ppl.get("persons", []):
            _p.pop("ground_key", None)  # internal ground truth never ships
        (SPACE / "data" / "people.json").write_text(_json.dumps(_ppl))
        print("people.json: updated (ground_key stripped)")
    faces_src = LIB / "faces"
    if faces_src.exists():
        faces_dst = SPACE / "data" / "faces"
        faces_dst.mkdir(exist_ok=True)
        src_names = {f.name for f in faces_src.glob("*.jpg")}
        for f in sorted(faces_src.glob("*.jpg")):
            shutil.copy2(f, faces_dst / f.name)
        for f in faces_dst.glob("*.jpg"):
            if f.name not in src_names:
                f.unlink()
        print(f"faces: {len(src_names)} avatars synced")
    print("DONE sync_space_jog")

if __name__ == "__main__":
    main()
