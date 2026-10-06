"""M1b-2 — deep fetch via Commons categories for persons short of target.

Enumerates Category:<Name> (+ 1 level of subcategories), batch-queries
imageinfo, applies the same license/size filters, appends candidates to
m1b_api.jsonl, then downloads with Wikimedia-friendly pacing.
Usage: .venv/bin/python code/fetch_celebrities_deep.py [name_filter ...]
"""
import concurrent.futures as cf
import hashlib
import io
import json
import random
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_celebrities import (BAD_TITLE, IMGDIR, RAW, UA, license_ok,  # noqa: E402
                               pick_event)
from fetch_celebrities_resume import dl  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"


def api(params):
    for attempt in range(4):
        try:
            r = requests.get(API, params=params, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 429:
                time.sleep(20 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  api err: {e}", flush=True)
            time.sleep(8)
    return None


def category_files(cat):
    files = []
    data = api({"action": "query", "format": "json", "list": "categorymembers",
                "cmtitle": cat, "cmlimit": "500", "cmtype": "file"})
    if data:
        files += [m["title"] for m in data.get("query", {}).get("categorymembers", [])]
    subs = []
    data = api({"action": "query", "format": "json", "list": "categorymembers",
                "cmtitle": cat, "cmlimit": "100", "cmtype": "subcat"})
    if data:
        subs += [m["title"] for m in data.get("query", {}).get("categorymembers", [])]
        for s in subs[:8]:
            time.sleep(1.2)
            d2 = api({"action": "query", "format": "json", "list": "categorymembers",
                      "cmtitle": s, "cmlimit": "500", "cmtype": "file"})
            if d2:
                files += [m["title"] for m in d2.get("query", {}).get("categorymembers", [])]
    return files[:400]


def imageinfo_batch(titles):
    out = []
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        data = api({"action": "query", "format": "json", "titles": "|".join(chunk),
                    "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
                    "iiurlwidth": "1000"})
        time.sleep(1.2)
        if not data:
            continue
        for p in data.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            ext = ii.get("extmetadata", {})
            lic = (ext.get("LicenseShortName", {}).get("value") or "")
            title = p.get("title", "")
            if ii.get("mime") != "image/jpeg" or (ii.get("width") or 0) < 800:
                continue
            if not license_ok(lic) or BAD_TITLE.search(title):
                continue
            import re
            artist = re.sub(r"<[^>]+>", "", (ext.get("Artist", {}).get("value") or "")).strip()
            out.append({
                "fileid": str(p.get("pageid")), "title": title.replace("File:", ""),
                "thumburl": ii.get("thumburl"), "url": ii.get("url"),
                "license": lic, "license_url": ext.get("LicenseUrl", {}).get("value") or "",
                "artist": artist,
                "filepage": f"https://commons.wikimedia.org/wiki/{title}",
            })
    return out


def main():
    names = sys.argv[1:] or None
    from fetch_celebrities import CELEBS
    raw = pd.read_csv(RAW)
    if "person_key" not in raw.columns:
        raw["person_key"] = ""
    committed = set(raw.loc[raw["source"] == "commons", "source_id"].astype(str))
    committed_person = raw[raw["person_key"].fillna("").ne("") & (raw["source"] == "commons")]
    LIB = BASE / "library"
    seen, downloaded = set(), {}
    cand_key = {}
    if (LIB / "m1b_api.jsonl").exists():
        for line in (LIB / "m1b_api.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "thumburl" in rec:
                seen.add(rec["fileid"])
                cand_key[rec["fileid"]] = rec.get("person_key", "")
            elif rec.get("downloaded") and "img_id" in rec:
                downloaded[rec["fileid"]] = rec["img_id"]
    nxt = max(int(i.split("_")[1]) for i in raw["img_id"]) + 1
    logf = open(LIB / "m1b_api.jsonl", "a")
    import imagehash
    all_cands = [json.loads(l) for l in (LIB / "m1b_api.jsonl").read_text().splitlines()
                 if l.strip() and '"thumburl"' in l]
    ph = {}
    for f in raw["filename"].astype(str):
        p = IMGDIR / f
        if p.exists():
            try:
                ph[f] = imagehash.phash(Image.open(p), hash_size=16)
            except Exception:
                pass

    new_rows = []
    for key, name, target, events in CELEBS:
        if names and name not in names:
            continue
        have = int(committed_person["person_key"].eq(key).sum()) if len(committed_person) else 0
        have += sum(1 for fid in downloaded if cand_key.get(fid) == key)
        if have >= target:
            print(f"{name}: already {have}/{target}, skip", flush=True)
            continue
        print(f"{name}: have {have}/{target}, deep-fetching category…", flush=True)
        files = category_files(f"Category:{name}")
        print(f"  {len(files)} files in category tree", flush=True)
        infos = imageinfo_batch(files)
        print(f"  {len(infos)} usable candidates", flush=True)
        rng = random.Random(int(hashlib.md5((key + "_deep").encode()).hexdigest()[:8], 16))
        ok_prev = 0
        for c in infos:
            if c["fileid"] in seen or c["fileid"] in committed:
                continue
            c["person_key"] = key
            c["event_id"] = pick_event(events, rng)
            seen.add(c["fileid"])
            cand_key[c["fileid"]] = key
            all_cands.append(c)
            logf.write(json.dumps(c) + "\n")
            if have + ok_prev + sum(1 for x in all_cands
                                    if x.get("person_key") == key and x["fileid"] not in downloaded
                                    and x["fileid"] not in committed) >= target:
                break
        logf.flush()
        # download the new ones (paced, reuse dl())
        todo = [c for c in all_cands if c.get("person_key") == key
                and c["fileid"] not in downloaded and c["fileid"] not in committed]
        todo = todo[: max(0, target - have - ok_prev)]
        for c in todo:
            c["img_id"] = f"img_{nxt:04d}"
            nxt += 1
        ok = 0
        if todo:
            with cf.ThreadPoolExecutor(max_workers=2) as ex:
                for res in ex.map(dl, todo):
                    rec = next(c for c in todo if c["img_id"] == res["img_id"])
                    if not res["ok"]:
                        print(f"  skip {rec['title'][:40]}: {res.get('err')}", flush=True)
                        continue
                    p = IMGDIR / f"{res['img_id']}.jpg"
                    if not p.exists():
                        continue
                    try:
                        Image.open(p).verify()
                    except Exception:
                        p.unlink(missing_ok=True)
                        continue
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
        print(f"{name}: +{ok} via category (have ~{have + ok}/{target})", flush=True)
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
        with open(LIB / "ATTRIBUTION.md", "a") as f:
            for r in sorted(new_rows, key=lambda x: x["img_id"]):
                f.write(f"- {r['img_id']} — {r['title']} · {r['artist']} · "
                        f"[{r['license']}]{r['license_url']} · {r['filepage']}\n")
    raw2 = pd.read_csv(RAW)
    nd = raw2[~raw2.deleted]
    pk = raw2["person_key"].fillna("")
    print("DEEP DONE. non-deleted:", len(nd), "| celebrity rows:", int((pk != "").sum()))


if __name__ == "__main__":
    main()
