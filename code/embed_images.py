"""
M4 — CLIP embeddings over the demo library.
Outputs: library/image_emb.npy (N x 512 float32, normalized), library/emb_index.json (row -> img_id)
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).resolve().parent.parent
LIB = BASE / "library"

def main():
    meta = pd.read_parquet(LIB / "meta.parquet")
    model = SentenceTransformer("clip-ViT-B-32")
    imgs, ids = [], []
    t0 = time.time()
    for _, r in meta.iterrows():
        try:
            im = Image.open(LIB / "images" / r["filename"]).convert("RGB")
            imgs.append(im)
            ids.append(r["img_id"])
        except Exception as e:
            print("  skip", r["img_id"], str(e)[:80])
    emb = model.encode(imgs, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)
    emb = emb.astype("float32")
    np.save(LIB / "image_emb.npy", emb)
    (LIB / "emb_index.json").write_text(json.dumps(ids))
    n = len(meta)
    print(f"emb shape {emb.shape} (meta rows {n}); {time.time()-t0:.0f}s total, "
          f"{(time.time()-t0)/max(len(ids),1)*1000:.0f} ms/image")
    assert emb.shape[0] == len(ids)
    if len(ids) != n:
        print(f"WARNING: {n - len(ids)} images failed to load")

    # sanity queries
    for q in ("a cup of coffee on a cafe table", "sunset over the sea with a boat"):
        qv = model.encode([q], convert_to_numpy=True, normalize_embeddings=True)
        sims = (emb @ qv[0])
        top = np.argsort(-sims)[:5]
        print(f"\nquery: {q!r}")
        for i in top:
            row = meta[meta["img_id"] == ids[i]].iloc[0]
            print(f"  {ids[i]} [{row['event_id']}] {sims[i]:.3f} | {str(row.get('caption'))[:90]}")
    print("DONE embed_images")

if __name__ == "__main__":
    main()
