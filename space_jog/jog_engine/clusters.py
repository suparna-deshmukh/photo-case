"""M6 — Moment clustering over the top-K results."""
import json
from collections import Counter
from typing import List

import numpy as np
import pandas as pd

from .config import MOMENT_GAP_HOURS, MOMENT_MAX_KM


def gazetteer():
    from .cues_rules import gazetteer as g
    return g()


def _gaz_terms():
    from .cues_rules import _gaz_terms as g
    return g()


def _haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, asin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def moments(scored: pd.DataFrame, meta: pd.DataFrame) -> List[dict]:
    """Group top-K rows into moments: new moment when gap > MOMENT_GAP_HOURS
    from previous image OR distance > MOMENT_MAX_KM from moment centroid."""
    sub = scored.copy()
    sub["ts"] = pd.to_datetime(sub["timestamp"])
    sub = sub.sort_values("ts").reset_index(drop=True)
    if sub.empty:
        return []
    lat = meta.set_index("img_id")["lat"].reindex(sub["img_id"]).values
    lon = meta.set_index("img_id")["lon"].reindex(sub["img_id"]).values
    moments = []
    cur = [0]
    centroid = (float(lat[0]) if lat[0] == lat[0] else 0.0, float(lon[0]) if lon[0] == lon[0] else 0.0)
    for i in range(1, len(sub)):
        t_gap = (sub.loc[i, "ts"] - sub.loc[i - 1, "ts"]).total_seconds() / 3600.0
        d_km = 0.0
        if lat[i] == lat[i] and lon[i] == lon[i]:
            d_km = _haversine_km(lat[i], lon[i], centroid[0], centroid[1])
        if t_gap > MOMENT_GAP_HOURS or d_km > MOMENT_MAX_KM:
            moments.append(cur)
            cur = [i]
            centroid = (float(lat[i]), float(lon[i]))
        else:
            cur.append(i)
            if lat[i] == lat[i] and lon[i] == lon[i]:
                n = len(cur)
                centroid = ((centroid[0] * (n - 1) + lat[i]) / n, (centroid[1] * (n - 1) + lon[i]) / n)
    moments.append(cur)
    out = []
    for group in moments:
        gdf = sub.loc[group]
        place = gdf["place_name"].fillna("").mode()
        area = gdf["area"].fillna("").mode()
        pname = (place.iloc[0] if len(place) else "") or (area.iloc[0] if len(area) else "somewhere")
        d0, d1 = gdf["ts"].min().date().isoformat(), gdf["ts"].max().date().isoformat()
        dates = d0 if d0 == d1 else f"{d0} – {d1}"
        setting = gdf["setting_type"].dropna().mode()
        st = setting.iloc[0] if len(setting) else ""
        label = f"{pname} · {dates} · {st}" if st else f"{pname} · {dates}"
        top3 = gdf["score"].sort_values(ascending=False).head(3)
        out.append({
            "label": label,
            "score": float(gdf["score"].max()),
            "mean_top3": float(top3.mean()),
            "size": len(group),
            "img_ids": gdf["img_id"].tolist(),
            "start": gdf["ts"].min().to_pydatetime(),
            "end": gdf["ts"].max().to_pydatetime(),
            "place_name": pname,
        })
    out.sort(key=lambda m: (m["score"], m["mean_top3"]), reverse=True)
    return out[:5]


def cluster_purity(moments: List[dict], meta: pd.DataFrame) -> float:
    """Share of images whose event_id equals the mode event of their moment (offline check)."""
    ev = meta.set_index("img_id")["event_id"]
    total = correct = 0
    for m in moments:
        ids = [i for i in m["img_ids"] if i in ev.index]
        if not ids:
            continue
        mode_ev = Counter(ev[i] for i in ids).most_common(1)[0][0]
        correct += sum(1 for i in ids if ev[i] == mode_ev)
        total += len(ids)
    return correct / total if total else 0.0
