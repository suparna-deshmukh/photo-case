"""
Purpose: D10 - evidence engine used by BOTH the offline cached-answer builder
         and the public Discovery app. Pure Python (pandas + numpy;
         sentence-transformers optional with TF-IDF fallback). Runs with NO LLM.
         live_call is any function (system, user) -> dict|None, so the same
         code works with the local profile (offline builder) and
         live_llm.live_json (public app).
Inputs : a data/app directory (episodes_public.parquet, episodes_emb.npy,
         emb_ids.json, enums.json, pipeline_counts.json, validation_report.json,
         T* tables incl. T7_scorecard.csv).
Outputs: plan/answer structures; build_cached_answers writes
         <app_dir>/cached_answers.json.
Privacy: never logs typed user text; no secrets.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

_CUE_PSEUDO = {"cue_remembered", "cue_missing"}


def load_data(app_dir):
    """Load app bundle. Returns (df, emb, enums, counts, validation)."""
    app_dir = Path(app_dir)
    df = pd.read_parquet(app_dir / "episodes_public.parquet")
    emb = np.load(app_dir / "episodes_emb.npy") if (app_dir / "episodes_emb.npy").exists() else None
    enums = json.loads((app_dir / "enums.json").read_text())
    counts = json.loads((app_dir / "pipeline_counts.json").read_text()) if (app_dir / "pipeline_counts.json").exists() else {}
    validation = None
    if (app_dir / "validation_report.json").exists():
        validation = json.loads((app_dir / "validation_report.json").read_text())
    return df, emb, enums, counts, validation


def load_emb_ids(app_dir):
    p = Path(app_dir) / "emb_ids.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _apply_filters(df, filters, enums):
    out = df
    for col, vals in (filters or {}).items():
        if col not in out.columns:
            continue
        vals = list(vals)
        if col in enums:
            vals = [v for v in vals if v in set(enums[col])]
        if not vals:
            continue
        out = out[out[col].isin(vals)]
    return out


def _cue_types_of(s):
    try:
        lst = json.loads(s) if s else []
        return [c["type"] if isinstance(c, dict) else str(c) for c in lst]
    except Exception:
        return []


def query_stats(df, group_by, filters, metric="count", enums=None):
    """Group-by counts/shares. Validates columns/values against enums;
    unknown values ignored. Returns DataFrame (group cols + n + share_pct).
    Pseudo-columns cue_remembered / cue_missing expand the JSON cue lists."""
    enums = enums or {}
    df = _apply_filters(df, filters, enums)
    n_total = len(df)
    out_frames = []
    plain = []
    for c in group_by:
        if c in _CUE_PSEUDO:
            base = "remembered_cues" if c == "cue_remembered" else "missing_cue_types"
            rows = []
            for _, s in df[base].items():
                for t in _cue_types_of(s):
                    rows.append({c: t})
            sub = pd.DataFrame(rows)
            g = sub.groupby(c).size().reset_index(name="n")
            g["share_pct"] = (100 * g["n"] / max(n_total, 1)).round(1)
            out_frames.append((c, g))
        elif c in df.columns:
            plain.append(c)
        # unknown columns ignored
    if plain:
        g = df.groupby(plain, dropna=False).size().reset_index(name="n")
        g["share_pct"] = (100 * g["n"] / max(n_total, 1)).round(1)
        out_frames.append(("+".join(plain), g))
    if not out_frames:
        raise ValueError("no valid group_by columns")
    parts = []
    for name, g in out_frames:
        g = g.copy()
        g.insert(0, "table", name)
        g = g.sort_values("n" if metric == "count" else "share_pct", ascending=False)
        parts.append(g)
    res = pd.concat(parts, ignore_index=True)
    return res


def _embed(texts, model_cache, force_tfidf=False):
    """Returns (vectors, method). MiniLM with TF-IDF fallback."""
    if not force_tfidf:
        try:
            if "model" not in model_cache:
                from sentence_transformers import SentenceTransformer
                model_cache["model"] = SentenceTransformer("all-MiniLM-L6-v2")
            v = model_cache["model"].encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
            return np.asarray(v, dtype="float32"), "minilm"
        except Exception:
            pass
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(stop_words="english", max_features=20000)
    X = vec.fit_transform([t if t else " " for t in texts]).toarray().astype("float32")
    nrm = np.linalg.norm(X, axis=1, keepdims=True)
    nrm[nrm == 0] = 1
    return X / nrm, "tfidf"


def semantic_search(df, emb, query, k=8, filters=None, enums=None, model_cache=None, force_tfidf=False, emb_ids=None):
    """Top-k episodes by cosine similarity. Returns (DataFrame, method).
    emb must be aligned with emb_ids (full bundle order); df may be filtered."""
    enums = enums or {}
    df = _apply_filters(df, filters, enums).reset_index(drop=True)
    if len(df) == 0:
        return pd.DataFrame(columns=["doc_id", "snippet", "score"]), "none"
    model_cache = model_cache or {}
    qv, method = _embed([query], model_cache, force_tfidf=bool(force_tfidf or emb is None))
    if emb is not None and emb_ids is not None and len(emb) == len(emb_ids):
        pos = {str(d): i for i, d in enumerate(emb_ids)}
        idxs = [pos[str(d)] for d in df["doc_id"].astype(str) if str(d) in pos]
        Xv = np.asarray(emb[idxs], dtype="float32")
        sims = Xv @ qv.T
        df = df.iloc[idxs].reset_index(drop=True)
    else:
        texts = (df["snippet"].fillna("") + ". " + df["failure_mechanism"].fillna("")).tolist()
        Xv, _ = _embed(texts, model_cache, force_tfidf=True)
        sims = Xv @ qv.T
    order = np.argsort(-sims.ravel())[:k]
    res = df.iloc[order][["doc_id", "snippet"]].copy()
    res["score"] = sims.ravel()[order]
    res = res.reset_index(drop=True)
    if "failure_gate" in df.columns:
        res["failure_gate"] = df.iloc[order]["failure_gate"].tolist()
    return res, method


def route_keywords(question, enums=None):
    """Rule-based plan (no LLM). Returns {"steps": [...]} with max 3 steps."""
    q = (question or "").lower()
    steps = []
    group_by = None
    if re.search(r"\b(break|broken|fail|failure|gate)\w*", q) or "where does it" in q:
        group_by = ["failure_gate"]
    elif re.search(r"what kind|kinds of|photo ?type|phototype", q):
        group_by = ["photo_type"]
    elif "workaround" in q or "what do they do" in q:
        group_by = ["workaround"]
    elif re.search(r"how do they (search|query)|query style|formulate search", q):
        group_by = ["query_style"]
    elif re.search(r"\bremember|forget|forgotten|cues?\b", q):
        group_by = ["cue_remembered", "cue_missing"]
    elif re.search(r"ask photos|before|after|\bera\b", q):
        group_by = ["era"]
    if group_by:
        steps.append({"tool": "query_stats", "group_by": group_by,
                      "filters": _detect_filters(q, enums or {}), "metric": "share"})
    if re.search(r"\bwhy\b|how do they|example|examples|quote|verbatim", q) and len(steps) < 3:
        steps.append({"tool": "semantic_search", "query": question.strip(), "k": 5,
                      "filters": _detect_filters(q, enums or {})})
    if not steps:
        steps.append({"tool": "semantic_search", "query": question.strip(), "k": 8,
                      "filters": _detect_filters(q, enums or {})})
    return {"steps": steps[:3]}


def _detect_filters(q, enums):
    f = {}
    era_map = [("wider_rollout", ["now", "recent", "current", "2026", "after 2025", "wider rollout"]),
               ("early_access", ["early access", "2024", "2025"]),
               ("pre_ask", ["pre-ask", "pre ask", "before ask", "before 2024"])]
    for e, pats in era_map:
        if any(p in q for p in pats):
            f["era"] = [e]
            break
    src_map = [("play", ["play store", "google play", "android"]), ("appstore", ["app store", "ios", "iphone"]), ("reddit", ["reddit"])]
    for s, pats in src_map:
        if any(p in q for p in pats):
            f["source"] = [s]
            break
    pt_map = [("document_utility", ["document", "receipt", "utility", "medicine", "notes"]),
              ("screenshot", ["screenshot"]), ("trip_event", ["trip", "travel", "event", "vacation"]),
              ("people_social", ["people", "person", "face", "friend", "family"]),
              ("food_place", ["food", "restaurant", "meal"]), ("scenery_pet", ["pet", "scenery", "nature"]),
              ("video", ["video"])]
    for p, pats in pt_map:
        if any(w in q for w in pats):
            f["photo_type"] = [p]
            break
    return f


def _valid_group_cols(enums):
    cols = ["failure_gate", "photo_type", "photo_age", "query_style", "workaround", "era", "source", "stakes", "outcome"]
    cols += list(_CUE_PSEUDO)
    return set(cols)


def _validate_step(step, enums):
    if not isinstance(step, dict):
        return False
    tool = step.get("tool")
    if tool == "query_stats":
        gb = step.get("group_by")
        if not isinstance(gb, list) or not gb or len(gb) > 3:
            return False
        if not all(c in _valid_group_cols(enums) for c in gb):
            return False
        for c, vals in (step.get("filters") or {}).items():
            if not isinstance(vals, list):
                return False
            if c in enums and not set(vals) <= set(enums[c]):
                return False
        if step.get("metric", "count") not in ("count", "share"):
            return False
        return True
    if tool == "semantic_search":
        if not isinstance(step.get("query"), str) or not step.get("query"):
            return False
        k = step.get("k", 5)
        if not isinstance(k, int) or isinstance(k, bool) or k < 1 or k > 8:
            return False
        for c, vals in (step.get("filters") or {}).items():
            if not isinstance(vals, list):
                return False
            if c in enums and not set(vals) <= set(enums[c]):
                return False
        return True
    return False


def plan_with_llm(question, live_call, enums):
    """LLM plan; validates every step; None if nothing valid remains."""
    if live_call is None:
        return None
    enum_txt = json.dumps(enums, ensure_ascii=False)
    system = ("You translate a product manager's question into a JSON plan over a table of user-feedback 'retrieval episodes'. "
              f"Columns and allowed values: {enum_txt}. Special group_by pseudo-columns: cue_remembered, cue_missing. "
              "Tools: query_stats {group_by: [columns], filters: {column: [values]}, metric: 'count' or 'share'}; "
              "semantic_search {query: string, k: integer <= 8, filters: {column: [values]}}. "
              "Use query_stats for 'how many / which is most common / compare'; use semantic_search for 'why / how / examples'; "
              "use both for comparisons. Return JSON {\"steps\": [...]} with at most 3 steps.")
    try:
        res = live_call(system, f"Question: {question}")
    except Exception:
        return None
    if not isinstance(res, dict) or "_error" in res:
        return None
    steps = res.get("steps")
    if not isinstance(steps, list):
        return None
    valid = [s for s in steps if _validate_step(s, enums)]
    return {"steps": valid[:3]} if valid else None


def run_plan(plan, df, emb, enums=None, model_cache=None, emb_ids=None):
    """Execute plan. Returns {tables, evidence_ids, method}."""
    enums = enums or {}
    tables = []
    evidence_ids = []
    methods = []
    for step in plan.get("steps", []):
        tool = step.get("tool")
        if tool == "query_stats":
            res = query_stats(df, step["group_by"], step.get("filters"), step.get("metric", "count"), enums)
            title = "query_stats(" + ",".join(step["group_by"]) + ")" + (f" filters={step['filters']}" if step.get("filters") else "")
            res = res.astype(object).where(pd.notna(res), None)
            tables.append({"title": title, "columns": list(res.columns), "rows": res.values.tolist(), "n": int(res["n"].sum())})
            methods.append("query_stats")
        elif tool == "semantic_search":
            res, method = semantic_search(df, emb, step["query"], k=step.get("k", 5), filters=step.get("filters"),
                                          enums=enums, model_cache=model_cache,
                                          force_tfidf=emb is None, emb_ids=emb_ids)
            res = res.astype(object).where(pd.notna(res), None)
            tables.append({"title": f"semantic_search k={step.get('k',5)} [{method}]",
                           "columns": list(res.columns), "rows": res.values.tolist(), "n": len(res)})
            evidence_ids.extend(res["doc_id"].astype(str).tolist())
            methods.append(method)
    return {"tables": tables, "evidence_ids": evidence_ids,
            "method": "+".join(dict.fromkeys(methods)) if methods else "none"}


def _allowed_numbers(results):
    nums = set()
    for t in results["tables"]:
        for row in t["rows"]:
            for v in row:
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    try:
                        f = float(v)
                        if np.isfinite(f):
                            nums.add(round(f, 1))
                            nums.add(round(f, 0))
                            nums.add(int(f))
                    except (ValueError, OverflowError):
                        pass
        if "n" in t["columns"]:
            idx = t["columns"].index("n")
            tot = sum(int(r[idx]) for r in t["rows"] if isinstance(r[idx], (int, float)))
            nums.add(tot)
            nums.add(round(float(tot), 1))
    nums.add(20)  # the "evidence is thin" threshold stated in the answer prompt
    return nums


def _numbers_in(text):
    out = set()
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\b", text):
        out.add(round(float(m.group(1)), 1))
    return out


def answer_with_llm(question, results, live_call):
    """LLM markdown answer with citation + number verification.
    Returns (markdown, used_llm: bool)."""
    if live_call is not None and results["tables"]:
        try:
            tbl_txt = json.dumps(results["tables"], ensure_ascii=False, default=str)[:6000]
            system = ("Answer using ONLY the tool results provided. Start with the direct answer in at most 3 sentences "
                      "including the numbers and n. Then give up to 3 evidence bullets, each citing an episode as [ep:<doc_id>]. "
                      "If n < 20 say the evidence is thin. If the results do not answer the question, say so. "
                      "Never state anything not in the results. Return JSON {\"answer\": \"<markdown>\"}.")
            res = live_call(system, f"Question: {question}\n\nTool results:\n{tbl_txt}")
            ans = res.get("answer") if isinstance(res, dict) and "_error" not in res else None
            if isinstance(ans, str) and ans.strip():
                ids = set(results["evidence_ids"])
                ans = re.sub(r"\[ep:([^\]]+)\]", lambda m: m.group(0) if m.group(1) in ids else "", ans)
                ans_clean = re.sub(r"\[ep:[^\]]+\]", " ", ans)
                ans_clean = re.sub(r"\d{4}-\d{2}-\d{2}", " ", ans_clean)
                bad = [n for n in _numbers_in(ans_clean) if n not in _allowed_numbers(results)]
                if not bad:
                    return ans, True
        except Exception:
            pass
    return templated_summary(question, results), False


def templated_summary(question, results):
    """Code-only summary, labelled 'Evidence view (no live AI)'."""
    lines = ["Evidence view (no live AI)"]
    t = results["tables"][0] if results["tables"] else None
    if t is None:
        lines.append("No matching data.")
        return "\n".join(lines)
    cols = t["columns"]
    if "n" in cols:
        gi = cols.index("n")
        name_col = [c for c in cols if c not in ("n", "share_pct", "table")][0]
        ni = cols.index(name_col)
        si = cols.index("share_pct") if "share_pct" in cols else None
        ranked = sorted(t["rows"], key=lambda r: -(r[gi] if isinstance(r[gi], (int, float)) else 0))
        parts = []
        for r in ranked[:3]:
            s = f"{float(r[si]):.0f}%" if si is not None else ""
            parts.append(f"{r[ni]} (n={int(r[gi])}, {s})".strip(" ,") if not s else f"{r[ni]} (n={int(r[gi])}, {s})")
        sentence = "Most common: " + parts[0]
        if len(parts) > 1:
            sentence += f"; second: {parts[1]}"
        if len(parts) > 2:
            sentence += f"; third: {parts[2]}"
        lines.append(sentence + ".")
    for ev in results["evidence_ids"][:3]:
        lines.append(f"- evidence [ep:{ev}]")
    return "\n".join(lines)


def nearest_estimate(text, df, emb, k=8, enums=None, model_cache=None, t7=None):
    """Nearest-episode estimate (no LLM). Majority votes for gate/phototype/
    workaround among k neighbours, 3 most similar items, scorecard cell."""
    texts = (df["snippet"].fillna("") + ". " + df["failure_mechanism"].fillna("")).tolist()
    qv, qm = _embed([text], model_cache or {}, force_tfidf=emb is None)
    Xv, dm = _embed(texts, model_cache or {}, force_tfidf=emb is None)
    sims = Xv @ qv.T
    order = np.argsort(-sims.ravel())[:k]
    nb = df.iloc[order]
    votes = {}
    for col in ["failure_gate", "photo_type", "workaround"]:
        vc = nb[col].dropna().value_counts()
        votes[col] = {str(k2): int(v2) for k2, v2 in vc.items()}
    top_gate = max(votes["failure_gate"], key=votes["failure_gate"].get) if votes["failure_gate"] else None
    top_pt = max(votes["photo_type"], key=votes["photo_type"].get) if votes["photo_type"] else None
    cell = None
    if t7 is not None and top_gate and top_pt:
        row = t7[(t7["photo_type"] == top_pt) & (t7["failure_gate"] == top_gate)]
        if len(row):
            r = row.iloc[0]
            cell = {"photo_type": top_pt, "failure_gate": top_gate, "n_cell": int(r["n_cell"]),
                    "score": float(r["score"]) if "score" in r and pd.notna(r["score"]) else None}
    return {
        "method": f"nearest-episode (emb={dm})",
        "votes": votes,
        "most_similar": [{"doc_id": str(d), "snippet": str(s)[:200]} for d, s in zip(nb["doc_id"], nb["snippet"])][:3],
        "scorecard_cell": cell,
        "label": f"Nearest-episode estimate (no live AI); n={k} neighbours",
    }


PRESET_QUESTIONS = [
    "What kinds of old photos do users struggle to retrieve?",
    "What do people actually remember about a photo, and what do they forget?",
    "How do users formulate searches when their memory is incomplete?",
    "Where in the retrieval journey does it break most, and did Ask Photos change that?",
    "Compare document/utility photos with trip/event photos: where does each fail?",
    "What workarounds do people use after search fails?",
]


def build_cached_answers(app_dir, live_call, model_cache=None):
    """Build cached answers for the 6 presets. live_call may be None."""
    app_dir = Path(app_dir)
    df, emb, enums, counts, validation = load_data(app_dir)
    emb_ids = load_emb_ids(app_dir)
    t7 = None
    t7p = app_dir / "T7_scorecard.csv"
    if t7p.exists():
        t7 = pd.read_csv(t7p)
    out = {}
    for q in PRESET_QUESTIONS:
        plan = plan_with_llm(q, live_call, enums)
        method_plan = "llm" if plan is not None else "keywords"
        if plan is None:
            plan = route_keywords(q, enums)
        results = run_plan(plan, df, emb, enums, model_cache=model_cache, emb_ids=emb_ids)
        ans, used_llm = answer_with_llm(q, results, live_call)
        out[q] = {"answer_markdown": ans, "evidence_ids": results["evidence_ids"][:8],
                  "tables": results["tables"], "n": int(len(df)),
                  "method": f"{method_plan}+{'llm_answer' if used_llm else 'template'}"}
    (app_dir / "cached_answers.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    print(f"cached_answers.json written: {len(out)} questions")
    return out
