"""
M2 — Tag every non-deleted image once, offline-capable, resume-safe.
Usage: .venv/bin/python code/tag_images.py --provider local|hosted|offline [--resume] [--workers 4]

Outputs: library/tags.parquet (img_id + tag fields; lists as JSON strings; tag_provider)
         library/contact_sheets/tags_check.png (8 random images + tags)
"""
import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
import llm_helper  # noqa: E402
from llm_helper import llm_json_image, llm_json_batch  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

LIB = BASE / "library"
TAGS = LIB / "tags.parquet"
SHEETS = LIB / "contact_sheets"

SYSTEM = (
    "You tag photos for a personal photo-library search system. Describe ONLY what is visible. "
    "Return JSON with keys: caption (one sentence, max 20 words), scene (short phrase), "
    "setting_type (one of: cafe, beach, street, campus, classroom_or_study, hostel_or_home, "
    "restaurant, temple_or_ruins, nature_landscape, transport, office, party_or_event, "
    "shop_or_market, document_or_utility, other), indoor_outdoor (indoor|outdoor|unclear), "
    "time_of_day (morning|afternoon|evening|night|unclear), people_count_bucket (0|1|2-3|4+), "
    "dominant_colors (list of 2 plain color words), objects (list of up to 6 nouns), "
    "activity (short phrase or null), visible_text (any legible text or null), has_text (true/false), "
    "season_hint (summer|monsoon|winter|unclear), distinctive_detail (one unusual visible detail or null)."
)

class Tags(BaseModel):
    caption: str
    scene: str = ""
    setting_type: str
    indoor_outdoor: str
    time_of_day: str
    people_count_bucket: "str | int | float | None" = ""

ALLOW = {
    "setting_type": {"cafe","beach","street","campus","classroom_or_study","hostel_or_home","restaurant",
                     "temple_or_ruins","nature_landscape","transport","office","party_or_event",
                     "shop_or_market","document_or_utility","other"},
    "indoor_outdoor": {"indoor","outdoor","unclear"},
    "time_of_day": {"morning","afternoon","evening","night","unclear"},
    "season_hint": {"summer","monsoon","winter","unclear"},
}

def _coerce_bucket(v):
    v = str(v if v is not None else "").strip().lower()
    if v in ("0", "1", "2-3", "4+"):
        return v
    if v in ("2", "3"):
        return "2-3"
    if v in ("4", "5", "many", "several", "crowd"):
        return "4+"
    if v.startswith("2") or v.startswith("3"):
        return "2-3"
    return "unclear"

def _clean_tags(d):
    for k, allowed in ALLOW.items():
        v = str(d.get(k) or "").strip().lower().replace("-", "_")
        d[k] = v if v in allowed else ("unclear" if k != "setting_type" else "other")
    d["people_count_bucket"] = _coerce_bucket(d.get("people_count_bucket"))
    d["has_text"] = bool(d.get("has_text"))
    return d
    dominant_colors: list[str] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list)
    activity: str | None = None
    visible_text: str | None = None
    has_text: bool = False
    season_hint: str = "unclear"
    distinctive_detail: str | None = None

LIST_FIELDS = ["dominant_colors", "objects"]

def user_msg(row):
    return (f"Tag this photo. It was downloaded for the life event \"{row['event_name']}\" "
            f"(search query used: \"{row['query']}\"), but tag ONLY what is actually visible in the image.")

_HOSTED = False

def tag_one(args):
    img_id, path, event_name, query = args
    res = llm_json_image(SYSTEM, user_msg({"event_name": event_name, "query": query}),
                         path, schema_model=Tags, profile="hosted" if _HOSTED else "local", max_retries=3)
    if "_error" in res:
        return img_id, None, res["_error"]
    d = res.model_dump() if hasattr(res, "model_dump") else res
    d = _clean_tags(d)
    out = {"img_id": img_id}
    for k in ("caption", "scene", "setting_type", "indoor_outdoor", "time_of_day",
              "people_count_bucket", "activity", "visible_text", "season_hint",
              "distinctive_detail"):
        out[k] = d.get(k)
    out["has_text"] = bool(d.get("has_text", False))
    for k in LIST_FIELDS:
        out[k] = json.dumps(d.get(k) or [], ensure_ascii=False)
    out["tag_provider"] = "hosted" if _HOSTED else "local"
    return img_id, out, None

