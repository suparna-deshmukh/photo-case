"""M6 — Retriever: score = W_VISUAL*vis + W_TIME*time + W_PLACE*place + W_ATTR*attr."""
import math
import re
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
import pandas as pd

from .clusters import gazetteer, _gaz_terms
from .config import (CERTAINTY, PLACE_KM, TOP_K, UNSURE_WIDEN_DAYS, W_ATTR, W_PLACE,
                     W_TIME, W_VISUAL, TIME_DECAY_DAYS)
from .cues import Cue


def _haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, asin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


class Retriever:
    def __init__(self, meta_df: pd.DataFrame, image_emb: np.ndarray, clip_model):
        self.meta = meta_df.reset_index(drop=True)
        self.emb = np.asarray(image_emb, dtype="float32")
        self.clip = clip_model
        self.img_ids = self.meta["img_id"].tolist()
        self.timestamps = pd.to_datetime(self.meta["timestamp"])

    def encode_text(self, text: str) -> np.ndarray:
        if not text or not text.strip():
            return None
        v = self.clip.encode([text[:300]], convert_to_numpy=True, normalize_embeddings=True)
        return v[0].astype("float32")

    def visual_sim(self, q_vec: np.ndarray) -> np.ndarray:
        if q_vec is None:
            return np.zeros(len(self.meta), dtype="float32")
        return self.emb @ q_vec

    def _minmax(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype="float64")
        lo, hi = x.min(), x.max()
        if hi - lo < 1e-9:
            return np.zeros_like(x)
        return (x - lo) / (hi - lo)

    @staticmethod
    def _aware(ts):
        t = pd.Timestamp(ts)
        if t.tzinfo is None:
            t = t.tz_localize("Asia/Kolkata")
        return t

    def _time_match(self, time_window, day: pd.Timestamp) -> float:
        if time_window is None:
            return 0.0
        start = time_window.start
        if not start:
            return 0.0
        s = self._aware(start)
        e = self._aware(time_window.end) if time_window.end else s + pd.Timedelta(days=60)
        widen = UNSURE_WIDEN_DAYS if time_window.certainty == "unsure" else 0
        s = s - pd.Timedelta(days=widen)
        e = e + pd.Timedelta(days=widen)
        if s <= day <= e:
            return 1.0
        gap_days = (s - day).days if day < s else (day - e).days
        decay = 1.0 - gap_days / TIME_DECAY_DAYS
        return max(0.0, decay)

    def _place_match(self, cues, row) -> float:
        place_cues = [c for c in cues if c.type == "place"]
        if not place_cues:
            return 0.0
        best = 0.0
        for c in place_cues:
            if c.negated:
                continue
            targets = {c.value.lower()}
            info = gazetteer().get(c.value)
            if info:
                for a in info.get("aliases", []):
                    targets.add(str(a).lower())
            hit = False
            row_place = str(row.get("place_name", "")).lower()
            row_area = str(row.get("area", "")).lower()
            for t in targets:
                if t in row_place or t in row_area:
                    hit = True
                    break
            if not hit and row.get("lat") is not None and info:
                try:
                    d = _haversine_km(row["lat"], row["lon"], info["lat"], info["lon"])
                    if d < PLACE_KM:
                        hit = True
                except Exception:
                    pass
            if hit:
                best = max(best, CERTAINTY.get(c.certainty, 0.5))
        return best

    def _attr_match(self, cues, row) -> float:
        parts = []
        attr_map = {
            "indoor_outdoor": "indoor_outdoor",
            "time_of_day": "time_of_day",
            "setting_type": "setting_type",
            "season": "season_hint",
        }
        for c in cues:
            if c.negated:
                continue
            if c.type in attr_map:
                col = attr_map[c.type]
                val = str(row.get(col, "") or "").lower()
                cv = c.value.lower()
                superset = {"daytime": {"morning", "afternoon"},
                            "nighttime": {"evening", "night"}}.get(cv)
                if val and (cv == val or (superset is not None and val in superset)):
                    parts.append((1.0, CERTAINTY.get(c.certainty, 0.5)))
                else:
                    parts.append((0.0, CERTAINTY.get(c.certainty, 0.5)))
            elif c.type == "object":
                cap = str(row.get("caption", "") or "").lower()
                objs = _json_list(row.get("objects"))
                blob = cap + " " + " ".join(objs)
                hit = c.value.lower() in blob
                parts.append((1.0 if hit else 0.0, CERTAINTY.get(c.certainty, 0.5)))
        if not parts:
            return 0.0
        return sum(s * m for s, m in parts) / len(parts)

    def score(self, q_vec, cues: List[Cue], time_window=None,
              anchor_window=None) -> pd.DataFrame:
        vis = self.visual_sim(q_vec)
        vis_n = self._minmax(vis)
        ts = self.timestamps
        time_m = np.array([self._time_match(time_window, d) for d in ts], dtype="float64")
        if anchor_window is not None:
            s, e = self._aware(anchor_window[0]), self._aware(anchor_window[1])
            a = np.where((ts >= s) & (ts <= e), 1.0, 0.0)
            time_m = np.maximum(time_m, a)
        rows = self.meta.to_dict("records")
        place_m = np.array([self._place_match(cues, r) for r in rows])
        attr_m = np.array([self._attr_match(cues, r) for r in rows])

        # negated cues: subtract 0.5 where they match
        neg_pen = np.zeros(len(rows), dtype="float64")
        for c in cues:
            if not c.negated:
                continue
            for r in rows:
                if c.type == "place":
                    blob = (str(r.get("place_name", "")) + " " + str(r.get("area", ""))).lower()
                    if c.value.lower() in blob:
                        neg_pen[self.meta["img_id"].tolist().index(r["img_id"])] -= 0.5
                elif c.type in ("indoor_outdoor", "time_of_day", "setting_type", "season"):
                    col = {"indoor_outdoor": "indoor_outdoor", "time_of_day": "time_of_day",
                           "setting_type": "setting_type", "season": "season_hint"}[c.type]
                    if str(r.get(col, "")).lower() == c.value.lower():
                        neg_pen[self.meta["img_id"].tolist().index(r["img_id"])] -= 0.5
                elif c.type == "object":
                    blob = str(r.get("caption", "") or "").lower()
                    if c.value.lower() in blob:
                        neg_pen[self.meta["img_id"].tolist().index(r["img_id"])] -= 0.5

        total = (W_VISUAL * vis_n + W_TIME * time_m + W_PLACE * place_m + W_ATTR * attr_m) + neg_pen
        out = pd.DataFrame({
            "img_id": self.img_ids,
            "score": total,
            "vis": W_VISUAL * vis_n,
            "time": W_TIME * time_m,
            "place": W_PLACE * place_m,
            "attr": W_ATTR * attr_m,
            "cos": vis,
        })
        extra = self.meta[["img_id", "filename", "timestamp", "place_name", "area",
                           "event_id", "setting_type", "time_of_day", "caption"]]
        out = out.merge(extra, on="img_id", how="left")
        return out.sort_values("score", ascending=False).reset_index(drop=True)

    def top_k(self, q_vec, cues, time_window=None, k=TOP_K, anchor_window=None) -> pd.DataFrame:
        return self.score(q_vec, cues, time_window, anchor_window).head(k)

    def encode_visual_query(self, visual_query: str):
        return self.encode_text(visual_query)


def _json_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    try:
        import json
        out = json.loads(v)
        return out if isinstance(out, list) else []
    except Exception:
        return []
