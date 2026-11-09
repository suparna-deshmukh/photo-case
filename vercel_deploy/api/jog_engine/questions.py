"""M6 — next-question selector (Shannon entropy x prior x dont-know decay)."""
import math
from typing import List, Optional

import numpy as np
import pandas as pd

from .config import MAX_ROUNDS, PRIORS, SOFTMAX_T, TOP_K

ATTR_COLUMNS = ["indoor_outdoor", "time_of_day", "place_name", "setting_type",
                "season_hint", "people_count_bucket", "has_text", "dominant_color"]

QUESTION_TEXT = {
    "indoor_outdoor": "Were you indoors or outdoors?",
    "time_of_day": "Do you remember roughly what time of day it was?",
    "place_name": "Do you remember which place this was in?",
    "setting_type": "What kind of place was it?",
    "season_hint": "Do you remember the weather or season?",
    "people_count_bucket": "How many people were in the photo?",
    "has_text": "Was there any visible writing in it?",
    "dominant_color": "Was there a standout color?",
}

def _softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max()
    e = np.exp(x)
    return e / e.sum()

def _entropy_bits(weights: np.ndarray) -> float:
    w = weights[weights > 1e-9]
    if len(w) < 2:
        return 0.0
    return float(-(w * np.log2(w)).sum())

def attribute_values(cands: pd.DataFrame, attr: str):
    if attr == "dominant_color":
        import json
        vals = []
        for v in cands.get("dominant_colors", []):
            try:
                lst = json.loads(v) if isinstance(v, str) else (v or [])
                vals.append(lst[0] if lst else None)
            except Exception:
                vals.append(None)
        return vals
    if attr == "has_text":
        return [bool(v) for v in cands.get("has_text", [False] * len(cands))]
    return list(cands.get(attr, [None] * len(cands)))

def next_question(cands: pd.DataFrame, state: dict, moments: List[dict]) -> Optional[dict]:
    """state: {answered: {attr: value}, dont_know: {attr: count}, asked: set, round: int}"""
    if state.get("round", 0) >= MAX_ROUNDS:
        return None
    if len(cands) < 2:
        return None
    scores = cands["score"].to_numpy(dtype="float64")[:TOP_K]
    w = _softmax(scores / SOFTMAX_T)

    # concentration stop: top moment holds >= 55% of weight mass
    if moments:
        mass = 0.0
        for m in moments:
            ids = set(m["img_ids"])
            mass += float(w[cands["img_id"].isin(ids).to_numpy()[:len(w)]].sum())
        if mass >= 0.55:
            return None

    answered = state.get("answered", {})
    dont = state.get("dont_know", {})
    asked = set(state.get("asked", set()))
    best = None
    for attr in ATTR_COLUMNS:
        if attr in answered or attr in asked:
            continue
        prior = PRIORS.get(attr, 0.5)
        decay = 0.5 ** int(dont.get(attr, 0))
        vals = attribute_values(cands, attr)
        unique = [v for v in vals if v is not None and str(v) != ""]
        if len(set(unique)) < 2:
            continue
        counts = {}
        for v, wi in zip(vals, w):
            if v is None or str(v) == "":
                continue
            counts[v] = counts.get(v, 0.0) + wi
        total = sum(counts.values())
        if total < 1e-9:
            continue
        dist = np.array([counts[v] / total for v in counts])
        h = _entropy_bits(dist)
        if h < 0.4:
            continue
        priority = h * prior * decay
        if best is None or priority > best["priority"]:
            order = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
            best = {"attribute": attr, "text": QUESTION_TEXT[attr],
                    "options": [str(v) for v, _ in order] + ["Something else", "I don't remember"],
                    "expected_info_gain": round(h, 3), "priority": priority}
    return best
