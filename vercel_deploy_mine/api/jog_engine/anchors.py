"""M6 — anchor windows (become 'sure' time cues)."""
from datetime import datetime, timedelta

import pandas as pd

RELATION_WINDOWS = {
    "same_day": (-12 * 3600, +12 * 3600),
    "right_after": (0, +3 * 24 * 3600),
    "right_before": (-3 * 24 * 3600, 0),
    "around": (-14 * 24 * 3600, +14 * 24 * 3600),
}


def apply_anchor(anchor_ts, relation: str):
    """anchor_ts: datetime; relation: same_day | right_after | right_before | around.
    Returns (window_start, window_end) datetimes; certainty 'sure'."""
    ts = anchor_ts
    if isinstance(ts, str):
        ts = pd.Timestamp(ts)
    if hasattr(ts, "to_pydatetime"):
        ts = ts.to_pydatetime()
    if not isinstance(ts, datetime):
        ts = datetime.fromisoformat(str(ts))
    lo, hi = RELATION_WINDOWS.get(relation, RELATION_WINDOWS["around"])
    return ts + timedelta(seconds=lo), ts + timedelta(seconds=hi)
