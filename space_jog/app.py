"""Jog MVP — Google Photos (2026) standard UI (Track A restyle).

Material 3 tokens in assets/gp.css, copy deck in copy.py, icons in icons.py.
jog_engine/ and the analytics logging contract are unchanged.
"""
import html
import json
import re
import sys
import time
import traceback
import uuid
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from jog_engine.config import MAX_ROUNDS  # noqa: E402
from jog_engine.session import JogSession  # noqa: E402
import live_llm  # noqa: E402
import gp_copy as C  # noqa: E402
from icons import icon, sparkle, pinwheel, cue_icon  # noqa: E402

st.set_page_config(page_title="Photos", layout="wide", initial_sidebar_state="collapsed")

GP_CSS = (BASE / "assets/gp.css").read_text()
st.markdown(f"<style>{GP_CSS}</style>", unsafe_allow_html=True)

# ---------------- helpers ----------------
def esc(s):
    return html.escape(str(s), quote=True)

def _svg_uri(name, s=24, c="#444746"):
    return "data:image/svg+xml;utf8," + icon(name, s, c).replace('"', "'").replace("#", "%23")

def _sparkle_uri(s=24):
    return "data:image/svg+xml;utf8," + sparkle(s, "g1").replace('"', "'").replace("#", "%23")

def _pinwheel_uri(s=26):
    return "data:image/svg+xml;utf8," + pinwheel(s).replace('"', "'").replace("#", "%23")

def iconbtn(key, name, label, s=24, c="#444746", kind="default", svg=None):
    """Icon-only button: accessible name = label (never visible), 40px circle.
    kind: default | tonal | back (44px)."""
    uri = svg if svg else _svg_uri(name, s, c)
    with st.container(key=f"ic_{key}"):
        pressed = st.button(label, key=f"icb_{key}")
    st.markdown(f"<style>[data-testid='stElement'][class*='icb_{key}'] [data-testid='stButton'] > button::before "
                f"{{ content:''; width:{s}px; height:{s}px; display:block; "
                f"background:url(\"{uri}\") center/contain no-repeat; }}</style>",
                unsafe_allow_html=True)
    return pressed

# ---------------- data bundle (loaded once) ----------------
@st.cache_resource
def load_bundle():
    meta = pd.read_parquet(BASE / "data/meta.parquet")
    emb = np.load(BASE / "image_emb.npy".replace("image_emb.npy", "data/image_emb.npy")).astype("float32")
    emb_idx = json.loads((BASE / "data/emb_index.json").read_text())
    ids = [i for i in emb_idx if i in set(meta["img_id"])]
    meta = meta[meta["img_id"].isin(ids)].reset_index(drop=True)
    emb = emb[[emb_idx.index(i) for i in ids]]
    people = json.loads((BASE / "data/people.json").read_text()) if (BASE / "data/people.json").exists() else {}
    gaz = json.loads((BASE / "data/gazetteer.json").read_text())
    tasks = json.loads((BASE / "data/tasks.json").read_text())
    examples = json.loads((BASE / "data/examples.json").read_text())
    from jog_engine.retrieval import Retriever
    from sentence_transformers import SentenceTransformer
    clip = SentenceTransformer("clip-ViT-B-32")
    ret = Retriever(meta, emb, clip)
    try:  # warm the CLIP text encoder at server start (keeps first search fast)
        clip.encode(["warmup"], convert_to_numpy=True, normalize_embeddings=True)
    except Exception:  # noqa: BLE001
        pass
    return {"meta": meta, "emb": emb, "people": people, "gaz": gaz,
            "tasks": tasks, "examples": examples, "ret": ret, "clip": clip}

BUNDLE = load_bundle()
META = BUNDLE["meta"].set_index("img_id", drop=False)
PERSONS = BUNDLE["people"].get("persons", [])
IMG2PERSON = BUNDLE["people"].get("img2person", {})
IMG2PERSON_IDS = set(IMG2PERSON.keys())
EVENT_TITLES = {
    "e01": "Orientation week", "e02": "Hostel life and fests", "e03": "Diwali at home",
    "e04": "Goa trip", "e05": "Exam season", "e06": "Hampi trip", "e07": "Sick week",
    "e08": "Pondicherry trip", "e09": "Internship Bengaluru", "e10": "Gokarna trip",
    "e11": "Fest night", "e12": "Ganesh Chaturthi at home", "e13": "Everyday and utility",
}
N_PHOTOS = len(META)

def img_path(img_id):
    return BASE / "images" / f"{img_id}.jpg"

def caption_of(img_id):
    row = META.loc[img_id]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return str(row.get("caption") or "").strip()

def date_of(img_id):
    row = META.loc[img_id]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return pd.to_datetime(row["timestamp"])

def person_label(pid):
    if pid == st.session_state.get("you_person"):
        return C.YOU
    p = next((x for x in PERSONS if x["id"] == pid), None)
    return p["label"] if p else "Person"

def person_avatar(pid):
    p = next((x for x in PERSONS if x["id"] == pid), None)
    if not p:
        return None
    ap = BASE / "data" / p.get("avatar", "")
    return str(ap) if ap.exists() else None

# ---------------- logging (contract-locked) ----------------
LOG_PATH = BASE / "logs" / "events.jsonl"
LOG_PATH.parent.mkdir(exist_ok=True)

def log_event(mode, task_id, event, payload=None):
    rec = {"ts": pd.Timestamp.utcnow().isoformat(),
           "session_id": st.session_state.get("anon_session"),
           "participant_id": st.session_state.get("participant") or None,
           "mode": mode, "task_id": task_id, "event": event, "payload": payload or {}}
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ---------------- mic (Web Speech API; local only) ----------------
MIC_JS = """
<script>
const mr = document.querySelector('span.micreq');
if (mr && !mr.dataset.done) {
  mr.dataset.done = '1';
  const rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!rec) { mr.remove(); return; }
  rec.lang = 'en-IN'; rec.interimResults = false; rec.maxAlternatives = 1;
  rec.onresult = (e) => {
    const t = e.results[0][0].transcript;
    const tgt = mr.dataset.target;
    const sel = tgt === 'pill' ? 'input[aria-label="Search Google Photos"]'
               : tgt === 'search' ? 'input[aria-label="Search your photos"]' : 'textarea';
    const inp = document.querySelector(sel);
    if (inp) { inp.value = t;
               inp.dispatchEvent(new Event('input', {bubbles:true}));
               inp.dispatchEvent(new Event('change', {bubbles:true})); }
    setTimeout(() => mr.remove(), 300);
  };
  rec.onend = () => setTimeout(() => mr.remove(), 4000);
  rec.onerror = () => setTimeout(() => mr.remove(), 4000);
  try { rec.start(); } catch (e) { mr.remove(); }
}
</script>
"""

def _mic_mark(target):
    st.markdown(f'<span class="micreq" data-target="{esc(target)}"></span>', unsafe_allow_html=True)

# ---------------- session boot ----------------
if "anon_session" not in st.session_state:
    st.session_state["anon_session"] = str(uuid.uuid4())
    log_event("free", "free", "session_start", {"queue": None})
log_event("free", "free", "live_status", {"mode": live_llm.mode_label()})

def _reset_all():
    for k in list(st.session_state.keys()):
        st.session_state.pop(k, None)
    st.session_state["anon_session"] = str(uuid.uuid4())
    st.rerun()

# =========================================================
# Shell — top bar / sidebar (desktop), top + floating nav (phone)
# =========================================================
def _pill_submitted():
    q = (st.session_state.get("pill_q") or "").strip()
    if not q:
        return
    st.session_state["search_q"] = q
    st.session_state["view"] = "search"
    st.session_state["search_mode"] = "search"
    _classic_go("free_classic", "pill_q")

def _ask_from_pill():
    st.session_state["view"] = "search"
    st.session_state["search_mode"] = "ask"

def desktop_bar():
    with st.container(key="gptop"):
        row = st.columns([0.8, 2.4, 0.6], vertical_alignment="center", gap="small")
        with row[0]:
            st.markdown(f'<div class="gptb-brand">{pinwheel(26)}<span>Photos</span></div>',
                        unsafe_allow_html=True)
        with row[1]:
            with st.container(key="gpsearchpill"):
                i_a, i_b, i_c, i_d = st.columns([0.4, 6, 0.35, 1.15],
                                                vertical_alignment="center", gap="small")
                with i_a:
                    st.markdown(f'<div class="gpp-searchicon">{icon("search", 20, "#444746")}</div>',
                                unsafe_allow_html=True)
                with i_b:
                    st.text_input(C.SEARCH_PLACEHOLDER, key="pill_q",
                                  label_visibility="collapsed", placeholder=C.SEARCH_PLACEHOLDER,
                                  on_change=_pill_submitted)
                with i_b:
                    iconbtn("pill_mic", "mic", "Voice search", s=22, c="#444746")
                    if st.session_state.get("mic_pill_pending"):
                        st.session_state.pop("mic_pill_pending", None)
                        _mic_mark("pill")
                with i_c:
                    st.button(C.ASK, key="pill_ask_chip", on_click=_ask_from_pill)
        with row[2]:
            with st.container(key="gpavatarbtn"):
                avatar_svg = ('<svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">'
                              '<circle cx="16" cy="16" r="16" fill="#D3E3FD"/>'
                              '<text x="16" y="21" font-size="14" font-weight="600" text-anchor="middle" '
                              'fill="#041E49" font-family="sans-serif">D</text></svg>')
                if iconbtn("avatar", "person", "Menu", s=30, svg=avatar_svg):
                    st.session_state["avatar_menu"] = True
                    st.rerun()
    st.markdown('<style>'
                '.st-key-gptop { position:sticky; top:0; z-index:50; background:var(--gp-surface);'
                ' border-bottom:1px solid var(--gp-divider); padding:8px 24px; margin:0; }'
                '.st-key-gptop [data-testid="stHorizontalBlock"]{align-items:center; gap:16px;}'
                '.st-key-gptop > [data-testid="stVerticalBlock"]{padding:0;margin:0;}'
                '.st-key-gpsearchpill > [data-testid="stHorizontalBlock"]{gap:2px; align-items:center;}'
                '.st-key-gpsearchpill, .st-key-gpsearchpill [data-testid="stVerticalBlock"]{padding:0;margin:0;}'
                '.st-key-gpsearchpill [data-testid="stHorizontalBlock"]{width:100%; max-width:720px; height:48px;'
                ' background:var(--gp-surface-container-high); border:2px solid transparent; border-radius:999px;'
                ' padding:0 8px; transition:all 250ms cubic-bezier(.2,0,0,1);}'
                '.st-key-gpsearchpill [data-testid="stHorizontalBlock"]:focus-within{'
                ' background:var(--gp-surface); border-color:var(--gp-primary); box-shadow:var(--gp-elev1);}'
                '.st-key-gpsearchpill [data-testid="stVerticalBlock"]{padding:0;margin:0;}'
                '.st-key-gpsearchpill input{background:transparent!important;border:none!important;box-shadow:none!important;'
                ' font-size:16px!important;color:var(--gp-on-surface)!important;padding:0 4px!important;height:40px!important;}'
                '.st-key-gpsearchpill input::placeholder{color:var(--gp-on-surface-variant);opacity:1;}'
                '.st-key-pill_ask_chip [data-testid="stButton"] > button{'
                ' border-radius:999px!important;height:36px!important;min-height:36px!important;padding:0 14px!important;'
                ' font-size:14px!important;font-weight:500!important;background:var(--gp-surface)!important;'
                ' color:var(--gp-on-primary-container)!important;border:1px solid var(--gp-outline-variant)!important;'
                ' display:inline-flex!important;align-items:center!important;gap:6px;}'
                '.st-key-pill_ask_chip [data-testid="stButton"] > button:hover{background:var(--gp-primary-container)!important;}'
                '</style>', unsafe_allow_html=True)

def sidebar():
    view = st.session_state.get("view", "home")
    with st.container(key="gpsidebar"):
        st.markdown('<style>.st-key-gpsidebar [data-testid="stVerticalBlock"]{gap:2px!important;padding:0!important;margin:0!important;width:100%!important;}.st-key-gpsidebar [data-testid="stVerticalBlock"] > div{width:100%!important;}</style>',
                    unsafe_allow_html=True)
        with st.container(key=f"navitem_photos"):
            if st.button(C.NAV_PHOTOS, key="nav_photos", use_container_width=True):
                st.session_state["view"] = "home"
                st.rerun()
        with st.container(key=f"navitem_coll"):
            if st.button(C.NAV_COLLECTIONS, key="nav_collections", use_container_width=True):
                st.session_state["view"] = "collections"
                st.session_state["coll_section"] = "all"
                st.rerun()
        with st.container(key="navitem_people"):
            if st.button(C.NAV_PEOPLE, key="nav_people", use_container_width=True):
                st.session_state["view"] = "collections"
                st.session_state["coll_section"] = "people"
                st.rerun()
        with st.container(key="navitem_places"):
            if st.button(C.NAV_PLACES, key="nav_places", use_container_width=True):
                st.session_state["view"] = "collections"
                st.session_state["coll_section"] = "places"
                st.rerun()
    st.markdown('<style>'
                '.st-key-gpsidebar{position:fixed;left:0;top:0;bottom:0;width:256px;z-index:40;box-sizing:border-box!important;'
                ' border-right:1px solid var(--gp-divider);background:var(--gp-surface);padding:12px;}'
                '.st-key-gpsidebar [data-testid="stButton"] > button{'
                ' border-radius:999px!important;height:44px!important;min-height:44px!important;width:100%!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;'
                ' background:transparent!important;border:none!important;box-shadow:none!important;'
                ' font-size:14px!important;font-weight:500!important;color:var(--gp-on-surface-variant)!important;'
                ' display:flex!important;align-items:center!important;padding:0 16px!important;}'
                '.st-key-gpsidebar [data-testid="stButton"] > button:hover{background:var(--gp-surface-container)!important;}'
                f'.st-key-navitem_{ "photos" if view=="home" else ("coll" if view=="collections" else "_") }'
                ' [data-testid="stButton"] > button, '
                f'.st-key-navitem_{ "people" if view=="collections" and st.session_state.get("coll_section")=="people" else ("places" if view=="collections" and st.session_state.get("coll_section")=="places" else "_") }'
                ' [data-testid="stButton"] > button{'
                ' background:var(--gp-primary-container)!important;color:var(--gp-on-primary-container)!important;}'
                '.st-key-navitem_people [data-testid="stButton"] > button,'
                '.st-key-navitem_places [data-testid="stButton"] > button{padding-left:24px!important;font-weight:400;}'
                '</style>', unsafe_allow_html=True)

