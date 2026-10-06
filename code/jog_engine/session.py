"""M6 — JogSession: the state machine driving the UI."""
import time
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .anchors import apply_anchor
from .clusters import moments as moments_fn
from .config import MAX_ROUNDS, TOP_K
from .cues import Cue, parse_memory
from .explain import why_matched
from .fallback import narrowed_window
from .feedback import pick_pair, update_query_vec
from .questions import next_question
from .retrieval import Retriever

ATTR_TO_CUE = {"indoor_outdoor": "indoor_outdoor", "time_of_day": "time_of_day",
               "place_name": "place", "setting_type": "setting_type",
               "season_hint": "season", "people_count_bucket": "other",
               "has_text": "text_in_image", "dominant_color": "visual_detail"}


@dataclass
class JogSession:
    retriever: Retriever
    meta: object = None
    emb: object = None
    img_index: dict = field(default_factory=dict)
    cues: list = field(default_factory=list)
    time_window: object = None
    anchor_window: tuple = None
    q_vec: object = None
    answered: dict = field(default_factory=dict)
    dont_know: dict = field(default_factory=dict)
    asked: set = field(default_factory=set)
    pos: list = field(default_factory=list)
    neg: list = field(default_factory=list)
    round: int = 0
    parse_source: Optional[str] = None
    scored: object = None
    start_ts: float = 0.0

    def __post_init__(self):
        self.meta = self.meta if self.meta is not None else self.retriever.meta
        self.emb = self.emb if self.emb is not None else self.retriever.emb
        self.img_index = self.img_index or {i: n for n, i in enumerate(self.retriever.img_ids)}

    # ---------- helpers ----------
    def _rescore(self):
        self.scored = self.retriever.top_k(self.q_vec, self.cues, self.time_window,
                                           k=TOP_K, anchor_window=self.anchor_window)

    def _moments(self):
        return moments_fn(self.scored, self.meta)

    def _state(self, question=None, pair=None):
        moments = self._moments()
        state = {
            "round": self.round,
            "parse_source": self.parse_source,
            "cues": [c.model_dump() if hasattr(c, "model_dump") else dict(c) for c in self.cues],
            "time_window": (self.time_window.model_dump() if self.time_window else None),
            "moments": moments,
            "question": question,
            "pair": pair,
            "fallback": None,
            "top": [],
        }
        if self.round >= MAX_ROUNDS:
            state["fallback"] = narrowed_window(moments, self.meta)
        if self.scored is not None:
            for _, r in self.scored.head(12).iterrows():
                row = r.to_dict()
                state["top"].append({
                    "img_id": row["img_id"], "filename": row.get("filename"),
                    "score": round(float(row["score"]), 4),
                    "caption": str(row.get("caption", ""))[:120],
                    "timestamp": str(row.get("timestamp", ""))[:10],
                    "place": row.get("place_name"),
                    "why": why_matched(row, self.cues),
                })
        return state

    def _maybe_pair(self):
        if self.round == 0:
            return None
        if (self.round - 1) % 2 != 0:  # after the first answered question and every 2nd round
            return None
        return pick_pair(self.scored, self.q_vec, self.emb, top_n=12)

    # ---------- API ----------
    def start(self, text: str, live_session=None) -> dict:
        self.start_ts = time.time()
        parsed, source = parse_memory(text, history={"cues": self.cues}, live_session=live_session)
        self.parse_source = source
        self.cues = parsed.cues
        self.time_window = parsed.time_window
        if parsed.anchor and (parsed.anchor.description or parsed.anchor.relation):
            self._resolve_anchor(parsed.anchor)
        self.q_vec = self.retriever.encode_visual_query(parsed.visual_query)
        if self.q_vec is None and self.cues:
            self._rescore()
        else:
            self._rescore()
        question = None
        moments = self._moments()
        q = next_question(self.scored, self._qstate(), moments)
        if q:
            self.asked.add(q["attribute"])
            question = q
        return self._state(question=question, pair=None)

    def _qstate(self):
        return {"answered": self.answered, "dont_know": self.dont_know,
                "asked": self.asked, "round": self.round}

    def _resolve_anchor(self, anchor):
        """Resolve an anchor description to the best-matching image (CLIP)."""
        if not anchor.description:
            return
        v = self.retriever.encode_text(anchor.description)
        if v is None:
            return
        sims = self.retriever.emb @ v
        best_i = int(np.argmax(sims))
        img_id = self.retriever.img_ids[best_i]
        row = self.meta[self.meta["img_id"] == img_id]
        if row.empty:
            return
        ts = row["timestamp"].iloc[0]
        rel = anchor.relation or "around"
        rel = {"after": "right_after", "before": "right_before", "during": "same_day",
               "near": "around"}.get(rel, "around")
        self.anchor_window = apply_anchor(ts, rel)

    def answer(self, attribute: str, value: str) -> dict:
        if value in ("I don't remember", None, ""):
            self.dont_know[attribute] = self.dont_know.get(attribute, 0) + 1
        elif value != "Something else":
            self.answered[attribute] = value
            ctype = ATTR_TO_CUE.get(attribute, "other")
            self.cues = [c for c in self.cues if c.type != ctype]
            self.cues.append(Cue(type=ctype, value=value, certainty="sure"))
        self.round += 1
        self._rescore()
        question = None
        q = next_question(self.scored, self._qstate(), self._moments())
        if q:
            self.asked.add(q["attribute"])
            question = q
        return self._state(question=question, pair=self._maybe_pair())

    def choose(self, pair_choice: str, pair: dict) -> dict:
        if pair_choice in ("left", "right"):
            pos = [pair[pair_choice]]
            neg = [pair["left" if pair_choice == "right" else "right"]]
        else:
            pos, neg = [], [pair["left"], pair["right"]]
        self.pos.extend(pos)
        self.neg.extend(neg)
        if self.q_vec is not None:
            self.q_vec = update_query_vec(self.q_vec, self.pos, self.neg, self.emb, self.img_index)
        if pos:
            row = self.meta[self.meta["img_id"] == pos[0]]
            if not row.empty:
                r = row.iloc[0]
                for attr in ("setting_type", "time_of_day"):
                    v = r.get(attr)
                    if v and not any(c.type == attr for c in self.cues):
                        self.cues.append(Cue(type=attr, value=v, certainty="unsure"))
        self.round += 1
        self._rescore()
        question = None
        q = next_question(self.scored, self._qstate(), self._moments())
        if q:
            self.asked.add(q["attribute"])
            question = q
        return self._state(question=question, pair=None)

    def set_anchor(self, img_id: str, relation: str) -> dict:
        row = self.meta[self.meta["img_id"] == img_id]
        if row.empty:
            return self._state()
        ts = row["timestamp"].iloc[0]
        self.anchor_window = apply_anchor(ts, relation)
        self.round += 1
        self._rescore()
        question = None
        q = next_question(self.scored, self._qstate(), self._moments())
        if q:
            self.asked.add(q["attribute"])
            question = q
        return self._state(question=question, pair=None)

    def edit_cues(self, new_cues: List[dict]) -> dict:
        cues = []
        for c in new_cues:
            if isinstance(c, dict):
                if c.get("remove"):
                    continue
                ctype = c.get("type", "visual_detail")
                val = c.get("value", "")
                if not val:
                    continue
                cues.append(Cue(type=ctype, value=str(val),
                                certainty=c.get("certainty", "unsure"),
                                negated=bool(c.get("negated", False))))
        self.cues = cues
        self._rescore()
        question = None
        q = next_question(self.scored, self._qstate(), self._moments())
        if q:
            self.asked.add(q["attribute"])
            question = q
        return self._state(question=question, pair=None)

    def confirm(self, img_id: str) -> dict:
        return {"confirmed": img_id, "seconds": round(time.time() - self.start_ts, 1),
                "rounds": self.round}

    def state_summary(self) -> dict:
        return self._state()
