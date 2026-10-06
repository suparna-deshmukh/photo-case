"""M1b — add ~1,000 freely-licensed photos of recognizable public figures.

These proxy the 'people who appear repeatedly' in a personal library so the
face-grouping feature has clean, identifiable clusters. Source: Wikimedia
Commons only (CC0 / CC BY / CC BY-SA / Public domain), same rules as M1.
Person identity is recorded in images_raw.csv person_key (internal ground
truth; the app shows anonymized 'Person N' labels).

Usage: .venv/bin/python code/fetch_celebrities.py   (resume-safe)
"""
import concurrent.futures as cf
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

try:
    import imagehash
except ImportError:
    imagehash = None

BASE = Path(__file__).resolve().parent.parent
LIB = BASE / "library"
RAW = LIB / "images_raw.csv"
API_LOG = LIB / "m1b_api.jsonl"
IMGDIR = LIB / "images"
UA = "photo-retrieval-research/0.2 (student case study)"
API = "https://commons.wikimedia.org/w/api.php"

CELEBS = [
    ("hrithik_roshan", "Hrithik Roshan", 200,
     {"e13": .22, "e02": .10, "e04": .12, "e05": .06, "e06": .10, "e08": .10,
      "e09": .12, "e10": .08, "e11": .05, "e03": .05, "e07": .03, "e12": .03, "e01": .04}),
    ("shahrukh_khan", "Shah Rukh Khan", 140,
     {"e04": .18, "e06": .16, "e08": .16, "e10": .16, "e11": .14, "e13": .20}),
    ("aamir_khan", "Aamir Khan", 110,
     {"e02": .18, "e05": .16, "e09": .18, "e13": .30, "e01": .18}),
    ("dwayne_johnson", "Dwayne Johnson", 90,
     {"e04": .22, "e10": .22, "e11": .18, "e13": .28, "e06": .10}),
    ("priyanka_chopra", "Priyanka Chopra", 100,
     {"e03": .18, "e04": .16, "e08": .16, "e12": .18, "e13": .32}),
    ("deepika_padukone", "Deepika Padukone", 90,
     {"e04": .20, "e06": .16, "e08": .16, "e10": .14, "e13": .34}),
    ("aishwarya_rai", "Aishwarya Rai", 70,
     {"e03": .22, "e12": .22, "e13": .38, "e08": .18}),
    ("sachin_tendulkar", "Sachin Tendulkar", 70,
     {"e01": .20, "e02": .20, "e05": .14, "e11": .16, "e13": .30}),
    ("tom_hanks", "Tom Hanks", 60,
     {"e06": .24, "e08": .24, "e09": .22, "e13": .30}),
    ("keanu_reeves", "Keanu Reeves", 50,
     {"e06": .26, "e10": .24, "e13": .50}),
    ("robert_downey_jr", "Robert Downey Jr.", 50,
     {"e09": .30, "e11": .22, "e13": .48}),
    ("natalie_portman", "Natalie Portman", 40,
     {"e04": .28, "e08": .28, "e13": .44}),
]

LICENSE_OK = ("cc0", "cc by", "cc by-sa", "public domain", "pd")
BAD_TITLE = re.compile(r"poster|movie|film|teaser|trailer|album|book|cover|logo|flag|stamp|map", re.I)


def license_ok(short):
    s = (short or "").lower()
    if not s:
        return False
    if "nc" in s or "nd" in s:
        return False
    return any(s.startswith(p) for p in LICENSE_OK)


def pick_event(person_events, rng):
    items = list(person_events.items())
    total = sum(w for _, w in items)
    r = rng.random() * total
    acc = 0.0
    for eid, w in items:
        acc += w
        if r <= acc:
            return eid
    return items[-1][0]


def load_progress():
    cands, downloaded = {}, {}
    if API_LOG.exists():
        for line in API_LOG.read_text().splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "thumburl" in rec:
                cands[rec["fileid"]] = rec
            elif rec.get("downloaded") and "img_id" in rec:
                downloaded[rec["fileid"]] = rec["img_id"]
    return cands, downloaded