def mobile_top():
    with st.container(key="gptopm"):
        row = st.columns([1, 1], vertical_alignment="center")
        with row[0]:
            st.markdown(f'<div class="gptb-brand">{pinwheel(24)}<span>Photos</span></div>',
                        unsafe_allow_html=True)
        with row[1]:
            avatar_svg = ('<svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">'
                          '<circle cx="16" cy="16" r="16" fill="#D3E3FD"/>'
                          '<text x="16" y="21" font-size="14" font-weight="600" text-anchor="middle" '
                          'fill="#041E49" font-family="sans-serif">D</text></svg>')
            if iconbtn("mtopavatar", "person", "Menu", s=30, svg=avatar_svg):
                st.session_state["avatar_menu"] = True
                st.rerun()

def float_nav():
    view = st.session_state.get("view", "home")
    with st.container(key="gpfloat"):
        row = st.columns([1, 1, 1.25, 0.25], gap="small", vertical_alignment="center")
        with row[0]:
            with st.container(key="navpill_photos"):
                if st.button("Photos", key="fnav_photos"):
                    st.session_state["view"] = "home"
                    st.rerun()
        with row[1]:
            with st.container(key="navpill_coll"):
                if st.button("Collections", key="fnav_coll"):
                    st.session_state["view"] = "collections"
                    st.session_state["coll_section"] = "all"
                    st.rerun()
        with row[2]:
            with st.container(key="gpaskbtn"):
                svg_ask = ('<svg viewBox="0 0 24 24" width="26" height="26">'
                           '<path fill="#444746" d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 '
                           '16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 '
                           '4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 '
                           '9.5 14z"/></svg>')
                st.button("Ask Photos", key="fnav_ask", on_click=_fnav_ask_click)
            st.markdown('<style>[data-testid=\'stElement\'][class*="fnav_ask"] [data-testid="stButton"] > button::before '
                         '{ content:""; width:26px; height:26px; display:block; '
                         + f"background:url(\"{svg_ask.replace(chr(34), chr(39))}\") center/contain no-repeat;"
                         + ' }</style>', unsafe_allow_html=True)
        with row[3]:
            pass
    active_p = "navpill_photos" if view == "home" else ""
    active_c = "navpill_coll" if view == "collections" else ""
    st.markdown(f'<style>'
                f'.st-key-{active_p or "_x"} [data-testid="stButton"] > button {{ background:var(--gp-primary-container)!important; color:var(--gp-on-primary-container)!important; }}'
                f'.st-key-{active_c or "_x"} [data-testid="stButton"] > button {{ background:var(--gp-primary-container)!important; color:var(--gp-on-primary-container)!important; }}'
                f'</style>', unsafe_allow_html=True)
    st.session_state["fnav_ask_done"] = True

def _fnav_ask_click():
    st.session_state["view"] = "search"
    st.session_state["search_mode"] = "ask"

def demo_notice():
    if st.session_state.get("demo_dismissed"):
        return
    with st.container(key="gpdemo"):
        row = st.columns([0.7, 5, 0.5], vertical_alignment="center", gap="small")
        with row[0]:
            st.markdown(f'<div class="gpdemo-chip">{C.DEMO_CHIP}</div>', unsafe_allow_html=True)
        with row[1]:
            st.markdown(f'<div class="gpdemo-text">{esc(C.DEMO_NOTICE)}</div>', unsafe_allow_html=True)
        with row[2]:
            if iconbtn("demo_x", "close", "Dismiss", s=20, c="#444746"):
                st.session_state["demo_dismissed"] = True
                st.rerun()
    st.markdown('<style>.st-key-gpdemo{display:flex;align-items:center;gap:10px;background:var(--gp-surface-container);'
                ' border-radius:16px;padding:10px 12px;margin:16px 0 4px;}'
                '.st-key-gpdemo [data-testid="stVerticalBlock"]{padding:0;margin:0;}'
                '.st-key-gpdemo [data-testid="stHorizontalBlock"]{align-items:center;gap:10px;}'
                '</style>', unsafe_allow_html=True)

# ---------------- photo cells / grids ----------------
def photo_cell(img_id, key, lb_ctx="home", ids=None, tk=None, tid_test=None):
    k = f"pcell_{key}"
    with st.container(key=k):
        st.image(str(img_path(img_id)), use_container_width=True)
        with st.container(key=f"pcellb_{key}"):
            if st.button(C.OPEN_PHOTO.format(d=C.day(date_of(img_id))), key=f"pcellbbtn_{key}"):
                grid_ids = ids or [img_id]
                st.session_state["lightbox"] = {
                    "ids": grid_ids, "idx": grid_ids.index(img_id),
                    "ctx": lb_ctx, "tk": tk or "free", "test": bool(tid_test)}
                if lb_ctx == "ask":
                    log_event("jog", tk or "free", "thumbnail_opened", {"img_id": img_id})
        if tid_test:
            if st.button(C.THIS_IS_IT, key=f"tfit_{tid_test}_{img_id}", type="tertiary"):
                st.session_state[f"confirm_img_test_{tid_test}"] = img_id

def photo_grid(ids, key_prefix, lb_ctx="home", mobile=3, desktop=4, tk=None,
               tid_test=None, limit=None):
    sub = ids if limit is None else ids[:limit]
    n = max(mobile, desktop)
    st.markdown(f'<div class="gpgrid m{mobile}d{desktop}">', unsafe_allow_html=True)
    cols = st.columns(n, gap="small")
    for i, img_id in enumerate(sub):
        with cols[i % n]:
            photo_cell(img_id, f"{key_prefix}_{i}", lb_ctx, ids=sub, tk=tk,
                       tid_test=tid_test)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# Photos home
# =========================================================
def _memory_covers():
    """Data-grounded memory cards: real places, real theme clusters, top person."""
    mems = []
    place_labels = [("Goa", "Goa"), ("Campus days", "Zuarinagar Goa"),
                    ("Pune", "Pune"), ("Hampi", "Hampi")]
    for label, pn in place_labels:
        sub = META[META["place_name"] == pn]
        if len(sub) >= 30:
            ts = pd.to_datetime(sub["timestamp"])
            mems.append({"kind": "place", "val": pn, "title": label,
                         "sub": f"{ts.min():%b %Y} · {C.plural(int(len(sub)))}",
                         "cover": _mid_image(sub)})
    text = (META["caption"].fillna("") + " " + META["objects"].fillna("")).str.lower()
    themes = [("Beach days", r"\bbeach|shore|seashore"),
              ("Café mornings", r"caf[eé]|coffee|latte|espresso"),
              ("Sunsets", r"sunset|sun setting"),
              ("Festive evenings", r"diwali|ganesh|diya|fireworks|rangoli|festival"),
              ("On the road", r"train|metro|scooter|cycling|bicycle|road trip")]
    for label, pat in themes:
        msk = text.str.contains(pat, regex=True)
        if int(msk.sum()) >= 40:
            sub = META[msk]
            mems.append({"kind": "theme", "val": pat, "title": label,
                         "sub": C.plural(int(msk.sum())), "cover": _mid_image(sub)})
    for p in PERSONS:
        ids = [i for i, pi in IMG2PERSON.items() if pi == p["id"]]
        if len(ids) >= 15:
            mems.append({"kind": "person", "val": p["id"],
                         "title": f"With {person_label(p['id'])}",
                         "sub": C.plural(len(ids)), "cover": next(iter(ids))})
            break
    return mems[:6]



def _mid_image(sub):
    ts = pd.to_datetime(sub["timestamp"])
    mid = ts.min() + (ts.max() - ts.min()) / 2
    return sub.assign(_d=(ts - mid).abs()).sort_values("_d").iloc[0]["img_id"]

def _mem_card(m, i):
    with st.container(key=f"memcard_{i}"):
        st.image(str(img_path(m["cover"])), use_container_width=True)
        st.markdown('<div class="gpmem-scrim"></div><div class="gpmem-meta">'
                    f'<div class="gpmem-title">{esc(m["title"])}</div>'
                    f'<div class="gpmem-sub">{esc(m["sub"])}</div></div>', unsafe_allow_html=True)
        if st.button(m["title"], key=f"memb_{i}", type="tertiary"):
            if m["kind"] == "person":
                st.session_state["person_filter"] = {"kind": "person", "val": m["val"], "title": m["title"]}
            elif m["kind"] == "place":
                st.session_state["place_filter"] = {"kind": "place", "val": m["val"], "title": m["title"]}
            else:
                st.session_state["mem_filter"] = {"kind": m["kind"], "val": m["val"], "title": m["title"]}
            st.session_state["view"] = "home"
            st.rerun()

def _filter_chip():
    f = st.session_state.get("mem_filter") or st.session_state.get("person_filter") \
        or st.session_state.get("place_filter")
    if not f:
        return
    n = 0
    if f["kind"] == "person":
        n = len([i for i, pi in IMG2PERSON.items() if pi == f["val"]])
    elif f["kind"] == "event":
        n = int((META["event_id"] == f["val"]).sum())
    elif f["kind"] == "place":
        n = int((META["place_name"] == f["val"]).sum())
    elif f["kind"] == "theme":
        t = (META["caption"].fillna("") + " " + META["objects"].fillna("")).str.lower()
        n = int(t.str.contains(f["val"], regex=True).sum())
    with st.container(key="gpfchip"):
        row = st.columns([5, 0.6], vertical_alignment="center")
        with row[0]:
            st.markdown(f'<div class="gpfchip-t">{esc(f["title"])} &middot; {C.plural(n)}</div>',
                        unsafe_allow_html=True)
        with row[1]:
            if iconbtn("fchip_x", "close", "Clear filter", s=18):
                st.session_state.pop("mem_filter", None)
                st.session_state.pop("person_filter", None)
                st.session_state.pop("place_filter", None)
                st.rerun()
    st.markdown('<style>.st-key-gpfchip [data-testid="stHorizontalBlock"]{display:inline-flex;align-items:center;'
                ' background:var(--gp-primary-container);border-radius:999px;padding:6px 6px 6px 14px;gap:4px;}'
                '.st-key-gpfchip .gpfchip-t{font-size:14px;font-weight:500;color:var(--gp-on-primary-container);}'
                '</style>', unsafe_allow_html=True)

def photos_home():
    demo_notice()
    _filter_chip()
    # resume card
    if st.session_state.get("jog_free") and not st.session_state.get("ask_success_free"):
        q = (st.session_state.get("jog_text_free") or "")[:80]
        with st.container(key="gresume"):
            row = st.columns([1.2, 3, 1, 0.5], vertical_alignment="center", gap="small")
            with row[0]:
                st.markdown(f'{sparkle(20, "spkr")}&nbsp; <span class="gr-t">{C.RESUME_TITLE}</span>',
                            unsafe_allow_html=True)
            with row[1]:
                st.markdown(f'<div class="gr-q">{esc(C.RESUME_QUERY.format(q=esc(q)))}</div>',
                            unsafe_allow_html=True)
            with row[2]:
                if st.button(C.BTN_CONTINUE, key="resume_go", type="primary"):
                    st.session_state["view"] = "search"
                    st.session_state["search_mode"] = "ask"
                    st.rerun()
            with row[3]:
                if iconbtn("resume_x", "close", "Dismiss", s=18):
                    st.session_state.pop("jog_free", None)
                    st.session_state.pop("jog_state_free", None)
                    st.rerun()
        st.markdown('<style>.st-key-gresume{display:flex;align-items:center;background:var(--gp-primary-container);'
                    ' border-radius:16px;padding:12px 14px;margin:12px 0;flex-wrap:wrap;gap:8px;}'
                    '.st-key-gresume .gr-t{font-size:14px;font-weight:500;color:var(--gp-on-primary-container);}'
                    '.st-key-gresume .gr-q{font-size:13px;color:var(--gp-on-primary-container);flex:1;min-width:160px;'
                    ' white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}'
                    '.st-key-gresume [data-testid="stButton"] > button{border-radius:999px!important;height:36px!important;'
                    ' font-size:14px!important;font-weight:500!important;background:var(--gp-primary)!important;'
                    ' color:#fff!important;border:none!important;}'
                    '</style>', unsafe_allow_html=True)
    # memories
    mems = _memory_covers()
    if mems:
        st.markdown(f'<div class="gp-section-title" style="margin:16px 0 8px">{C.HOME_MEMORIES}</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="gpmem-grid">', unsafe_allow_html=True)
        for i, m in enumerate(mems):
            _mem_card(m, i)
        st.markdown('</div>', unsafe_allow_html=True)
    # timeline
    _timeline()

