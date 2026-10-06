"""M6 — fallback: narrowed window + day-grouped grid (search never dead-ends)."""
from datetime import timedelta

import pandas as pd


def narrowed_window(moments, meta: pd.DataFrame):
    """Date range covering the top 2 moments +/- 3 days, plus a day-grouped list
    of ALL library images in that window."""
    top2 = moments[:2]
    if not top2:
        ts = pd.to_datetime(meta["timestamp"])
        start, end = ts.min(), ts.max()
    else:
        start = min(m["start"] for m in top2) - timedelta(days=3)
        end = max(m["end"] for m in top2) + timedelta(days=3)
    ts = pd.to_datetime(meta["timestamp"])
    in_win = meta[(ts >= pd.Timestamp(start)) & (ts <= pd.Timestamp(end))].copy()
    in_win["ts"] = ts[(ts >= pd.Timestamp(start)) & (ts <= pd.Timestamp(end))]
    in_win["day"] = in_win["ts"].dt.date
    days = {}
    for d, grp in in_win.groupby("day"):
        days[str(d)] = grp["img_id"].tolist()
    return {"start": start.isoformat(), "end": end.isoformat(),
            "n_images": len(in_win), "days": dict(sorted(days.items()))}
