"""M6 — Rule-based memory parser (PRIMARY path; no LLM, no network).

parse_rules(text, today=TODAY, history=None) -> ParsedMemory
"""
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

from rapidfuzz import fuzz

from .config import LIBRARY_END, TODAY
from .cues import Anchor, Cue, ParsedMemory, TimeWindow, normalize_text

_PKG = Path(__file__).resolve().parent

# ---------------- gazetteer ----------------
DEFAULT_GAZETTEER = {
    "Goa": {"lat": 15.4909, "lon": 73.8278, "aliases": ["Panjim", "Palolem", "Panaji"]},
    "Zuarinagar Goa": {"lat": 15.391, "lon": 73.878, "aliases": ["BITS Goa", "campus", "Zuarinagar"]},
    "Bengaluru": {"lat": 12.9716, "lon": 77.5946, "aliases": ["Bangalore"]},
    "Pondicherry": {"lat": 11.9416, "lon": 79.8083, "aliases": ["Puducherry", "Pondy"]},
    "Gokarna": {"lat": 14.5479, "lon": 74.3188, "aliases": []},
    "Hampi": {"lat": 15.335, "lon": 76.46, "aliases": []},
    "Pune": {"lat": 18.5204, "lon": 73.8567, "aliases": []},
}

_gaz_cache = None

def gazetteer():
    global _gaz_cache
    if _gaz_cache is None:
        try:
            p = _PKG.parent.parent / "library" / "gazetteer.json"
            if p.exists():
                _gaz_cache = json.loads(p.read_text())
            else:
                _gaz_cache = DEFAULT_GAZETTEER
        except Exception:
            _gaz_cache = DEFAULT_GAZETTEER
    return _gaz_cache

def _gaz_terms():
    terms = {}
    for place, info in gazetteer().items():
        terms[place.lower()] = place
        for a in info.get("aliases", []):
            terms[a.lower()] = place
    return terms

# ---------------- lexicons ----------------
HEDGES = ["think", "maybe", "might", "probably", "around", "somewhere", "guess",
          "believe", "could", "ish", "roughly", "or so"]
NEGATORS = ["not", "wasn't", "isn't", "weren't", "never", "didn't", "don't", "no"]

TOD_WORDS = {
    "morning": ["morning", "breakfast", "early"],
    "afternoon": ["afternoon", "lunch", "midday"],
    "evening": ["evening", "dinner", "dusk"],
    "night": ["night", "midnight", "late"],
}
# Words that describe a VISIBLE scene rather than a stated time: they imply a
# time of day (inference -> certainty "unsure") and are kept as visual cues too.
INFERRED_TOD = {"sunset": "evening", "sunrise": "morning"}
# Multi-word / ambiguous expressions, checked before the single-word lists.
# "daytime" is a superset value: it matches morning and afternoon images alike.
TOD_PHRASES = {
    "daytime": ["during the day", "in the day", "by day", "middle of the day",
                "daytime", "daylight"],
    "morning": ["in the morning", "first thing in the morning", "early in the morning"],
    "evening": ["in the evening", "later in the day", "towards the evening"],
    "night": ["late at night", "in the middle of the night", "after dark"],
}
INDOOR_WORDS = ["indoors", "indoor", "inside", "interior"]
OUTDOOR_WORDS = ["outdoors", "outdoor", "outside"]

SETTING_KEYWORDS = [
    ("cafe", ["cafe", "café", "coffee", "latte", "espresso", "chai", "teashop"]),
    ("beach", ["beach", "sea", "shore", "coast", "sand"]),
    ("classroom_or_study", ["whiteboard", "classroom", "class", "exam", "library", "notes", "study", "bookshelf"]),
    ("document_or_utility", ["receipt", "ticket", "prescription", "medicine", "tablet", "blister", "timetable", "screenshot"]),
    ("temple_or_ruins", ["ruins", "ruin", "temple", "monument", "boulder", "idol"]),
    ("office", ["office", "desk", "laptop", "work", "internship", "meeting"]),
    ("party_or_event", ["concert", "party", "fest", "stage", "dance", "celebration", "fireworks"]),
    ("hostel_or_home", ["hostel", "dorm", "room", "home", "corridor", "bedroom"]),
    ("restaurant", ["restaurant", "food", "meal", "dinner", "lunch", "seafood", "sweets", "modak", "dining"]),
    ("shop_or_market", ["market", "shop", "mall", "store", "pharmacy"]),
    ("transport", ["metro", "train", "bus", "flight", "scooter", "bicycle", "bike", "car"]),
    ("campus", ["campus", "college", "university", "hostel corridor"]),
    ("street", ["street", "road", "traffic", "promenade", "alley"]),
    ("nature_landscape", ["mountain", "forest", "hill", "landscape", "valley", "cliff", "river"]),
]

