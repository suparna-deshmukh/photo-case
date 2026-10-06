"""
M1 — Build the Jog demo image library (keyless: Openverse primary, Wikimedia Commons top-up).

Outputs:
  library/events.csv            (exact 13 event rows)
  library/images/img_NNNN.jpg   (longest side <= 800, JPEG q82)
  library/images_raw.csv        (img_id, filename, event_id, query, source, source_id,
                                 title, creator, creator_url, license, license_url,
                                 source_url, deleted, delete_reason)
  library/ATTRIBUTION.md
  library/contact_sheets/contact_eXX.png
Resume-safe: cache/m1_api.jsonl (per query), cache/m1_dl/ (downloaded originals),
             cache/m1_screen.jsonl (per img_id).

Usage: .venv/bin/python code/build_library.py [--skip-screen]
"""
import csv
import io
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageOps
import imagehash

BASE = Path(__file__).resolve().parent.parent
LIB = BASE / "library"
IMAGES = LIB / "images"
SHEETS = LIB / "contact_sheets"
CACHE = BASE / "cache"
DL_DIR = CACHE / "m1_dl"
EVENTS_CSV = LIB / "events.csv"
RAW_CSV = LIB / "images_raw.csv"
ATTR = LIB / "ATTRIBUTION.md"
API_LOG = CACHE / "m1_api.jsonl"
SCR_LOG = CACHE / "m1_screen.jsonl"

UA = "photo-retrieval-research/0.1 (student project)"
SLEEP_API = 1.2
MAX_SIDE = 800
JPEG_Q = 82

