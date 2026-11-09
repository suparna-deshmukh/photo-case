"""M6 — why-matched line (no LLM)."""
from typing import List

from .cues import Cue


def why_matched(row: dict, cues: List[Cue]) -> str:
    bits = []
    attr_map = {"indoor_outdoor": "indoor_outdoor", "time_of_day": "time_of_day",
                "setting_type": "setting_type", "season": "season_hint"}
    for c in cues:
        added = False
        if c.type == "place":
            hit = c.value.lower() in str(row.get("place_name", "")).lower() or \
                  c.value.lower() in str(row.get("area", "")).lower()
            mark = "✓" if hit else "✗"
            bits.append(f"{c.value} {mark}")
            added = True
        elif c.type in attr_map:
            col = attr_map[c.type]
            hit = str(row.get(col, "")).lower() == c.value.lower()
            mark = "✓" if hit else "✗"
            bits.append(f"{c.value} {mark}")
            added = True
        elif c.type == "object":
            blob = str(row.get("caption", "") or "").lower()
            mark = "✓" if c.value.lower() in blob else "✗"
            bits.append(f"{c.value} {mark}")
            added = True
        if added and c.certainty == "unsure":
            bits[-1] += " ~"
    if not bits:
        return "Matched on visual similarity."
    line = "Matched: " + ", ".join(bits[:5])
    unsure = [c.value for c in cues if c.certainty == "unsure"]
    if unsure:
        line += f" (~ unsure: {', '.join(dict.fromkeys(unsure))[:40]})"
    return line
