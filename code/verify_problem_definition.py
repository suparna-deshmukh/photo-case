"""R3 checkpoint: every number in problem_definition.md must appear in a source file;
no forbidden phrase."""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DOC = BASE / "research" / "problem_definition.md"
SOURCES = [
    BASE / "data" / "tables" / f
    for f in ["T1_gate_distribution.csv", "T2_cue_matrix.csv", "T2_cue_by_phototype.csv",
              "T2_cue_certainty.csv", "T3_phototype_by_gate.csv", "T3_phototype_by_gate_pct.csv",
              "T4_query_style.csv", "T5_workarounds.csv", "T6_mechanisms.csv",
              "T6_cluster_map.csv", "T7_scorecard.csv", "findings.json"]
] + [BASE / "data" / "validation_report.json", BASE / "data" / "pipeline_counts.json",
     BASE / "research" / "ask_photos_facts.md"]
SOURCES += sorted((BASE / "research" / "sim").rglob("*.md"))
SOURCES += sorted((BASE / "research" / "sim" / "tables").glob("*")) if (BASE / "research" / "sim" / "tables").exists() else []

FORBIDDEN = "find it difficult to search"
text = DOC.read_text()

corpus = "\n".join(p.read_text(errors="ignore") for p in SOURCES if p.exists())
corpus_flat = corpus.replace(",", "").replace("%", "")

nums = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
missing = []
for n in sorted(set(nums), key=lambda x: (len(x), x)):
    variants = {n, n.replace(",", ""), n.rstrip("0").rstrip(".") if "." in n else n}
    # also bare int form of a float like "100.0" -> "100"
    if "." in n:
        variants.add(n.split(".")[0])
    if not any(v in corpus_flat or v in corpus for v in variants):
        missing.append(n)

print(f"numbers found in doc: {len(set(nums))}")
if missing:
    print("MISSING from sources:", missing)
else:
    print("ALL numbers present in source files")

# forbidden phrase (and close variants)
low = text.lower()
hits = [p for p in [FORBIDDEN, "difficult to search for old photos",
                    "users find it hard to search", "struggle to search for old photos"]
        if p in low]
print("forbidden phrase hits:", hits if hits else "none")
print("RESULT:", "PASS" if not missing and not hits else "FAIL")