OBJECT_WORDS = ["coffee", "cup", "boat", "sailboat", "bicycle", "bike", "cat", "dog", "food", "plate",
                "sunset", "fire", "bonfire", "medicine", "tablet", "blister", "notebook",
                "notes", "note", "whiteboard", "book", "window", "rain", "flower", "idol",
                "sweets", "ticket", "receipt", "palm", "coracle", "diya", "rangoli", "selfie",
                "laptop", "thermometer", "soup", "chai", "tea", "croissant", "pastries",
                "umbrella", "balloon", "city", "rooftop", "sky", "sea", "mountain"]
ACTIVITY_WORDS = ["walking", "cycling", "eating", "dancing", "studying", "working",
                  "cooking", "playing", "reading", "sleeping", "shopping", "driving",
                  "swimming", "hiking", "photographing"]
PERSON_WORDS = ["friends", "friend", "family", "cousin", "mom", "mum", "dad", "sister",
                "brother", "roommate", "my team", "colleagues"]
PURPOSE_RE = re.compile(r"\b(?:so (?:i|we) (?:could|would|can) (?:remember|not forget|keep)|to remember|remember the|so i took|took it to|i took it)\b", re.I)
TEXT_IN_IMG_RE = re.compile(r"\b(?:the (?:receipt|ticket|paper|board|screen|note) (?:said|showed|had)|it (?:said|showed|had)|number on it|written on)\b", re.I)
EMOTION_RE = re.compile(r"\b(?:so happy|very happy|happy day|felt (?:so )?(?:happy|peaceful|good)|best day|unforgettable|wonderful|beautiful day|such a)\b", re.I)

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
SEASON_WINDOWS = {
    "winter": (12, 1, 2),
    "summer": (3, 4, 5),
    "monsoon": (6, 7, 8, 9),
}

def _days_in_year(y, m):
    import calendar
    return calendar.monthrange(y, m)[1]

def _clamp(d: date) -> date:
    lo = date(2022, 8, 1)
    hi = date.fromisoformat(LIBRARY_END)
    return max(lo, min(hi, d))

# ---------------- helpers ----------------
def _tokens(text: str):
    return re.findall(r"[a-z']+", text.lower())

def _has_hedge_near(text: str, start: int, end: int, tokens, spans) -> bool:
    """hedge word within 4 tokens before the match span"""
    match_start = text.lower().find(text[start:end], max(0, start - 40))
    before = text[:match_start].lower().split()
    tail = before[-4:] if len(before) >= 4 else before
    for h in HEDGES:
        if h in tail:
            return True
    if "not sure" in " ".join(tail) or "i think" in " ".join(tail):
        return True
    return False

def _negated_near(text: str, start: int, end: int) -> bool:
    match_start = text.lower().find(text[start:end], max(0, start - 30))
    before = text[:match_start].lower().split()
    tail = before[-3:] if len(before) >= 3 else before
    for n in NEGATORS:
        if n in tail:
            return True
    return False

def _find_cue(text: str, words, cue_type, value=None, tokens=None):
    """Find first occurrence of any word; return (start, end) or None."""
    for w in words:
        m = re.search(r"\b" + re.escape(w) + r"\b", text, re.I)
        if m:
            return m.start(), m.end()
    return None

# ---------------- date resolution ----------------
def _season_month(season: str, y: int, today: date):
    if season == "winter":
        return y, 12
    if season == "summer":
        return y, 4
    return y, 7  # monsoon

