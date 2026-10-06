"""
M5 — Build 8 retrieval tasks (sets X/Y, types T1-T4) + 2 practice tasks,
fairness report, contact sheets, examples.json and task_parses.json (llm half).

Run after M1-M4. Human gate (delegated): agent review + log.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
LIB = BASE / "library"
SHEETS = LIB / "contact_sheets"

def ts():
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def log(msg):
    print(f"{ts()} {msg}", flush=True)

def main():
    from sentence_transformers import SentenceTransformer
    meta = pd.read_parquet(LIB / "meta.parquet")
    emb = np.load(LIB / "image_emb.npy")
    idx = {img_id: i for i, img_id in enumerate(json.loads((LIB / "emb_index.json").read_text()))}
    model = SentenceTransformer("clip-ViT-B-32")
    meta["emb_row"] = meta["img_id"].map(idx)
    meta = meta[meta["emb_row"].notna()].copy()
    E = emb[meta["emb_row"].astype(int).to_numpy()]

    def clip_sim_text(text, sub):
        v = model.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]
        rows = sub["emb_row"].astype(int).to_numpy()
        sims = E[rows] @ v
        return pd.Series(sims, index=sub.index)

    def sim_to_img(img_id, sub):
        if img_id not in idx:
            return pd.Series(np.nan, index=sub.index)
        rows = sub["emb_row"].astype(int).to_numpy()
        sims = E[rows] @ E[idx[img_id]]
        return pd.Series(sims, index=sub.index)

    meta["tod"] = meta["time_of_day"].fillna("unclear")
    meta["ts"] = pd.to_datetime(meta["timestamp"])
    non_deleted = meta  # meta.parquet contains only non-deleted images (built from images_raw.csv filter)

    # ---------- selection ----------
    tasks = []

    # X1 / Y1 — T1 event-context cafe
    x1_pool = non_deleted[(non_deleted["event_id"] == "e04") &
                          (non_deleted["setting_type"] == "cafe") &
                          (non_deleted["tod"].isin(["morning", "afternoon"]))]
    x1_target = x1_pool.iloc[0]["img_id"] if len(x1_pool) else None
    x1_decoys = []
    if x1_target:
        other_cafes = non_deleted[(non_deleted["event_id"].isin(["e06", "e08", "e09"])) &
                                  (non_deleted["setting_type"] == "cafe")]
        s = sim_to_img(x1_target, other_cafes).dropna().sort_values(ascending=False)
        x1_decoys = s.head(8).index.tolist()

    y1_pool = non_deleted[((non_deleted["event_id"].isin(["e06", "e08"])) &
                           (non_deleted["setting_type"] == "cafe") &
                           (non_deleted["tod"].isin(["morning", "afternoon"])))]
    y1_target = y1_pool.iloc[0]["img_id"] if len(y1_pool) else None
    y1_decoys = []
    if y1_target:
        other_cafes = non_deleted[(non_deleted["event_id"].isin(["e04", "e09"])) &
                                  (non_deleted["setting_type"] == "cafe")]
        s = sim_to_img(y1_target, other_cafes).dropna().sort_values(ascending=False)
        y1_decoys = s.head(8).index.tolist()

    # X2 / Y2 — T2 utility
    x2_pool = non_deleted[(non_deleted["event_id"] == "e07") &
                          (non_deleted["setting_type"] == "document_or_utility")]
    x2_target = x2_pool.iloc[0]["img_id"] if len(x2_pool) else None
    if x2_target is None and len(non_deleted[non_deleted["event_id"] == "e07"]):
        x2_target = non_deleted[non_deleted["event_id"] == "e07"].iloc[0]["img_id"]
    x2_decoys = []
    if x2_target:
        doc = non_deleted[(non_deleted["setting_type"] == "document_or_utility") &
                          (non_deleted["img_id"] != x2_target)]
        s = sim_to_img(x2_target, doc).dropna().sort_values(ascending=False)
        x2_decoys = s.head(8).index.tolist()

    y2_pool = non_deleted[(non_deleted["event_id"] == "e05") &
                          (non_deleted["setting_type"].isin(["classroom_or_study", "document_or_utility"]))]
    y2_target = y2_pool.iloc[0]["img_id"] if len(y2_pool) else None
    y2_decoys = []
    if y2_target:
        doc = non_deleted[(non_deleted["event_id"].isin(["e13", "e09"])) &
                          (non_deleted["setting_type"].isin(["classroom_or_study", "document_or_utility"]))]
        s = sim_to_img(y2_target, doc).dropna().sort_values(ascending=False)
        y2_decoys = s.head(8).index.tolist()

    # X3 — T3 anchor-relative (Pondicherry)
    x3_anchor_pool = non_deleted[(non_deleted["event_id"] == "e08") &
                                 (non_deleted["tod"].isin(["morning", "afternoon"])) &
                                 (non_deleted["setting_type"].isin(["street", "campus"]))]
    x3_anchor = x3_anchor_pool.iloc[0]["img_id"] if len(x3_anchor_pool) else None
    x3_target = None
    x3_decoys = []
    if x3_anchor:
        a_ts = meta[meta["img_id"] == x3_anchor]["ts"].iloc[0]
        cand = non_deleted[(non_deleted["event_id"] == "e08") &
                           (non_deleted["tod"] == "night") &
                           (non_deleted["setting_type"].isin(["restaurant", "cafe"]))]
        cand = cand[(cand["ts"] >= a_ts + pd.Timedelta(days=1)) & (cand["ts"] <= a_ts + pd.Timedelta(days=2))]
        if len(cand):
            x3_target = cand.iloc[0]["img_id"]
        else:
            cand2 = non_deleted[(non_deleted["event_id"] == "e08") & (non_deleted["tod"] == "night")]
            x3_target = cand2.iloc[0]["img_id"] if len(cand2) else None
        if x3_target:
            decoy_pool = non_deleted[(non_deleted["event_id"].isin(["e04", "e09"])) &
                                     (non_deleted["tod"].isin(["evening", "night"]))]
            s = sim_to_img(x3_target, decoy_pool).dropna().sort_values(ascending=False)
            x3_decoys = s.head(8).index.tolist()

    # Y3 — T3 anchor-relative (Bengaluru internship)
    # library reality: e09 evening/night shots fall in the LAST week of the
    # internship, so the office anchor is the latest office/desk image within
    # two weeks before the first evening/night shot (fragment says "a week or
    # two after I started at the office").
    e09 = non_deleted[non_deleted["event_id"] == "e09"]
    e09_even = e09[e09["tod"].isin(["evening", "night"])].sort_values("ts")
    y3_anchor, y3_target, y3_decoys = None, None, []
    if len(e09_even):
        first_even = e09_even.iloc[0]
        fe_ts = first_even["ts"]
        office = e09[e09["setting_type"] == "office"].sort_values("ts")
        anchor_cand = office[office["ts"] <= fe_ts]
        if len(anchor_cand):
            y3_anchor = anchor_cand.iloc[-1]["img_id"]
            a_ts = meta[meta["img_id"] == y3_anchor]["ts"].iloc[0]
            cand = e09_even[e09_even["ts"] >= a_ts]
            if len(cand):
                y3_target = cand.iloc[0]["img_id"]
        if y3_target:
            decoy_pool = non_deleted[(non_deleted["event_id"].isin(["e10", "e11"])) &
                                     (non_deleted["tod"].isin(["evening", "night"]))]
            s = sim_to_img(y3_target, decoy_pool).dropna().sort_values(ascending=False)
            y3_decoys = s.head(8).index.tolist()

    # X4 — T4 near-duplicate sunset with boat
    x4_pool = non_deleted[(non_deleted["event_id"] == "e10")]
    x4_pool = x4_pool[x4_pool.apply(
        lambda r: "boat" in str(r.get("caption", "")).lower() or "boat" in str(r.get("objects", "")).lower(), axis=1)]
    x4_target = x4_pool.iloc[0]["img_id"] if len(x4_pool) else None
    x4_decoys = []
    if x4_target:
        sunsets = non_deleted[(non_deleted["event_id"].isin(["e04", "e06", "e10"])) &
                              (non_deleted["img_id"] != x4_target)]
        s = sim_to_img(x4_target, sunsets).dropna().sort_values(ascending=False)
        x4_decoys = s.head(8).index.tolist()

    # Y4 — T4 golden-hour ruins with a person
    y4_pool = non_deleted[(non_deleted["event_id"] == "e06") &
                          (non_deleted["setting_type"].isin(["temple_or_ruins", "nature_landscape"]))]
    y4_pool = y4_pool[y4_pool["people_count_bucket"].isin(["1", "2-3", "4+"])]
    y4_target = y4_pool.iloc[0]["img_id"] if len(y4_pool) else None
    if y4_target is None and len(non_deleted[non_deleted["event_id"] == "e06"]):
        y4_target = non_deleted[non_deleted["event_id"] == "e06"].iloc[0]["img_id"]
    y4_decoys = []
    if y4_target:
        pool = non_deleted[(non_deleted["setting_type"].isin(["temple_or_ruins", "nature_landscape"])) &
                           (non_deleted["img_id"] != y4_target)]
        s = sim_to_img(y4_target, pool).dropna().sort_values(ascending=False)
        y4_decoys = s.head(8).index.tolist()

    spec = [
        ("X1", "X", "T1_event_context", x1_target, None, x1_decoys,
         "A café from the Goa trip, vague about the day; daytime coffee before the beach."),
        ("Y1", "Y", "T1_event_context", y1_target, None, y1_decoys,
         "A daytime café from the riverside trip (Hampi/Pondicherry); day not stated."),
        ("X2", "X", "T2_utility", x2_target, None, x2_decoys,
         "A utility photo taken for a purpose (medicine/dosage), approximate period."),
        ("Y2", "Y", "T2_utility", y2_target, None, y2_decoys,
         "Study notes photographed during exam season; exact day forgotten."),
        ("X3", "X", "T3_anchor_relative", x3_target, x3_anchor, x3_decoys,
         "A night rooftop dinner remembered only as 'the evening after the old-town walk'."),
        ("Y3", "Y", "T3_anchor_relative", y3_target, y3_anchor, y3_decoys,
         "An evening with friends remembered relative to the first week of the internship."),
        ("X4", "X", "T4_near_duplicate", x4_target, None, x4_decoys,
         "One of many similar sunsets, distinguished by a boat in the foreground."),
        ("Y4", "Y", "T4_near_duplicate", y4_target, None, y4_decoys,
         "Golden-hour stone ruins with a person, among similar ruins shots."),
    ]

    fragments = {
        "X1": "I'm trying to find a photo of a small café on our Goa trip. I think it was daytime and we were having coffee before the beach. I don't remember which day or which café.",
        "Y1": "There's a photo from the trip where we stopped at a café by the river. It was during the day, I'm sure. I don't remember which day of the trip it was.",
        "X2": "When I was ill I photographed my medicine so I'd remember the dosage. I think it was around the end of 2023, maybe November. I don't remember where I took it.",
        "Y2": "I had photographed my handwritten notes right before exams last year, around April or May. I can't remember the exact day or which page it was.",
        "X3": "In Pondicherry we had dinner on a rooftop at night, the evening after we walked around the old French-style buildings. I want that dinner photo.",
        "Y3": "In Bengaluru, near the end of my internship, a few days after a stretch of late nights at the office, we went out one evening and I saw the city from up high. I want that evening photo.",
        "X4": "A sunset photo with a boat in the foreground. It was either Goa or Gokarna. I'm sure about the boat.",
        "Y4": "A photo of the old stone ruins at sunset, and I think one of us was standing in front of them. It was the Hampi trip.",
    }

    difficulty = {
        "X1": "Café decoys are visually similar; day-level recall is the only discriminator.",
        "Y1": "Multiple daytime cafés across trips; anchor is the river, which is weakly stated.",
        "X2": "Utility images are visually similar documents; the period is approximate.",
        "Y2": "Notes images recur across events; month-level memory only.",
        "X3": "Only an anchor-relative memory; the target night is 1-2 days after the anchor.",
        "Y3": "Week-level anchor; evening city-view shots recur.",
        "X4": "Near-duplicate sunsets; the boat is the only reliable cue.",
        "Y4": "Ruins shots are similar; a person + golden hour must disambiguate.",
    }
    pair_of = {"X1": "Y1", "Y1": "X1", "X2": "Y2", "Y2": "X2",
               "X3": "Y3", "Y3": "X3", "X4": "Y4", "Y4": "X4"}

    tasks = []
    missing = []
    for tid, tset, ttype, target, anchor, decoys, note in spec:
        if target is None:
            missing.append(tid)
            continue
        tasks.append({
            "id": tid, "set": tset, "type": ttype,
            "fragment_text": fragments[tid],
            "target_img_id": target,
            "anchor_img_id": anchor,
            "decoy_img_ids": decoys[:8],
            "difficulty_note": difficulty[tid],
            "counterbalance_pair": pair_of[tid],
        })
    log(f"tasks selected: {len(tasks)}/8; missing: {missing}")

    # practice tasks P1, P2
    p1_pool = non_deleted[non_deleted["event_id"] == "e03"]
    p1_target = p1_pool.iloc[0]["img_id"] if len(p1_pool) else None
    p2_pool = non_deleted[non_deleted["event_id"] == "e11"]
    p2_target = p2_pool.iloc[0]["img_id"] if len(p2_pool) else None
    if p1_target:
        tasks.append({"id": "P1", "set": "practice", "type": "practice",
                      "fragment_text": "A festival photo from home last year — sweets and lights. I don't remember which day.",
                      "target_img_id": p1_target, "anchor_img_id": None,
                      "decoy_img_ids": non_deleted[non_deleted["event_id"] == "e12"].head(8)["img_id"].tolist(),
                      "difficulty_note": "Practice: warm-up with an easy festive target.",
                      "counterbalance_pair": "P2"})
    if p2_target:
        tasks.append({"id": "P2", "set": "practice", "type": "practice",
                      "fragment_text": "A photo from a college fest night — stage lights and a crowd. I think it was last year.",
                      "target_img_id": p2_target, "anchor_img_id": None,
                      "decoy_img_ids": non_deleted[non_deleted["event_id"] == "e02"].head(8)["img_id"].tolist(),
                      "difficulty_note": "Practice: event-night warm-up.",
                      "counterbalance_pair": "P1"})
    (LIB / "tasks.json").write_text(json.dumps(tasks, indent=2))
    log(f"wrote tasks.json ({len(tasks)} tasks)")

    # ---------- examples.json (free-play chips) ----------
    examples = [
        "a café somewhere in Goa, daytime I think, we had coffee before the beach",
        "the sunset with a boat, either the Goa trip or the later one",
        "a photo of my medicine strip I took when I was sick, maybe last November",
        "notes I photographed before exams, around last April",
        "the night we dined on a rooftop in Pondicherry, after the old-town walk",
    ]
    (LIB / "examples.json").write_text(json.dumps(examples, indent=2))
    log("wrote examples.json (5 chips)")

    # ---------- task_parses.json (llm half) ----------
    import llm_helper
    from jog_engine.cues import LIVE_PROMPT, TODAY, _coerce_parsed
    parse_file = LIB / "task_parses.json"
    parses = json.loads(parse_file.read_text()) if parse_file.exists() else {}
    texts = [t["fragment_text"] for t in tasks] + examples
    import re
    for t in texts:
        norm = re.sub(r"\s+", " ", t).strip().lower()
        if norm in parses and parses[norm].get("llm"):
            continue
        res = llm_helper.llm_json(LIVE_PROMPT.format(today=TODAY),
                                  f"Memory text:\n\"\"\"\n{t}\n\"\"\"\n\nReturn the JSON object.",
                                  profile="local")
        if "_error" not in res:
            parses.setdefault(norm, {})["llm"] = res
        log(f"parsed: {norm[:50]!r} {'ok' if '_error' not in res else 'ERR ' + str(res.get('_error'))[:60]}")
        _flush_parses(parses, parse_file)
    _flush_parses(parses, parse_file)

    # ---------- fairness report ----------
    log("\n===== FAIRNESS REPORT (classic vs visual-only) =====")
    feasible = 0
    trivial = 0
    for t in [x for x in tasks if x["set"] in ("X", "Y")]:
        frag = t["fragment_text"]
        v = model.encode([frag], convert_to_numpy=True, normalize_embeddings=True)[0]
        sims = E @ v
        order = np.argsort(-sims)
        rank_visual = int(np.where(order == meta["emb_row"].astype(int)[meta["img_id"] == t["target_img_id"]].iloc[0])[0][0]) + 1
        # classic: visual + place/keyword boosts
        boost = np.zeros(len(meta))
        cap_blobs = meta["caption"].fillna("").str.lower().to_numpy()
        for kw in ["cafe", "coffee", "boat", "sunset", "ruins", "medicine", "tablet", "notes",
                   "rooftop", "dinner", "evening", "night", "office", "team", "friends", "festival",
                   "stage", "sweets", "lights", "river"]:
            for j, b in enumerate(cap_blobs):
                if kw in b:
                    boost[j] += 0.05
        for j, place in enumerate(meta["place_name"].fillna("").str.lower()):
            if any(p in frag.lower() for p in ("goa", "pondicherry", "bengaluru", "hampi", "gokarna", "pune")):
                if place in frag.lower():
                    boost[j] += 0.10
        combined = sims * 0.8 + boost
        order2 = np.argsort(-combined)
        rank_classic = int(np.where(order2 == meta["emb_row"].astype(int)[meta["img_id"] == t["target_img_id"]].iloc[0])[0][0]) + 1
        tag = "TRIVIAL(top5)" if rank_classic <= 5 else ("feasible" if rank_classic <= 150 else "NOT feasible")
        if rank_classic <= 150:
            feasible += 1
        if rank_classic <= 5:
            trivial += 1
        log(f"  {t['id']}: target rank visual-only={rank_visual}, classic={rank_classic} [{tag}]")
    log(f"classic feasible (<=150): {feasible}/8; trivial (<=5): {trivial}/8")

    # ---------- contact sheets per task ----------
    try:
        font = ImageFont.load_default(14)
    except Exception:
        font = ImageFont.load_default()
    for t in tasks:
        ids = [t["target_img_id"]] + ([t["anchor_img_id"]] if t.get("anchor_img_id") else []) + t["decoy_img_ids"]
        cols = 6
        rows_n = max(1, (len(ids) + cols - 1) // cols)
        sheet = Image.new("RGB", (cols * 204, 20 + rows_n * 146), "white")
        d = ImageDraw.Draw(sheet)
        d.text((4, 2), f"{t['id']} ({t['type']}) target=T anchor=A + 8 decoys", fill="black", font=font)
        for i, img_id in enumerate(ids):
            rr, cc = divmod(i, cols)
            y0, x0 = 20 + rr * 146, cc * 204
            mrow = meta[meta["img_id"] == img_id]
            if mrow.empty:
                continue
            try:
                img = Image.open(LIB / "images" / mrow.iloc[0]["filename"]).convert("RGB")
                img.thumbnail((194, 100))
                sheet.paste(img, (x0 + 5, y0))
            except Exception:
                pass
            label = "T" if img_id == t["target_img_id"] else ("A" if img_id == t.get("anchor_img_id") else "D")
            d.text((x0 + 5, y0 + 102), f"{label} {img_id} {mrow.iloc[0]['event_id']} {str(mrow.iloc[0].get('caption', ''))[:24]}",
                   fill="black", font=font)
        sheet.save(SHEETS / f"task_{t['id']}.png")
    log(f"contact sheets for {len(tasks)} tasks")
    log("DONE build_tasks")


def _flush_parses(parses, path):
    path.write_text(json.dumps(parses, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