def _timeline():
    m = META.copy()
    f = st.session_state.get("mem_filter") or st.session_state.get("person_filter") \
        or st.session_state.get("place_filter")
    if f:
        if f["kind"] == "person":
            ids = {i for i, pi in IMG2PERSON.items() if pi == f["val"]}
            m = m[m["img_id"].isin(ids)]
        elif f["kind"] == "event":
            m = m[m["event_id"] == f["val"]]
        elif f["kind"] == "theme":
            t = (m["caption"].fillna("") + " " + m["objects"].fillna("")).str.lower()
            m = m[t.str.contains(f["val"], regex=True)]
        else:
            m = m[m["place_name"] == f["val"]]
    m = m.sort_values("timestamp")
    if m.empty:
        st.markdown(f'<div class="gp-body-sm" style="margin:24px 0">{C.COLL_PEOPLE_EMPTY}</div>',
                    unsafe_allow_html=True)
        return
    yrs = pd.to_datetime(m["timestamp"]).dt.year.value_counts().sort_index()
    latest2 = set(yrs.index[-2:])
    for y, cnt in yrs.items():
        sub = m[pd.to_datetime(m["timestamp"]).dt.year == y]
        key_y = f"year_{y}"
        expanded = y in latest2 or st.session_state.get(f"year_open_{y}")
        if expanded:
            st.markdown(f'<div class="gpdatehead">{y} &middot; {C.plural(int(cnt))}</div>',
                        unsafe_allow_html=True)
            _month_blocks(sub, key_y)
        else:
            if st.button(f"{y} \u00b7 {C.plural(int(cnt))} \u2014 {C.YEAR_ALL}", key=f"yropen_{y}",
                         type="tertiary"):
                st.session_state[f"year_open_{y}"] = True
                st.rerun()

def _month_blocks(sub, key_prefix):
    months = pd.to_datetime(sub["timestamp"]).dt.to_period("M").value_counts().sort_index(ascending=False)
    for pm, cnt in months.items():
        msub = sub[pd.to_datetime(sub["timestamp"]).dt.to_period("M") == pm]
        key_m = f"{key_prefix}_{pm}"
        head = f"{pm.to_timestamp():%b} {pm.year}"
        if cnt > 12 and not st.session_state.get(f"month_open_{key_m}"):
            st.markdown(f'<div class="gpdatehead">{esc(head)} &middot; {C.plural(int(cnt))}</div>',
                        unsafe_allow_html=True)
            photo_grid(msub["img_id"].tolist(), f"mg_{key_m}", "home", mobile=3, desktop=5, limit=12)
            if st.button(C.MONTH_ALL.format(n=int(cnt)), key=f"mall_{key_m}", type="tertiary"):
                st.session_state[f"month_open_{key_m}"] = True
                st.rerun()
        else:
            st.markdown(f'<div class="gpdatehead">{esc(head)} &middot; {C.plural(int(cnt))}</div>',
                        unsafe_allow_html=True)
            photo_grid(msub["img_id"].tolist(), f"mg_{key_m}", "home", mobile=3, desktop=5)

# =========================================================
# Collections
# =========================================================
def collections_view():
    section = st.session_state.get("coll_section", "all")
    if section in ("all", "people"):
        st.markdown(f'<div class="gp-section-title" style="margin:18px 0 4px">{C.COLL_PEOPLE}</div>',
                    unsafe_allow_html=True)
        # "Which one is you?" (dismissible, optional)
        if not st.session_state.get("you_person") and not st.session_state.get("you_skipped"):
            with st.container(key="gpyou"):
                st.markdown(f'<div class="gpyoucard"><div class="t">{C.WHICH_IS_YOU}</div>'
                            f'<div class="s">{C.WHICH_IS_YOU_SUB}</div></div>',
                            unsafe_allow_html=True)
                top4 = PERSONS[:4]
                cols = st.columns(len(top4), gap="small")
                for c, p in zip(cols, top4):
                    with c:
                        with st.container(key=f"youcard_{p['id']}"):
                            av = person_avatar(p["id"])
                            if av:
                                st.image(av, width=56)
                            if st.button(C.THIS_IS_ME, key=f"youme_{p['id']}"):
                                st.session_state["you_person"] = p["id"]
                                st.rerun()
                if st.button(C.NOT_SURE, key="youskip", type="tertiary"):
                    st.session_state["you_skipped"] = True
                    st.rerun()
                st.markdown('<style>.st-key-gpyou [data-testid="stVerticalBlock"]{gap:6px}'
                            '.st-key-gpyou [data-testid="stHorizontalBlock"]{gap:14px}'
                            '[class*="st-key-youcard_"] [data-testid="stImage"]{margin:0 auto;}'
                            '[class*="st-key-youcard_"] [data-testid="stImage"] img{border-radius:50%;'
                            ' border:2px solid #fff;box-shadow:var(--gp-elev1);}'
                            '[class*="st-key-youcard_"] [data-testid="stButton"] > button{'
                            ' border-radius:999px!important;height:34px!important;font-size:13px!important;'
                            ' font-weight:500!important;background:var(--gp-surface)!important;'
                            ' color:var(--gp-on-primary-container)!important;border:none!important;}'
                            '</style>', unsafe_allow_html=True)
        if PERSONS:
            st.markdown('<div class="gpcoll-grid">', unsafe_allow_html=True)
            cols = st.columns(min(len(PERSONS), 6), gap="small")
            for c, p in zip(cols, PERSONS):
                with c:
                    with st.container(key=f"collp_{p['id']}"):
                        av = person_avatar(p["id"])
                        if av:
                            st.image(av, width=64)
                        st.markdown(f'<div class="gpcoll-person"><div class="nm">{esc(person_label(p["id"]))}</div>'
                                    f'<div class="ct">{C.plural(p["count"])}</div></div>',
                                    unsafe_allow_html=True)
                        if st.button(person_label(p["id"]), key=f"collpbtn_{p['id']}", type="tertiary"):
                            st.session_state["person_filter"] = {
                                "kind": "person", "val": p["id"], "title": person_label(p["id"])}
                            st.session_state["view"] = "home"
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<style>[class*="st-key-collp_"]{text-align:center;padding:10px;background:var(--gp-surface-container);'
                        ' border-radius:16px;position:relative;}'
                        '[class*="st-key-collp_"] [data-testid="stImage"]{margin:0 auto 6px;}'
                        '[class*="st-key-collp_"] [data-testid="stImage"] img{border-radius:50%;border:2px solid #fff;'
                        ' box-shadow:var(--gp-elev1);}'
                        '[class*="st-key-collp_"] .nm{font-size:14px;font-weight:500;color:var(--gp-on-surface);}'
                        '[class*="st-key-collp_"] .ct{font-size:12px;color:var(--gp-on-surface-variant);}'
                        '[class*="st-key-collp_"] [data-testid="stButton"]{position:absolute;inset:0;margin:0;}'
                        '[class*="st-key-collp_"] [data-testid="stButton"] > button{opacity:0;width:100%;height:100%;'
                        ' border:none;background:transparent;box-shadow:none;border-radius:16px;}'
                        '</style>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="gp-body-sm" style="margin:12px 0">{C.COLL_PEOPLE_EMPTY}</div>',
                        unsafe_allow_html=True)
    if section in ("all", "places"):
        st.markdown(f'<div class="gp-section-title" style="margin:22px 0 4px">{C.COLL_PLACES}</div>',
                    unsafe_allow_html=True)
        pc = META["place_name"].fillna("").value_counts()
        places = [(str(n), int(c)) for n, c in pc.items() if n and n != "mixed"][:12]
        if places:
            st.markdown('<div class="gpcoll-grid">', unsafe_allow_html=True)
            cols = st.columns(min(len(places), 4), gap="small")
            for c, (name, cnt) in zip(cols, places):
                with c:
                    with st.container(key=f"collpl_{esc(name).replace(' ', '_')}"):
                        sub = META[META["place_name"] == name]
                        cover = _mid_image(sub)
                        st.image(str(img_path(cover)), use_container_width=True)
                        st.markdown(f'<div class="scrim"></div><div class="meta">'
                                    f'<div class="nm">{esc(name)}</div><div class="ct">{C.plural(cnt)}</div>'
                                    f'</div>', unsafe_allow_html=True)
                        if st.button(name, key=f"collplbtn_{esc(name).replace(' ', '_')}", type="tertiary"):
                            st.session_state["place_filter"] = {
                                "kind": "place", "val": name, "title": name}
                            st.session_state["view"] = "home"
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<style>[class*="st-key-collpl_"]{position:relative;border-radius:16px;overflow:hidden;'
                        ' aspect-ratio:16/10;background:var(--gp-surface-container-high);}'
                        '[class*="st-key-collpl_"] [data-testid="stImage"]{margin:0;padding:0;}'
                        '[class*="st-key-collpl_"] [data-testid="stImage"] img{width:100%;height:100%;object-fit:cover;}'
                        '[class*="st-key-collpl_"] .scrim{position:absolute;inset:0;'
                        ' background:linear-gradient(180deg,transparent 40%,rgba(0,0,0,.65));}'
                        '[class*="st-key-collpl_"] .meta{position:absolute;left:10px;right:10px;bottom:8px;color:#fff;}'
                        '[class*="st-key-collpl_"] .nm{font-size:14px;font-weight:500;}'
                        '[class*="st-key-collpl_"] .ct{font-size:12px;opacity:.85;}'
                        '[class*="st-key-collpl_"] [data-testid="stButton"]{position:absolute;inset:0;margin:0;}'
                        '[class*="st-key-collpl_"] [data-testid="stButton"] > button{opacity:0;width:100%;height:100%;'
                        ' border:none;background:transparent;box-shadow:none;}'
                        '</style>', unsafe_allow_html=True)

# =========================================================
# About sheet (avatar menu)
# =========================================================
@st.dialog(C.ABOUT_TITLE, width="small")
def classic_boost(text):
    frag = text.lower()
    boost = np.zeros(len(META))
    cap = META["caption"].fillna("").str.lower().to_numpy()
    toks = [t for t in re.findall(r"[a-z']{4,}", frag)]
    for j, blob in enumerate(cap):
        for t in toks:
            if t in blob:
                boost[j] += 0.04
    place_hits = set()
    for place, info in BUNDLE["gaz"].items():
        for t in [place.lower()] + [a.lower() for a in info.get("aliases", [])]:
            if t in frag:
                place_hits.add(place)
    if place_hits:
        pn = META["place_name"].fillna("").str.lower().to_numpy()
        area = META["area"].fillna("").str.lower().to_numpy()
        for j in range(len(META)):
            if pn[j] in place_hits or area[j] in place_hits:
                boost[j] += 0.15
    ym = re.search(r"\b(19|20)\d{2}\b", frag)
    if ym:
        tsy = pd.to_datetime(META["timestamp"]).dt.year.to_numpy()
        boost[tsy == int(ym.group(0))] += 0.25
    return boost

def classic_search(text, pool=False):
    text = (text or "").strip()
    if not text:
        return None
    qv = BUNDLE["clip"].encode([text[:300]], convert_to_numpy=True, normalize_embeddings=True)[0]
    sims = BUNDLE["emb"] @ qv.astype("float32")
    combined = sims + classic_boost(text)
    df = pd.DataFrame({"img_id": META["img_id"], "score": combined,
                       "cos": sims, "ts": pd.to_datetime(META["timestamp"])})
    if pool:
        pool_df = df[df["cos"] >= 0.22].copy()
        if IMG2PERSON_IDS and (len(pool_df) > 0 or PERSON_INTENT_RE.search(text.lower())):
            fmask = df["img_id"].isin(IMG2PERSON_IDS)
            face_rows = df[fmask].sort_values("score", ascending=False).head(40)
            pool_df = pd.concat([pool_df, face_rows]).drop_duplicates(subset="img_id")
        if len(pool_df) == 0:
            return None
        return pool_df.sort_values("score", ascending=False).reset_index(drop=True)
    return df.sort_values("score", ascending=False).head(30).reset_index(drop=True)

PERSON_INTENT_RE = re.compile(
    r"\b(friends?|family|people|person|persons?|mom|dad|mother|father|"
    r"brother|sister|kids?|child|me|myself|with me|who|faces?)\b")
HEDGES = re.compile(r"\b(i think|maybe|not sure|kind of|roughly|somewhere|vaguely|"
                    r"half.?remember|can'?t remember|don'?t remember)\b")

def _classic_go(task_id, qkey):
    text = (st.session_state.get(qkey, "") or "").strip()
    if not text:
        return
    st.session_state.pop("force_show_free", None)
    st.session_state[f"classic_queries_{task_id}"] = \
        st.session_state.get(f"classic_queries_{task_id}", 0) + 1
    log_event("classic", task_id, "dump_submitted", {"text": text})
    with st.spinner("Searching…"):
        res = classic_search(text, pool=(task_id == "free_classic"))
    st.session_state[f"classic_res_{task_id}"] = res
    st.session_state["search_q"] = text
    st.session_state["view"] = "search"
    if task_id == "free_classic":
        st.session_state["search_mode"] = "search"
    st.rerun()

def _group_people(res_df, q):
    out = []
    ql = q.lower()
    person_intent = PERSON_INTENT_RE.search(ql)
    for p in PERSONS:
        ids = {i for i, pi in IMG2PERSON.items() if pi == p["id"]}
        n = int(res_df["img_id"].isin(ids).sum())
        label = person_label(p["id"]).lower()
        toks = re.findall(r"[a-z]{3,}", label)
        qmatch = any(t in ql for t in toks)
        if n >= 2 or qmatch or (person_intent and n >= 1):
            out.append((p, n, qmatch))
    out.sort(key=lambda x: (not x[2], -x[1]))
    return out[:4]