def _season_year(season: str, explicit_year, today: date, has_last: bool, has_this: bool):
    if explicit_year:
        return int(explicit_year)
    if has_last:
        return today.year - 1
    months = SEASON_WINDOWS[season]
    cur = today.month
    in_cur = any(mm == cur for mm in months) or (season == "winter" and cur in (1, 2, 12))
    return today.year if in_cur else today.year - 1

def _resolve_time_window(text: str, today: date):
    """Return (TimeWindow|None, certainty). Picks the most specific date expression."""
    low = text.lower()
    cands = []  # (specificity, year, month, day, certainty)

    m = re.search(r"\b(\d{1,2})\s+([a-z]{3,9})(?:st|nd|rd|th)?\s+(\d{4})\b", low)
    if m and m.group(2) in MONTHS:
        cands.append((5, int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)), "sure"))

    m = re.search(r"\b(?:around|during|for|on|near)\s+(?:the\s+)?diwali\s*(\d{4})?\b", low)
    if m:
        y = int(m.group(1)) if m.group(1) else (today.year if today.month >= 10 else today.year - 1)
        cands.append((4, y, 10, 10, "unsure"))

    m = re.search(r"\b(?:around|during|for|on|near)\s+(?:the\s+)?ganesh\s+chaturthi\s*(\d{4})?\b", low)
    if m:
        y = int(m.group(1)) if m.group(1) else (today.year if today.month >= 8 else today.year - 1)
        cands.append((4, y, 8, 20, "unsure"))

    m = re.search(r"\b(?:around|last|this|the|in|during)?\s*(winter|summer|monsoon)\b(\s+(\d{4}))?", low)
    if m:
        season = m.group(1)
        explicit_year = m.group(3)
        has_last = bool(re.search(r"\blast\s+" + season + r"\b", low))
        has_this = bool(re.search(r"\bthis\s+" + season + r"\b", low))
        y = _season_year(season, explicit_year, today, has_last, has_this)
        yy, mm = _season_month(season, y, today)
        cands.append((3, yy, mm, 10, "unsure"))

    m = re.search(r"\b(?:two|2)\s+years?\s+ago\b", low)
    if m:
        cands.append((2, today.year - 2, today.month, today.day, "unsure"))
    m = re.search(r"\b(?:three|3)\s+years?\s+ago\b", low)
    if m:
        cands.append((2, today.year - 3, today.month, today.day, "unsure"))
    m = re.search(r"\blast\s+year\b", low)
    if m:
        cands.append((2, today.year - 1, today.month, today.day, "unsure"))

    for mm_name, mm_num in MONTHS.items():
        m = re.search(r"\b(?:in|on|during)\s+" + mm_name + r"(?:\s+(\d{4}))?\b", low)
        if m:
            y = int(m.group(1)) if m.group(1) else today.year
            if y > today.year:
                y = today.year - 1
            cands.append((3, y, mm_num, 1, "unsure"))
            break

    m = re.search(r"\b(19|20)\d{2}\b", low)
    if m:
        y = int(m.group(0))
        cands.append((1, y, today.month, today.day, "unsure"))

    if not cands:
        return None
    cands.sort(key=lambda c: -c[0])
    _spec, y, mo, d, certainty = cands[0]
    try:
        start = _clamp(date(y, mo, d))
    except ValueError:
        start = _clamp(date(y, mo, 1))
    return TimeWindow(start=start.isoformat(), end=None, certainty=certainty)

# ---------------- helpers ----------------
def _tokens(text: str):
    return re.findall(r"[a-z']+", text.lower())

def _has_hedge_near(text: str, start: int, end: int, tokens, spans) -> bool:
    """hedge word within 4 tokens before the match span"""
    match_start = text.lower().find(text[start:end], max(0, start - 40))
    before = text[:match_start].lower().split()
    tail = before[-4:] if len(before) >= 4 else before
    for h in HEDGES:
        if h in tail:
            return True
    if "not sure" in " ".join(tail) or "i think" in " ".join(tail):
        return True
    return False

def _negated_near(text: str, start: int, end: int) -> bool:
    match_start = text.lower().find(text[start:end], max(0, start - 30))
    before = text[:match_start].lower().split()
    tail = before[-3:] if len(before) >= 3 else before
    for n in NEGATORS:
        if n in tail:
            return True
    return False

