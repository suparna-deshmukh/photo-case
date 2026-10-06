"""Resume M1b downloads with Wikimedia-friendly pacing (2 workers, 429 backoff)."""
import concurrent.futures as cf
import io
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_celebrities import (API_LOG, BASE, CELEBS, IMGDIR, RAW, UA,  # noqa: E402
                               existing_phashes, load_progress)

try:
    import imagehash
except ImportError:
    imagehash = None


def dl(rec):
    dest = IMGDIR / f"{rec['img_id']}.jpg"
    for attempt in range(6):
        url = rec.get("thumburl") or rec.get("url")
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
            if r.status_code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if max(im.size) > 800:
                im.thumbnail((800, 800), Image.LANCZOS)
            im.save(dest, "JPEG", quality=82)
            return {"ok": True, "img_id": rec["img_id"]}
        except Exception as e:  # noqa: BLE001
            if "429" in str(e):
                time.sleep(30 * (attempt + 1))
                continue
            if attempt < 2:
                time.sleep(5)
                continue
            return {"ok": False, "img_id": rec["img_id"], "err": str(e)[:100]}
    return {"ok": False, "img_id": rec["img_id"], "err": "429 after retries"}


def main():
    raw = pd.read_csv(RAW)
    if "person_key" not in raw.columns:
        raw["person_key"] = ""
    committed = set(raw.loc[raw["source"] == "commons", "source_id"].astype(str))
    committed_person = raw[raw["person_key"].fillna("").ne("") & (raw["source"] == "commons")]
    cands, downloaded = load_progress()
    ph = existing_phashes()
    nxt = max(int(i.split("_")[1]) for i in raw["img_id"]) + 1
    logf = open(API_LOG, "a")
    new_rows = []
    print(f"resume: next {nxt}, cands {len(cands)}, downloaded {len(downloaded)}", flush=True)

    for key, name, target, _events in CELEBS:
        have = int(committed_person["person_key"].eq(key).sum()) if len(committed_person) else 0
        have += sum(1 for c in cands.values()
                    if c.get("person_key") == key and c["fileid"] in downloaded)
        if have >= target:
            print(f"{name}: done {have}/{target}", flush=True)
            continue
        todo = [c for c in cands.values() if c.get("person_key") == key
                and c["fileid"] not in downloaded and c["fileid"] not in committed]
        todo = todo[: max(0, target - have)]
        for c in todo:
            c["img_id"] = f"img_{nxt:04d}"
            nxt += 1
        print(f"{name}: have {have}/{target}, downloading {len(todo)}", flush=True)
        ok = 0
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            it = ex.map(dl, todo)
            for res in it:
                rec = next(c for c in todo if c["img_id"] == res["img_id"])
                if not res["ok"]:
                    print(f"  skip {rec['title'][:40]}: {res.get('err')}", flush=True)
                    time.sleep(0.5)
                    continue
                p = IMGDIR / f"{res['img_id']}.jpg"
                if not p.exists():
                    continue
                try:
                    Image.open(p).verify()
                except Exception:
                    p.unlink(missing_ok=True)
                    continue
                if imagehash is not None:
                    h = imagehash.phash(Image.open(p), hash_size=16)
                    if any(abs(h - h2) <= 5 for h2 in ph.values()):
                        p.unlink(missing_ok=True)
                        continue
                    ph[res["img_id"] + ".jpg"] = h
                logf.write(json.dumps({"fileid": rec["fileid"], "downloaded": True,
                                       "img_id": res["img_id"]}) + "\n")
                logf.flush()
                new_rows.append(rec)
                ok += 1
                time.sleep(0.4)
        print(f"{name}: +{ok} (total {have + ok}/{target})", flush=True)
    logf.close()

    if new_rows:
        add = pd.DataFrame([{
            "img_id": r["img_id"], "filename": f'{r["img_id"]}.jpg', "event_id": r["event_id"],
            "query": r["person_key"], "source": "commons", "source_id": r["fileid"],
            "title": r["title"], "creator": r["artist"], "creator_url": r["filepage"],
            "license": r["license"].lower().replace(" ", "-"), "license_url": r["license_url"],
            "source_url": r["filepage"], "deleted": False, "delete_reason": "",
            "person_key": r["person_key"],
        } for r in new_rows])
        add = add.reindex(columns=list(raw.columns))
        raw = pd.concat([raw, add], ignore_index=True)
        raw.to_csv(RAW, index=False)
        with open(BASE / "library" / "ATTRIBUTION.md", "a") as f:
            for r in sorted(new_rows, key=lambda x: x["img_id"]):
                f.write(f"- {r['img_id']} — {r['title']} · {r['artist']} · "
                        f"[{r['license']}]{r['license_url']} · {r['filepage']}\n")
    raw2 = pd.read_csv(RAW)
    nd = raw2[~raw2.deleted]
    pk = raw2["person_key"].fillna("")
    print("RESUME DONE. non-deleted:", len(nd), "| celebrity rows:", int((pk != "").sum()))
    print(nd.event_id.value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