def _group_places(res_df):
    counts = {}
    for _, r in res_df.iterrows():
        row = META.loc[r["img_id"]]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        for name in (row.get("place_name"), row.get("area")):
            if name and name != "mixed" and str(name):
                counts[str(name)] = counts.get(str(name), 0) + 1
    lib = META["place_name"].fillna("").value_counts()
    lib2 = META["area"].fillna("").value_counts()
    out = []
    for name, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if n >= 2:
            out.append((name, n, int(lib.get(name, 0) or 0) or int(lib2.get(name, 0) or 0)))
    return out[:4]

def _go_place(name):
    st.session_state["place_filter"] = {"kind": "place", "val": name, "title": name}
    st.session_state["view"] = "home"
    st.rerun()

def _nudge_needed(res):
    q = (st.session_state.get("search_q") or "").lower()
    if HEDGES.search(q):
        return True
    nq = st.session_state.get("classic_queries_free_classic", 0)
    top = float(res["cos"].head(30).max())
    if top < 0.20:
        return True
    return nq >= 2 and top < 0.26

def _grouped_results(res, task_id="free_classic"):
    q = st.session_state.get("search_q", "")
    with st.container(key="gprehead"):
        st.markdown(f'<div class="gpresults-head"><span class="q">{esc(C.RESULTS_HEADER.format(q=q[:60]))}</span>'
                    f'<span class="c">{C.plural(len(res))}</span></div>', unsafe_allow_html=True)
    log_event("classic", task_id, "results_shown", {"img_ids": res["img_id"].head(30).tolist()})
    # nudge banner (hedged / weak)
    if task_id == "free_classic" and _nudge_needed(res):
        with st.container(key="gpnudge"):
            row = st.columns([1, 3, 1.2], vertical_alignment="center", gap="small")
            with row[0]:
                st.markdown(f'<div class="nt">{esc(C.NUDGE_TITLE)}</div>', unsafe_allow_html=True)
            with row[1]:
                st.markdown(f'<div class="ns">{esc(C.NUDGE_TEXT)}</div>', unsafe_allow_html=True)
            with row[2]:
                if st.button(C.BTN_ASK_PHOTOS, key="nudge_ask", type="secondary"):
                    st.session_state["guided_prefill"] = q
                    st.session_state["view"] = "search"
                    st.session_state["search_mode"] = "ask"
                    st.session_state["ask_autostart"] = True
                    st.rerun()
        st.markdown('<style>.st-key-gpnudge{display:flex;align-items:center;gap:12px;background:var(--gp-primary-container);'
                    ' border-radius:16px;padding:12px 14px;margin:10px 0;flex-wrap:wrap;}'
                    '.st-key-gpnudge .nt{font-size:14px;font-weight:500;color:var(--gp-on-primary-container);}'
                    '.st-key-gpnudge .ns{font-size:13px;color:var(--gp-on-primary-container);flex:1;min-width:180px;}'
                    '.st-key-gpnudge [data-testid="stButton"] > button{border-radius:999px!important;height:36px!important;'
                    ' font-size:14px!important;font-weight:500!important;background:var(--gp-surface)!important;'
                    ' color:var(--gp-on-primary-container)!important;border:none!important;}'
                    '</style>', unsafe_allow_html=True)
    # People
    people = _group_people(res, q)
    if people:
        with st.container(key="grp_pp_head"):
            h1, h2 = st.columns([5, 1], vertical_alignment="center", gap="small")
            with h1:
                st.markdown(f'<div class="gpgroup-head" style="margin-top:6px"><span class="t">{C.GROUP_PEOPLE}</span>'
                            f'<span class="c">{esc(C.GROUP_PEOPLE_SUB)}</span></div>', unsafe_allow_html=True)
            with h2:
                if st.button(C.SEE_ALL, key="grp_pp_seeall", type="tertiary"):
                    st.session_state["view"] = "collections"
                    st.session_state["coll_section"] = "people"
                    st.rerun()
        st.markdown('<div class="gpppl-strip">', unsafe_allow_html=True)
        cols = st.columns(len(people), gap="small")
        for c, (p, n, qm), i in zip(cols, people, range(len(people))):
            with c:
                with st.container(key=f"spp_{i}"):
                    av = person_avatar(p["id"])
                    if av:
                        st.image(av, width=56)
                    st.markdown(f'<div class="nm">{esc(person_label(p["id"]))}</div>'
                                f'<div class="ct">{esc(C.IN_RESULTS.format(n=n))}</div>', unsafe_allow_html=True)
                    if st.button(person_label(p["id"]), key=f"grp_pp_{p['id']}", type="tertiary"):
                        st.session_state["person_filter"] = {
                            "kind": "person", "val": p["id"],
                            "title": f"{person_label(p['id'])} \u00b7 {C.IN_RESULTS.format(n=n)}"}
                        st.session_state["view"] = "home"
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<style>[class*="st-key-spp_"]{width:72px;text-align:center;position:relative;flex:0 0 auto;}'
                    '[class*="st-key-spp_"] [data-testid="stImage"]{margin:0 auto 4px;}'
                    '[class*="st-key-spp_"] [data-testid="stImage"] img{border-radius:50%;border:2px solid #fff;'
                    ' box-shadow:var(--gp-elev1);}'
                    '[class*="st-key-spp_"] .nm{font-size:12px;font-weight:500;color:var(--gp-on-surface);}'
                    '[class*="st-key-spp_"] .ct{font-size:11px;color:var(--gp-on-surface-variant);}'
                    '[class*="st-key-spp_"] [data-testid="stButton"]{position:absolute;inset:0;margin:0;}'
                    '[class*="st-key-spp_"] [data-testid="stButton"] > button{opacity:0;width:100%;height:100%;'
                    ' border:none;background:transparent;box-shadow:none;}'
                    '</style>', unsafe_allow_html=True)
    # Places
    places = _group_places(res)
    if places:
        with st.container(key="grp_pl_head"):
            st.markdown(f'<div class="gpgroup-head"><span class="t">{C.GROUP_PLACES}</span>'
                        f'<span class="c">{esc(C.GROUP_PLACES_SUB)}</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="gppl-strip">', unsafe_allow_html=True)
        cols = st.columns(min(len(places), 4), gap="small")
        for c, (name, n, libn) in zip(cols, places):
            with c:
                with st.container(key=f"grp_pl_{esc(name).replace(' ', '_')}"):
                    st.markdown(f'<div class="plc"><div class="nm">{icon("place", 16, "#444746")}'
                                f'<span>{esc(name)}</span></div>'
                                f'<div class="ct">{C.plural(libn)}</div></div>', unsafe_allow_html=True)
                    if st.button(f"{name} \u00b7 {C.plural(libn)}", key=f"grp_plb_{esc(name).replace(' ', '_')}",
                                 type="tertiary"):
                        _go_place(name)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<style>[class*="st-key-grp_pl_"]{width:128px;background:var(--gp-surface-container);'
                    ' border-radius:12px;padding:12px;position:relative;flex:0 0 auto;}'
                    '[class*="st-key-grp_pl_"] .plc .nm{font-size:14px;font-weight:500;color:var(--gp-on-surface);'
                    ' display:flex;align-items:center;gap:6px;white-space:nowrap;overflow:hidden;}'
                    '[class*="st-key-grp_pl_"] .ct{font-size:12px;color:var(--gp-on-surface-variant);margin-top:4px;}'
                    '[class*="st-key-grp_pl_"] [data-testid="stButton"]{position:absolute;inset:0;margin:0;}'
                    '[class*="st-key-grp_pl_"] [data-testid="stButton"] > button{opacity:0;width:100%;height:100%;'
                    ' border:none;background:transparent;box-shadow:none;}'
                    '</style>', unsafe_allow_html=True)
    # Photos (top 30, clean grid — no per-photo buttons; tap opens lightbox)
    with st.container(key="grp_ph_head"):
        st.markdown(f'<div class="gpgroup-head"><span class="t">{C.GROUP_PHOTOS}</span>'
                    f'<span class="c">{esc(C.GROUP_PHOTOS_SUB)}</span></div>',
                    unsafe_allow_html=True)
    photo_grid(res["img_id"].head(30).tolist(), f"grd_{task_id}", "search", mobile=3, desktop=5)

def _zero_router(q):
    with st.container(key="gpzero"):
        st.markdown(f'<div class="gpzero"><div class="t">{C.ZERO_TITLE}</div>'
                    f'<div class="s">{esc(C.ZERO_TEXT.format(q=esc(q[:80])))}</div></div>',
                    unsafe_allow_html=True)
        if st.button(C.BTN_ASK_PHOTOS, key="zero_ask", type="primary"):
            st.session_state["guided_prefill"] = q
            st.session_state["search_mode"] = "ask"
            st.session_state["ask_autostart"] = True
            st.rerun()
        if st.button(C.BTN_SHOW_ANYWAY, key="zero_show", type="tertiary"):
            st.session_state["force_show_free"] = True
            st.rerun()

def _suggestions_ui():
    tp = _build_tag_panel()
    if tp["people"]:
        st.markdown(f'<div class="gpsugg-head">{C.SUG_PEOPLE}</div>', unsafe_allow_html=True)
        st.markdown('<div class="gpsugg-row">', unsafe_allow_html=True)
        for lab, pid in tp["people"][:6]:
            with st.container(key=f"sugpp_{pid}"):
                av = person_avatar(pid)
                if av:
                    st.markdown(f'<img class="sugav" src="data:image/jpeg;base64,'
                                + __import__("base64").b64encode(open(av, "rb").read()).decode() + '">',
                                unsafe_allow_html=True)
                st.markdown(f'<span class="sugtxt">{esc(lab)}</span>', unsafe_allow_html=True)
                if st.button(lab, key=f"sugppb_{pid}", type="tertiary"):
                    st.session_state["person_filter"] = {
                        "kind": "person", "val": pid, "title": f"{lab} photos"}
                    st.session_state["view"] = "home"
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    for key, items, go in (("Places", tp["places"], _go_place), ("Things", tp["things"], None),
                           ("Years", tp["years"], None)):
        if not items:
            continue
        head = {"Places": C.SUG_PLACES, "Things": C.SUG_THINGS, "Years": C.SUG_YEARS}[key]
        st.markdown(f'<div class="gpsugg-head">{head}</div>', unsafe_allow_html=True)
        st.markdown('<div class="gpsugg-row">', unsafe_allow_html=True)
        for i, (val, cnt) in enumerate(items[:6]):
            with st.container(key=f"sug{key.lower()}_{i}"):
                st.markdown(f'<span class="sugtxt">{esc(str(val))} &middot; {cnt}</span>',
                            unsafe_allow_html=True)
                if st.button(f"{val} \u00b7 {cnt}", key=f"sug{key.lower()}b_{i}", type="tertiary"):
                    st.session_state["search_q"] = str(val)
                    if key == "Places":
                        _go_place(str(val))
                    else:
                        _classic_go("free_classic", "search_q")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<style>[class*="st-key-sugpp_"],[class*="st-key-sugplaces_"],[class*="st-key-sugthings_"],'
                '[class*="st-key-sugyears_"]{display:inline-flex;align-items:center;gap:8px;background:var(--gp-surface-container-high);'
                ' border-radius:999px;padding:7px 14px;margin:0 8px 8px 0;position:relative;flex:0 0 auto;}'
                '[class*="st-key-sugpp_"] .sugav{width:26px;height:26px;border-radius:50%;object-fit:cover;}'
                '[class*="st-key-sugpp_"] .sugtxt,[class*="st-key-sugplaces_"] .sugtxt,'
                '[class*="st-key-sugthings_"] .sugtxt,[class*="st-key-sugyears_"] .sugtxt{'
                ' font-size:14px;color:var(--gp-on-surface);white-space:nowrap;}'
                '[class*="st-key-sugpp_"] [data-testid="stButton"],[class*="st-key-sugplaces_"] [data-testid="stButton"],'
                '[class*="st-key-sugthings_"] [data-testid="stButton"],[class*="st-key-sugyears_"] [data-testid="stButton"]{'
                ' position:absolute;inset:0;margin:0;}'
                '[class*="st-key-sugpp_"] [data-testid="stButton"] > button,[class*="st-key-sugplaces_"] [data-testid="stButton"] > button,'
                '[class*="st-key-sugthings_"] [data-testid="stButton"] > button,[class*="st-key-sugyears_"] [data-testid="stButton"] > button{'
                ' opacity:0;width:100%;height:100%;border:none;background:transparent;box-shadow:none;border-radius:999px;}'
                '</style>', unsafe_allow_html=True)