_clip_model = None

def _get_clip():
    global _clip_model
    if _clip_model is None:
        from sentence_transformers import SentenceTransformer
        _clip_model = SentenceTransformer("clip-ViT-B-32")
    return _clip_model

def tag_offline(img_id, path, event_name, query):
    """Approximate tags without any LLM: CLIP zero-shot for categorical fields,
    k-means (k=3) for dominant colors. caption/objects/visible_text empty by design."""
    import numpy as np
    from sklearn.cluster import KMeans
    im = Image.open(path).convert("RGB")
    small = im.resize((224, 224))
    arr = np.asarray(small).astype("float32") / 255.0
    model = _get_clip()
    def zscore(options):
        sims = model.similarity(model.encode([arr[None, ...]], convert_to_tensor=True),
                                model.encode(options, convert_to_tensor=True))
        return options[int(sims.argmax())]
    setting = zscore(["cafe", "beach", "street", "campus", "classroom_or_study", "hostel_or_home",
                      "restaurant", "temple_or_ruins", "nature_landscape", "transport", "office",
                      "party_or_event", "shop_or_market", "document_or_utility", "other"])
    iout = zscore(["indoor photo", "outdoor photo", "unclear indoor or outdoor photo"])
    iout = {"indoor photo": "indoor", "outdoor photo": "outdoor", "unclear indoor or outdoor photo": "unclear"}[iout]
    tod = zscore(["a morning photo", "an afternoon photo", "an evening photo", "a night photo", "an unclear photo"])
    tod = {"a morning photo": "morning", "an afternoon photo": "afternoon",
           "an evening photo": "evening", "a night photo": "night", "an unclear photo": "unclear"}[tod]
    ppl = zscore(["a photo with no people", "a photo with one person",
                  "a photo with two or three people", "a photo with many people"])
    ppl = {"a photo with no people": "0", "a photo with one person": "1",
           "a photo with two or three people": "2-3", "a photo with many people": "4+"}[ppl]
    season = zscore(["a summer scene", "a monsoon scene", "a winter scene", "an unclear season scene"])
    season = {"a summer scene": "summer", "a monsoon scene": "monsoon",
              "a winter scene": "winter", "an unclear season scene": "unclear"}[season]
    pixels = np.asarray(im.resize((64, 64))).reshape(-1, 3).astype("float32")
    km = KMeans(n_clusters=3, n_init=2, random_state=42).fit(pixels)
    def name_color(rgb):
        r_, g_, b_ = (int(v) for v in rgb)
        if r_ > 190 and g_ > 190 and b_ > 190: return "white"
        if r_ < 60 and g_ < 60 and b_ < 60: return "black"
        if r_ > 150 and g_ < 110 and b_ < 110: return "red"
        if g_ > 130 and r_ < 120 and b_ < 120: return "green"
        if b_ > 140 and r_ < 120 and g_ < 120: return "blue"
        if r_ > 180 and g_ > 140 and b_ < 130: return "orange"
        if r_ > 150 and g_ > 110 and b_ > 150: return "pink"
        if r_ > 170 and g_ > 170 and b_ < 140: return "yellow"
        if r_ > 140 and g_ > 110 and b_ > 90 and abs(r_ - g_) < 60: return "brown"
        return "gray"
    colors = list(dict.fromkeys(name_color(c) for c in km.cluster_centers_))[:2]
    while len(colors) < 2:
        colors.append("gray")
    out = {"img_id": img_id, "caption": "not tagged (offline CLIP-only fallback)",
           "scene": "", "setting_type": setting, "indoor_outdoor": iout,
           "time_of_day": tod, "people_count_bucket": ppl,
           "dominant_colors": json.dumps(colors, ensure_ascii=False),
           "objects": json.dumps([], ensure_ascii=False),
           "activity": None, "visible_text": None, "has_text": False,
           "season_hint": season, "distinctive_detail": None, "tag_provider": "offline"}
    return img_id, out, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["local", "hosted", "offline"], default="local")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    global _HOSTED
    _HOSTED = (args.provider == "hosted")

    raw = pd.read_csv(LIB / "images_raw.csv")
    raw = raw[~raw["deleted"].fillna(False).astype(bool)]
    events = pd.read_csv(LIB / "events.csv").set_index("event_id")
    raw["event_name"] = raw["event_id"].map(events["name"])
    raw["path"] = [LIB / "images" / f for f in raw["filename"]]

    todo = raw
    if args.resume and TAGS.exists():
        prev = pd.read_parquet(TAGS)
        done = set(prev["img_id"])
        todo = raw[~raw["img_id"].isin(done)]
        print(f"RESUME: {len(done)} tagged, {len(todo)} todo", flush=True)

    print(f"PROVIDER={args.provider} todo={len(todo)} workers={args.workers}", flush=True)
    items = [(r["img_id"], str(r["path"]), r["event_name"], r["query"]) for _, r in todo.iterrows()]
    if args.provider == "offline":
        results = []
        for i, it in enumerate(items, 1):
            try:
                results.append(tag_offline(*it))
            except Exception as e:
                results.append((it[0], None, str(e)[:120]))
            if i % 20 == 0:
                print(f"  offline {i}/{len(items)}", flush=True)
    else:
        results = llm_helper.llm_json_batch(items, tag_one, workers=args.workers)

    rows = []
    n_fail = 0
    for (img_id, _p, _e, _q), res in zip(items, results):
        if res is None:
            n_fail += 1
            continue
        _id, out, err = res
        if out is None:
            n_fail += 1
            print(f"  FAIL {img_id}: {str(err)[:120]}", flush=True)
            continue
        rows.append(out)
        if len(rows) >= 25:
            _flush(rows, args.resume)
            rows.clear()
    if rows:
        _flush(rows, args.resume)
        rows.clear()

    if TAGS.exists():
        tags = pd.read_parquet(TAGS).drop_duplicates("img_id", keep="last")
    else:
        tags = pd.DataFrame(rows)
    n = len(raw)
    ok = len(tags)
    print(f"tagged {ok}/{n} ({ok/max(n,1)*100:.1f}%), failed {n_fail}")
    for col in ("setting_type", "time_of_day", "indoor_outdoor", "season_hint", "people_count_bucket"):
        if col in tags.columns:
            print(f"  {col}: {dict(Counter(tags[col]).most_common(8))}")

    # contact sheet of 8 random images with tags
    SHEETS.mkdir(parents=True, exist_ok=True)
    try:
        font = ImageFont.load_default(14)
    except Exception:
        font = ImageFont.load_default()
    sample = tags.sample(min(8, len(tags)), random_state=42)
    sheet = Image.new("RGB", (2 * 300, 4 * 300), "white")
    d = ImageDraw.Draw(sheet)
    for i, (_, r) in enumerate(sample.iterrows()):
        rr, cc = divmod(i, 2)
        y0, x0 = rr * 300, cc * 300
        try:
            t = Image.open(LIB / "images" / raw.set_index("img_id").loc[r["img_id"], "filename"]).convert("RGB")
            t.thumbnail((290, 120))
            sheet.paste(t, (x0 + 5, y0 + 5))
        except Exception:
            pass
        txt = (f"{r['img_id']} [{r['setting_type']}|{r['time_of_day']}|{r['indoor_outdoor']}|{r['people_count_bucket']}]\n"
               f"{str(r['caption'])[:70]}")
        d.multiline_text((x0 + 5, y0 + 130), txt, fill="black", font=font)
    sheet.save(SHEETS / "tags_check.png")
    print(f"wrote {SHEETS / 'tags_check.png'} (8 random, verify yourself)")
    print("DONE tag_images")

def _flush(rows, resume):
    frame = pd.DataFrame(rows)
    if resume and TAGS.exists():
        prev = pd.read_parquet(TAGS)
        frame = pd.concat([prev, frame], ignore_index=True)
    frame.to_parquet(TAGS, index=False)

if __name__ == "__main__":
    main()
