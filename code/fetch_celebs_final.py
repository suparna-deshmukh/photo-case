"""M1b-final — paced single-writer celebrity fetch (Commons, search-based category discovery).

- Per person: search namespace-14 (Categories) for the person's name, keep all
  matching categories (incl. "by year"/"by decade" trees -> descend one level),
  collect files, batch imageinfo, license/size filter, paced downloads.
- Correct per-person counting (committed CSV rows only).
- Single download worker, 2.0s interval; on 429 a 120s global pause (max 6/person).
- Appends to images_raw.csv exactly once, at the end. Cleans orphan files at start.

Usage: .venv/bin/python code/fetch_celebs_final.py [name_filter ...]
"""
import hashlib
import io
import json
import random
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_celebrities import (BAD_TITLE, CELEBS, IMGDIR, RAW, UA, license_ok,  # noqa: E402
                               pick_event)

try:
    import imagehash
except ImportError:
    imagehash = None

BASE = Path(__file__).resolve().parent.parent
LIB = BASE / "library"
API = "https://commons.wikimedia.org/w/api.php"
PACE = 2.5
PAUSE_429 = 120.0
MAX_PAIUSES_PER_PERSON = 3
MAX_CATS = 25


def api(params, tries=4):
    for attempt in range(tries):
        try:
            r = requests.get(API, params=params, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  api err: {e}", flush=True)
            time.sleep(10)
    return None


def norm(s):
    return re.sub(r"\s+", "", str(s).lower())


def person_categories(name):
    data = api({"action": "query", "format": "json", "list": "search",
                "srnamespace": "14", "srlimit": "50", "srsearch": name})
    time.sleep(2.0)
    cats = []
    if data:
        want = norm(name)
        for r in data.get("query", {}).get("search", []):
            t = r["title"]
            base = t.split(":", 1)[1] if ":" in t else t
            if want in norm(base) or norm(base) in want:
                cats.append(t)
    # descend one level for tree categories
    extra = []
    for c in list(cats):
        base = c.split(":", 1)[1]
        if re.search(r"by (year|decade)$|family$", base, re.I):
            d2 = api({"action": "query", "format": "json", "list": "categorymembers",
                      "cmtitle": c, "cmlimit": "100", "cmtype": "subcat"})
            time.sleep(2.0)
            if d2:
                extra += [m["title"] for m in d2.get("query", {}).get("categorymembers", [])]
    for c in extra:
        if c not in cats:
            cats.append(c)
    return cats[:MAX_CATS]


def category_files(cat):
    data = api({"action": "query", "format": "json", "list": "categorymembers",
                "cmtitle": cat, "cmlimit": "500", "cmtype": "file"})
    time.sleep(1.5)
    if not data:
        return []
    return [m["title"] for m in data.get("query", {}).get("categorymembers", [])]


def imageinfo_batch(titles):
    out = []
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        data = api({"action": "query", "format": "json", "titles": "|".join(chunk),
                    "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
                    "iiurlwidth": "1000"})
        time.sleep(1.5)
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
    raw = pd.read_csv(RAW)
    if "person_key" not in raw.columns:
        raw["person_key"] = ""
    committed = set(raw.loc[raw["source"] == "commons", "source_id"].astype(str))
    committed_person = raw[raw["person_key"].fillna("").ne("") & (raw["source"] == "commons")]

    # clean orphans (files on disk without a CSV row)
    known = set(raw["filename"].astype(str))
    for f in IMGDIR.glob("img_*.jpg"):
        if f.name not in known:
            f.unlink()
            print(f"orphan removed: {f.name}", flush=True)

    ph = {}
    for f in raw["filename"].astype(str):
        p = IMGDIR / f
        if p.exists():
            try:
                ph[f] = imagehash.phash(Image.open(p), hash_size=16)
            except Exception:
                pass

    # leftover candidate pool from earlier runs
    pool = []
    downloaded = {}
    cjsonl = LIB / "m1b_api.jsonl"
    csv_ids = set(raw["img_id"])
    if cjsonl.exists():
        for line in cjsonl.read_text().splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "thumburl" in rec:
                pool.append(rec)
            elif rec.get("downloaded") and rec.get("img_id") in csv_ids:
                downloaded[rec["fileid"]] = rec["img_id"]

    nxt = max(int(i.split("_")[1]) for i in raw["img_id"]) + 1
    new_rows = []
    summary = []
    for key, name, target, events in CELEBS:
        if names and name not in names:
            continue
        have = int(committed_person["person_key"].eq(key).sum()) if len(committed_person) else 0
        if have >= target:
            print(f"{name}: done {have}/{target}", flush=True)
            summary.append((name, have, target))
            continue
        need = target - have
        print(f"{name}: have {have}/{target}, need {need}", flush=True)

        rng = random.Random(int(hashlib.md5(key.encode()).hexdigest()[:8], 16))
        cands = [c for c in pool
                 if c.get("person_key") == key and c["fileid"] not in downloaded
                 and c["fileid"] not in committed]
        seen_ids = {c["fileid"] for c in cands}
        if len(cands) < need:
            cats = person_categories(name)
            print(f"  categories: {len(cats)} -> {[c.split(':',1)[1] for c in cats[:6]]}...", flush=True)
            files = []
            for c in cats:
                files += category_files(c)
            files = list(dict.fromkeys(files))[:1200]
            infos = imageinfo_batch(files)
            print(f"  files {len(files)}, usable {len(infos)}", flush=True)
            for c in infos:
                if c["fileid"] in seen_ids or c["fileid"] in committed:
                    continue
                c["person_key"] = key
                c["event_id"] = pick_event(events, random.Random(int(
                    hashlib.md5((key + "_" + c["fileid"]).encode()).hexdigest()[:8], 16)))
                seen_ids.add(c["fileid"])
                cands.append(c)
        rng.shuffle(cands)
        todo = cands[:min(need, 100)]  # per-pass cap; re-run later for the rest

        ok = 0
        pauses = 0
        for c in todo:
            if ok >= need or pauses > MAX_PAIUSES_PER_PERSON:
                break
            c["img_id"] = f"img_{nxt:04d}"
            nxt += 1
            dest = IMGDIR / f"{c['img_id']}.jpg"
            got = False
            for attempt in range(3):
                try:
                    r = requests.get(c.get("thumburl") or c["url"],
                                     headers={"User-Agent": UA}, timeout=60)
                    if r.status_code == 429:
                        pauses += 1
                        print(f"  429, global pause {PAUSE_429:.0f}s "
                              f"(pauses {pauses}/{MAX_PAIUSES_PER_PERSON})", flush=True)
                        if pauses > MAX_PAIUSES_PER_PERSON:
                            break
                        time.sleep(PAUSE_429)
                        continue
                    r.raise_for_status()
                    im = Image.open(io.BytesIO(r.content)).convert("RGB")
                    if max(im.size) > 800:
                        im.thumbnail((800, 800), Image.LANCZOS)
                    im.save(dest, "JPEG", quality=82)
                    got = True
                    break
                except Exception as e:  # noqa: BLE001
                    if attempt < 2:
                        time.sleep(8)
                    else:
                        print(f"  skip {c['title'][:40]}: {str(e)[:80]}", flush=True)
            if not got:
                dest.unlink(missing_ok=True)
                continue
            try:
                Image.open(dest).verify()
            except Exception:
                dest.unlink(missing_ok=True)
                continue
            if imagehash is not None:
                h = imagehash.phash(Image.open(dest), hash_size=16)
                if any(abs(h - h2) <= 5 for h2 in ph.values()):
                    dest.unlink(missing_ok=True)
                    continue
                ph[c["img_id"] + ".jpg"] = h
            new_rows.append(c)
            ok += 1
            time.sleep(PACE)
        print(f"{name}: +{ok} (now ~{have + ok}/{target})", flush=True)
        summary.append((name, have + ok, target))
        time.sleep(20)
        if new_rows:
            add = pd.DataFrame([{
                "img_id": c["img_id"], "filename": f'{c["img_id"]}.jpg', "event_id": c["event_id"],
                "query": c["person_key"], "source": "commons", "source_id": c["fileid"],
                "title": c["title"], "creator": c["artist"], "creator_url": c["filepage"],
                "license": c["license"].lower().replace(" ", "-"), "license_url": c["license_url"],
                "source_url": c["filepage"], "deleted": False, "delete_reason": "",
                "person_key": c["person_key"],
            } for c in new_rows])
            add = add.reindex(columns=list(raw.columns))
            raw = pd.concat([raw, add], ignore_index=True)
            raw.to_csv(RAW, index=False)
            with open(LIB / "ATTRIBUTION.md", "a") as f:
                for c in sorted(new_rows, key=lambda x: x["img_id"]):
                    f.write(f"- {c['img_id']} — {c['title']} · {c['artist']} · "
                            f"[{c['license']}]{c['license_url']} · {c['filepage']}\n")
            committed |= {str(c["fileid"]) for c in new_rows}
            new_rows = []

    raw2 = pd.read_csv(RAW)
    nd = raw2[~raw2.deleted]
    pk = raw2["person_key"].fillna("")
    print("FINAL DONE. non-deleted:", len(nd), "| celebrity rows:", int((pk != "").sum()))
    for n, h, t in summary:
        print(f"  {n}: {h}/{t}")


if __name__ == "__main__":
    main()