def _build_tag_panel():
    m = META
    out = {"people": [], "places": [], "things": [], "years": []}
    for p in PERSONS:
        if any(pi == p["id"] for pi in IMG2PERSON.values()):
            out["people"].append((person_label(p["id"]), p["id"]))
    place_counts = m["place_name"].value_counts()
    for name, cnt in place_counts.head(7).items():
        if name in ("mixed",):
            continue
        out["places"].append((str(name), int(cnt)))
    cap = m["caption"].fillna("").str.lower()
    obj = m["objects"].fillna("")
    text = (cap + " " + obj.str.replace('"', "", regex=False)).str.lower()
    # Consumer vocabulary, measured against the actual library; keep what exists.
    things = [
        ("Coffee", r"\bcoffee\b|latte|espresso|chai"), ("Beach", r"\bbeach\b|shore|seashore"),
        ("Sunset", r"sunset"), ("Sea and waves", r"\bsea\b|waves|ocean"),
        ("Food and meals", r"\bfood\b|dinner|lunch|plate|curry|biryani|sweets|modak"),
        ("Bicycle", r"\bbicycle\b|cycling|\bbike\b"), ("Cat", r"\bcat\b|kitten"),
        ("Boat", r"\bboat\b|sailboat|coracle"), ("Flowers", r"flower|flowers|garland|marigold"),
        ("Fireworks", r"fireworks|firecracker|sparkler"), ("Dog", r"\bdog\b|puppy"),
        ("Temple", r"\btemple\b|idol|shrine"), ("Notes and study", r"notebook|whiteboard|timetable|equations"),
        ("Laptop", r"laptop"), ("Tickets and receipts", r"ticket|receipt|board pass"),
        ("Rain", r"\brain\b|rainy|umbrella"), ("Stage and lights", r"stage|concert|stage lights"),
        ("Bookshelf", r"bookshelf|books"),
    ]
    for label, pat in things:
        n = int(text.str.contains(pat, regex=True).sum())
        if n >= 8:
            out["things"].append((label, n))
    out["things"] = sorted(out["things"], key=lambda x: -x[1])[:10]
    yrs = pd.to_datetime(m["timestamp"]).dt.year.value_counts()
    out["years"] = [(str(y), int(c)) for y, c in yrs.items()]
    return out

def search_view():
    mode = st.session_state.get("search_mode", "search")
    with st.container(key="gpsearchview"):
        # header: back + segmented toggle
        row = st.columns([0.5, 2, 1], vertical_alignment="center", gap="small")
        with row[0]:
            if iconbtn("searchback", "back", "Back", s=22, c="#444746"):
                st.session_state["view"] = "home"
                st.rerun()
        with row[1]:
            with st.container(key="gpseg"):
                c1, c2 = st.columns(2, gap="small", vertical_alignment="center")
                with c1:
                    if st.button(C.TOGGLE_SEARCH, key="seg_search"):
                        st.session_state["search_mode"] = "search"
                        st.rerun()
                with c2:
                    if st.button(C.TOGGLE_ASK, key="seg_ask"):
                        st.session_state["search_mode"] = "ask"
                        st.rerun()
        with row[2]:
            pass
        if mode == "search":
            _search_bar_free()
            res = st.session_state.get("classic_res_free_classic")
            q = (st.session_state.get("search_q") or "").strip()
            if res is None and not q:
                _suggestions_ui()
            elif res is None and not st.session_state.get("force_show_free"):
                _zero_router(q)
            elif res is None:
                _grouped_results(classic_search(q, pool=False), "free_classic")
            else:
                _grouped_results(res, "free_classic")
            _confirm_free()
        else:
            ask_photos()
    st.markdown('<style>.st-key-gpsearchview{animation:gpslidein 250ms cubic-bezier(.2,0,0,1);}'
                '@keyframes gpslidein{from{transform:translateX(24px);opacity:.4}to{transform:none;opacity:1}}'
                '.st-key-gpseg{display:inline-flex;background:var(--gp-surface-container-high);border-radius:999px;'
                ' padding:3px;gap:2px;}'
                '.st-key-gpseg [data-testid="stButton"] > button{border-radius:999px!important;height:36px!important;'
                ' min-height:36px!important;padding:0 20px!important;font-size:14px!important;font-weight:500!important;'
                ' background:transparent!important;color:var(--gp-on-surface-variant)!important;border:none!important;}'
                + ('.st-key-seg_search [data-testid="stButton"] > button' if mode == "search"
                   else '.st-key-seg_ask [data-testid="stButton"] > button')
                + '{background:var(--gp-surface)!important;color:var(--gp-on-surface)!important;'
                ' box-shadow:var(--gp-elev1)!important;}'
                '</style>', unsafe_allow_html=True)

def _search_bar_free():
    with st.container(key="searchpill_free"):
        row = st.columns([6, 0.5, 1], vertical_alignment="center", gap="small")
        with row[0]:
            st.text_input("Search your photos", key="search_q",
                          placeholder="Search for a person, place, or thing",
                          label_visibility="collapsed")
        with row[1]:
            if iconbtn("mic_free", "mic", "Voice search", s=22):
                _mic_mark("search")
        with row[2]:
            if st.button(C.BTN_SEARCH, key="classic_go_free", type="primary"):
                _classic_go("free_classic", "search_q")
        st.markdown(MIC_JS, unsafe_allow_html=True)
    st.markdown('<style>.st-key-searchpill_free [data-testid="stHorizontalBlock"]{'
                ' display:flex;align-items:center;gap:8px;background:var(--gp-surface-container-high);'
                ' border:2px solid transparent;border-radius:999px;height:52px;padding:0 6px 0 18px;'
                ' transition:all 250ms cubic-bezier(.2,0,0,1);max-width:860px;}'
                '.st-key-searchpill_free [data-testid="stHorizontalBlock"]:focus-within{'
                ' background:var(--gp-surface);border-color:var(--gp-primary);box-shadow:var(--gp-elev1);}'
                '.st-key-searchpill_free [data-testid="stVerticalBlock"]{padding:0;margin:0;}'
                '.st-key-searchpill_free input{background:transparent!important;border:none!important;'
                ' box-shadow:none!important;font-size:16px!important;color:var(--gp-on-surface)!important;'
                ' height:44px!important;padding:0!important;}'
                '.st-key-searchpill_free [data-testid="stButton"] > button{'
                ' background:var(--gp-primary)!important;color:#fff!important;border-radius:999px!important;'
                ' height:40px!important;min-height:40px!important;font-weight:500!important;border:none!important;}'
                '</style>', unsafe_allow_html=True)

def _pretty_setting(s):
    s = str(s or "")
    return SETTING_PRETTY.get(s, s.replace("_", " ").capitalize() if s else "")

def _pretty_place(p):
    p = str(p or "")
    if p in ("", "mixed", "somewhere"):
        return ""
    return p

def _cue_value_label(c):
    v = str(c.value)
    pv = SETTING_PRETTY.get(v.lower(), None)
    if pv:
        v = pv
    elif v.islower() and v.replace("'", "").isalpha():
        v = v[:1].upper() + v[1:]
    return v

def _dedupe_cues(cues):
    """Merge overlapping cues (coffee \u2282 having coffee \u2282 caf\u00e9); cap at 5."""
    items = []
    for c in cues:
        toks = set(re.findall(r"[a-z0-9']{3,}", c.value.lower()))
        items.append({"c": c, "toks": toks})
    kept = []
    for it in items:
        for k in kept:
            if it["c"].negated != k["c"].negated:
                continue
            if it["toks"] and k["toks"] and (it["toks"] <= k["toks"] or k["toks"] <= it["toks"]):
                if len(k["c"].value) >= len(it["c"].value):
                    it = None
                else:
                    kept.remove(k)
                break
        if it is not None:
            kept.append(it)
    kept.sort(key=lambda it: (0 if it["c"].certainty == "sure" else 1))
    return [it["c"] for it in kept[:5]]

def _start_ask(text, tk="free"):
    text = (text or "").strip()
    if len(text) < 3:
        return
    log_event("jog", tk, "dump_submitted", {"text": text})
    st.session_state[f"jog_text_{tk}"] = text
    st.session_state[f"ask_ts_{tk}"] = time.time()
    st.session_state[f"ask_steps_{tk}"] = 1
    with st.spinner(C.LOADING.format(n=f"{N_PHOTOS:,}")):
        sess = JogSession(BUNDLE["ret"], BUNDLE["meta"], BUNDLE["emb"])
        state = sess.start(text, live_session=st.session_state.live_session)
    st.session_state[f"jog_{tk}"] = sess
    st.session_state[f"jog_state_{tk}"] = state
    st.session_state.pop(f"ask_fallback_view_{tk}", None)
    st.session_state.pop(f"ask_undo_{tk}", None)
    log_event("jog", tk, "cues_parsed",
              {"count": len(sess.cues), "parse_source": sess.parse_source})
    _log_moments(state, tk)
    st.rerun()

def _bump_steps(tk):
    st.session_state[f"ask_steps_{tk}"] = st.session_state.get(f"ask_steps_{tk}", 1) + 1

def _log_moments(state, tk="free"):
    mids = "|".join(i for m in state.get("moments", []) for i in m["img_ids"][:3])
    sig = mids + str(len(state.get("top", [])))
    if st.session_state.get(f"_moments_sig_{tk}") != sig:
        st.session_state[f"_moments_sig_{tk}"] = sig
        log_event("jog", tk, "moments_shown",
                  {"n": sum(m["size"] for m in state.get("moments", [])), "img_ids": mids[:300]})

def _ask_idle():
    text = st.session_state.get("ask_text_free", "") or ""
    with st.container(key="gpassk"):
        st.markdown(f'<div class="gphaskead">{sparkle(26, "spka")}<span class="t">{C.ASK_TITLE}</span></div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="gpassub">{esc(C.ASK_SUBTITLE)}</div>', unsafe_allow_html=True)
        st.text_area("Describe the photo", key="ask_text_free", value=text, height=96,
                     placeholder=C.ASK_PLACEHOLDER, label_visibility="collapsed")
        row = st.columns([1.4, 3, 0.5], vertical_alignment="center", gap="small")
        with row[0]:
            if st.button(C.BTN_FIND, key="ask_go", type="primary", disabled=len(text.strip()) < 3):
                _start_ask(text)
        with row[1]:
            if len(text.strip()) < 3:
                st.markdown(f'<div class="gpasskhelper">{esc(C.ASK_HELPER)}</div>', unsafe_allow_html=True)
        with row[2]:
            if iconbtn("ask_mic", "mic", "Voice search", s=22):
                _mic_mark("ask")
        st.markdown(MIC_JS, unsafe_allow_html=True)
        ex = BUNDLE["examples"][:3]
        st.markdown('<div class="gpasskex">', unsafe_allow_html=True)
        cols = st.columns(3, gap="small")
        for c, e in zip(cols, ex):
            with c:
                if st.button(e, key=f"askex_{e[:8]}", type="tertiary"):
                    st.session_state["ask_text_free"] = e
                    _start_ask(e)
        st.markdown('</div>', unsafe_allow_html=True)
        provider = live_llm.mode_label()
        line = C.PRIVACY_AI.format(provider=provider) if live_llm.available() else C.PRIVACY_OFFLINE
        st.markdown(f'<div class="gpasskprivacy">{esc(line)}</div>', unsafe_allow_html=True)


# =========================================================
# Ask Photos — active session (hero flow)
# =========================================================
from jog_engine.fallback import narrowed_window  # noqa: E402

def _reset_ask(tk):
    keys = [f"jog_{tk}", f"jog_state_{tk}", f"jog_text_{tk}", f"ask_ts_{tk}",
            f"ask_steps_{tk}", f"ask_fallback_view_{tk}", f"ask_undo_{tk}",
            f"ask_more_dates_{tk}", f"ask_day_open_{tk}", f"chip_menu_{tk}",
            f"_qsig_{tk}", f"_psig_{tk}", f"_fsig_{tk}", f"_moments_sig_{tk}",
            f"asksent_i_{tk}"]
    for k in keys:
        st.session_state.pop(k, None)
    for k in list(st.session_state.keys()):
        if k.startswith(f"grp_expand_{tk}_") or k.startswith(f"dayb_{tk}_"):
            st.session_state.pop(k, None)

def _ask_chips(tk, session):
    cues = _dedupe_cues(list(session.cues))
    menu_i = st.session_state.pop(f"chip_menu_{tk}", None)
    st.markdown(f'<div class="gpcues-label">{C.PICKED_UP} \u00b7 {C.CHIP_HINT}</div>',
                unsafe_allow_html=True)
    if not cues:
        st.markdown(f'<div class="gpcues-label">{C.NO_CUES}</div>', unsafe_allow_html=True)
        return
    st.markdown('<div class="gpcues-row">', unsafe_allow_html=True)
    for i, c in enumerate(cues):
        label = _cue_value_label(c)
        cls = "gpcue"
        if c.negated:
            cls += " excluded"
            shown = f"Not {label}"
        elif c.certainty == "unsure":
            cls += " maybe"
            shown = f"{label}?"
        else:
            shown = label
        with st.container(key=f"chip_{tk}_{i}"):
            st.markdown(f'<div class="{cls}">{cue_icon(c.type, 14, "currentColor")}'
                        f'<span class="gpcue-v">{esc(shown)}</span></div>',
                        unsafe_allow_html=True)
            if st.button(shown, key=f"chipb_{tk}_{i}", type="tertiary"):
                st.session_state[f"chip_menu_{tk}"] = i
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    if menu_i is not None and menu_i < len(cues):
        c = cues[menu_i]
        with st.container(key=f"chipmenu_{tk}"):
            st.markdown(f'<div class="cm-v">{esc(_cue_value_label(c))}</div>',
                        unsafe_allow_html=True)
            b1, b2, b3, b4, b5 = st.columns([1.2, 1, 1, 0.9, 0.5],
                                             vertical_alignment="center", gap="small")
            def _edit(action):
                recs = []
                for j, cc in enumerate(session.cues):
                    neg, rem, cert = cc.negated, False, cc.certainty
                    if j == menu_i:
                        if action == "right":
                            neg, cert = False, "sure"
                        elif action == "unsure":
                            cert = "unsure"
                        elif action == "notthis":
                            neg = not cc.negated
                        elif action == "remove":
                            rem = True
                    recs.append({"type": cc.type, "value": cc.value, "certainty": cert,
                                 "negated": neg, "remove": rem})
                st.session_state[f"ask_undo_{tk}"] = [
                    {"type": cc.type, "value": cc.value, "certainty": cc.certainty,
                     "negated": cc.negated, "remove": False} for cc in session.cues]
                log_event("jog", tk, "cue_edited",
                          {"count": len([r for r in recs if not r["remove"]])})
                st.session_state[f"jog_state_{tk}"] = session.edit_cues(recs)
                st.session_state.pop(f"chip_menu_{tk}", None)
                _bump_steps(tk)
                st.rerun()
            with b1:
                if st.button(C.CHIP_MENU[0], key=f"cm0_{tk}", type="tertiary"):
                    _edit("right")
            with b2:
                if st.button(C.CHIP_MENU[1], key=f"cm1_{tk}", type="tertiary"):
                    _edit("unsure")
            with b3:
                if st.button(C.CHIP_MENU[2], key=f"cm2_{tk}", type="tertiary"):
                    _edit("notthis")
            with b4:
                if st.button(C.CHIP_MENU[3], key=f"cm3_{tk}", type="tertiary"):
                    _edit("remove")
            with b5:
                if iconbtn(f"cmx_{tk}", "close", "Close", s=18):
                    st.session_state.pop(f"chip_menu_{tk}", None)
                    st.rerun()
    if st.session_state.get(f"ask_undo_{tk}"):
        u1, u2 = st.columns([0.8, 1], vertical_alignment="center")
        with u1:
            st.markdown(f'<div class="gpundo-row">{esc(C.TOAST_UPDATED)}</div>',
                        unsafe_allow_html=True)
        with u2:
            if st.button(C.BTN_UNDO, key=f"undob_{tk}", type="tertiary"):
                sess = st.session_state.get(f"jog_{tk}")
                if sess is not None:
                    st.session_state[f"jog_state_{tk}"] = sess.edit_cues(
                        st.session_state[f"ask_undo_{tk}"])
                    _bump_steps(tk)
                st.session_state.pop(f"ask_undo_{tk}", None)
                st.rerun()