EVENTS = [
    ("e01","Orientation week","2022-08-02","2022-08-08","Zuarinagar Goa",15.391,73.878,125,"university campus building|dorm room|students group photo|college entrance|hostel corridor|university library interior|campus lawn students|dorm room desk|college classroom|hostel corridor window|university gate evening|campus canteen food|college building facade|students walking campus|hostel bunk beds|university building|empty classroom desks|library shelves books|student backpack|campus path trees|college building arch|university students walking|dorm room bed"),
    ("e02","Hostel life and fests","2022-09-10","2022-11-05","Zuarinagar Goa",15.391,73.878,160,"college festival lights|students studying night|canteen food|friends laughing indoors|street food night|indian street food stall|hostel bunk beds room|students laptop study desk|college hostel corridor|indian college canteen|college fest stage|friends cards night|mess hall food tray|college notice board|hostel desk lamp|college football field|friends walking campus night|college library reading|friends table food|student desk lamp|indian food curry|group friends talking|hostel bed blanket|string lights room|friends cards game|mess food tray|students reading library|football field"),
    ("e03","Diwali at home","2022-10-22","2022-10-26","Pune",18.5204,73.8567,150,"diwali diyas|rangoli|indian family dinner|fireworks night|indian sweets|marigold garland|diya row lit|ladoo sweets|fireworks over city|family puja diya|indian sweets plate|diya festival night|rangoli colorful floor|diwali decoration|fireworks sky city|clay lamp flame|marigold flowers bunch|sweets dessert bowl|family eating dinner|house festival lights|incense stick smoke|colorful sweets plate|diya row table"),
    ("e04","Goa trip","2023-01-13","2023-01-16","Goa",15.4909,73.8278,275,"cafe table coffee morning|beach cafe|beach sunset palm|beach shack|scooter tropical road|seafood plate|friends on beach|cafe interior chairs|coffee latte cup|goa beach shack|palolem beach view|coffee cup cafe table|beach chair sunset|seafood curry rice|beach walk footprints|cafe terrace sea|scooter tropical|cafe breakfast table|beach sunset sea|coastal road palm|cafe window table|latte art coffee|beach palm tree|seafood bowl rice|friends sunset beach|scooter road tropical"),
    ("e05","Exam season","2023-04-20","2023-05-10","Zuarinagar Goa",15.391,73.878,135,"whiteboard equations|handwritten notes notebook|library desk study|timetable schedule|coffee laptop night|study desk lamp|whiteboard formulas|exam hall desks|notebook highlighter|study group table|library reading desk|handwritten notes page|desk study coffee|timetable paper|study room night|notebook pen desk|classroom whiteboard|books stack|student library reading|desk calculator|window study night"),
    ("e06","Hampi trip","2023-09-08","2023-09-11","Hampi",15.335,76.46,215,"ancient ruins temple stone|boulders landscape|riverside cafe|coracle boat river|sunset ruins|friends cycling|hampi temple ruins|ancient stone chariot|hampi boulders|ancient stone temple india|hampi river|stone chariot monument|hampi sunset temple|river rocks hampi|sunset over boulders|ancient ruins india|hampi cycling road|stone gate hampi|coracle boat|boulder landscape sunrise|ancient stone ruins|red boulders|stone temple pillars|wooden boat river|cycling road hills|sunset rocks river|temple ruins|boulder landscape|stone monument|river boulders"),
    ("e07","Sick week","2023-11-12","2023-11-19","Pune",18.5204,73.8567,90,"medicine tablets blister pack|prescription paper|thermometer|soup bowl|pharmacy|medicine blister pack|soup bowl spoon|thermometer digital|cough syrup bottle|pharmacy shelf|medicine bottle|sick day bed|bandaid plasters|pill bottle closeup|soup steam bowl|bed rest day|medicine cabinet home|herbal tea"),
    ("e08","Pondicherry trip","2024-02-09","2024-02-12","Pondicherry",11.9416,79.8083,220,"french quarter yellow buildings|promenade sea|cafe breakfast|rooftop restaurant dinner night|sunrise beach|colorful street bicycle|french colonial building|promenade palm trees|cafe terrace breakfast|rooftop dinner candle|beach sunrise promenade|pondicherry street|french quarter buildings|rooftop restaurant|french cafe table|bicycle promenade|yellow building street|seaside promenade|breakfast cafe|rooftop city night|quiet beach morning|bicycle street|colonial street|promenade sunset"),
    ("e09","Internship Bengaluru","2024-05-27","2024-07-26","Bengaluru",12.9716,77.5946,260,"office desk laptop|metro train|rooftop friends evening|cafe laptop|city street traffic|team lunch|office cubicle laptop|metro station crowd|rooftop evening friends|bengaluru traffic road|city skyline night|startup office desk|office meeting room|cafe laptop work|rooftop sunset city|metro platform|office laptop work|city traffic road|rooftop friends city|cafe coffee cup table|metro train platform|friends restaurant food|city skyline evening|office meeting people|street food stall|window city view"),
    ("e10","Gokarna trip","2025-01-10","2025-01-13","Gokarna",14.5479,74.3188,200,"beach sunset boat|beach bonfire night|cliff coastline|beach shack|friends walking beach|sunset boat sea|bonfire beach night|cliff coast view|boat sea sunset|coastal cliff path|gokarna beach|beach sunset palm|beach shack view|beach sunset|boat water calm|fire night beach|coast cliff|people walking beach|palm beach|ocean sunset|beach hut"),
    ("e11","Fest night","2025-03-14","2025-03-16","Zuarinagar Goa",15.391,73.878,160,"concert crowd lights|friends group selfie|stage lights night|dance students|concert crowd night|stage lights concert|band stage performance|crowd phone lights|neon lights night|festival crowd|concert stage|dance floor night|concert stage crowd|friends dancing party|crowd event|music festival|confetti party"),
    ("e12","Ganesh Chaturthi at home","2025-08-27","2025-08-31","Pune",18.5204,73.8567,150,"ganesh idol|flower decoration|family gathering festive|modak sweets|festival procession|marigold flower garland|indian sweets plate|diyas festival night|ganesha statue|ganpati|hindu puja diya|ganesh idol statue|modak sweet|puja diya lit|festival street procession|ganpati immersion|indian festival food|family puja home|ganesh festival|diya flame night|ganesha statue|oil lamp flame|sweets indian bowl|garland marigold|family puja|street festival|idol flowers|modak sweets plate|diyas table|home celebration"),
    ("e13","Everyday and utility","2022-08-01","2026-09-28","mixed","","",620,"receipt paper|train ticket|bus stop timetable|notebook page|cat|street dog|chai cup|bookshelf|bicycle|rainy window glass|paper map|passport document|ticket stub|tea glass|dog park|plant pot|shoes pair|headphones|umbrella|sunglasses pair|wristwatch|backpack|laptop on desk|phone on table|water bottle|park bench|city bridge|building staircase|coffee cup saucer|flowers vase|clouds sky|keys bunch|bus ticket|calendar wall|open book page|wall poster|desk lamp|stationery desk|balcony view city|kitchen window|old camera|vinyl record player|typewriter keys|wall clock|photo frame wall|fridge magnets|kitchen utensils|old radio|mirror reflection|doorway light|staircase spiral|office chair desk|chalkboard writing|compass map|tent camping|mountain trail|lake view|waterfall nature|fountain park|garden path|flower field|starry night sky|moon night|rain drops glass|sunrise city|sunset city skyline|neon sign shop|market stall|food stall street|street lamp night|lantern light|balloon party|birthday cake|gift box|candles cake|tea cup saucer|cat window|dog city street|bicycle parked|bookshelf living room|rain window pane|open notebook|shoes floor|headphones desk|umbrella street|keys table|window city view|house plant|vase flowers|market vendors"),
]

