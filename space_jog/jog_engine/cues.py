"""M6 — Cue models + parse_memory dispatcher (cache -> llm -> rules)."""
import json
import re
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

PKG_DIR = Path(__file__).resolve().parent
CODE_DIR = PKG_DIR.parent if PKG_DIR.name == "jog_engine" else PKG_DIR.parent
sys.path.insert(0, str(CODE_DIR))

from .config import CUE_TYPES, TODAY  # noqa: E402


class Cue(BaseModel):
    type: str  # one of CUE_TYPES (validated loosely to survive LLM drift)
    value: str
    certainty: str = "unsure"  # sure | unsure
    negated: bool = False


class TimeWindow(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    certainty: str = "unsure"  # sure | unsure


class Anchor(BaseModel):
    description: Optional[str] = None
    relation: Optional[str] = None  # before | after | during | near | None


class ParsedMemory(BaseModel):
    cues: List[Cue] = []
    time_window: Optional[TimeWindow] = None
    visual_query: str = ""
    anchor: Optional[Anchor] = None


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


LIVE_PROMPT = (
    "You convert a person's vague memory of a photo into structured search cues. "
    "Today is {today}. Return JSON: {{\"cues\":[{{\"type\":\"place|time_window|person|object|activity|"
    "setting_type|visual_detail|time_of_day|indoor_outdoor|season|anchor_event|purpose|text_in_image|emotion\","
    "\"value\":string,\"certainty\":\"sure|unsure\",\"negated\":boolean}}],\"time_window\":{{\"start\":\"YYYY-MM-DD or null\","
    "\"end\":\"YYYY-MM-DD or null\",\"certainty\":\"sure|unsure\"}},\"visual_query\":\"<=20 English words describing how the photo "
    "LOOKS (objects, scene, colors), no places or dates\",\"anchor\":{{\"description\":string or null,"
    "\"relation\":\"before|after|during|near|null\"}}}}. Rules: words like 'I think', 'maybe', 'not sure', 'around' make certainty "
    "'unsure'. Resolve relative dates ('last winter', 'two years ago', 'around Diwali 2022', 'monsoon 2023') into a plausible date "
    "range and mark unsure unless a precise date is given. Never invent cues the person did not state. A cue the person says is "
    "definitely NOT true gets negated=true. If nothing is known about a field, omit it."
)


def _strip_dangling_anchor(parsed):
    """If the anchor object is empty, drop stray anchor_event cues (LLM drift)."""
    if not (parsed.anchor and (parsed.anchor.description or parsed.anchor.relation)):
        parsed.cues = [c for c in parsed.cues if c.type != "anchor_event"]
    return parsed


def _coerce_parsed(obj: dict) -> ParsedMemory:
    cues = []
    for c in obj.get("cues") or []:
        if isinstance(c, str):
            cues.append(Cue(type="visual_detail", value=c, certainty="unsure"))
        elif isinstance(c, dict):
            ctype = c.get("type") or "visual_detail"
            if ctype not in CUE_TYPES:
                ctype = "other" if ctype else "visual_detail"
            if ctype == "other":
                ctype = "visual_detail"
            cert = c.get("certainty") or "unsure"
            cues.append(Cue(type=ctype, value=str(c.get("value") or c.get("cue") or ""),
                            certainty=cert if cert in ("sure", "unsure") else "unsure",
                            negated=bool(c.get("negated", False))))
    tw = obj.get("time_window")
    time_window = None
    if isinstance(tw, dict) and (tw.get("start") or tw.get("end")):
        time_window = TimeWindow(start=tw.get("start"), end=tw.get("end"),
                                 certainty=tw.get("certainty") or "unsure")
    anchor_obj = obj.get("anchor")
    anchor = None
    if isinstance(anchor_obj, dict) and (anchor_obj.get("description") or anchor_obj.get("relation")):
        anchor = Anchor(description=anchor_obj.get("description"),
                        relation=anchor_obj.get("relation") or None)
    visual = obj.get("visual_query") or ""
    return ParsedMemory(cues=cues, time_window=time_window, visual_query=str(visual), anchor=anchor)


def parse_memory(text: str, history=None, session=None, live_session=None):
    """Dispatch: (1) cache lookup in task_parses.json; (2) live LLM if available; (3) rules.

    Returns (ParsedMemory, parse_source) with parse_source in {"cache","llm","rules"}.
    Never raises; falls back to rules on any failure. live_session is the live-layer
    session dict used for PER_SESSION_CAP accounting (may be None).
    """
    from .cues_rules import parse_rules
    norm = normalize_text(text)
    # 1) cache
    try:
        candidates = [
            PKG_DIR.parent / "data" / "task_parses.json",
            CODE_DIR.parent / "library" / "task_parses.json",
            PKG_DIR.parent / "library" / "task_parses.json",
        ]
        parse_file = next((p for p in candidates if p.exists()), None)
        if parse_file is not None:
            data = json.loads(parse_file.read_text())
            entry = data.get(norm)
            if isinstance(entry, dict) and entry.get("llm"):
                return _strip_dangling_anchor(_coerce_parsed(entry["llm"])), "cache"
    except Exception:
        pass
    # 2) live LLM
    try:
        import live_llm
        if live_llm.live_status().get("available"):
            system = LIVE_PROMPT.format(today=TODAY)
            user = f"Memory text:\n\"\"\"\n{text[:600]}\n\"\"\"\n\nReturn the JSON object."
            res = live_llm.live_json(system, user, session=live_session)
            if isinstance(res, dict) and "_error" not in res:
                return _strip_dangling_anchor(_coerce_parsed(res)), "llm"
    except Exception:
        pass
    # 3) rules
    return parse_rules(text, history=history), "rules"