# ---------------- assistant prompt card ----------------
Q_TEXT = {"indoor_outdoor": C.Q_INDOOR_OUTDOOR, "time_of_day": C.Q_TIME_OF_DAY,
          "setting_type": C.Q_SETTING, "season_hint": C.Q_SEASON,
          "people_count_bucket": C.Q_PEOPLE, "has_text": C.Q_WRITING,
          "place_name": C.Q_PLACE, "dominant_color": C.Q_COLOR}

FIXED_OPTS = {
    "indoor_outdoor": [(C.OPT_INDOORS, "indoor"), (C.OPT_OUTDOORS, "outdoor"),
                       (C.OPT_UNSURE, "unclear")],
    "has_text": [(C.OPT_WRITING_YES, True), (C.OPT_WRITING_NO, False)],
    "people_count_bucket": [(C.OPT_PEOPLE_NONE, "1"), (C.OPT_PEOPLE_ONE, "2"),
                            (C.OPT_PEOPLE_FEW, "2-3"), (C.OPT_PEOPLE_GROUP, "4+")],
    "season_hint": [(C.OPT_SEASON_SUMMER, "summer"), (C.OPT_SEASON_MONSOON, "monsoon"),
                    (C.OPT_SEASON_WINTER, "winter")],
}

def _question_options(q):
    attr = q["attribute"]
    if attr in FIXED_OPTS:
        return FIXED_OPTS[attr]
    out = []
    for v in q["options"]:
        if v in ("Something else", "I don't remember", "unclear"):
            continue
        if attr == "setting_type":
            lab = _pretty_setting(v) or str(v)
        elif attr == "time_of_day":
            lab = str(v)[:1].upper() + str(v)[1:]
        else:
            lab = str(v)
        if lab:
            out.append((lab, v))
    if not out:
        out = {"time_of_day": [(C.OPT_MORNING, "morning"), (C.OPT_AFTERNOON, "afternoon"),
                               (C.OPT_EVENING, "evening"), (C.OPT_NIGHT, "night")],
               "place_name": [(str(k), k) for k in list(BUNDLE["gaz"].keys())[:3]],
               "dominant_color": []}.get(attr, [])
    if attr == "setting_type" and len(out) < 4:
        out.append((C.OPT_SETTING_OTHER, "other"))
    return out[:4]

def _apply_answer(tk, session, attr, value):
    st.session_state[f"jog_state_{tk}"] = session.answer(attr, value)
    log_event("jog", tk, "question_answered",
              {"attribute": attr, "value": str(value)})
    _bump_steps(tk)
    _log_moments(st.session_state[f"jog_state_{tk}"], tk)
    st.rerun()

def _apply_choice(tk, session, pair, choice):
    st.session_state[f"jog_state_{tk}"] = session.choose(choice, pair)
    log_event("jog", tk, "pair_choice", {"choice": choice})
    _bump_steps(tk)
    _log_moments(st.session_state[f"jog_state_{tk}"], tk)
    st.rerun()

def _ask_prompt(tk, session, state):
    q = state.get("question")
    pair = state.get("pair")
    if q:
        attr = q["attribute"]
        sig = f"{attr}:{state.get('round')}"
        if st.session_state.get(f"_qsig_{tk}") != sig:
            st.session_state[f"_qsig_{tk}"] = sig
            log_event("jog", tk, "question_shown", {"attribute": attr})
        with st.container(key=f"gpprompt_{tk}"):
            st.markdown(f'<div class="gpprompt"><div class="sysline">{sparkle(22, "spq")}'
                        f'<span class="qt">{esc(Q_TEXT.get(attr, q["text"]))}</span></div>',
                        unsafe_allow_html=True)
            opts = _question_options(q)
            st.markdown('<div class="gpop-row">', unsafe_allow_html=True)
            cols = st.columns(len(opts) + 1, gap="small")
            for c, (lab, val) in zip(cols, opts):
                with c:
                    with st.container(key=f"qopt_{tk}_{lab[:14]}"):
                        if st.button(lab, key=f"qob_{tk}_{lab[:14]}"):
                            _apply_answer(tk, session, attr, val)
            with cols[len(opts)]:
                if st.button(C.SKIP, key=f"qskip_{tk}", type="tertiary"):
                    _apply_answer(tk, session, attr, "I don't remember")
            st.markdown('</div></div>', unsafe_allow_html=True)
        return
    if pair and pair.get("left") and pair.get("right"):
        sig = f"{pair['left']}:{pair['right']}"
        if st.session_state.get(f"_psig_{tk}") != sig:
            st.session_state[f"_psig_{tk}"] = sig
            log_event("jog", tk, "pair_shown",
                      {"left": pair["left"], "right": pair["right"]})
        with st.container(key=f"gpprompt_{tk}"):
            st.markdown(f'<div class="gpprompt"><div class="sysline">{sparkle(22, "spq")}'
                        f'<span class="qt">{esc(C.WHICH_CLOSER)}</span></div>',
                        unsafe_allow_html=True)
            st.markdown('<div class="gppair">', unsafe_allow_html=True)
            c1, c2 = st.columns(2, gap="small")
            for c, side in zip((c1, c2), ("left", "right")):
                pid = pair[side]
                with c:
                    with st.container(key=f"pair_{tk}_{side}"):
                        st.markdown(f'<div class="gppair-item">'
                                    f'<img src="images/{pid}.jpg" alt="Candidate photo '
                                    f'{side}" style="width:100%;height:100%;object-fit:cover">'
                                    f'</div>', unsafe_allow_html=True)
                        if st.button(C.PAIR_LEFT if side == "left" else C.PAIR_RIGHT,
                                     key=f"pairb_{tk}_{side}", type="tertiary"):
                            _apply_choice(tk, session, pair, side)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button(C.NEITHER, key=f"pairneither_{tk}", type="tertiary"):
                _apply_choice(tk, session, pair, "neither")
            st.markdown('</div>', unsafe_allow_html=True)
# ---------------- status line / groups / fallback ----------------
def _ask_range(state):
    tw = state.get("time_window") or {}
    if tw.get("start") and tw.get("end"):
        try:
            return C.daterange(tw["start"], tw["end"])
        except Exception:  # noqa: BLE001
            return None
    ms = state.get("moments") or []
    if ms:
        try:
            s = min(pd.to_datetime(m["start"]) for m in ms)
            e = max(pd.to_datetime(m["end"]) for m in ms)
            if (e - s).days <= 21:
                return C.daterange(s, e)
        except Exception:  # noqa: BLE001
            pass
    return None

def _moment_setting(m, limit=24):
    ids = m["img_ids"][:limit]
    vals = META.loc[[i for i in ids if i in META.index], "setting_type"].dropna()
    if vals.empty:
        return ""
    v = vals.mode().iloc[0]
    return _pretty_setting(v)

def _ask_groups(tk, session, state, is_test=False):
    ms = state.get("moments") or []
    if not ms:
        st.markdown(f'<div class="gp-body-sm" style="margin:12px 0">{C.NO_CUES}</div>',
                    unsafe_allow_html=True)
        return
    more = st.session_state.get(f"ask_more_dates_{tk}")
    visible = ms[:5 if more else 3]
    for gi, m in enumerate(visible):
        ids = m["img_ids"]
        parts = []
        pl = _pretty_place(str(m.get("place_name") or ""))
        if pl:
            parts.append(pl)
        stt = _moment_setting(m)
        if stt:
            parts.append(stt)
        sub = " \u00b7 ".join(parts + [C.plural(m["size"])])
        with st.container(key=f"gpgrp_{tk}_{gi}"):
            h1, h2 = st.columns([5, 0.45], vertical_alignment="center", gap="small")
            with h1:
                st.markdown(f'<div class="gpgrp-head"><span class="d">{esc(C.day(m["start"]))}</span>'
                            f'<span class="s">{esc(sub)}</span></div>',
                            unsafe_allow_html=True)
            with h2:
                if iconbtn(f"grp_around_{tk}_{gi}", "calendar", C.SEARCH_AROUND_DATE, s=20,
                           c="#747775"):
                    st.session_state["anchor_img"] = ids[0]
                    st.session_state["anchor_tk"] = tk
                    st.rerun()
        expanded = st.session_state.get(f"grp_expand_{tk}_{gi}")
        photo_grid(ids if expanded else ids[:6], f"grp_{tk}_{gi}", "ask",
                   mobile=3, desktop=6, tk=tk, tid_test=tk if is_test else None)
        if m["size"] > 6 and not expanded:
            if st.button(C.SEE_ALL_N.format(n=m["size"]), key=f"grp_seeall_{tk}_{gi}",
                         type="tertiary"):
                st.session_state[f"grp_expand_{tk}_{gi}"] = True
                st.rerun()
    if len(ms) > 3 and not more:
        if st.button(C.SHOW_MORE_DATES, key=f"more_dates_{tk}", type="tertiary"):
            st.session_state[f"ask_more_dates_{tk}"] = True
            st.rerun()

def _ask_fallback(tk, session, state):
    ms = state.get("moments") or []
    fw = state.get("fallback") or narrowed_window(ms, BUNDLE["meta"])
    sig = f"{fw['start']}:{fw['end']}"
    if st.session_state.get(f"_fsig_{tk}") != sig:
        st.session_state[f"_fsig_{tk}"] = sig
        log_event("jog", tk, "fallback_shown", {"n": fw.get("n_images", 0)})
    rng = C.daterange(fw["start"], fw["end"])
    with st.container(key=f"gpfallback_{tk}"):
        st.markdown(f'<div class="gpfallback"><div class="t">'
                    f'{esc(C.FALLBACK_TITLE.format(range=rng))}</div>'
                    f'<div class="s">{C.FALLBACK_SUB}</div></div>',
                    unsafe_allow_html=True)
        days = fw.get("days") or {}
        open_day = st.session_state.get(f"ask_day_open_{tk}")
        st.markdown('<div class="gpdayrow">', unsafe_allow_html=True)
        for i, (d, ids) in enumerate(list(days.items())[:14]):
            with st.container(key=f"daychip_{tk}_{i}"):
                st.markdown(f'<div class="gpdaychip">{esc(C.short_day(d))} '
                            f'\u00b7 {C.plural(len(ids))}</div>',
                            unsafe_allow_html=True)
                if st.button(f"{C.short_day(d)} \u00b7 {len(ids)}",
                             key=f"dayb_{tk}_{i}_{d}"):
                    st.session_state[f"ask_day_open_{tk}"] = d
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        if open_day and open_day in days:
            photo_grid(days[open_day], f"daygrid_{tk}_{open_day}", "ask",
                       mobile=3, desktop=5, tk=tk)

def _ask_bottombar(tk, state):
    fw = state.get("fallback")
    rng = C.daterange(fw["start"], fw["end"]) if fw else _ask_range(state)
    with st.container(key=f"gpbotbar_{tk}"):
        b1, b2 = st.columns([2.4, 1.4], vertical_alignment="center", gap="small")
        with b1:
            lab = C.BTN_BROWSE_DATE_RANGE.format(range=rng) if rng else C.BTN_BROWSE_DATE
            if st.button(lab, key=f"browse_{tk}"):
                st.session_state[f"ask_fallback_view_{tk}"] = \
                    not st.session_state.get(f"ask_fallback_view_{tk}", False)
                st.rerun()
        with b2:
            if st.button(C.BTN_START_OVER, key=f"startover_{tk}", type="tertiary"):
                _reset_ask(tk)
                st.rerun()

