"""
Purpose: R2 - interview synthesis from the filled Note Sheet export.
Reads  : research/notes.csv (raw tab export; anonymized columns only used in outputs)
Uses   : data/tables/*.csv + data/pipeline_counts.json (discovery side, if present)
Writes : research/interview_cards.md, research/anonymized_notes.md,
         research/tables/p1_cue_accuracy.csv, research/tables/p2_behavior.csv,
         research/tables/p3_input.md (per-participant gate-coding input),
         research/r2_synthesis.md (tables + hypothesis comparison scaffold)
Rules  : never invent data; missing values -> "not recorded".
Usage  : .venv/bin/python code/synthesis_r2.py
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
NOTES = BASE / "research" / "notes.csv"
CUE_TYPES = ["person","place","time_when","event_context","anchor_relation","visual_detail",
             "setting","activity","emotion_or_vibe","purpose_or_reason","text_in_image",
             "source","device_or_app","other"]
QUERY_STYLES = ["keyword","natural_language","date_or_filter","people_or_face","map_or_place",
                "browse_scroll","ask_photos_chat","none_stated"]

ANON_EXCLUDE = ["date", "relationship"]  # excluded from shared outputs


def parse_cues(s, n_parts):
    """Parse 'type|value|certainty[|verified]; ...' into rows."""
    rows = []
    if not isinstance(s, str) or not s.strip() or s.strip().lower() in ("not recorded", "nan"):
        return rows
    for part in re.split(r";|\n", s):
        part = part.strip()
        if not part:
            continue
        bits = [b.strip() for b in part.split("|")]
        while len(bits) < n_parts:
            bits.append("")
        rows.append(bits[:n_parts])
    return rows


def code_first_query_style(q, notes_text):
    q = (q or "").strip()
    if not q or q.lower() in ("not recorded", "nan"):
        return "none_stated"
    if re.search(r"\b(19|20)\d{2}\b|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|\b(morning|evening|night|afternoon)\b|\byear\b|\bdate\b", q, re.I):
        return "date_or_filter"
    ql = q.lower()
    if re.search(r"\b(mom|mommy|mum|dad|papa|papa|dad|aunty|aunt|uncle|friend|bday|birthday|wedding)\b", ql):
        return "people_or_face"
    if re.search(r"\b(in|at|near) (the|a|goa|pune|home|hotel|beach|temple|city)\b", ql):
        return "map_or_place"
    words = len(q.split())
    if words <= 3:
        return "keyword"
    if words >= 8 or re.search(r"[,;]|i think|maybe|when we|last year", ql):
        return "natural_language"
    return "keyword"


def code_reformulation_style(qs):
    if not isinstance(qs, str) or not qs.strip() or len(qs.split(";")) < 2:
        return "other" if isinstance(qs, str) and qs.strip() else "not recorded"
    qs = [x.strip() for x in qs.split(";") if x.strip()]
    base_tokens = set(re.findall(r"[a-z0-9']+", qs[0].lower()))
    for q in qs[1:]:
        new_tokens = set(re.findall(r"[a-z0-9']+", q.lower())) - base_tokens
        if len(new_tokens) >= 2:
            return "added_info"
    return "swapped_keywords"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(NOTES))
    ap.add_argument("--outdir", default=str(BASE / "research"))
    args = ap.parse_args()
    src = Path(args.input)
    outdir = Path(args.outdir)
    if not src.exists():
        print(f"PENDING: {src} not found. Nothing to synthesize.")
        return 0
    df = pd.read_csv(src)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)
    cards, p1_rows, p2_rows = [], [], []
    p3_input = []
    for _, r in df.iterrows():
        pid = str(r["participant_id"])
        notes_text = " ".join(str(v) for v in r if isinstance(v, str))
        # participant card (5 lines max + 1 verified verbatim quote)
        quote = str(r.get("notable_quote_verbatim", "") or "")
        quote_ok = quote and quote.lower() in notes_text.lower()
        inc_type = r.get("incident_photo_type", "not recorded")
        p2_rows.append({
            "participant_id": pid,
            "time_to_find_s": r.get("probe_time_to_find_s", ""),
            "probe_success": r.get("probe_success", ""),
            "n_queries": len([q for q in str(r.get("probe_queries", "") or "").split(";") if q.strip()])
                          if isinstance(r.get("probe_queries"), str) and str(r.get("probe_queries", "")).strip() not in ("", "nan") else "",
            "first_query_style": code_first_query_style(str(r.get("first_action", "") or ""), notes_text),
            "n_reformulations": r.get("probe_reformulations", r.get("incident_reformulation_count", "")),
            "reformulation_style": code_reformulation_style(str(r.get("probe_queries", "") or "")),
            "fell_back_to_scrolling": "Y" if re.search(r"scroll", notes_text, re.I) else "N",
            "used_ask_tab": r.get("probe_used_ask_tab", ""),
        })
        # P1 cue accounting (probe cues: type|value|certainty|verified)
        for bits in parse_cues(str(r.get("probe_cues", "") or ""), 4):
            ctype, val, cert, ver = (bits + ["", "", "", ""])[:4]
            p1_rows.append({"type": ctype or "other", "spoke": 1,
                            "said_sure": 1 if cert.lower().startswith("sure") else 0,
                            "verified_correct": 1 if ver.lower().startswith("correc") else 0,
                            "verified_wrong": 1 if ver.lower().startswith("wrong") else 0,
                            "forgotten": 1 if ver.lower().startswith("forgotten") else 0})
        cards.append(f"""### {pid}
