"""Verify library/data consistency for the space_jog app."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
LIB = BASE / "library"
SP = BASE / "space_jog"

raw = pd.read_csv(LIB / "images_raw.csv")
kept = raw[~raw.deleted.fillna(False).astype(bool)]
meta = pd.read_parquet(LIB / "meta.parquet")
tags = pd.read_parquet(LIB / "tags.parquet")
emb = np.load(LIB / "image_emb.npy")
emb_ids = json.loads((LIB / "emb_index.json").read_text())

print(f"raw rows {len(raw)} | non-deleted {len(kept)}")
print(f"meta {len(meta)} | tags {len(tags)} | emb {len(emb)}x{emb.shape[1]}")
assert len(meta) == len(kept), "meta != non-deleted"
assert len(emb) == len(meta), "emb != meta"
assert set(meta.img_id) == set(emb_ids), "emb_ids != meta"
pk = meta.get("person_key")
if pk is not None:
    print("meta person_key set:", int((pk.fillna('') != '').sum()))
sp_meta = pd.read_parquet(SP / "data" / "meta.parquet")
sp_emb = np.load(SP / "data" / "image_emb.npy")
sp_ids = json.loads((SP / "data" / "emb_index.json").read_text())
print(f"space: meta {len(sp_meta)} | emb {len(sp_emb)} | ids {len(sp_ids)}")
assert len(sp_meta) == len(sp_emb) == len(sp_ids) == len(meta), "space/library mismatch"
img_n = len(list((SP / "images").glob("img_*.jpg")))
print(f"space images: {img_n} files")
assert img_n == len(kept), "space images != non-deleted"
people_p = SP / "data" / "people.json"
if people_p.exists():
    pl = json.loads(people_p.read_text())
    print("persons:", [(p["id"], p["count"]) for p in pl["persons"]])
    print("img2person mapped:", len(pl["img2person"]))
    faces = list((SP / "data" / "faces").glob("*.jpg"))
    print("face avatars:", len(faces))
total_mb = sum(f.stat().st_size for f in (SP / "images").glob("img_*.jpg")) / 1e6
print(f"space image MB: {total_mb:.0f}")
celeb = raw[raw.person_key.fillna("") != ""]
print("celebrity rows by person:")
print(celeb.groupby("person_key").size().to_string())
print("VERIFY PASS")