def _ask_active(tk, session, state, is_test=False):
    with st.container(key=f"gpaskact_{tk}"):
        row = st.columns([0.4, 6, 0.4], vertical_alignment="center", gap="small")
        with row[0]:
            if is_test:
                st.markdown('<div class="gp-spacer"></div>', unsafe_allow_html=True)
            elif iconbtn(f"askback_{tk}", "back", "Back", s=22):
                _reset_ask(tk)
                st.rerun()
        with row[1]:
            with st.container(key=f"asksent_{tk}"):
                s1, s2 = st.columns([6, 0.55], vertical_alignment="center", gap="small")
                with s1:
                    st.text_input("Your description", key=f"asksent_i_{tk}",
                                  value=st.session_state.get(f"jog_text_{tk}", ""),
                                  label_visibility="collapsed")
                with s2:
                    if iconbtn(f"askeedit_{tk}", "edit", "Update search", s=18):
                        _start_ask(st.session_state.get(f"asksent_i_{tk}", ""), tk)
        n = sum(m["size"] for m in state.get("moments", []))
        rng = _ask_range(state)
        st.markdown('<div class="gpstatus">%s</div>' % esc(
            C.STATUS_MATCHES_RANGE.format(n=n, range=rng) if rng
            else C.STATUS_MATCHES.format(n=n)), unsafe_allow_html=True)
        _ask_chips(tk, session)
        _ask_prompt(tk, session, state)
        show_fb = st.session_state.get(f"ask_fallback_view_{tk}") or bool(state.get("fallback"))
        if show_fb:
            _ask_fallback(tk, session, state)
        else:
            _ask_groups(tk, session, state, is_test)
        _ask_bottombar(tk, state)

def ask_photos():
    if st.session_state.pop("ask_autostart", None):
        _start_ask(st.session_state.pop("guided_prefill", ""), "free")
    if st.session_state.get("ask_success_free"):
        return
    session = st.session_state.get("jog_free")
    if session is None:
        _ask_idle()
        return
    state = st.session_state.get("jog_state_free") or session.state_summary()
    st.session_state["jog_state_free"] = state
    _ask_active("free", session, state, is_test=False)
# =========================================================
# Lightbox / success / anchor (dialogs)
# =========================================================
SHARE_JS = """
<script>
const sh = document.querySelector('span.shreq');
if (sh && !sh.dataset.done) {
  sh.dataset.done = '1';
  const u = sh.dataset.url;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(u).catch(() => {});
  }
  setTimeout(() => sh.remove(), 250);
}
</script>
"""

LB_KB_JS = """
<script>
if (!window.__gpLbKb) {
  window.__gpLbKb = 1;
  document.addEventListener('keydown', (e) => {
    const dlg = document.querySelector('[data-testid="stDialog"]');
    if (!dlg || !dlg.querySelector('.gplb')) return;
    const find = (label) => Array.from(dlg.querySelectorAll('button'))
      .find(b => ((b.getAttribute('aria-label') || '') + ' ' + (b.textContent || '')).trim()
                 .split(' ').join(' ').indexOf(label) >= 0);
    if (e.key === 'ArrowRight') {
      const b = find('Next photo'); if (b) { e.preventDefault(); b.click(); }
    } else if (e.key === 'ArrowLeft') {
      const b = find('Previous photo'); if (b) { e.preventDefault(); b.click(); }
    } else if (e.key === 'Enter' && !/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) {
      const b = find("That's it"); if (b) { e.preventDefault(); b.click(); }
    }
  });
}
</script>
"""

def _lb_close():
    st.session_state.pop("lightbox", None)
    st.rerun()