REWRITES = {
    "university campus building": "university building campus",
    "dorm room": "bedroom interior",
    "students group photo": "group of young friends outdoors",
    "college entrance": "college building entrance",
    "hostel corridor": "corridor hallway interior",
    "college festival lights": "festival lights night",
    "students studying night": "student studying desk lamp",
    "canteen food": "indian food plate",
    "friends laughing indoors": "friends talking indoors",
    "street food night": "street food stall",
    "diwali diyas": "diya clay lamp flame",
    "rangoli": "rangoli floor design",
    "indian family dinner": "family dinner table food",
    "fireworks night": "fireworks sky night",
    "indian sweets": "sweets dessert plate",
    "whiteboard equations": "whiteboard math writing",
    "handwritten notes notebook": "handwritten notes notebook",
    "library desk study": "library books reading desk",
    "timetable schedule": "timetable schedule paper",
    "coffee laptop night": "laptop coffee desk",
    "ancient ruins temple stone": "ancient stone ruins",
    "boulders landscape": "large boulders landscape",
    "riverside cafe": "river cafe",
    "coracle boat river": "small boat river",
    "sunset ruins": "sunset ancient stones",
    "friends cycling": "cycling road landscape",
    "medicine tablets blister pack": "medicine tablets",
    "prescription paper": "prescription paper document",
    "thermometer": "thermometer medicine",
    "soup bowl": "soup bowl food",
    "pharmacy": "pharmacy medicine shop",
    "french quarter yellow buildings": "yellow colonial buildings street",
    "promenade sea": "seafront promenade walk",
    "cafe breakfast": "breakfast cafe table",
    "rooftop restaurant dinner night": "rooftop restaurant night",
    "sunrise beach": "beach sunrise morning",
    "colorful street bicycle": "bicycle street colorful",
    "office desk laptop": "office desk computer work",
    "metro train": "metro train station",
    "rooftop friends evening": "city rooftop evening people",
    "cafe laptop": "cafe laptop working",
    "city street traffic": "city traffic street cars",
    "team lunch": "people lunch restaurant",
    "beach sunset boat": "sunset boat sea",
    "beach bonfire night": "beach bonfire night fire",
    "cliff coastline": "cliff coastline sea",
    "friends walking beach": "people walking beach",
    "concert crowd lights": "concert crowd night",
    "friends group selfie": "group of friends smiling",
    "stage lights night": "concert stage lights",
    "dance students": "people dancing event",
    "ganesh idol": "ganesh idol statue",
    "flower decoration": "flower decoration home",
    "family gathering festive": "family gathering festive",
    "modak sweets": "sweet dessert food",
    "festival procession": "festival procession street",
    "receipt paper": "receipt paper table",
    "train ticket": "train ticket paper",
    "bus stop timetable": "bus stop sign",
    "notebook page": "notebook page handwriting",
    "cat window": "cat window sill",
    "dog city street": "dog on street",
    "bicycle parked": "bicycle parked street",
    "bookshelf living room": "bookshelf books home",
    "rain window pane": "rain on window glass",
    "open notebook": "open notebook page",
    "shoes floor": "shoes on floor",
    "headphones desk": "headphones on desk",
    "umbrella street": "umbrella rain street",
    "keys table": "keys on table",
    "window city view": "balcony window city",
    "house plant": "potted plant home",
    "vase flowers": "flowers in vase",
    "market vendors": "market stall vendors",
    "tea cup saucer": "tea cup saucer table",
    "clay lamp flame": "diya clay lamp",
    "marigold flowers bunch": "marigold flowers",
    "ganesha statue": "ganesha idol statue",
    "oil lamp flame": "diya lamp flame",
    "sweets indian bowl": "indian sweets plate",
    "garland marigold": "marigold garland flowers",
    "idol flowers": "ganesha idol flowers",
    "modak sweets plate": "modak sweets",
    "family puja": "family puja diya",
    "street festival": "festival street celebration",
    "home celebration": "family celebration home",
    "university building": "university campus building",
    "empty classroom desks": "classroom desks empty",
    "library shelves books": "library bookshelves books",
    "student backpack": "backpack student bag",
    "campus path trees": "campus walkway trees",
    "college building arch": "college building entrance",
    "university students walking": "students walking university",
    "dorm room bed": "bedroom bed single",
    "friends table food": "friends food table",
    "student desk lamp": "desk lamp studying",
    "indian food curry": "indian curry food plate",
    "group friends talking": "group friends talking table",
    "hostel bed blanket": "bed room blanket",
    "string lights room": "string lights indoors",
    "friends cards game": "friends playing cards",
    "mess food tray": "food tray meal",
    "students reading library": "students library books",
    "football field": "football soccer field grass",
    "cafe window table": "cafe table window seat",
    "latte art coffee": "latte coffee cup",
    "beach palm tree": "beach palm trees",
    "seafood bowl rice": "seafood rice bowl",
    "friends sunset beach": "friends beach sunset",
    "scooter road tropical": "scooter tropical road",
    "notebook pen desk": "notebook pen on desk",
    "classroom whiteboard": "whiteboard classroom",
    "books stack": "stack of books",
    "student library reading": "student reading library",
    "desk calculator": "calculator desk papers",
    "window study night": "study desk window night",
    "ancient stone ruins": "ancient ruins stones",
    "red boulders": "large red boulders",
    "stone temple pillars": "ancient stone pillars",
    "wooden boat river": "small wooden boat river",
    "cycling road hills": "cycling scenic road",
    "sunset rocks river": "sunset rocks river",
    "temple ruins": "ancient temple ruins",
    "boulder landscape": "boulders landscape",
    "stone monument": "ancient stone monument",
    "river boulders": "river with boulders",
    "pill bottle closeup": "pill bottle medicine",
    "soup steam bowl": "hot soup bowl",
    "bed rest day": "bed rest bedroom",
    "medicine cabinet home": "medicine cabinet",
    "herbal tea": "herbal tea cup",
    "yellow building street": "yellow buildings street",
    "seaside promenade": "seafront promenade",
    "breakfast cafe": "breakfast cafe table",
    "rooftop city night": "rooftop city night view",
    "quiet beach morning": "empty beach morning",
    "bicycle street": "bicycle on street",
    "colonial street": "colonial buildings street",
    "promenade sunset": "promenade sunset walk",
    "office laptop work": "office desk laptop work",
    "city traffic road": "city traffic road cars",
    "rooftop friends city": "rooftop friends city evening",
    "cafe coffee cup table": "coffee cup cafe table",
    "metro train platform": "metro train station",
    "friends restaurant food": "friends restaurant dinner",
    "city skyline evening": "city skyline evening",
    "office meeting people": "office meeting room people",
    "street food stall": "street food stall india",
    "beach sunset": "sunset beach sea",
    "boat water calm": "boat calm water",
    "fire night beach": "beach bonfire night",
    "coast cliff": "coastline cliff sea",
    "people walking beach": "people walking on beach",
    "palm beach": "beach palm trees sunset",
    "ocean sunset": "sunset over ocean",
    "beach hut": "beach shack hut",
    "concert stage crowd": "concert crowd stage",
    "friends dancing party": "friends dancing party",
    "crowd event": "event crowd night",
    "music festival": "music festival crowd",
    "confetti party": "party confetti",
    "chai cup": "tea cup chai",
}

