"""
Purpose: Discovery Engine public app (Hugging Face Space, Streamlit).
         Explores structured "retrieval episodes" extracted from public
         feedback: ask questions, explore figures, analyze a pasted review,
         and read the opportunity scorecard. Works fully with ZERO LLM;
         live AI (Gemini) is optional behind live_llm.py.
Inputs : data/ bundle (episodes_public.parquet, embeddings, tables T1-T7,
         figures F1-F6, cached_answers.json, enums.json, pipeline_counts.json,
         validation_report.json); optional LIVE_LLM_* env (Space secrets).
Outputs: interactive web app. No stack traces, no secret output, no typed
         user text logged.
"""
import json
import traceback

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import evidence_engine as ee
import live_llm
from schemas import Episode

st.set_page_config(page_title="Photo Retrieval Discovery Engine", page_icon="🔎", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    [data-testid="stApp"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    h1, h2, h3, h4 { letter-spacing: -0.015em; }
    [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 6px; }
    [data-baseweb="tab"] {
      border: 1px solid #d9deea; border-bottom: none;
      border-radius: 12px 12px 0 0;
      padding: 8px 18px; font-weight: 600; font-size: 14px;
      transition: all .15s;
    }
    [data-baseweb="tab"]:hover { border-color: #4f46e5; color: #4f46e5; }
    [data-baseweb="tab"][aria-selected="true"] { border-color: #4f46e5; color: #4f46e5; font-weight: 700; }
    [data-testid="stButton"] > button { border-radius: 12px; font-weight: 600; font-size: 14px; transition: all .15s; }
    [data-testid="stExpander"] details {
      border: 1px solid #e7eaf2; border-radius: 14px;
      background: #fff; box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 3px 12px rgba(16,24,40,.05);
    }
    [data-testid="stExpander"] summary { font-weight: 700; }
    [data-testid="stDataFrame"] { border: 1px solid #e7eaf2; border-radius: 12px; overflow: hidden; }
    [data-testid="stAlert"] { border-radius: 12px; }
    section[data-testid="stSidebar"] { background: #fbfcff; }
    .stMetric {
      border: 1px solid #e7eaf2; border-radius: 14px;
      background: #fff; box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 3px 12px rgba(16,24,40,.05);
      padding: 12px 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA = st.cache_data(ttl=300, show_spinner=False)
MODEL = st.cache_resource(ttl=3600, show_spinner=False)


@DATA
def load_bundle():
    df, emb, enums, counts, validation = ee.load_data("data")
    emb_ids = ee.load_emb_ids("data")
    t7 = None
    try:
        t7 = pd.read_csv("data/T7_scorecard.csv")
    except Exception:
        t7 = None
    cached = None
    try:
        cached = json.loads(open("data/cached_answers.json").read())
    except Exception:
        cached = None
    return df, emb, enums, counts, validation, emb_ids, t7, cached


try:
    DF, EMB, ENUMS, COUNTS, VALIDATION, EMB_IDS, T7, CACHED = load_bundle()
except Exception as _e:
    st.error(f"The data bundle is missing or unreadable ({type(_e).__name__}). "
             "Please contact the authors; no personal data is stored in this app.")
    st.stop()


@MODEL
def _emb_cache():
    return {}


MC = _emb_cache()

GATE_COLOR = {"expression": "#0072B2", "interpretation": "#E69F00", "evaluation": "#009E73",
              "refinement": "#D55E00", "persistence": "#CC79A7",
              "not_search_related": "#999999", "unclear": "#56B4E9"}
BLUE, ORANGE, GREEN, VERM, PINK, SKY, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#999999"

N_EP = len(DF)

# ---------------- sidebar ----------------
st.sidebar.title("🔎 Photo Retrieval Discovery Engine")
with st.sidebar:
    with st.expander("How this works", expanded=True):
        c = COUNTS or {}
        st.markdown(
            f"**Collect \u2192 Clean \u2192 Screen \u2192 Extract \u2192 Validate \u2192 Analyze**\n\n"
            f"- collected: **{c.get('n_play', 0) + c.get('n_appstore', 0) + c.get('n_reddit', 0):,}** documents (play + app store + reddit)\n"
            f"- cleaned: **{c.get('n_clean', 'n/a'):,}**\n"
            f"- screened: **{c.get('n_for_llm', 'n/a'):,}**\n"
            f"- relevant: **{c.get('n_relevant', 'n/a'):,}**\n"
            f"- episodes: **{c.get('n_episodes', 'n/a'):,}** of {c.get('n_extracted_attempted', 'n/a'):,} relevant"
            f"{' (capped for wall-clock)' if c.get('stage2_capped') else ''}\n"
        )
        if VALIDATION:
            vp = VALIDATION.get("prompt_version", "n/a")
            lab = VALIDATION.get("labeling_note", "")
            flds = VALIDATION.get("fields", {})
            gate_acc = (flds.get("failure_gate") or {}).get("accuracy_pct", "n/a")
            st.markdown(
                f"**Validation:** model-vs-human agreement on a held-out sample of "
                f"{VALIDATION.get('n_test', 40)} documents (prompt {vp}); "
                f"failure_gate agreement {gate_acc}%. {lab}"
            )
        else:
            st.markdown("**Validation:** report pending.")
        st.caption("Offline extraction used an open model run on a personal computer; live AI mode is optional.")
    st.markdown("**Global filters**")
    f_source = st.multiselect("source", sorted(DF["source"].dropna().unique().tolist()),
                              default=sorted(DF["source"].dropna().unique().tolist()))
    f_era = st.multiselect("era", ["pre_ask", "early_access", "wider_rollout"],
                           default=["pre_ask", "early_access", "wider_rollout"])
    f_pt = st.multiselect("photo_type", ENUMS.get("photo_type", []), default=[])
    f_gate = st.multiselect("failure_gate", ENUMS.get("failure_gate", []), default=[])

status = live_llm.live_status()
_c = COUNTS or {}
_total_docs = _c.get("n_play", 0) + _c.get("n_appstore", 0) + _c.get("n_reddit", 0)
_badge_color = "#009E73" if status["available"] else "#64748b"
st.markdown(
    f"""
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-top:8px;flex-wrap:wrap;">
      <div style="flex:1;min-width:280px;">
        <div style="font-size:30px;font-weight:800;letter-spacing:-0.02em;line-height:1.15;color:#101828;">
          Where does photo retrieval
          <span style="background:linear-gradient(120deg,#4f46e5,#7c3aed);-webkit-background-clip:text;background-clip:text;color:transparent;">actually break</span>?
        </div>
        <div style="margin-top:8px;color:#3f4a5f;font-size:15px;max-width:760px;">
          An interactive evidence base for <b>why old-photo search fails</b>: <b>{N_EP}</b> structured retrieval episodes
          mined from <b>{_total_docs:,}</b> public Google Photos feedback documents (Play Store, App Store, Reddit),
          screened and extracted by an open model running on a personal computer.
          Start with a preset question in the Ask tab, then explore the charts and the scorecard — every chart shows <b>n</b>.
        </div>
      </div>
      <div><span style="background:{_badge_color};color:white;padding:6px 14px;border-radius:999px;font-size:13px;
                        font-weight:600;white-space:nowrap;box-shadow:0 4px 14px rgba(16,24,40,.15);">
        {live_llm.mode_label()}
      </span></div>
    </div>
    """,
    unsafe_allow_html=True,
)
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Collected", f"{_total_docs:,}", help="raw documents: Play Store + App Store + Reddit")
m2.metric("Cleaned", f"{_c.get('n_clean', 0):,}", help="deduplicated, English, >=8 words")
m3.metric("Screened", f"{_c.get('n_for_llm', 0):,}", help="keyword prefilter + 10% control sample")
m4.metric("Relevant", f"{_c.get('n_relevant', 0):,}", help="stage-1 model screen")
m5.metric("Episodes", f"{_c.get('n_episodes', 0):,}", help="structured retrieval episodes")
st.caption(f"Structured evidence from {N_EP} public retrieval episodes (app reviews + Reddit). "
           "Era dates are a working assumption — verify before citing.")

FILT = {}
if f_source:
    FILT["source"] = f_source
if f_era:
    FILT["era"] = f_era
if f_pt:
    FILT["photo_type"] = f_pt
if f_gate:
    FILT["failure_gate"] = f_gate
FDF = ee._apply_filters(DF, FILT, ENUMS)

tabs = st.tabs(["🔎 Ask the evidence", "📊 Explore", "🧪 Try it", "🎯 Opportunity scorecard"])

# ================= TAB 1: Ask the evidence =================
with tabs[0]:
    st.markdown("### Ask the evidence")
    if "notice" not in st.session_state:
        st.session_state.notice = True
    if st.session_state.notice:
        st.info("Do not paste personal information. Preset answers are pre-computed and instant; "
                "free-text uses live AI when available, otherwise a code-only evidence view.")
        st.session_state.notice = False

    st.markdown("**Preset questions**")
    cols = st.columns(3)
    preset_keys = list((CACHED or {}).keys())
    for i, q in enumerate(preset_keys):
        with cols[i % 3]:
            if st.button(q, key=f"preset_{i}", use_container_width=True):
                st.session_state["selected_preset"] = q

    sel = st.session_state.get("selected_preset")
    if sel and sel in (CACHED or {}):
        entry = CACHED[sel]
        st.markdown(f"#### {sel}")
        st.markdown(f"*{entry.get('method', '')} · n={entry.get('n', N_EP)}*")
        st.markdown(entry["answer_markdown"])
        for t in entry.get("tables", [])[:3]:
            with st.expander(f"Table: {t['title']} (n={t.get('n')})", expanded=False):
                cols_ = [c for c in t["columns"] if c != "table"]
                rows = [[r[t["columns"].index(c)] for c in t["columns"]] for r in t["rows"]]
                st.dataframe(pd.DataFrame(rows, columns=t["columns"]).drop(columns=["table"], errors="ignore"),
                             use_container_width=True, hide_index=True)
                if "share_pct" in t["columns"] and len(t["rows"]) > 0:
                    gi = t["columns"].index("n")
                    name_col = [c for c in t["columns"] if c not in ("n", "share_pct", "table")][0]
                    ni = t["columns"].index(name_col)
                    data = pd.DataFrame(rows, columns=t["columns"]).drop(columns=["table"], errors="ignore")
                    data = data.dropna(subset=[name_col])
                    chart = (alt.Chart(data).mark_bar().encode(
                        x=alt.X(f"{name_col}:N", title=name_col, sort="-y"),
                        y=alt.Y("share_pct:Q", title="share (%)"),
                        color=alt.Color(f"{name_col}:N", scale=alt.Scale(domain=list(data[name_col].head(8)), range=list(GATE_COLOR.values()) * 2)),
                        tooltip=[name_col, "n", "share_pct"]).properties(height=280))
                    st.altair_chart(chart, use_container_width=True)
        st.markdown("**Evidence**")
        for ev in entry.get("evidence_ids", [])[:5]:
            row = DF[DF["doc_id"].astype(str) == str(ev)]
            if len(row):
                r = row.iloc[0]
                with st.expander(f"[ep:{ev}] {str(r.get('snippet'))[:120]}…"):
                    st.markdown(f"- source: {r.get('source')} · {str(r.get('date'))[:10]} · gate: {r.get('failure_gate')}")
                    if r.get("evidence_quote"):
                        st.markdown(f"> “{r.get('evidence_quote')}”")
                    if r.get("url"):
                        st.markdown(f"[link]({r.get('url')})")

    st.divider()
    st.markdown("**Free-text question**")
    q = st.text_input("Ask about the evidence…", key="q_input", max_chars=500)
if st.button("Ask"):
    if not q.strip():
        st.info("Type a question first.")
    else:
            live_call = None
            if status["available"]:
                if "live_session" not in st.session_state:
                    st.session_state.live_session = {"live_calls": 0}
                sess = st.session_state.live_session
                live_call = lambda s, u: live_llm.live_json(s, u, session=sess, max_tokens=600)
            try:
                plan = ee.plan_with_llm(q, live_call, ENUMS) if live_call else None
                if plan is None:
                    plan = ee.route_keywords(q, ENUMS)
                res = ee.run_plan(plan, FDF, EMB, ENUMS, model_cache=MC, emb_ids=EMB_IDS)
                if live_call is not None:
                    ans, used = ee.answer_with_llm(q, res, live_call)
                    st.markdown(ans)
                    if not used:
                        st.caption("LLM answer failed verification — showing the code-only evidence view instead.")
                else:
                    ans, _ = ee.templated_summary(q, res), False
                    st.markdown(ans)
                st.markdown("**Tables**")
                for t in res["tables"][:3]:
                    rows = [[r[t["columns"].index(c)] for c in t["columns"]] for r in t["rows"]]
                    dft = pd.DataFrame(rows, columns=t["columns"]).drop(columns=["table"], errors="ignore")
                    st.dataframe(dft, use_container_width=True, hide_index=True)
                    if "share_pct" in dft.columns and len(dft) and "n" in dft.columns:
                        name_col = [c for c in dft.columns if c not in ("n", "share_pct", "table")][0]
                        chart = (alt.Chart(dft).mark_bar().encode(
                            x=alt.X(f"{name_col}:N", sort="-y"), y=alt.Y("share_pct:Q", title="share (%)"),
                            color=alt.Color(f"{name_col}:N", scale=alt.Scale(range=list(GATE_COLOR.values()) * 2)),
                            tooltip=[name_col, "n", "share_pct"]).properties(height=260))
                        st.altair_chart(chart, use_container_width=True)
                st.markdown(f"*method: {res['method']} · Evidence view (no live AI) if no AI available*")
                st.markdown("**Evidence cards**")
                for ev in res["evidence_ids"][:5]:
                    row = FDF[FDF["doc_id"].astype(str) == str(ev)]
                    if len(row):
                        r = row.iloc[0]
                        with st.expander(f"[ep:{ev}] {str(r.get('snippet'))[:110]}…"):
                            st.markdown(f"- source: {r.get('source')} · {str(r.get('date'))[:10]} · gate: {r.get('failure_gate')}")
                            if r.get("evidence_quote"):
                                st.markdown(f"> “{r.get('evidence_quote')}”")
                            if r.get("url"):
                                st.markdown(f"[link]({r.get('url')})")
            except Exception as e:
                st.error(f"Something went wrong: {type(e).__name__}. Please try a different question.")


# ================= TAB 2: Explore =================
with tabs[1]:
    st.markdown("### Explore the evidence")
    st.caption(f"Showing {len(FDF)} of {N_EP} episodes under the current filters.")
    c1, c2 = st.columns(2)
    with c1:
        sub = FDF[FDF["failure_gate"].notna()]
        g = sub["failure_gate"].value_counts().rename("n").reset_index()
        g["share_pct"] = (100 * g["n"] / max(len(sub), 1)).round(1)
        g = g.sort_values("n", ascending=True)
        g["color"] = g["failure_gate"].map(GATE_COLOR).fillna(GREY)
        g["label"] = (g["share_pct"].round(0).astype(int).astype(str) + "% (n=" + g["n"].astype(str) + ")")
        ch = alt.layer(
            alt.Chart(g).mark_bar().encode(
                x=alt.X("share_pct:Q", title="share (%)"),
                y=alt.Y("failure_gate:N", sort=list(g["failure_gate"])),
                color=alt.value("blue"),
                tooltip=["failure_gate", "n", "share_pct"]).properties(height=320),
            alt.Chart(g).mark_text().encode(
                x=alt.X("share_pct:Q"),
                y=alt.Y("failure_gate:N", sort=list(g["failure_gate"])),
                text=alt.Text("label:N")).properties(height=320),
        )
        st.altair_chart(ch, use_container_width=True)
        st.markdown(f"**Failure gates** (n={len(sub)}; excludes not_search_related/unclear where null)")
    with c2:
        cue_rows = []
        for ct in ENUMS.get("cue_type", []):
            rem = FDF["remembered_cues"].map(lambda s: ct in ee._cue_types_of(s)).sum()
            mis = FDF["missing_cue_types"].map(lambda s: ct in ee._cue_types_of(s)).sum()
            if rem or mis:
                cue_rows.append({"cue_type": ct, "remembered_pct": round(100 * rem / max(len(FDF), 1), 1),
                                 "missing_pct": round(100 * mis / max(len(FDF), 1), 1)})
        cue_df = pd.DataFrame(cue_rows)
        if len(cue_df):
            melted = cue_df.melt(id_vars="cue_type", var_name="kind", value_name="pct")
            melted["sign"] = np.where(melted["kind"] == "remembered_pct", 1, -1)
            melted["val"] = melted["pct"] * melted["sign"]
            ch2 = (alt.Chart(melted).mark_bar().encode(
                x=alt.X("val:Q", title="% of episodes (+remembered / −forgotten)"),
                y=alt.Y("cue_type:N", sort="-x"),
                color=alt.Color("kind:N", scale=alt.Scale(domain=["remembered_pct", "missing_pct"], range=[BLUE, VERM])),
                tooltip=["cue_type", "kind", "pct"]).properties(height=320))
            st.altair_chart(ch2, use_container_width=True)
            st.markdown(f"**Remembered vs forgotten cues** (n={len(FDF)})")
    with st.expander("Query styles & workarounds"):
        c3, c4 = st.columns(2)
        for col, colname, color in [(c3, "query_style", BLUE), (c4, "workaround", ORANGE)]:
            with col:
                s2 = FDF[colname].fillna("none_stated").value_counts().rename("n").reset_index()
                s2["share_pct"] = (100 * s2["n"] / max(len(FDF), 1)).round(1)
                s2 = s2.sort_values("n", ascending=True)
                ch3 = (alt.Chart(s2).mark_bar(color=color).encode(
                    x=alt.X("share_pct:Q", title="share (%)"), y=alt.Y(f"{colname}:N", sort=list(s2[colname])),
                    tooltip=[colname, "n", "share_pct"]).properties(height=340))
                st.altair_chart(ch3, use_container_width=True)
                st.markdown(f"**{colname}** (n={len(FDF)})")
    with st.expander("Episode table (searchable)"):
        search = st.text_input("Filter by text…", key="table_search", max_chars=200)
        view = FDF.copy()
        if search:
            s = search.lower()
            view = view[view["snippet"].str.lower().str.contains(s, na=False) |
                        view["failure_mechanism"].fillna("").str.lower().str.contains(s, na=False)]
        show = view[["doc_id", "source", "date", "failure_gate", "photo_type", "snippet",
                     "evidence_quote", "url"]].copy()
        show["date"] = show["date"].astype(str).str[:10]
        st.dataframe(show, use_container_width=True, hide_index=True, height=400)
        st.caption(f"{len(show)} episodes shown")

# ================= TAB 3: Try it =================
with tabs[2]:
    st.markdown("### Try it: analyze a feedback text")
    st.markdown("Paste a public feedback text (max 1,200 characters) about finding a photo.")
    txt = st.text_area("Feedback text", key="tryit", max_chars=1200,
                       placeholder="e.g. 'I am looking for a picture of my trip to the mountains last year with my friends…'")
if st.button("Analyze"):
    if not txt.strip():
        st.info("Paste a feedback text first (max 1,200 characters).")
    else:
            st.markdown("**Nearest-episode estimate (no live AI)** — always shown:")
            try:
                t7 = T7
                ne = ee.nearest_estimate(txt, FDF, EMB, k=8, enums=ENUMS, model_cache=MC, t7=t7)
                st.markdown(f"*{ne['label']}*")
                st.markdown(f"- votes: " + ", ".join(
                    f"{k}={v}" for k, v in ne["votes"].items() if v))
                cell = ne.get("scorecard_cell")
                if cell:
                    st.markdown(f"- scorecard cell: {cell['photo_type']} × {cell['failure_gate']} "
                                f"(n_cell={cell['n_cell']}, score={cell['score']:.0f})" if cell.get("score") is not None
                                else f"- scorecard cell: {cell['photo_type']} × {cell['failure_gate']} (n_cell={cell['n_cell']})")
                else:
                    st.markdown("- scorecard cell: none (no scored cell ≥8 for the majority combination)")
                st.markdown("**3 most similar evidence**")
                for item in ne["most_similar"]:
                    row = DF[DF["doc_id"].astype(str) == item["doc_id"]]
                    r = row.iloc[0] if len(row) else None
                    with st.expander(f"[ep:{item['doc_id']}] {item['snippet'][:110]}…"):
                        if r is not None:
                            st.markdown(f"- source: {r.get('source')} · {str(r.get('date'))[:10]} · gate: {r.get('failure_gate')}")
                            if r.get("evidence_quote"):
                                st.markdown(f"> “{r.get('evidence_quote')}”")
                            if r.get("url"):
                                st.markdown(f"[link]({r.get('url')})")
            except Exception as e:
                st.error(f"Nearest-estimate failed: {type(e).__name__}")

            st.divider()
            if status["available"]:
                st.markdown("**AI-mode extraction** (live Gemini)")
                prompt_file = "stage2_v1.txt"
                try:
                    system = open(prompt_file).read().strip()
                except Exception:
                    system = ("You are an annotation engine for UX research. Read ONE user feedback text about "
                              "Google Photos and fill the JSON schema. Return ONLY JSON matching the schema.")
                if "live_session" not in st.session_state:
                    st.session_state.live_session = {"live_calls": 0}
                res = live_llm.live_json(system, f'User feedback text:\n"""\n{txt}\n"""\n\nReturn the JSON object.',
                                         schema_model=Episode, session=st.session_state.live_session, max_tokens=1000)
                if res is None:
                    st.warning("Live AI unavailable just now (cap, timeout, or breaker). The basic-mode estimate above still applies.")
                else:
                    epd = res
                    quote_ok = True
                    q = epd.get("evidence_quote")
                    if q:
                        import re as _re
                        nq = _re.sub(r"\s+", " ", q).strip().lower()
                        nt = _re.sub(r"\s+", " ", txt).strip().lower()
                        if nq not in nt:
                            epd["evidence_quote"] = None
                            quote_ok = False
                    st.json(epd)
                    if not quote_ok:
                        st.caption("evidence_quote dropped: not a verbatim substring of your text.")
                    st.caption("Structured extraction per the stage-2 schema (prompt v1).")
            else:
                st.markdown("**Basic mode** — no live AI configured; showing the rule-based reading:")
                try:
                    plan = ee.route_keywords("Where does it break: " + txt[:200], ENUMS)
                    res = ee.run_plan(plan, FDF, EMB, ENUMS, model_cache=MC, emb_ids=EMB_IDS)
                    st.markdown(ee.templated_summary("try", res))
                except Exception as e:
                    st.error(f"Basic analysis failed: {type(e).__name__}")
            st.info("Do not paste personal information. In AI mode your text is sent to Google's Gemini API; "
                    "in basic mode it stays inside this demo.")

# ================= TAB 4: Opportunity scorecard =================
with tabs[3]:
    st.markdown("### Opportunity scorecard")
    if T7 is None or not len(T7):
        st.warning("Scorecard table (T7) not present in this build.")
    else:
        t7 = T7.copy()
        st.markdown("Cell = photo_type × failure_gate with n_cell ≥ 8 (excludes not_search_related/unclear). "
                    "score = 100·(w_f·freq/maxfreq + w_s·sev + w_g·gap + w_l·lev).")
        c1, c2, c3, c4 = st.columns(4)
        w_f = c1.slider("w freq", 0.0, 0.6, 0.35, 0.01)
        w_s = c2.slider("w severity", 0.0, 0.6, 0.25, 0.01)
        w_g = c3.slider("w gap", 0.0, 0.6, 0.20, 0.01)
        w_l = c4.slider("w AI-leverage", 0.0, 0.6, 0.20, 0.01)
        no_lev = st.toggle("Remove AI-leverage assumption (renormalize weights)")
        mf = (t7["n_cell"].max() / t7["n_cell"].sum()) if len(t7) else 1
        if no_lev:
            tot = w_f + w_s + w_g
            if tot > 0:
                a, b, c_ = w_f / tot, w_s / tot, w_g / tot
            else:
                a, b, c_ = 1 / 3, 1 / 3, 1 / 3
            t7["live_score"] = 100 * (a * t7["freq"] / mf + b * t7["sev"] + c_ * t7["gap"])
        else:
            tot = w_f + w_s + w_g + w_l
            if tot > 0:
                a, b, c_, d = w_f / tot, w_s / tot, w_g / tot, w_l / tot
            else:
                a, b, c_, d = 0.35, 0.25, 0.2, 0.2
            t7["live_score"] = 100 * (a * t7["freq"] / mf + b * t7["sev"] + c_ * t7["gap"] + d * t7["lev"])
        t7["live_rank"] = t7["live_score"].rank(ascending=False).astype(int)
        t7["cell"] = t7["photo_type"] + " × " + t7["failure_gate"]
        show = t7.sort_values("live_score", ascending=False)
        st.dataframe(show[["photo_type", "failure_gate", "n_cell", "freq", "sev", "gap", "gap_flag",
                           "lev", "score", "live_score", "live_rank", "p_top3"]],
                     use_container_width=True, hide_index=True)
        top = show.head(10).copy()
        top["txt"] = (top["live_score"].round(0).astype(int).astype(str)
                      + "  P(top3)=" + top["p_top3"].round(2).astype(str)
                      + "  n=" + top["n_cell"].astype(str))
        ch = alt.layer(
            alt.Chart(top).mark_bar().encode(
                x=alt.X("live_score:Q", title="opportunity score (live weights)"),
                y=alt.Y("cell:N", sort="-x"),
                color=alt.Color("failure_gate:N", scale=alt.Scale(domain=list(top["failure_gate"]), range=[GATE_COLOR[g] for g in top["failure_gate"] if g in GATE_COLOR])),
                tooltip=["photo_type", "failure_gate", "n_cell", "live_score", "p_top3"]).properties(height=420),
            alt.Chart(top).mark_text().encode(
                x=alt.X("live_score:Q"),
                y=alt.Y("cell:N", sort="-x"),
                text=alt.Text("txt:N")).properties(height=420),
        )
        st.altair_chart(ch, use_container_width=True)
        st.markdown(f"**Top-10 opportunity cells** (n={len(t7)} scored cells, cell n≥8). "
                    "P(top3) = probability of a top-3 finish under 1,000 random Dirichlet weight vectors.")
        st.warning(
            "**Limits of this evidence:** app-store reviews skew to complaints; Reddit skews to power users; "
            "failure gates are model-inferred (see sidebar validation numbers); the scorecard shows failure "
            "**types**, not prevalence in the user population; era boundaries are a working assumption.")

# keep a top-level guard so no raw traceback reaches the user
def _guard():
    try:
        yield
    except Exception as e:  # pragma: no cover
        st.error(f"Unexpected error: {type(e).__name__}. The data bundle is intact; please retry.")

st.caption("Data: public app-store reviews + Reddit, cleaned and model-extracted. "
           "Quotes are verbatim substrings verified in code. No personal data is stored.")
