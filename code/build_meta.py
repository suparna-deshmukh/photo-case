"""
M3 — Synthetic timestamps + places for the demo library.
Outputs: library/meta.parquet, library/gazetteer.json
Run after M1+M2.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
LIB = BASE / "library"
TZ = timezone(timedelta(hours=5, minutes=30))
SEED = 42
TOD_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, "night": 3}
CLOCK = {
    "morning": (7 * 3600, 11 * 3600 + 59 * 60 + 59),
    "afternoon": (12 * 3600, 16 * 3600 + 59 * 60 + 59),
    "evening": (17 * 3600, 19 * 3600 + 59 * 60 + 59),
    "night": (20 * 3600, 23 * 3600 + 30 * 60),
}

def _img_rng(img_id):
    import zlib
    return np.random.default_rng(zlib.crc32(img_id.encode("utf-8")) & 0xFFFFFFFF)

def main():
    raw = pd.read_csv(LIB / "images_raw.csv")
    raw = raw[~raw["deleted"].fillna(False).astype(bool)].reset_index(drop=True)
    tags = pd.read_parquet(LIB / "tags.parquet")
    events = pd.read_csv(LIB / "events.csv")
    meta = raw.merge(tags, on="img_id", how="left")

    # append-safe: keep existing meta rows untouched (M5 task geometry depends on them)
    existing = None
    if (LIB / "meta.parquet").exists():
        existing = pd.read_parquet(LIB / "meta.parquet")
        existing = existing[existing["img_id"].isin(raw["img_id"])].reset_index(drop=True)
        if "person_key" not in existing.columns:
            existing["person_key"] = ""
    existing_ids = set(existing["img_id"]) if existing is not None else set()
    new_meta = meta[~meta["img_id"].isin(existing_ids)].copy()
    new_meta["tod"] = new_meta["time_of_day"].fillna("afternoon").replace({"unclear": "afternoon"})
    print(f"meta: {len(raw)} non-deleted, {len(existing_ids)} existing rows kept, {len(new_meta)} new to assign")

    # per-event existing day distributions (for narrative-consistent new dates)
    ev_days = {}
    if existing is not None:
        for _, ev in events.iterrows():
            eid = ev["event_id"]
            if eid == "e13":
                continue
            sub = existing[existing["event_id"] == eid]
            if len(sub) == 0:
                continue
            t = pd.to_datetime(sub["timestamp"]).dt.date
            ev_days[eid] = [(d - pd.Timestamp(ev["start"]).date()).days for d in t]

    out_rows = []
    month_hist = {}
    for _, ev in events.iterrows():
        eid = ev["event_id"]
        sub = new_meta[new_meta["event_id"] == eid].copy()
        if len(sub) == 0:
            continue
        start = pd.Timestamp(ev["start"])
        end = pd.Timestamp(ev["end"])
        n_days = (end - start).days + 1
        sub["tod_rank"] = sub["tod"].map(TOD_ORDER)
        sub = sub.sort_values(["tod_rank"], kind="stable").reset_index(drop=True)
        dist_days = ev_days.get(eid, [])
        for i, (_, r) in enumerate(sub.iterrows()):
            rng = _img_rng(r["img_id"])
            if eid == "e13":
                day = pd.Timestamp("2022-08-01") + timedelta(days=int(rng.integers(
                    0, (pd.Timestamp("2026-09-28") - pd.Timestamp("2022-08-01")).days + 1)))
            elif dist_days:
                dd = np.array(dist_days)
                day = start + timedelta(days=int(rng.choice(dd)))
            else:
                if n_days >= 2:
                    day_idx = int(np.clip(np.linspace(0, n_days - 1, len(sub)).round()[i], 0, n_days - 1))
                else:
                    day_idx = 0
                day = start + timedelta(days=day_idx)
            tod = r["tod"]
            lo, hi = CLOCK[tod]
            secs = int(rng.integers(lo, hi + 1))
            ts = day.to_pydatetime() + timedelta(seconds=secs)
            ts = ts.replace(tzinfo=TZ)
            if eid == "e13":
                place_name = "mixed"
                choices = events[(events["event_id"] != "e13") & events["lat"].notna()]
                pe = choices.iloc[int(rng.integers(0, len(choices)))]
                lat, lon = float(pe["lat"]) + float(rng.uniform(-0.02, 0.02)), \
                           float(pe["lon"]) + float(rng.uniform(-0.02, 0.02))
                area = "mixed"
            else:
                place_name = ev["place_name"]
                lat = float(ev["lat"]) + float(rng.uniform(-0.02, 0.02))
                lon = float(ev["lon"]) + float(rng.uniform(-0.02, 0.02))
                if eid == "e04":
                    cap = str(r.get("caption", "")).lower()
                    area = "Palolem" if (r.get("setting_type") == "beach" or "beach" in cap or "sea" in cap) else "Panjim"
                elif eid == "e10":
                    area = "Gokarna"
                else:
                    area = place_name
            if not (start <= day <= end or eid == "e13"):
                print(f"  WARN out-of-window {r['img_id']} {day} ({start}..{end})")
            mk = ts.strftime("%Y-%m")
            month_hist[mk] = month_hist.get(mk, 0) + 1
            row = {"img_id": r["img_id"], "filename": r["filename"], "event_id": eid,
                   "timestamp": ts.isoformat(), "place_name": place_name, "area": area,
                   "lat": round(lat, 5), "lon": round(lon, 5)}
            for k in ("caption", "scene", "setting_type", "indoor_outdoor", "time_of_day",
                      "people_count_bucket", "dominant_colors", "objects", "activity",
                      "visible_text", "has_text", "season_hint", "distinctive_detail", "tag_provider"):
                if k in meta.columns:
                    row[k] = r.get(k)
            pk = r.get("person_key")
            row["person_key"] = pk if pd.notna(pk) else ""
            row["synthetic_metadata"] = True
            out_rows.append(row)

    mdf = pd.DataFrame(out_rows)
    if existing is not None and len(existing):
        mdf = pd.concat([existing, mdf], ignore_index=True)
    mdf.to_parquet(LIB / "meta.parquet", index=False)
    print(f"meta rows: {len(mdf)} (non-deleted images: {len(raw)})")
    assert len(mdf) == len(raw), "meta row count mismatch"

    # sanity: per-month histogram
    ts_all = pd.to_datetime(mdf["timestamp"])
    print("per-month histogram:")
    for mk in sorted(month_hist):
        print(f"  {mk}: {month_hist[mk]}")

    # sanity: no timestamp outside event window
    bad = 0
    for _, r in mdf.iterrows():
        if r["event_id"] == "e13":
            continue
        ev = events[events["event_id"] == r["event_id"]].iloc[0]
        t = pd.Timestamp(r["timestamp"])
        if not (ev["start"] <= t.date().isoformat() <= ev["end"]):
            bad += 1
    print(f"sanity out-of-window timestamps: {bad} (expect 0)")

    # sanity: within each event, avg day-index(night) >= avg day-index(morning)
    evs = events[events["event_id"] != "e13"]
    for _, ev in evs.iterrows():
        eid = ev["event_id"]
        sub = mdf[mdf["event_id"] == eid]
        if len(sub) < 4:
            continue
        t = pd.to_datetime(sub["timestamp"], utc=True).dt.tz_convert(TZ).dt.tz_localize(None)
        days = (t - pd.Timestamp(ev["start"])).dt.days
        m = days[sub["time_of_day"] == "morning"]
        n = days[sub["time_of_day"] == "night"]
        if len(m) and len(n):
            ok = n.mean() >= m.mean()
            if not ok:
                print(f"  WARN {eid}: night avg day {n.mean():.2f} < morning avg day {m.mean():.2f}")

    gaz = {
        "Goa": {"lat": 15.4909, "lon": 73.8278, "aliases": ["Panjim", "Palolem", "Panaji"]},
        "Zuarinagar Goa": {"lat": 15.391, "lon": 73.878, "aliases": ["BITS Goa", "campus", "Zuarinagar"]},
        "Bengaluru": {"lat": 12.9716, "lon": 77.5946, "aliases": ["Bangalore"]},
        "Pondicherry": {"lat": 11.9416, "lon": 79.8083, "aliases": ["Puducherry", "Pondy"]},
        "Gokarna": {"lat": 14.5479, "lon": 74.3188, "aliases": []},
        "Hampi": {"lat": 15.335, "lon": 76.46, "aliases": []},
        "Pune": {"lat": 18.5204, "lon": 73.8567, "aliases": []},
    }
    (LIB / "gazetteer.json").write_text(json.dumps(gaz, indent=2))
    print("wrote meta.parquet + gazetteer.json")
    print("DONE build_meta")

if __name__ == "__main__":
    main()