ALLOWED_OV_LICENSES = {"cc0", "pdm", "by", "by-sa"}

def ts():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def log(msg):
    print(f"{ts()} {msg}", flush=True)

def read_jsonl(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out

def append_jsonl(path, obj):
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")

def commons_license_ok(lic_value):
    lic = re.sub(r"\s+", " ", (lic_value or "")).strip()
    if not lic:
        return False
    up = lic.upper().replace(" ", "")
    if "NC" in up or "ND" in up:
        return False
    if lic == "CC0" or lic.startswith("Public domain"):
        return True
    return lic.startswith("CC BY")

def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()

def _ov_get(query, page):
    time.sleep(SLEEP_API)
    r = requests.get(
        "https://api.openverse.org/v1/images/",
        params={"q": query, "license": "cc0,pdm,by,by-sa", "category": "photograph",
                "extension": "jpg", "page_size": 20, "page": page},
        headers={"User-Agent": UA}, timeout=40)
    if r.status_code == 429:
        log(f"  OV {query!r} p{page} 429 -> backoff 60s, retry once")
        time.sleep(60)
        r = requests.get(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "license": "cc0,pdm,by,by-sa", "category": "photograph",
                    "extension": "jpg", "page_size": 20, "page": page},
            headers={"User-Agent": UA}, timeout=40)
    return r

def fetch_openverse(query, pages_max=4, start=1):
    out = []
    last_err = None
    for page in range(start, pages_max + 1):
        try:
            r = _ov_get(query, page)
        except Exception as e:
            last_err = f"net {str(e)[:120]}"
            log(f"  OV {query!r} p{page} net error: {last_err}")
            break
        if r.status_code != 200:
            last_err = f"http {r.status_code} {r.text[:200]}"
            log(f"  OV {query!r} p{page} status={r.status_code} body={r.text[:200]!r}")
            break
        try:
            data = r.json()
        except Exception:
            last_err = f"not json: {r.text[:200]!r}"
            log(f"  OV {query!r} p{page} {last_err}")
            break
        results = data.get("results", [])
        if not results:
            break
        for it in results:
            w, h = it.get("width"), it.get("height")
            if w is not None and h is not None and (int(w) < 800 or int(h) < 500):
                continue
            lic = (it.get("license") or "").lower()
            if lic and lic not in ALLOWED_OV_LICENSES:
                continue
            out.append({
                "source": "openverse",
                "source_id": it.get("id"),
                "title": it.get("title") or "",
                "creator": it.get("creator") or "",
                "creator_url": it.get("creator_url") or "",
                "license": it.get("license") or "unknown",
                "license_version": it.get("license_version") or "",
                "license_url": it.get("license_url") or "",
                "foreign_landing_url": it.get("foreign_landing_url") or "",
                "provider": it.get("provider") or "",
                "url": it.get("url") or "",
                "thumb": it.get("thumbnail") or "",
            })
        if len(results) < 20:
            break
    return out, last_err

