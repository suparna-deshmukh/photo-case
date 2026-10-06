"""
Purpose: D7 - compute model-vs-human (second-model) agreement on the TEST
         split of the validation set; write data/validation_report.json.
         TEST rows only for the reported numbers; DEV rows reported separately
         (DEV is the only split usable for prompt improvement).
Inputs : research/validation_key.parquet, research/validation_filled.csv,
         data/pipeline_counts.json (pass-2 agreement).
Outputs: data/validation_report.json
         data/pipeline_counts.json key validation_prompt_version
         printed confusion matrix + disagreement rows.
Usage  : .venv/bin/python code/validation_report.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "code"))
from pipeline_counts import update_counts  # noqa: E402

PHOTO_DEFAULT = "other_unspecified"
GATE_DEFAULT = "unclear"
OUTCOME_DEFAULT = "unknown"


def norm_human_is_retrieval(v):
    v = str(v or "").strip().lower()
    return v in ("yes", "y", "true", "1")


def norm_field(v, default):
    v = str(v or "").strip().lower()
    if not v or v in ("nan", "none", "n/a"):
        return default
    return v


def main():
    key = pd.read_parquet(BASE / "research" / "validation_key.parquet")
    filled = pd.read_csv(BASE / "research" / "validation_filled.csv")
    merged = key.merge(filled, on="id", how="left", suffixes=("", "_h"))

    test = merged[merged["split"] == "TEST"].copy()
    dev = merged[merged["split"] == "DEV"].copy()
    n_test, n_dev = len(test), len(dev)
    prompt_version = str(key["prompt_version"].iloc[0]) if len(key) else "unknown"

    counts = {}
    try:
        counts = json.loads((BASE / "data" / "pipeline_counts.json").read_text())
    except Exception:
        pass

    report = {
        "n_test": n_test, "n_dev": n_dev, "prompt_version": prompt_version,
        "labeling_note": ("Labels written by a second AI model (independent blind pass), "
                          "per user instruction 2026-10-06. This is a second-model audit, NOT human "
                          "validation; human validation deferred. Blind CSV kept valid for a later human pass."),
        "fields": {}, "failure_gate_confusion": {}, "disagreements_test": [], "dev_disagreements": [],
        "model_pass2_gate_agreement": counts.get("gate_pass_agreement"),
        "integrity": "reported agreement corresponds to the prompt that produced episodes_full.parquet",
    }

    def field_report(df, field, model_col, human_col, default):
        m = [str(r[model_col]).lower() if pd.notna(r[model_col]) and str(r[model_col]).strip() not in ("", "nan", "None") else default
             for _, r in df.iterrows()]
        h = [norm_field(r[human_col], default) for _, r in df.iterrows()]
        m = [norm_field(x, default) for x in m]
        pairs = list(zip(m, h))
        n = len(pairs)
        acc = sum(1 for a, b in pairs if a == b) / n if n else 0.0
        try:
            kappa = float(cohen_kappa_score([a for a, _ in pairs], [b for _, b in pairs]))
        except Exception:
            kappa = None
        return acc, kappa, m, h

    def norm_yn(v):
        v = str(v or "").strip().lower()
        if v in ("true", "1", "yes", "y"):
            return "yes"
        return "no"
    m_yn = [norm_yn(r["model_is_episode"]) for _, r in test.iterrows()]
    h_yn = ["yes" if norm_human_is_retrieval(r["human_is_retrieval"]) else "no" for _, r in test.iterrows()]
    acc_r = sum(1 for a, b in zip(m_yn, h_yn) if a == b) / len(m_yn) if len(m_yn) else 0.0
    try:
        kap_r = float(cohen_kappa_score(m_yn, h_yn))
    except Exception:
        kap_r = None
    m_r, h_r = m_yn, h_yn
    report["fields"]["is_retrieval"] = {"accuracy_pct": round(100 * acc_r, 1), "kappa": round(kap_r, 3) if kap_r is not None else None}
    acc_p, kap_p, m_p, h_p = field_report(test, "photo_type", "model_photo_type", "human_photo_type", PHOTO_DEFAULT)
    report["fields"]["photo_type"] = {"accuracy_pct": round(100 * acc_p, 1), "kappa": round(kap_p, 3) if kap_p is not None else None}
    acc_g, kap_g, m_g, h_g = field_report(test, "failure_gate", "model_gate", "human_failure_gate", GATE_DEFAULT)
    report["fields"]["failure_gate"] = {"accuracy_pct": round(100 * acc_g, 1), "kappa": round(kap_g, 3) if kap_g is not None else None}
    acc_o, kap_o, m_o, h_o = field_report(test, "outcome", "model_outcome", "human_outcome", OUTCOME_DEFAULT)
    report["fields"]["outcome"] = {"accuracy_pct": round(100 * acc_o, 1), "kappa": round(kap_o, 3) if kap_o is not None else None}

    cm = confusion_matrix(h_g, m_g, labels=sorted(set(h_g) | set(m_g)))
    labels = sorted(set(h_g) | set(m_g))
    report["failure_gate_confusion"] = {"labels": labels, "matrix": cm.tolist(),
                                        "note": "rows=human, cols=model"}

    for i, (_, r) in enumerate(test.iterrows()):
        dis = []
        if m_r[i] != h_r[i]:
            dis.append(f"is_retrieval human={h_r[i]} model={m_r[i]}")
        if m_p[i] != h_p[i]:
            dis.append(f"photo_type human={h_p[i]} model={m_p[i]}")
        if m_g[i] != h_g[i]:
            dis.append(f"failure_gate human={h_g[i]} model={m_g[i]}")
        if m_o[i] != h_o[i]:
            dis.append(f"outcome human={h_o[i]} model={m_o[i]}")
        if dis:
            report["disagreements_test"].append({"id": str(r["id"]), "details": "; ".join(dis)})

    for _, r in dev.iterrows():
        dis = []
        h_yn = "yes" if norm_human_is_retrieval(r["human_is_retrieval"]) else "no"
        m_yn = "yes" if r["model_is_episode"] else "no"
        if h_yn != m_yn:
            dis.append(f"is_retrieval human={h_yn} model={m_yn}")
        if norm_field(r["human_photo_type"], PHOTO_DEFAULT) != norm_field(r["model_photo_type"], PHOTO_DEFAULT):
            dis.append(f"photo_type human={norm_field(r['human_photo_type'], PHOTO_DEFAULT)} model={norm_field(r['model_photo_type'], PHOTO_DEFAULT)}")
        if norm_field(r["human_failure_gate"], GATE_DEFAULT) != norm_field(r["model_gate"], GATE_DEFAULT):
            dis.append(f"failure_gate human={norm_field(r['human_failure_gate'], GATE_DEFAULT)} model={norm_field(r['model_gate'], GATE_DEFAULT)}")
        if dis:
            report["dev_disagreements"].append({"id": str(r["id"]), "details": "; ".join(dis)})

    # snippets for disagreements
    blind = pd.read_csv(BASE / "research" / "validation_blind.csv")
    txt = dict(zip(blind["id"].astype(str), blind["text"].astype(str)))
    for d in report["disagreements_test"]:
        d["snippet"] = txt.get(d["id"], "")[:200]
    for d in report["dev_disagreements"]:
        d["snippet"] = txt.get(d["id"], "")[:200]

    out = BASE / "data" / "validation_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: report[k] for k in ("n_test", "n_dev", "prompt_version", "fields")}, indent=2))
    print(f"disagreements: TEST={len(report['disagreements_test'])} DEV={len(report['dev_disagreements'])}")
    print(f"confusion (rows=human, cols=model) labels={labels}\n{cm}")
    update_counts(validation_prompt_version=prompt_version)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