def commons_page(name, offset):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": "6", "gsrsearch": f'"{name}"', "gsrlimit": "50",
        "gsroffset": str(offset), "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": "1000",
    }
    for attempt in range(3):
        try:
            r = requests.get(API, params=params, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 429:
                time.sleep(8 * (attempt + 1))
                continue
            r.raise_for_status()
            pages = r.json().get("query", {}).get("pages", {})
            out = []
            for p in pages.values():
                ii = (p.get("imageinfo") or [{}])[0]
                ext = ii.get("extmetadata", {})
                lic = (ext.get("LicenseShortName", {}).get("value") or "")
                title = p.get("title", "")
                if ii.get("mime") != "image/jpeg":
                    continue
                if (ii.get("width") or 0) < 800:
                    continue
                if not license_ok(lic):
                    continue
                if BAD_TITLE.search(title):
                    continue
                artist = re.sub(r"<[^>]+>", "", (ext.get("Artist", {}).get("value") or "")).strip()
                out.append({
                    "fileid": str(p.get("pageid")), "title": title.replace("File:", ""),
                    "thumburl": ii.get("thumburl"), "url": ii.get("url"),
                    "license": lic, "license_url": ext.get("LicenseUrl", {}).get("value") or "",
                    "artist": artist,
                    "filepage": f"https://commons.wikimedia.org/wiki/File:{title}",
                })
            return out
        except Exception as e:  # noqa: BLE001
            print(f"  api error offset={offset}: {e}", flush=True)
            time.sleep(4)
    return []


def existing_phashes():
    raw = pd.read_csv(RAW)
    raw["filename"] = raw["filename"].astype(str)
    hashes = {}
    if imagehash is None:
        return hashes
    for f in raw["filename"]:
        p = IMGDIR / f
        if p.exists():
            try:
                hashes[f] = imagehash.phash(Image.open(p), hash_size=16)
            except Exception:
                pass
    return hashes


def download_one(rec):
    dest = IMGDIR / f"{rec['img_id']}.jpg"
    last_err = ""
    for url in (rec.get("thumburl"), rec.get("url")):
        if not url:
            continue
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if max(im.size) > 800:
                im.thumbnail((800, 800), Image.LANCZOS)
            im.save(dest, "JPEG", quality=82)
            return {"ok": True, "img_id": rec["img_id"]}
        except Exception as e:  # noqa: BLE001
            last_err = str(e)[:120]
    return {"ok": False, "img_id": rec["img_id"], "err": last_err}


def main():
    raw = pd.read_csv(RAW)
    if "person_key" not in raw.columns:
        raw["person_key"] = ""
    committed = set(raw.loc[raw["source"] == "commons", "source_id"].astype(str)) \
        if "source_id" in raw.columns else set()
    committed_person = raw[raw.get("person_key", pd.Series(dtype=str)).fillna("").ne("") \
                           & (raw["source"] == "commons")].copy() \
        if len(raw) else raw.iloc[0:0]
    cands, downloaded = load_progress()
    ph = existing_phashes()
    nxt = max(int(i.split("_")[1]) for i in raw["img_id"]) + 1
    print(f"start: next id {nxt}, phashes {len(ph)}, api cands {len(cands)}, "
          f"downloaded {len(downloaded)}, committed {len(committed)}", flush=True)

    logf = open(API_LOG, "a")
    new_rows = []
    for key, name, target, events in CELEBS:
        have = sum((committed_person["person_key"] == key).sum()
                   for _ in [0]) if len(committed_person) else 0
        have = int(committed_person["person_key"].eq(key).sum()) if len(committed_person) else 0
        have += sum(1 for c in cands.values() if c.get("person_key") == key and c["fileid"] in downloaded)
        if have >= target:
            print(f"{name}: already at {have} >= {target}", flush=True)
            continue
        rng = random.Random(int(hashlib.md5(key.encode()).hexdigest()[:8], 16))
        offset = 0
        while True:
            mine = [c for c in cands.values() if c.get("person_key") == key
                    and c["fileid"] not in downloaded]
            if len(mine) >= target - have or offset >= 500:
                break
            for c in commons_page(name, offset):
                if c["fileid"] in cands or c["fileid"] in committed:
                    continue
                c["person_key"] = key
                c["event_id"] = pick_event(events, rng)
                cands[c["fileid"]] = c
                logf.write(json.dumps(c) + "\n")
            logf.flush()
            offset += 50
            time.sleep(1.2)
        to_dl = [c for c in cands.values() if c.get("person_key") == key
                 and c["fileid"] not in downloaded][:max(0, target - have)]
        for c in to_dl:
            c["img_id"] = f"img_{nxt:04d}"
            nxt += 1
        print(f"{name}: have {have}, downloading {len(to_dl)}", flush=True)
        ok = 0
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for res in ex.map(download_one, to_dl):
                rec = next(c for c in to_dl if c["img_id"] == res["img_id"])
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
        print(f"{name}: +{ok} (total {have + ok})", flush=True)
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
        cols = list(raw.columns)
        add = add.reindex(columns=cols)
        raw = pd.concat([raw, add], ignore_index=True)
        raw.to_csv(RAW, index=False)
        with open(LIB / "ATTRIBUTION.md", "a") as f:
            f.write("\n## Celebrity set (face-grouping demo, fetched 2026-10-06)\n\n")
            for r in sorted(new_rows, key=lambda x: x["img_id"]):
                f.write(f"- {r['img_id']} — {r['title']} · {r['artist']} · "
                        f"[{r['license']}]{r['license_url']} · {r['filepage']}\n")
    raw2 = pd.read_csv(RAW)
    nd = raw2[~raw2.deleted]
    pk = raw2["person_key"].fillna("") if "person_key" in raw2.columns else ""
    print("DONE. non-deleted:", len(nd), "| celebrity rows:", int((pk != "").sum()))
    print(nd.event_id.value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