def fetch_commons(query, pages_max=3, start=1):
    out = []
    last_err = None
    for page in range(start, pages_max + 1):
        if page > start:
            time.sleep(SLEEP_API)
        params = {
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": 20, "sroffset": 20 * (page - 1),
            "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1000,
        }
        try:
            r = requests.get("https://commons.wikimedia.org/w/api.php", params=params,
                             headers={"User-Agent": UA}, timeout=40)
            data = r.json()
        except Exception as e:
            last_err = f"net {str(e)[:120]}"
            log(f"  WC {query!r} p{page} error: {last_err}")
            break
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            break
        for p in pages.values():
            ii = (p.get("imageinfo") or [{}])[0]
            if ii.get("mime") != "image/jpeg":
                continue
            if not ii.get("width") or int(ii["width"]) < 800:
                continue
            em = ii.get("extmetadata", {})
            lic_val = strip_html(em.get("LicenseShortName", {}).get("value", ""))
            if not commons_license_ok(lic_val):
                continue
            artist = strip_html(em.get("Artist", {}).get("value", ""))
            fname = p.get("title", "").replace("File:", "")
            out.append({
                "source": "commons",
                "source_id": re.sub(r"\.(jpg|jpeg|JPG)$", "", fname)[:120],
                "title": fname[:160],
                "creator": artist,
                "creator_url": "",
                "license": lic_val,
                "license_version": "",
                "license_url": em.get("LicenseUrl", {}).get("value", "") or "",
                "foreign_landing_url": p.get("fullurl", ""),
                "provider": "wikimedia-commons",
                "url": ii.get("thumburl") or ii.get("url") or "",
                "thumb": ii.get("url") or "",
            })
        if len(pages) < 20:
            break
    return out, last_err

def _depth_pages(deep):
    """(ov_start, ov_max, cm_start, cm_max, rw_ov_start, rw_ov_max) per depth."""
    if deep <= 0:
        return 1, 4, 1, 3, 1, 3
    if deep == 1:
        return 3, 7, 3, 6, 2, 5
    return 8, 14, 6, 10, 4, 7

def fetch_query(query, need, deep=0):
    """Fetch candidates for one query. deep=0 shallow, 1 mid pages, 2 deep pages."""
    seen = set()
    cands = []

    def add(c):
        k = (c["source"], str(c["source_id"]))
        if k in seen:
            return
        seen.add(k)
        cands.append(c)

    ov_s, ov_m, cm_s, cm_m, rw_s, rw_m = _depth_pages(deep)
    ov, ov_err = fetch_openverse(query, pages_max=ov_m, start=ov_s)
    for c in ov:
        add(c)
    rewritten = None
    if len(cands) < max(5, need):
        rw = REWRITES.get(query)
        if rw and rw != query:
            rewritten = rw
            ov2, _ = fetch_openverse(rw, pages_max=rw_m, start=rw_s)
            for c in ov2:
                add(c)
    if len(cands) < need:
        cm, cm_err = fetch_commons(query, pages_max=cm_m, start=cm_s)
        for c in cm:
            add(c)
        if len(cands) < need and rewritten:
            cm2, _ = fetch_commons(rewritten, pages_max=3, start=1)
            for c in cm2:
                add(c)
    return cands, rewritten, ov_err

def tmp_path_for(c):
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(c["source_id"]))[:80]
    return DL_DIR / f"{c['source']}__{safe_id}.jpg"

def download_one(c, tmp):
    urls = [u for u in dict.fromkeys([c.get("url") or "", c.get("thumb") or ""]) if u]
    last_err = ""
    for u in urls:
        try:
            r = requests.get(u, headers={"User-Agent": UA}, timeout=60)
            if r.status_code != 200:
                last_err = f"http {r.status_code}"
                continue
            data = r.content
            if len(data) < 2000:
                last_err = "too small"
                continue
            im = Image.open(io.BytesIO(data))
            im.load()
            im = im.convert("RGB")
            im.save(tmp, "JPEG", quality=95)
            return im, None
        except Exception as e:
            last_err = str(e)[:120]
    return None, last_err

def write_outputs(final, by_ev, events):
    with open(RAW_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["img_id", "filename", "event_id", "query", "source",
                                          "source_id", "title", "creator", "creator_url",
                                          "license", "license_url", "source_url", "deleted",
                                          "delete_reason"])
        w.writeheader()
        w.writerows(final)
    lines = ["# Image attribution", "",
             "All photos are free-licensed (CC0 / PDM / CC BY / CC BY-SA / Public domain), downloaded "
             "from Openverse and Wikimedia Commons for a student research demo. "
             "CC BY / BY-SA images require the credit below.", ""]
    for r in final:
        lic = (r["license"] or "unknown").replace("cc0", "CC0").replace("pdm", "PDM") \
             .replace("by-sa", "CC BY-SA").replace("by", "CC BY")
        lic_link = f"[{lic}]({r['license_url']})" if r["license_url"] else lic
        creator = r["creator"] or "Unknown"
        src = r["source_url"] or "n/a"
        note = " [FLAGGED-DELETED]" if r["deleted"] else ""
        lines.append(f"- {r['img_id']} ({r['event_id']}, query {r['query']!r}): \"{r['title'] or 'untitled'}\" "
                     f"— {creator}, {lic_link}, {src}{note}")
    ATTR.write_text("\n".join(lines) + "\n")