def _find_cue(text: str, words, cue_type, value=None, tokens=None):
    """Find first occurrence of any word; return (start, end) or None."""
    for w in words:
        m = re.search(r"\b" + re.escape(w) + r"\b", text, re.I)
        if m:
            return m.start(), m.end()
    return None

# ---------------- date resolution ----------------
def _resolve_time_window(text: str, today: date):
    """Return (TimeWindow|None, list of (start,end) spans consumed by date expressions)."""
    low = text.lower()
    consumed = []
    cands = []  # (specificity, start, end, certainty)

    def add(spec, y, m, d, certainty):
        try:
            start = _clamp(date(y, m, d))
        except ValueError:
            return
        cands.append((spec, start, certainty))
        consumed.append((start.isoformat(), certainty))

    # precise day: "14 february 2023" / "14 feb 2023"
    m = re.search(r"\b(\d{1,2})\s+([a-z]{3,9})(?:st|nd|rd|th)?\s+(\d{4})\b", low)
    if m and m.group(2) in MONTHS:
        add(5, int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)), "sure")
        consumed_span = (m.start(), m.end())
    else:
        # "around diwali 2022" / "around ganesh chaturthi"
        m = re.search(r"\b(?:around|during|for|around|on|near)?\s*diwali\s*(\d{4})?\b", low)
        if m:
            y = int(m.group(1)) if m.group(1) else today.year - (0 if today.month >= 10 else 1)
            add(4, y, 10, 10, "unsure")
            consumed_span = (m.start(), m.end())
        else:
            m = re.search(r"\b(?:around|during|for|near)?\s*ganesh\s+chaturthi\s*(\d{4})?\b", low)
            if m:
                y = int(m.group(1)) if m.group(1) else today.year - (0 if today.month >= 8 else 1)
                add(4, y, 8, 20, "unsure")
                consumed_span = (m.start(), m.end())
            else:
                # season (+ optional year): "monsoon 2023", "last winter", "winter last year"
                m = re.search(r"\b(winter|summer|monsoon)\b(?:\s+(\d{4}))?", low)
                rel_year = None
                if re.search(r"\blast\s+(?:year|winter|summer|monsoon)\b", low):
                    rel_year = today.year - 1
                    if m and (m.group(1) == "winter" or m.group(1) == "summer" or m.group(1) == "monsoon"):
                        pass
                elif re.search(r"\b(?:two|2)\s+years?\s+ago\b", low):
                    rel_year = today.year - 2
                elif re.search(r"\b(?:three|3)\s+years?\s+ago\b", low):
                    rel_year = today.year - 3
                elif re.search(r"\blast\s+year\b", low):
                    rel_year = today.year - 1
                if m:
                    season = m.group(1)
                    y = int(m.group(2)) if m.group(2) else (rel_year or today.year)
                    if season == "monsoon" and (y == today.year or (rel_year and rel_year <= today.year)):
                        first_month = 6
                    else:
                        first_month = SEASON_WINDOWS[season][0] if season != "monsoon" else 6
                    months = SEASON_WINDOWS[season]
                    # pick the month of the season that belongs to year y
                    chosen = None
                    for mm in months:
                        if mm == 12 or (first_month <= mm <= 12):
                            chosen = (y, mm)
                        elif mm == 1:
                            chosen = (y, mm)
                    if season == "winter":
                        chosen = (y, 12)
                    if season == "summer":
                        chosen = (y, 4)
                    if season == "monsoon":
                        chosen = (y, 7)
                    add(3, chosen[0], chosen[1], 10, "unsure")
                else:
                    # month names, possibly several: "april or may", "(last year)"
                    months_found = []
                    for mm_name in sorted(MONTHS, key=len, reverse=True):
                        m2 = re.search(r"\b(?:in|on|during)?\s*" + mm_name + r"(?:\s+(\d{4}))?\b", low)
                        if not m2:
                            continue
                        if mm_name == "may":
                            after = low[m2.end():m2.end() + 4]
                            if re.match(r"\s+(i|we|you|he|she|it|there|a|an|could|would)\b", after):
                                continue
                        if m2.group(1):
                            y = int(m2.group(1))
                        elif rel_year:
                            y = rel_year
                        else:
                            near = low[max(0, m2.start() - 30):m2.end() + 12]
                            ym = re.search(r"\b((?:19|20)\d{2})\b", near)
                            y = int(ym.group(1)) if ym else today.year
                            if y == today.year and MONTHS[mm_name] < today.month:
                                y = today.year - 1
                        months_found.append((y, MONTHS[mm_name]))
                    if months_found:
                        (y0, m0), (y1, m1) = min(months_found), max(months_found)
                        start = _clamp(date(y0, m0, 1))
                        end = _clamp(date(y1, m1, _days_in_year(y1, m1)))
                        cands.append((4, start, "unsure", end))
                        consumed.append((start.isoformat(), "unsure"))
                    elif re.search(r"\b(?:two|2)\s+years?\s+ago\b", low) or re.search(r"\blast\s+year\b", low) or re.search(r"\b(?:three|3)\s+years?\s+ago\b", low):
                        y = rel_year or today.year - 1
                        add(2, y, today.month, today.day, "unsure")
                    elif re.search(r"\b(?:around|last|this|the)\s+(winter|summer|monsoon)\b", low):
                        season = re.search(r"\b(?:around|last|this|the)\s+(winter|summer|monsoon)\b", low).group(1)
                        y = today.year
                        if season == "winter":
                            chosen = (y - 1, 12) if today.month < 12 else (y, 12)
                        elif season == "summer":
                            chosen = (y, 4) if today.month > 4 else (y - 1, 4)
                        else:
                            chosen = (y, 7) if today.month >= 6 else (y - 1, 7)
                        add(3, chosen[0], chosen[1], 10, "unsure")
                    else:
                        # bare year
                        m3 = re.search(r"\b(19|20)\d{2}\b", low)
                        if m3:
                            y = int(m3.group(0))
                            add(1, y, today.month, today.day, "unsure")
    if not cands:
        return None, consumed
    cands.sort(key=lambda c: -c[0])
    best = cands[0]
    end = best[3] if len(best) > 3 else None
    return TimeWindow(start=best[1].isoformat(),
                      end=end.isoformat() if end else None,
                      certainty=best[2]), consumed