def _lightbox_render():
    lb = st.session_state.get("lightbox")
    if not lb or not lb.get("ids"):
        return
    ids, idx = lb["ids"], lb.get("idx", 0)
    ctx, tk = lb.get("ctx", "home"), lb.get("tk", "free")
    is_test = bool(lb.get("test"))
    img_id = ids[idx]
    if img_id not in META.index:
        st.session_state.pop("lightbox", None)
        return
    row = META.loc[img_id]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    with st.dialog(C.day(row["timestamp"]), key="gplb", bind_key="Escape",
                   on_close=lambda: st.session_state.pop("lightbox", None)):
        with st.container(key="gplb"):
            top = st.columns([0.5, 3, 0.5, 0.5, 0.5], vertical_alignment="center",
                             gap="small")
            with top[0]:
                if iconbtn("lbclose", "back", "Close", s=22, c="#FFFFFF"):
                    _lb_close()
            with top[1]:
                st.markdown(
                    f'<div class="gplb-pos">{esc(C.LB_POSITION.format(i=idx + 1, n=len(ids)))}</div>',
                    unsafe_allow_html=True)
            with top[2]:
                if iconbtn("lbdetails", "info", C.DETAILS, s=22, c="#FFFFFF"):
                    st.session_state["lb_details"] = not st.session_state.get("lb_details", False)
                    st.rerun()
            with top[3]:
                if iconbtn("lbshare", "share", C.SHARE, s=22, c="#FFFFFF"):
                    st.session_state["lb_share"] = f"?photo={img_id}"
                    st.toast(C.TOAST_LINK_COPIED)
                    st.rerun()
            with top[4]:
                pass
            st.markdown('<div class="gplbimgwrap">', unsafe_allow_html=True)
            st.image(str(img_path(img_id)), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.session_state.get("lb_details"):
                place = _pretty_place(str(row.get("place_name", ""))) or "Unknown place"
                cap = caption_of(img_id) or "\u2014"
                sub_line = f"{place} \u00b7 {str(row.get('timestamp', ''))[:10]}"
                st.markdown(f'<div class="gplb-details"><div>{esc(cap)}</div>'
                            f'<div class="sub">{esc(sub_line)}</div>'
                            f'<div class="sub">{C.DETAILS_SYNTHETIC}</div></div>',
                            unsafe_allow_html=True)
            if st.session_state.get("lb_share"):
                st.markdown(
                    f'<span class="shreq" data-url="{esc(st.session_state.pop("lb_share"))}"></span>',
                    unsafe_allow_html=True)
            st.markdown(SHARE_JS + LB_KB_JS, unsafe_allow_html=True)
            nav = st.columns([0.5, 5, 0.5], vertical_alignment="center")
            with nav[0]:
                if idx > 0:
                    if iconbtn("lbprev", "chevron_left", C.LB_PREV, s=26, c="#FFFFFF"):
                        st.session_state["lightbox"]["idx"] = idx - 1
                        st.rerun()
            with nav[2]:
                if idx < len(ids) - 1:
                    if iconbtn("lbnxt", "chevron_right", C.LB_NEXT, s=26, c="#FFFFFF"):
                        st.session_state["lightbox"]["idx"] = idx + 1
                        st.rerun()
            if ctx == "ask":
                bar = st.columns([2.2, 2.2, 0.5], vertical_alignment="center", gap="small")
                with bar[0]:
                    if st.button(C.LB_THATS_IT, key="lb_thatsit", type="primary",
                                 use_container_width=True):
                        if is_test:
                            st.session_state[f"confirm_img_test_{tk}"] = img_id
                            st.session_state.pop("lightbox", None)
                        else:
                            log_event("jog", tk, "confirm_attempt",
                                      {"img_id": img_id, "correct": None})
                            secs = round(time.time() - st.session_state.get(
                                f"ask_ts_{tk}", time.time()), 1)
                            st.session_state["ask_success_free"] = {
                                "img_id": img_id, "seconds": secs,
                                "steps": st.session_state.get(f"ask_steps_{tk}", 1)}
                            st.session_state.pop("lightbox", None)
                        st.rerun()
                with bar[1]:
                    if st.button(C.LB_CLOSE_NOT_IT, key="lb_closenotit", type="secondary",
                                 use_container_width=True):
                        session = st.session_state.get(f"jog_{tk}")
                        if session is not None:
                            ts = pd.to_datetime(row["timestamp"]).to_pydatetime()
                            session.anchor_window = (ts - timedelta(days=3),
                                                     ts + timedelta(days=3))
                            recs = [{"type": c.type, "value": c.value,
                                     "certainty": c.certainty, "negated": c.negated,
                                     "remove": False} for c in session.cues]
                            st.session_state[f"jog_state_{tk}"] = session.edit_cues(recs)
                            log_event("jog", tk, "anchor_set",
                                      {"relation": "close_not_it"})
                            _bump_steps(tk)
                            st.toast(C.TOAST_NARROWED)
                        st.session_state.pop("lightbox", None)
                        st.rerun()
                with bar[2]:
                    if iconbtn("lb_aroundbtn", "calendar", C.SEARCH_AROUND_DATE, s=20):
                        st.session_state["anchor_img"] = img_id
                        st.session_state["anchor_tk"] = tk
                        st.session_state.pop("lightbox", None)
                        st.rerun()

def _success_render():
    s = st.session_state.get("ask_success_free")
    if not s:
        return
    img_id = s["img_id"]

    def _close_succ():
        st.session_state.pop("ask_success_free", None)
        st.rerun()

    with st.dialog("Found it", key="gpsucc", on_close=_close_succ):
        st.image(str(img_path(img_id)), use_container_width=True)
        st.markdown(f'<div class="gpsucc-chips">'
                    f'<span class="gchip ok">{esc(C.SUCCESS_FOUND_IN.format(t=f"{s["seconds"]:.0f} s"))}</span>'
                    f'<span class="gchip">{esc(C.SUCCESS_STEPS.format(k=s["steps"]))}</span>'
                    f'</div>', unsafe_allow_html=True)
        r1, r2 = st.columns([1.3, 1.3], vertical_alignment="center")
        with r1:
            if st.button(C.LB_SHARE, key="succ_share", type="secondary"):
                st.session_state["lb_share"] = f"?photo={img_id}"
                st.toast(C.TOAST_LINK_COPIED)
                st.rerun()
        with r2:
            if st.button(C.BTN_SEARCH_ANOTHER, key="succ_next", type="tertiary"):
                _reset_ask("free")
                _close_succ()
        if st.session_state.get("lb_share"):
            st.markdown(f'<span class="shreq" data-url="{esc(st.session_state.pop("lb_share"))}"></span>',
                        unsafe_allow_html=True)
            st.markdown(SHARE_JS, unsafe_allow_html=True)
        st.markdown(f'<div class="gpsucc-q">{esc(C.SUCCESS_RIGHT_PHOTO)}</div>',
                    unsafe_allow_html=True)
        y1, y2 = st.columns(2, gap="small")
        for c, right in zip((y1, y2), (True, False)):
            with c:
                if st.button(C.YES if right else C.NO, key=f"succ_yn_{int(right)}",
                             use_container_width=True):
                    log_event("jog", "free", "success_feedback",
                              {"img_id": img_id, "right": right})
                    st.toast(C.TOAST_THANKS)
                    _close_succ()

def _anchor_clear():
    st.session_state.pop("anchor_img", None)
    st.session_state.pop("anchor_tk", None)
    st.rerun()

def _anchor_render():
    tk = st.session_state.get("anchor_tk")
    img_id = st.session_state.get("anchor_img")
    if not tk or not img_id:
        return
    session = st.session_state.get(f"jog_{tk}")
    if session is None:
        st.session_state.pop("anchor_img", None)
        st.session_state.pop("anchor_tk", None)
        return
    with st.dialog(C.ANCHOR_TITLE, key="gpanchor", on_close=_anchor_clear):
        with st.container(key="gpanchor"):
            for lab, rel in ((C.ANCHOR_SAME_DAY, "same_day"), (C.ANCHOR_AFTER, "right_after"),
                             (C.ANCHOR_BEFORE, "right_before"), (C.ANCHOR_AROUND, "around")):
                if st.button(lab, key=f"anch_{rel}", use_container_width=True):
                    st.session_state[f"jog_state_{tk}"] = session.set_anchor(img_id, rel)
                    log_event("jog", tk, "anchor_set", {"relation": rel})
                    _bump_steps(tk)
                    _anchor_clear()

def _avatar_menu_render():
    if not st.session_state.get("avatar_menu"):
        return
    with st.dialog("Menu", key="gpavmenu",
                   on_close=lambda: (st.session_state.pop("avatar_menu", None), st.rerun())):
        if st.button(C.AVATAR_MENU[0], key="am_about", use_container_width=True):
            st.session_state.pop("avatar_menu", None)
            st.session_state["about_open"] = "about"
            st.rerun()
        if st.button(C.AVATAR_MENU[1], key="am_how", use_container_width=True):
            st.session_state.pop("avatar_menu", None)
            st.session_state["about_open"] = "how"
            st.rerun()
        if st.button(C.AVATAR_MENU[2], key="am_reset", use_container_width=True):
            _reset_all()

def _about_render():
    which = st.session_state.get("about_open")
    if not which:
        return
    provider = live_llm.mode_label()
    if which == "how":
        with st.dialog(C.HOW_TITLE, key="aboutdlg_how",
                       on_close=lambda: (st.session_state.pop("about_open", None),
                                         st.rerun())):
            for pt in C.HOW_POINTS:
                st.markdown(f'<div class="gp-body-sm" style="margin:8px 0">&bull; '
                            f'{esc(pt)}</div>', unsafe_allow_html=True)
    else:
        with st.dialog(C.ABOUT_TITLE, key="aboutdlg_about",
                       on_close=lambda: (st.session_state.pop("about_open", None),
                                         st.rerun())):
            st.markdown(f'<div class="gp-body-sm">{esc(C.ABOUT_TEXT)}</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="gp-caption" style="margin-top:10px">'
                        f'{esc(C.PROVIDER_LINE.format(provider=esc(provider)))}</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="gp-caption" style="margin-top:6px">'
                        f'{esc(C.LICENSE_NOTE)}</div>', unsafe_allow_html=True)
            if st.button(C.BTN_START_OVER, type="secondary"):
                _reset_all()
# =========================================================
# Test mode (?test=1) + admin (?admin=1) — contract-locked
# =========================================================
TASK_LIMIT_S = 180
PRACTICE_LIMIT_S = 60

def _read_events():
    out = []
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    return out

def study_bar():
    with st.container(key="gpstudybar"):
        st.markdown(f'<div class="gptb-brand">{pinwheel(24)}<span>{C.APP_NAME}</span>'
                    f'<span class="gpstudychip">{C.STUDY_CHIP}</span></div>',
                    unsafe_allow_html=True)

def participant_index(code):
    m = re.match(r"P(\d+)", str(code).strip().upper())
    return int(m.group(1)) - 1 if m else None

def build_queue(idx):
    tasks = {t["id"]: t for t in BUNDLE["tasks"]}
    set_x = [tasks[k] for k in ("X1", "X2", "X3", "X4") if k in tasks]
    set_y = [tasks[k] for k in ("Y1", "Y2", "Y3", "Y4") if k in tasks]
    mode_x = "classic" if idx % 2 == 0 else "jog"
    mode_y = "jog" if mode_x == "classic" else "classic"
    first_is_x = (idx // 2) % 2 == 0
    first, second = (set_x, set_y) if first_is_x else (set_y, set_x)
    mode_map = {t["id"]: mode_x for t in set_x}
    mode_map.update({t["id"]: mode_y for t in set_y})
    practice = []
    for k, mode in (("P1", "classic"), ("P2", "jog")):
        if k in tasks:
            practice.append((tasks[k], mode))
    queue = []
    for t, mode in practice:
        queue.append({"task": t, "mode": mode, "practice": True})
    for t in first:
        queue.append({"task": t, "mode": mode_map[t["id"]], "practice": False})
    for t in second:
        queue.append({"task": t, "mode": mode_map[t["id"]], "practice": False})
    return queue

def task_timer(task_id, deadline, running_key):
    def frag():
        if not st.session_state.get(running_key):
            return
        left = deadline - time.time()
        if left <= 0:
            st.session_state["task_timeout_" + task_id] = True
            st.session_state[running_key] = False
            st.error(C.TM_TIME_UP)
            return
        mins, secs = divmod(int(left), 60)
        st.caption(f"{mins}:{secs:02d} left")
    try:
        st.fragment(run_every="1s")(frag)
    except Exception:  # noqa: BLE001
        left = deadline - time.time()
        if left <= 0:
            st.session_state["task_timeout_" + task_id] = True
            st.session_state[running_key] = False
            st.error(C.TM_TIME_UP)
        else:
            mins, secs = divmod(int(left), 60)
            st.caption(f"{mins}:{secs:02d} left")

def _end_task(item, outcome):
    t = item["task"]
    tid = t["id"]
    mode = item["mode"]
    seconds = 0
    dl = st.session_state.get(f"task_deadline_{tid}")
    if dl:
        seconds = int(max(0, time.time() - (dl - (
            PRACTICE_LIMIT_S if item["practice"] else TASK_LIMIT_S))))
    nq = (st.session_state.get(f"task_queries_{tid}", 0) if mode == "jog"
          else st.session_state.get(f"classic_queries_{tid}", 0))
    sess = st.session_state.get(f"jog_{tid}")
    n_rounds = sess.round if sess is not None else 0
    log_event(mode, tid, "task_end",
              {"outcome": outcome, "seconds": seconds, "n_queries": nq,
               "n_rounds": n_rounds})
    st.session_state[f"task_result_{tid}"] = {"outcome": outcome, "seconds": seconds,
                                              "n_queries": nq}
    st.session_state["test_phase"] = "post"
    st.rerun()

def _test_confirm(item):
    tid = item["task"]["id"]
    img_id = st.session_state.get(f"confirm_img_test_{tid}")
    if not img_id or img_id not in META.index:
        return

    def _dismiss():
        st.session_state.pop(f"confirm_img_test_{tid}", None)
        st.rerun()

    with st.dialog(C.TM_CONFIRM_TITLE, key=f"tcfm_{tid}", on_close=_dismiss):
        st.image(str(img_path(img_id)), use_container_width=True)
        st.markdown(f'<div class="gp-body-sm" style="margin-top:8px">'
                    f'{esc(caption_of(img_id) or "")} \u00b7 {esc(date_of(img_id))}</div>',
                    unsafe_allow_html=True)
        st.caption(C.TM_CONFIRM_SUB)
        y1, y2 = st.columns(2, gap="small")
        with y1:
            if st.button(C.YES, key=f"tcfm_yes_{tid}", type="primary",
                         use_container_width=True):
                correct = img_id == item["task"]["target_img_id"]
                log_event(item["mode"], tid, "confirm_attempt",
                          {"img_id": img_id, "correct": correct})
                if correct:
                    _end_task(item, "success")
                else:
                    wrong = st.session_state.get(f"task_wrong_{tid}", 0) + 1
                    st.session_state[f"task_wrong_{tid}"] = wrong
                    st.session_state.pop(f"confirm_img_test_{tid}", None)
                    if wrong >= 3:
                        _end_task(item, "fail")
                    else:
                        st.toast(C.TM_KEEP_LOOKING)
                        st.rerun()
        with y2:
            if st.button(C.NO, key=f"tcfm_no_{tid}", use_container_width=True):
                _dismiss()

def classic_task_ui(item):
    t = item["task"]
    tid = t["id"]
    res = st.session_state.get(f"classic_res_{tid}")
    c1, c2 = st.columns([5, 1], vertical_alignment="center")
    with c1:
        st.text_input(C.SEARCH_PLACEHOLDER, key=f"classic_q_{tid}",
                      placeholder=C.TM_CLASSIC_PH, label_visibility="collapsed")
    with c2:
        if st.button(C.BTN_SEARCH, key=f"classic_go_{tid}", type="primary"):
            _classic_go(tid, f"classic_q_{tid}")
    if res is not None:
        log_event("classic", tid, "results_shown",
                  {"img_ids": res["img_id"].tolist()})
        photo_grid(res["img_id"].head(30).tolist(), f"tc_{tid}", "test",
                   mobile=3, desktop=4, tid_test=tid)

def jog_test_ui(item):
    t = item["task"]
    tid = t["id"]
    session = st.session_state.get(f"jog_{tid}")
    if session is None:
        with st.container(key="gptaskcard"):
            st.markdown(f'<div class="t">{esc(C.TM_MEMORY_CARD)}</div>'
                        f'<div class="sub">{esc(C.TM_MEMORY_SUB)}</div>',
                        unsafe_allow_html=True)
            st.text_area(C.TM_MEMORY_PH, value=t["fragment_text"],
                         key=f"jogtestmem_{tid}", height=90)
            if st.button(C.BTN_FIND, type="primary", key=f"jogfind_{tid}"):
                _start_ask(st.session_state.get(f"jogtestmem_{tid}", t["fragment_text"]),
                           tk=tid)
        return
    state = st.session_state.get(f"jog_state_{tid}") or session.state_summary()
    st.session_state[f"jog_state_{tid}"] = state
    _ask_active(tid, session, state, is_test=True)

def test_mode():
    if st.session_state.get("test_done"):
        with st.container(key="gptaskcard"):
            st.markdown(f'<div class="t">{C.TM_COMPLETE}</div>', unsafe_allow_html=True)
            st.success(C.TM_COMPLETE_TXT)
            mine = [r for r in _read_events()
                    if r.get("session_id") == st.session_state.get("anon_session")]
            st.download_button(C.TM_DOWNLOAD,
                               data=("\n".join(json.dumps(r, ensure_ascii=False)
                                               for r in mine) + "\n").encode(),
                               file_name=f"session_{st.session_state['anon_session'][:8]}.jsonl",
                               mime="application/jsonl", key="dl_mine")
        st.stop()
    if "test_queue" not in st.session_state:
        with st.container(key="gptaskcard"):
            st.markdown(f'<div class="t">{C.TM_JOIN}</div>'
                        f'<div class="sub">{C.TM_SUB}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1], vertical_alignment="center")
            with c1:
                code = st.text_input(C.TM_CODE_LABEL, key="pcode")
            with c2:
                if st.button(C.TM_START, type="primary"):
                    idx = participant_index(code)
                    if idx is None or idx > 20:
                        st.error(C.TM_BAD_CODE)
                        return
                    st.session_state["participant"] = f"P{idx + 1}"
                    st.session_state["test_queue"] = build_queue(idx)
                    st.session_state["test_pos"] = 0
                    st.session_state["test_phase"] = "card"
                    log_event("test", "", "session_start",
                              {"queue": [(q["task"]["id"], q["mode"], q["practice"])
                                         for q in st.session_state["test_queue"]]})
                    log_event("test", "", "live_status",
                              {"mode": live_llm.mode_label()})
                    st.rerun()
        return
    q = st.session_state["test_queue"]
    pos = st.session_state["test_pos"]
    if pos >= len(q):
        st.session_state["test_done"] = True
        st.rerun()
    item = q[pos]
    t = item["task"]
    tid = t["id"]
    mode = item["mode"]
    phase = st.session_state.get("test_phase", "card")
    tag = C.TM_PRACTICE_TAG if item["practice"] else C.TM_TASK_TAG.format(n=pos - 1)

    if phase == "card":
        with st.container(key="gptaskcard"):
            st.markdown(f'<div class="t">{esc(C.TM_TASK.format(id=esc(tid)))}</div>'
                        f'<div class="meta"><span class="gptag blue">{esc(tag)}</span>'
                        f'<span class="gptag grey">{esc(C.TM_MODE_TAG.format(mode=mode.upper()))}</span></div>'
                        f'<div class="gptaskfrag">{esc(t["fragment_text"])}</div>'
                        f'<div class="sub">{C.TM_LIMIT_PRACTICE if item["practice"] else C.TM_LIMIT}</div>',
                        unsafe_allow_html=True)
            if st.button(C.TM_START_TASK, type="primary", key=f"tstart_{tid}"):
                limit = PRACTICE_LIMIT_S if item["practice"] else TASK_LIMIT_S
                st.session_state[f"task_deadline_{tid}"] = time.time() + limit
                st.session_state[f"task_running_{tid}"] = True
                st.session_state[f"task_wrong_{tid}"] = 0
                st.session_state["test_phase"] = "running"
                log_event(mode, tid, "task_start",
                          {"limit_s": limit, "practice": item["practice"]})
                st.rerun()
    elif phase == "running":
        deadline = st.session_state[f"task_deadline_{tid}"]
        if (st.session_state.get(f"task_running_{tid}") and time.time() > deadline
                and not st.session_state.get(f"task_timeout_{tid}")):
            st.session_state[f"task_timeout_{tid}"] = True
            st.session_state[f"task_running_{tid}"] = False
            st.toast(C.TM_TIME_UP)
        task_timer(tid, deadline, f"task_running_{tid}")
        if st.session_state.get(f"task_timeout_{tid}"):
            _end_task(item, "timeout")
            return
        if mode == "jog":
            jog_test_ui(item)
        else:
            classic_task_ui(item)
        if st.button(C.TM_GIVE_UP, key=f"tgive_{tid}", type="tertiary"):
            _end_task(item, "give_up")
            return
        if st.session_state.get(f"confirm_img_test_{tid}"):
            _test_confirm(item)
    elif phase == "post":
        r = st.session_state[f"task_result_{tid}"]
        with st.container(key="gptaskcard"):
            st.markdown(f'<div class="t">{esc(C.TM_FINISHED.format(id=esc(tid)))}</div>'
                        f'<div class="meta"><span class="gptag grey">{esc(r["outcome"])}</span>'
                        f'<span class="gptag grey">{r["seconds"]}s \u00b7 {r["n_queries"]} queries</span></div>',
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2, gap="small")
            with c1:
                conf = st.selectbox(C.TM_CONF_Q, list(range(1, 6)), key=f"tconf_{tid}")
            with c2:
                ease = st.selectbox(C.TM_EASE_Q, list(range(1, 8)), key=f"tease_{tid}")
            if st.button(C.TM_CONTINUE, type="primary", key=f"tcont_{tid}"):
                log_event(mode, tid, "post_task", {"confidence": conf, "ease": ease})
                st.session_state["test_phase"] = "card"
                st.session_state["test_pos"] += 1
                st.rerun()

def admin_screen():
    with st.container(key="gptaskcard"):
        st.markdown(f'<div class="t">{C.TM_ADMIN}</div>'
                    f'<div class="sub">{C.TM_ADMIN_NOTE}</div>', unsafe_allow_html=True)
        st.download_button(C.TM_ADMIN_FILE,
                           data=("\n".join(json.dumps(r, ensure_ascii=False)
                                           for r in _read_events()) + "\n").encode(),
                           file_name="events.jsonl", mime="application/jsonl")

# =========================================================
# Main
# =========================================================
def main():
    qp = st.query_params
    study = qp.get("test") == "1" or qp.get("admin") == "1"
    if study:
        study_bar()
    else:
        desktop_bar()
        sidebar()
        mobile_top()
    if qp.get("admin") == "1":
        admin_screen()
    elif qp.get("test") == "1":
        test_mode()
    else:
        view = st.session_state.get("view", "home")
        if view not in ("home", "search", "collections"):
            view = "home"
        with st.container(key="gpmain"):
            if view == "search":
                search_view()
            elif view == "collections":
                collections_view()
            else:
                photos_home()
        float_nav()
    _avatar_menu_render()
    _about_render()
    _lightbox_render()
    _success_render()
    _anchor_render()

try:
    main()
except Exception as e:  # noqa: BLE001
    try:
        (BASE / "logs_ui_error.txt").write_text(
            f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
    except Exception:  # noqa: BLE001
        pass
    st.error(C.ERROR_FATAL)