def make_sheets(final, by_ev, events):
    from PIL import ImageFont
    try:
        font = ImageFont.load_default(14)
    except Exception:
        font = ImageFont.load_default()
    for ev in events:
        eid, name = ev[0], ev[1]
        imgs = by_ev.get(eid, [])
        if not imgs:
            continue
        cols = 6
        th_w, th_h = 180, 120
        rows_n = math.ceil(len(imgs) / cols)
        sheet = Image.new("RGB", (cols * (th_w + 4), 20 + rows_n * (th_h + 26)), "white")
        d = ImageDraw.Draw(sheet)
        d.text((4, 2), f"{eid} — {name} ({len(imgs)} imgs)", fill="black", font=font)
        for i, r in enumerate(imgs):
            rr, cc = divmod(i, cols)
            try:
                t = Image.open(IMAGES / r["filename"]).convert("RGB")
                t.thumbnail((th_w, th_h))
                sheet.paste(t, (cc * (th_w + 4), 20 + rr * (th_h + 26)))
            except Exception:
                pass
            d.text((cc * (th_w + 4) + 2, 20 + rr * (th_h + 26) + th_h + 2),
                   f"{r['img_id']} {r['query'][:18]}", fill="black", font=font)
        sheet.save(SHEETS / f"contact_{eid}.png")

def add_image(final, hashes, counter_state, eid, q, c, im):
    hsh = imagehash.phash(im)
    if any(hsh - h <= 5 for h in hashes):
        return None
    hashes.append(hsh)
    img_counter = counter_state[0] + 1
    counter_state[0] = img_counter
    im2 = ImageOps.exif_transpose(im)
    im2.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    filename = f"img_{img_counter:04d}.jpg"
    im2.save(IMAGES / filename, "JPEG", quality=JPEG_Q)
    row = {
        "img_id": f"img_{img_counter:04d}", "filename": filename, "event_id": eid,
        "query": q, "source": c["source"], "source_id": str(c["source_id"]),
        "title": (c.get("title") or "")[:160], "creator": (c.get("creator") or "")[:120],
        "creator_url": c.get("creator_url") or "",
        "license": c.get("license") or "", "license_url": c.get("license_url") or "",
        "source_url": (c.get("foreign_landing_url") or c.get("url") or "")[:300],
        "deleted": False, "delete_reason": "",
    }
    final.append(row)
    return row

def process_candidates(eid, q, need, cands, final, hashes, counter_state, seen_tmp):
    """Download+dedup+save up to `need` images from cands for (eid, q). Returns kept count."""
    kept = 0
    n_fail = 0
    for c in cands:
        if kept >= need:
            break
        tmp = tmp_path_for(c)
        if tmp in seen_tmp:
            continue
        seen_tmp.add(tmp)
        im = None
        if tmp.exists() and tmp.stat().st_size > 2000:
            try:
                im = Image.open(tmp)
                im.load()
                im = im.convert("RGB")
            except Exception:
                im = None
        if im is None:
            im, err = download_one(c, tmp)
            if im is None:
                n_fail += 1
                log(f"  DL-FAIL {eid} {q!r} {c['source']}:{str(c['source_id'])[:40]} {err!r}")
                continue
        row = add_image(final, hashes, counter_state, eid, q, c, im)
        if row is not None:
            kept += 1
    if n_fail:
        log(f"  {eid} {q!r}: {n_fail} download failures")
    return kept

def _kept_nondeleted(final, eid):
    return sum(1 for r in final if r["event_id"] == eid and not r["deleted"])