- Segment: {r.get('segment_flags', 'not recorded')}
- Incident: {inc_type}; outcome {r.get('incident_outcome', 'not recorded')}; first action: {str(r.get('first_action',''))[:120]}
- Probe: {r.get('probe_success', 'not recorded')} in {r.get('probe_time_to_find_s', 'not recorded')}s; {r.get('probe_reformulations', 'not recorded')} reformulations
- First query style: {p2_rows[-1]['first_query_style']}; ask tab: {r.get('probe_used_ask_tab', 'not recorded')}
- Quote (verified substring: {'YES' if quote_ok else 'NO - check note'}): "{quote[:200]}"
""")
        p3_input.append(f"""### {pid}
- first_action: {r.get('first_action', 'not recorded')}
- incident_queries: {r.get('incident_queries', 'not recorded')}
- incident_outcome: {r.get('incident_outcome', 'not recorded')}
- probe_queries: {r.get('probe_queries', 'not recorded')}
- probe_success: {r.get('probe_success', 'not recorded')}
- observed: {str(r.get('observed_behavior_notes', ''))[:300]}
""")
    p1 = (pd.DataFrame(p1_rows).groupby("type")
          .agg(spoken=("spoke", "sum"), said_sure=("said_sure", "sum"),
               verified_correct=("verified_correct", "sum"),
               verified_wrong=("verified_wrong", "sum"), forgotten=("forgotten", "sum"))
          .reset_index())
    p1["share_sure_pct"] = (100 * p1["said_sure"] / p1["spoken"]).round(0)
    p1["share_correct_pct"] = (100 * p1["verified_correct"] / p1["spoken"]).round(0)
    p1["share_wrong_pct"] = (100 * p1["verified_wrong"] / p1["spoken"]).round(0)
    p1 = p1.sort_values("spoken", ascending=False)
    p1.to_csv(outdir / "tables" / "p1_cue_accuracy.csv", index=False)
    p2 = pd.DataFrame(p2_rows)
    med = {c: p2[c].median() for c in ("time_to_find_s", "n_queries", "n_reformulations")
           if pd.api.types.is_numeric_dtype(p2[c])}
    p2.to_csv(outdir / "tables" / "p2_behavior.csv", index=False)

    # discovery side (if present)
    disc = {}
    for t in ("t1_gate_distribution", "t4_query_style", "t5_workarounds"):
        pth = BASE / "data/tables" / f"{t}.csv"
        if pth.exists():
            disc[t] = pd.read_csv(pth).to_dict("records")
    pc = {}
    try:
        pc = json.loads((BASE / "data/pipeline_counts.json").read_text())
    except Exception:
        pass

    anon_cols = [c for c in df.columns if c not in ANON_EXCLUDE and c != "notable_quote_verbatim"]
    with (outdir / "anonymized_notes.md").open("w") as f:
        f.write("| " + " | ".join(anon_cols) + " |\n")
        f.write("|" + "---|" * len(anon_cols) + "\n")
        for _, r in df.iterrows():
            cells = [str(r.get(c, "")).replace("|", "/") for c in anon_cols]
            f.write("| " + " | ".join(cells) + " |\n")

    out = outdir / "r2_synthesis.md"
    with out.open("w") as f:
        f.write("# R2 — Interview Synthesis\n\n")
        f.write(f"n = {len(df)} participants. Generated by code from {src.name} (no values invented; gaps = not recorded).\n\n")
        f.write("## Per-participant cards\n\n" + "\n".join(cards) + "\n")
        f.write("## Table P1 — cue accuracy in the probe\n\n")
        f.write(p1.to_markdown(index=False) + "\n\n")
        f.write("## Table P2 — retrieval behaviour per participant\n\n")
        f.write(p2.to_markdown(index=False) + "\n\nMedians: " + json.dumps(med) + "\n\n")
        f.write("## Table P3 — where each attempt broke (agent-coded from notes; see tables/p3_input.md)\n\n"
                "_PENDING: agent codes failure_gate + evidence line per participant._\n\n")
        f.write("## Comparison with discovery engine (H1-H5)\n\n")
        f.write(f"Discovery n: n_relevant={pc.get('n_relevant')}, n_episodes={pc.get('n_episodes')}. "
                "Interview evidence: " + ("see P3 + cards" if len(df) else "PENDING (notes.csv absent)") + ".\n\n")
        f.write("## What changed in our thinking\n\n_PENDING: <=5 statements after P3 is coded._\n\n")
        f.write("## Limitations\n\n"
                "- n small; participants are friends/acquaintances (relationship recorded per participant in the private raw tab, excluded here).\n"
                "- Self-report bias; probe used a photo the participant chose (easier than a random one).\n\n")
        f.write("## 3 most common retrieval scenarios (task cards)\n\n_PENDING after coding._\n")
    (outdir / "tables" / "p3_input.md").write_text("\n".join(p3_input))
    print(f"WROTE {out} + p1/p2/p3_input + anonymized_notes.md; n={len(df)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