# ---------------- main parser ----------------
def parse_rules(text: str, today=None, history=None) -> ParsedMemory:
    today = date.fromisoformat(today) if today else date.fromisoformat(TODAY)
    cues: List[Cue] = []
    low0 = text

    # history: start from previous cues, drop types re-stated now
    prev_cues = list(history.get("cues", [])) if history else []

    # place (word-boundary match on gazetteer terms + aliases; "either/or" -> unsure)
    matched_terms = []
    low_pl = low0.lower().replace("-", " ")
    disjunctive = re.search(r"\b(?:either|or)\b", low_pl) is not None
    for term, place in _gaz_terms().items():
        tnorm = term.lower().replace("-", " ")
        if tnorm not in low_pl:
            continue
        m = re.search(r"\b" + re.escape(tnorm) + r"\b", low_pl)
        if not m:
            continue
        cert = "unsure" if (_has_hedge_near(low0, m.start(), m.end(), None, None) or disjunctive) else "sure"
        neg = _negated_near(low0, m.start(), m.end())
        if any(c.type == "place" and c.value == place for c in cues):
            continue
        cues.append(Cue(type="place", value=place, certainty=cert, negated=neg))
        matched_terms.append((m.start(), m.end(), place, term))
    if len(cues) > 2:
        cues = cues[:2]

    # time window
    tw, consumed = _resolve_time_window(low0, today)
    if tw is not None:
        tw.certainty = "unsure" if _has_hedge_near(low0, 0, 50, None, None) or "around" in low0 else tw.certainty

    # time of day (multi-word phrases / superset expressions first)
    tod_found = None
    for tod, phrases in TOD_PHRASES.items():
        sp = _find_cue(low0, phrases, "time_of_day")
        if sp:
            tod_found = (tod, sp)
            break
    if not tod_found:
        for tod, words in TOD_WORDS.items():
            sp = _find_cue(low0, words, "time_of_day")
            if sp:
                tod_found = (tod, sp)
                break
    if tod_found:
        tod, (s, e) = tod_found
        cert = "unsure" if _has_hedge_near(low0, s, e, None, None) else "sure"
        cues.append(Cue(type="time_of_day", value=tod, certainty=cert,
                        negated=_negated_near(low0, s, e)))
    else:
        # inferred time of day from visible scene words (always unsure)
        for word, tod in INFERRED_TOD.items():
            sp = _find_cue(low0, [word], "time_of_day")
            if sp:
                s, e = sp
                cues.append(Cue(type="time_of_day", value=tod, certainty="unsure",
                                negated=_negated_near(low0, s, e)))
                break

    # indoor / outdoor
    sp = _find_cue(low0, INDOOR_WORDS, "indoor_outdoor")
    if not sp:
        sp = _find_cue(low0, OUTDOOR_WORDS, "indoor_outdoor")
    if sp:
        s, e = sp
        val = "indoor" if any(w in low0.lower() for w in INDOOR_WORDS) else "outdoor"
        cert = "unsure" if _has_hedge_near(low0, s, e, None, None) else "sure"
        cues.append(Cue(type="indoor_outdoor", value=val, certainty=cert,
                        negated=_negated_near(low0, s, e)))

    # setting
    for setting, words in SETTING_KEYWORDS:
        sp = _find_cue(low0, words, "setting_type")
        if sp:
            s, e = sp
            cert = "unsure" if _has_hedge_near(low0, s, e, None, None) else "sure"
            cues.append(Cue(type="setting_type", value=setting, certainty=cert,
                            negated=_negated_near(low0, s, e)))
            break

    # objects (up to 6)
    obj_found = []
    for w in OBJECT_WORDS:
        m = re.search(r"\b" + re.escape(w) + r"\b", low0, re.I)
        if m:
            cert = "unsure" if _has_hedge_near(low0, m.start(), m.end(), None, None) else "sure"
            obj_found.append((m.start(), w, cert))
    for _s, w, cert in sorted(obj_found)[:6]:
        cues.append(Cue(type="object", value=w, certainty=cert))

    # activity
    for w in ACTIVITY_WORDS:
        m = re.search(r"\b" + re.escape(w) + r"\b", low0, re.I)
        if m:
            cert = "unsure" if _has_hedge_near(low0, m.start(), m.end(), None, None) else "sure"
            cues.append(Cue(type="activity", value=w, certainty=cert))
            break

    # person
    for w in PERSON_WORDS:
        m = re.search(r"\b" + re.escape(w) + r"\b", low0, re.I)
        if m:
            cert = "unsure" if _has_hedge_near(low0, m.start(), m.end(), None, None) else "sure"
            cues.append(Cue(type="person", value=w, certainty=cert))
            break

    # purpose / text-in-image / emotion
    m = PURPOSE_RE.search(low0)
    if m:
        cues.append(Cue(type="purpose", value=low0[m.start():m.end()][:60], certainty="unsure"))
    m = TEXT_IN_IMG_RE.search(low0)
    if m:
        cues.append(Cue(type="text_in_image", value=low0[m.start():m.end()][:60], certainty="unsure"))
    m = EMOTION_RE.search(low0)
    if m:
        cues.append(Cue(type="emotion", value=low0[m.start():m.end()][:40], certainty="unsure"))

    # anchor phrases
    # Strong markers always create an anchor. Weak markers (bare "after the X" etc.)
    # only do so when the description carries an event verb; otherwise the phrase is
    # a time/object expression, not a photo anchor (e.g. "coffee before the beach",
    # "during the day", "around the end of 2023").
    anchor = None
    STRONG_ANCHORS = ("the day after", "the evening after", "the night after",
                      "the morning after", "the day before", "the night before",
                      "the week after", "the week before", "right after", "right before",
                      "a few days after", "a few days before")
    WEAK_ANCHORS = ("after the", "before the", "during the", "around the")
    VERB_HINTS = ("walked", "walking", "walk", "dined", "dinner", "lunch", "ate",
                  "studied", "studying", "visited", "cycling", "cycled", "hiking",
                  "hiked", "party", "partied", "celebrated", "concert", "fest",
                  "exam", "trips", "trip", "photoshoot", "gathered", "picnic")
    m = re.search(r"\b((" + "|".join(STRONG_ANCHORS) + ")|" +
                  "(the day after|the evening after|the night after|the morning after|"
                  "the day before|the night before|right after|right before|"
                  "a few days after|a few days before|after the|before the|during the|around the))\b(.{0,60})",
                  low0, re.I)
    if m:
        rel_word = m.group(1).lower()
        is_strong = any(rel_word.startswith(st) for st in
                        ("the day", "the evening", "the night", "the morning", "the week",
                         "right ", "a few days"))
        desc = re.sub(r"\s+", " ", m.group(2))
        desc = re.split(r"\s*\.[\s,]", desc)[0][:60].strip(" .,")
        if not is_strong and not any(h in desc.lower() for h in VERB_HINTS):
            desc = ""
        if desc:
            relation = {"after the": "after", "right after": "after",
                        "the day after": "after", "the evening after": "after",
                        "the night after": "after", "the morning after": "after",
                        "a few days after": "after", "right before": "before",
                        "the day before": "before", "the night before": "before",
                        "before the": "before", "during the": "during",
                        "around the": "near"}.get(rel_word, "around")
            anchor = Anchor(description=desc[:60], relation=relation)
            cues.append(Cue(type="anchor_event", value=f"{relation}: {desc}"[:80], certainty="unsure"))

    # visual_query: strip place names, dates, hedges
    vq = low0
    for s, e, place, term in sorted(matched_terms, key=lambda x: -x[0]):
        vq = vq[:s] + " " + vq[e:]
    vq = re.sub(r"\b(?:19|20)\d{2}\b", " ", vq)
    vq = re.sub(r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b", " ", vq, flags=re.I)
    for h in HEDGES:
        vq = re.sub(r"\b" + re.escape(h) + r"\b", " ", vq)
    vq = re.sub(r"\b(?:i|we|my|our|your|me|him|her|them|you|the|a|an|was|were|is|are|it|that|this|these|those|"
                 r"in|on|at|to|of|for|from|by|with|without|over|under|between|and|or|but|so|if|as|when|where|which|"
                 r"who|what|how|why|there|here|then|now|later|right|left|up|down|one|two|three|few|little|small|big|"
                 r"just|very|really|quite|also|photo|photos|picture|pic|shot|image|images|memory|memories|"
                 r"remember|remembering|remembered|forget|forgot|took|taking|taken|take|wanted|want|wanting|need|"
                 r"had|have|having|before|after|last|year|years|some|any|much|many|more|most|other|another|"
                 r"foreground|background|front|behind|"
                 r"during|stopped|stopping|stop|sure|certain|absolutely|positive|either|about|because|since|while|"
                 r"looking|look|find|found|finding|search|searching|knew|know|trip|trips|day|time)\b", " ", vq, flags=re.I)
    vq = re.sub(r"\b(?:i'?m|i'?ve|isn'?t|wasn'?t|weren'?t|aren'?t|don'?t|doesn'?t|didn'?t|won'?t|"
                 r"couldn'?t|shouldn'?t|it'?s|it'?ll|you'?re|you'?ll|we'?re|we'?ve|they'?re|they'?ve|"
                 r"that'?s|there'?s|what'?s|who'?s|let'?s)\b", " ", vq, flags=re.I)
    vq = re.sub(r"['\u2019][a-z]{0,2}\b", " ", vq)
    vq = re.sub(r"[^0-9a-z\u00c0-\u024f]+", " ", vq)
    vq = re.sub(r"\s+", " ", vq).strip()
    if not vq.split():
        vq = re.sub(r"\s+", " ", low0).strip()[:200]

    # merge history: replace same-type cues
    if prev_cues:
        new_types = {c.type for c in cues}
        merged = [c for c in prev_cues if c.type not in new_types]
        merged += cues
        cues = merged

    return ParsedMemory(cues=cues, time_window=tw, visual_query=vq, anchor=anchor)