def main():
    skip_screen = "--skip-screen" in sys.argv
    append_mode = "--append" in sys.argv
    for d in (IMAGES, SHEETS, CACHE, DL_DIR):
        d.mkdir(parents=True, exist_ok=True)

    with open(EVENTS_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "name", "start", "end", "place_name", "lat", "lon", "target_count", "queries"])
        for ev in EVENTS:
            w.writerow(ev)
    log(f"wrote {EVENTS_CSV.name} (13 events)")

    api_records = read_jsonl(API_LOG)
    done_api = {(r["event_id"], r["query"], int(r.get("deep", False))) for r in api_records}

    final = []
    hashes = []
    counter_state = [0]
    seen_tmp = set()

    if append_mode:
        if RAW_CSV.exists():
            with open(RAW_CSV, newline="") as f:
                final = list(csv.DictReader(f))
            for r in final:
                r["deleted"] = str(r.get("deleted", "")).strip().lower() in ("true", "1")
                r.setdefault("delete_reason", "")
            for r in final:
                if not r["deleted"]:
                    p = IMAGES / r["filename"]
                    if p.exists():
                        try:
                            im = Image.open(p)
                            im.load()
                            hashes.append(imagehash.phash(im))
                        except Exception:
                            pass
            counter_state[0] = max(int(r["img_id"].split("_")[1]) for r in final)
            log(f"APPEND mode: {len(final)} existing rows, {sum(not r['deleted'] for r in final)} non-deleted, "
                f"{len(hashes)} phashes loaded, continuing from img_{counter_state[0]:04d}")
        else:
            log("APPEND mode but no existing CSV -> starting fresh")

    # Phase 1+2: fetch (resume-safe) then download+dedup+save per query
    for ev in EVENTS:
        eid, name, start, end, place, lat, lon, target, qstr = ev
        queries = qstr.split("|")
        if not append_mode:
            base = target // len(queries)
            needs = [base + (1 if i < target % len(queries) else 0) for i in range(len(queries))]
            for q, need in zip(queries, needs):
                key = (eid, q, 0)
                if key in done_api:
                    log(f"SKIP fetch {eid} {q!r} (resume)")
                else:
                    log(f"FETCH {eid} {q!r} need={need}")
                    cands, rewritten, err = fetch_query(q, need, deep=0)
                    rec_new = {"event_id": eid, "query": q, "need": need, "deep": 0,
                               "rewritten": rewritten, "err": err, "n_cands": len(cands),
                               "cands": cands}
                    api_records.append(rec_new)
                    append_jsonl(API_LOG, rec_new)
                    done_api.add(key)
                    log(f"  -> {len(cands)} candidates (rewrite={rewritten}, err={err})")
                rec = next(r for r in api_records if (r["event_id"], r["query"], int(r.get("deep", False))) == key)
                kept = process_candidates(eid, q, need, rec["cands"], final, hashes, counter_state, seen_tmp)
                log(f"  {eid} {q!r}: kept {kept}/{need}")
            continue
        # append mode: fetch only the non-deleted shortfall, deepest-first per query
        cur_kept = _kept_nondeleted(final, eid)
        shortfall = max(0, target - cur_kept)
        if shortfall == 0:
            log(f"APPEND {eid}: already at target ({cur_kept}>={target})")
            continue
        log(f"APPEND {eid}: {cur_kept}/{target} non-deleted, shortfall {shortfall}")
        for depth in (0, 1, 2):
            if _kept_nondeleted(final, eid) >= target:
                break
            for q in queries:
                if _kept_nondeleted(final, eid) >= target:
                    break
                per_q = max(1, math.ceil((target - _kept_nondeleted(final, eid)) / len(queries)))
                key = (eid, q, depth)
                if key in done_api:
                    log(f"SKIP fetch {eid} {q!r} (resume, depth={depth})")
                else:
                    log(f"FETCH {eid} {q!r} need={per_q} depth={depth}")
                    cands, rewritten, err = fetch_query(q, per_q, deep=depth)
                    rec_new = {"event_id": eid, "query": q, "need": per_q, "deep": depth,
                               "rewritten": rewritten, "err": err, "n_cands": len(cands),
                               "cands": cands}
                    api_records.append(rec_new)
                    append_jsonl(API_LOG, rec_new)
                    done_api.add(key)
                    log(f"  -> {len(cands)} candidates (rewrite={rewritten}, err={err})")
                rec = next(r for r in api_records if (r["event_id"], r["query"], int(r.get("deep", False))) == key)
                need_now = max(0, target - _kept_nondeleted(final, eid))
                if need_now == 0:
                    break
                kept = process_candidates(eid, q, need_now, rec["cands"], final, hashes, counter_state, seen_tmp)
                log(f"  {eid} {q!r}: kept {kept} (now {_kept_nondeleted(final, eid)}/{target})")

    # Top-up pass for events below 60% of target
    for ev in EVENTS:
        eid, name, target, qstr = ev[0], ev[1], ev[7], ev[8]
        cur = sum(1 for r in final if r["event_id"] == eid)
        if cur >= 0.6 * target:
            continue
        log(f"TOPUP {eid} ({name}): {cur}/{target} (<60%) -> deeper fetch")
        queries = qstr.split("|")
        for q in queries:
            key = (eid, q, 1)
            if key in done_api:
                cands = next(r for r in api_records if (r["event_id"], r["query"], int(r.get("deep", False))) == key)["cands"]
            else:
                cands, rewritten, err = fetch_query(q, 99, deep=1)
                rec_new = {"event_id": eid, "query": q, "need": 99, "deep": 1,
                           "rewritten": rewritten, "err": err, "n_cands": len(cands),
                           "cands": cands}
                api_records.append(rec_new)
                append_jsonl(API_LOG, rec_new)
                done_api.add(key)
            extra_needed = target - cur
            kept = process_candidates(eid, q, max(1, extra_needed), cands, final, hashes, counter_state, seen_tmp)
            cur = sum(1 for r in final if r["event_id"] == eid)
            if cur >= target:
                break

    by_ev = {}
    for r in final:
        by_ev.setdefault(r["event_id"], []).append(r)
    log("per-event kept:")
    for ev in EVENTS:
        eid = ev[0]
        n = len(by_ev.get(eid, []))
        flag = "" if n >= 0.6 * ev[7] else "  <-- BELOW 60%"
        log(f"  {eid} {ev[1]}: {n}/{ev[7]}{flag}")
    total_mb = sum(f.stat().st_size for f in IMAGES.glob("img_*.jpg")) / 1e6
    log(f"TOTAL {len(final)} images, {total_mb:.1f} MB in library/images/")

    write_outputs(final, by_ev, EVENTS)
    make_sheets(final, by_ev, EVENTS)
    log(f"contact sheets for {len(by_ev)} events -> {SHEETS}")

    if not skip_screen:
        sys.path.insert(0, str(BASE / "code"))
        import llm_helper
        from pydantic import BaseModel

        class ScreenDecision(BaseModel):
            delete: bool = False
            reason: str = ""

        scr_records = {r["img_id"]: r for r in read_jsonl(SCR_LOG)}
        event_names = {ev[0]: ev[1] for ev in EVENTS}
        todo = [r for r in final if r["img_id"] not in scr_records]
        log(f"vision screen: {len(todo)} to do, {len(scr_records)} cached")

        def screen_one(r):
            ev_name = event_names.get(r["event_id"], r["event_id"])
            system = ("You screen stock photos for a synthetic personal photo-library demo. "
                      "Judge ONLY what is visible.")
            user = (f"The photo was fetched for the life event \"{ev_name}\" with search query "
                    f"\"{r['query']}\". Decide whether it is safe and usable as a demo personal photo. "
                    "Return JSON: {\"delete\": true|false, \"reason\": \"<=15 words; empty if keep\"}. "
                    "delete=true ONLY if: clearly irrelevant to the event/query; nudity or graphic/violent content; "
                    "a close-up or clearly identifiable portrait of a private individual (crowd shots and "
                    "landmark scenes are fine); a close-up of a child's face; or a logo/watermark/ad dominates "
                    "the frame. delete=false otherwise, even if generic.")
            res = llm_helper.llm_json_image(system, user, IMAGES / r["filename"],
                                            schema_model=ScreenDecision, profile="local")
            if "_error" in res:
                return r["img_id"], {"delete": False, "reason": "", "_error": res["_error"]}
            return r["img_id"], {"delete": bool(res.get("delete", False)),
                                 "reason": str(res.get("reason", ""))[:120]}

        results = llm_helper.llm_json_batch(todo, screen_one, workers=8)
        for r, res in zip(todo, results):
            if res is None:
                res = {"delete": False, "reason": "", "_error": "batch None"}
            if isinstance(res, tuple):
                res = res[1]
            if not isinstance(res, dict):
                res = {"delete": False, "reason": "", "_error": f"bad result {type(res).__name__}"}
            append_jsonl(SCR_LOG, {"img_id": r["img_id"], **res})
            scr_records[r["img_id"]] = res

        flagged = []
        for r in final:
            res = scr_records.get(r["img_id"], {})
            if res.get("delete"):
                r["deleted"] = True
                r["delete_reason"] = res.get("reason", "screen")
                flagged.append(r)
        write_outputs(final, by_ev, EVENTS)
        kept = [r for r in final if not r["deleted"]]
        log(f"SCREEN flagged {len(flagged)} images:")
        for r in flagged:
            log(f"  {r['img_id']} ({r['event_id']}, {r['query']!r}): {r['delete_reason']}")
        log(f"kept {len(kept)} non-deleted images")

        checks = {
            "medicine/tablets (e07)": any(r["event_id"] == "e07" and not r["deleted"] and
                                          any(k in (r["query"] + " " + r["title"]).lower()
                                              for k in ("medicine", "tablet", "pill", "blister", "prescription"))
                                          for r in final),
            "notes/whiteboard (e05)": any(r["event_id"] == "e05" and not r["deleted"] for r in final),
            "sunset with boat (e10)": any(r["event_id"] == "e10" and not r["deleted"] and
                                          "sunset boat" in (r["query"] + " " + r["title"]).lower() for r in final),
            "ancient ruins (e06)": any(r["event_id"] == "e06" and not r["deleted"] and
                                       "ruins" in (r["query"] + " " + r["title"]).lower() for r in final),
            "rooftop dinner (e08)": any(r["event_id"] == "e08" and not r["deleted"] and
                                        "rooftop" in (r["query"] + " " + r["title"]).lower() for r in final),
            "cafes (e04/e06/e08)": sum(1 for r in final if r["event_id"] in ("e04", "e06", "e08")
                                       and not r["deleted"]
                                       and "cafe" in (r["query"] + " " + r["title"]).lower()),
        }
        for k, v in checks.items():
            log(f"  M5-check {k}: {v}")
    log("DONE build_library")

if __name__ == "__main__":
    main()
