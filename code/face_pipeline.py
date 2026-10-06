"""M2b — face detection, identity clustering and 'People' data for the demo.

Detects faces in every non-deleted image, clusters embeddings into
'people', maps each image to its most prominent person, and writes:
  library/people.json   -> copied to space_jog/data/people.json
  library/faces/pN.jpg  -> face avatar per person (copied to space_jog/data/faces/)

Ground truth (person_key in images_raw.csv, celebrity set) is used ONLY to
merge/sanity-check clusters; the app shows anonymized 'Person N' labels.
Usage: .venv/bin/python code/face_pipeline.py [--resume]
"""
import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
LIB = BASE / "library"
IMGDIR = LIB / "images"
PROGRESS = LIB / "faces_progress.jsonl"
RAWFACES = LIB / "faces_raw.pkl"


def get_app():
    from insightface.app import FaceAnalysis
    app = FaceAnalysis(name="buffalo_l", root=str(LIB / "models_insightface"),
                       providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


def detect_all(app, meta, done):
    import pickle
    faces = {}
    if RAWFACES.exists():
        faces = pickle.loads(RAWFACES.read_bytes())
    logf = open(PROGRESS, "a") if not done else None
    t0 = time.time()
    for n, (_, row) in enumerate(meta.iterrows()):
        iid = row["img_id"]
        if iid in done or iid in faces:
            continue
        p = IMGDIR / row["filename"]
        got = []
        try:
            img = np.array(Image.open(p).convert("RGB"))
            fs = app.get(img)
            for f in sorted(fs, key=lambda f: -float(f.det_score))[:3]:
                w = f.bbox[2] - f.bbox[0]
                if w < 70:
                    continue
                got.append((f.bbox.tolist(), float(f.det_score), f.normed_embedding.astype("float32")))
        except Exception:  # noqa: BLE001
            got = []
        faces[iid] = got
        if logf:
            logf.write(iid + "\n")
        if (n + 1) % 100 == 0:
            dt = time.time() - t0
            print(f"  {n + 1}/{len(meta)} faces ({dt / max(1, n + 1 - len(done)):.2f}s/img)",
                  flush=True)
    if logf:
        logf.close()
    import pickle as pk
    RAWFACES.write_bytes(pk.dumps(faces))
    return faces


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    meta = pd.read_parquet(LIB / "meta.parquet")
    raw = pd.read_csv(LIB / "images_raw.csv")
    pk_map = dict(zip(raw["img_id"], raw.get("person_key", pd.Series(dtype=str)).fillna("")))
    done = set()
    if PROGRESS.exists() and args.resume:
        done = set(PROGRESS.read_text().split())
    print("loading insightface (first run downloads models)…", flush=True)
    app = get_app()
    print("detecting faces…", flush=True)
    faces = detect_all(app, meta, done)
    nfaces = sum(len(v) for v in faces.values())
    print(f"detected {nfaces} faces in {len(faces)} images", flush=True)

    embs, meta_rows = [], []
    for iid, fl in faces.items():
        for bbox, score, emb in fl:
            embs.append(emb)
            meta_rows.append((iid, bbox, score, pk_map.get(iid, "")))
    if not embs:
        print("NO FACES — aborting")
        return
    E = np.stack(embs)
    from sklearn.cluster import AgglomerativeClustering
    t0 = time.time()
    clu = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="average",
                                  distance_threshold=0.55).fit(E)
    print(f"clustering done in {time.time() - t0:.0f}s; "
          f"{len(set(clu.labels_))} raw clusters", flush=True)

    # merge clusters that share the same celebrity ground truth
    cluster_key = {}
    for c in set(clu.labels_):
        keys = [meta_rows[i][3] for i in np.where(clu.labels_ == c)[0] if meta_rows[i][3]]
        top = Counter(keys).most_common(1)
        cluster_key[c] = top[0][0] if top else None
    final_id = {}
    p = 0
    used = {}
    for c, key in cluster_key.items():
        if key is None:
            size = int((clu.labels_ == c).sum())
            if size < 8:
                continue
        p += 1
        if key in used:
            final_id[c] = used[key]
        else:
            used[key] = f"p{p}" if key else f"u{p}"
            final_id[c] = used[key]

    person_counts = Counter()
    img2person = {}
    for i, (iid, bbox, score, _g) in enumerate(meta_rows):
        pid = final_id.get(clu.labels_[i])
        if not pid:
            continue
        person_counts[pid] += 1
        key = (score, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
        if iid not in img2person or key > img2person[iid][0]:
            img2person[iid] = (key, pid, bbox, score)

    persons = []
    faces_out = LIB / "faces"
    faces_out.mkdir(exist_ok=True)
    for pid, cnt in sorted(person_counts.items(), key=lambda x: -x[1]):
        if cnt < 5:
            continue
        n = len(persons) + 1
        gkey = None
        for i, (iid, _b, _s, g) in enumerate(meta_rows):
            if final_id.get(clu.labels_[i]) == pid and g:
                gkey = g
                break
        # avatar: best face crop among this person's images
        best = None
        cands = [(key, iid, bbox) for iid, (key, pid2, bbox, score)
                 in img2person.items() if pid2 == pid]
        if cands:
            best = max(cands, key=lambda t: t[0])
        avatar = f"p{n}.jpg"
        if best:
            _k, iid, bbox = best
            img = Image.open(IMGDIR / dict(zip(meta["img_id"], meta["filename"]))[iid]).convert("RGB")
            x1, y1, x2, y2 = [int(v) for v in bbox]
            w, h = x2 - x1, y2 - y1
            pad = int(0.3 * max(w, h))
            x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
            x2, y2 = min(img.width, x2 + pad), min(img.height, y2 + pad)
            side = max(1, min(x2 - x1, y2 - y1))
            x1, y1 = x1 + max(0, (x2 - x1 - side) // 2), y1 + max(0, (y2 - y1 - side) // 2)
            crop = img.crop((x1, y1, x1 + side, y1 + side)).resize((240, 240), Image.LANCZOS)
            crop.save(faces_out / avatar, "JPEG", quality=88)
        persons.append({"id": f"p{n}", "label": f"Person {n}", "count": int(cnt),
                        "avatar": avatar, "ground_key": gkey})
    # renumber img2person to final ids
    final_map = {x["id"] for x in persons}
    img2person_out = {iid: v[1] for iid, v in img2person.items() if v[1] in final_map}
    people = {"persons": persons, "img2person": img2person_out}
    (LIB / "people.json").write_text(json.dumps(people))
    purity = {}
    for x in persons:
        if x["ground_key"]:
            purity[x["label"]] = x["ground_key"]
    print(f"DONE: {len(persons)} persons, {len(img2person_out)} images mapped")
    for x in persons:
        print(f"  {x['id']} {x['label']}: {x['count']} faces  (gt: {x['ground_key']})")
    print("cluster->groundtruth:", purity)


if __name__ == "__main__":
    main()
