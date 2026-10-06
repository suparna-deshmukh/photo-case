# ============================================================
# PART 1: header + icon system
# ============================================================

"""Google Photos (demo) with Gemini-guided search — the Jog MVP.

A Google-Photos-styled app over a synthetic free-licensed library (with
recurring face-grouped 'people'). Search is the hero: classic one-shot
search (control) plus Gemini-guided narrowing (Jog engine) that only
activates when a plain search can't resolve the memory. Test mode
(?test=1) + admin (?admin=1) keep the logging contract. Optional AI mode
via live_llm.py (Gemini).
"""
import html
import base64
import json
import re
import sys
import time
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DATA = APP_DIR / "data"
IMAGES = APP_DIR / "images"
LOGS = APP_DIR / "logs"
sys.path.insert(0, str(APP_DIR))

from live_llm import live_status, mode_label  # noqa: E402
from logger import Logger  # noqa: E402
from jog_engine import JogSession, Retriever  # noqa: E402
from jog_engine.config import MAX_ROUNDS  # noqa: E402

TASK_LIMIT_S = 180
PRACTICE_LIMIT_S = 60

st.set_page_config(page_title="Photos", page_icon="📷",
                   layout="wide", initial_sidebar_state="collapsed")

# ---------------- icon system (1.3) ----------------
SPARKLE = ('<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
           '<stop offset="0" stop-color="#1ba1e2"/><stop offset="0.45" stop-color="#9a63f0"/>'
           '<stop offset="0.78" stop-color="#ea4c89"/><stop offset="1" stop-color="#f9ab00"/>'
           '</linearGradient></defs>'
           '<path fill="url(#{gid})" d="M12 1.8c.95 5.6 4.3 8.95 9.9 9.9-5.6.95-8.95 4.3-9.9 9.9'
           '.95-5.6-4.3-8.95-9.9-9.9 5.6-.95 8.95-4.3 9.9-9.9z"/>')


def sparkle(s=20, gid="spk1"):
    return f'<svg viewBox="0 0 24 24" width="{s}" height="{s}">{SPARKLE.format(gid=gid)}</svg>'


PINWHEEL = ('<svg viewBox="0 0 24 24" width="{s}" height="{s}">'
            '<path fill="#4285f4" d="M12 2.8A9.2 9.2 0 0 0 2.8 12H12Z"/>'
            '<path fill="#ea4335" d="M12 2.8A9.2 9.2 0 0 1 21.2 12H12Z"/>'
            '<path fill="#34a853" d="M2.8 12A9.2 9.2 0 0 0 12 21.2V12Z"/>'
            '<path fill="#fbbc04" d="M12 12h9.2A9.2 9.2 0 0 1 12 21.2Z"/></svg>')


def pinwheel(s=26):
    return PINWHEEL.format(s=s)


ICONS = {
    "search": "M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 "
              "9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 "
              "5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z",
    "mic": "M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9 "
            ".36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09 "
            ".54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08c3.02-.43 5.42-2.78 5.91"
            "-5.78.1-.6-.39-1.14-1-1.14z",
    "person": "M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0"
              "-2.66-5.33-4-8-4z",
    "settings": "M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l"
                "-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81c-.04-.24-"
                ".24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41L9.25 5.35c-.59.24-1.13.57-1.62.94l-2.39-.96c-"
                ".22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02"
                ".64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1"
                ".03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1"
                ".13-.57 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.21.08-.47-.12-.61l-2.01-1.58"
                "zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z",
    "share": "M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54 "
             ".5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 "
             "9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08"
             ".43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z",
    "check": "M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z",
    "close": "M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 "
             "13.41 12z",
    "chevron": "M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z",
    "left": "M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z",
    "place": "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-"
             "1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
    "calendar": "M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0"
               "-1.1-.9-2-2-2zm0 16H5V8h14v11z",
    "photo": "M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 "
             "3.01L14.5 12l4.5 6H5l3.5-4.5z",
    "home": "M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z",
    "refresh": "M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 "
              "7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78"
              "L13 11h7V4l-2.35 2.35z",
}


def icon(name, s=24, c="#5f6368"):
    return f'<svg viewBox="0 0 24 24" width="{s}" height="{s}" fill="{c}"><path d="{ICONS[name]}"/></svg>'

# ============================================================
# PART 2: design system CSS + assets
# ============================================================

CSS = """
/* ================= design tokens (Phase 1) ================= */
@font-face {
  font-family: "Roboto Flex";
  font-style: normal;
  font-weight: 100 1000;
  src: url("assets/roboto-flex.woff2") format("woff2");
  font-display: swap;
}
:root {
  --gp-primary: #1a73e8; --gp-primary-d: #1765cc; --gp-tonal: #e8f0fe;
  --gp-text: #202124; --gp-secondary: #5f6368; --gp-disabled: #80868b;
  --gp-hairline: #e8eaed; --gp-fill: #f1f3f4; --gp-bg: #f8f9fa;
  --gp-error: #d93025; --gp-success: #188038;
  --gp-r-card: 16px; --gp-r-img: 8px;
  --gp-shadow-rest: 0 1px 2px rgba(60,64,67,.10);
  --gp-shadow-hover: 0 4px 10px rgba(60,64,67,.16);
  --gp-ease: cubic-bezier(.2,0,.27,1);
}
html, body, [data-testid="stMain"] { background:#ffffff !important; }
.stApp, [data-testid="stMainBlockContainer"] {
  font-family:"Roboto Flex", Roboto, "Helvetica Neue", Arial, sans-serif !important;
  font-optical-sizing:auto; color:var(--gp-text);
}
h1,h2,h3,h4 { letter-spacing:-0.01em; }

/* focus rings */
button:focus-visible, input:focus-visible, textarea:focus-visible {
  outline:2px solid var(--gp-primary) !important; outline-offset:1px; border-radius:8px;
}

/* Streamlit chrome */
[data-testid="stHeader"] { display:none !important; }
[data-testid="stSidebar"] { display:none !important; }
.stApp [data-testid="stToolbar"] { display:none !important; }
[data-testid="stMain"] { max-width:1200px; margin:0 auto; padding:0 24px 40px; }
[data-testid="stMainBlockContainer"] { padding-top:0 !important; }
[data-testid="stMarkdown"]:has(style) { display:none; }
.stElementToolbar { display:none !important; }
@media (max-width:900px) { [data-testid="stMain"] { padding:0 12px 24px; max-width:none; } }

/* ================= desktop app bar (1.6) ================= */
.st-key-gpbar { position:sticky; top:0; z-index:900; background:#fff; border-bottom:1px solid var(--gp-hairline);
  min-height:64px; display:flex; align-items:center; padding:4px 0; }
.st-key-gpbar [data-testid="stVerticalBlock"] { padding:0; }
.st-key-gpbar > [data-testid="stHorizontalBlock"] { width:100%; }
.gpb-inner { display:flex; align-items:center; gap:14px; padding:8px 0; }
.gpb-word { display:flex; align-items:center; gap:8px; font-size:22px; font-weight:500; color:var(--gp-text);
  white-space:nowrap; }
@media (max-width:900px) { .st-key-gpbar { display:none !important; } }
.st-key-gpbpill { flex:1 1 auto; max-width:720px;
  background:var(--gp-fill); border-radius:999px; padding:4px 6px 4px 16px;
  transition:box-shadow .2s var(--gp-ease), background .2s var(--gp-ease); }
.st-key-gpbpill > [data-testid="stHorizontalBlock"] { width:100%; align-items:center; gap:2px;
  padding:0; margin:0; }
.st-key-gpbpill > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] {
  padding:0; margin:0; }
.st-key-gpbpill:focus-within { background:#fff; box-shadow:0 1px 6px rgba(60,64,67,.28); }
.st-key-gpbpill input { border:none !important; background:transparent !important; box-shadow:none !important;
  height:100% !important; font-size:15px; padding:0 !important; min-height:0; }
.st-key-gpbpill input::placeholder { color:var(--gp-disabled); }
.gpb-icobtn { width:40px; height:40px; border-radius:50%; border:none; background:transparent;
  display:inline-flex; align-items:center; justify-content:center; cursor:pointer;
  color:var(--gp-secondary); transition:background .15s var(--gp-ease); }
.gpb-icobtn:hover { background:rgba(60,64,67,.08); }
.gpb-spark { width:34px; height:34px; border-radius:50%; border:none; background:transparent;
  display:inline-flex; align-items:center; justify-content:center; cursor:pointer; }
.gpb-spark:hover { background:var(--gp-tonal); }
.gavatar { width:28px; height:28px; border-radius:50%; background:var(--gp-primary); color:#fff;
  font-size:13px; font-weight:500; display:inline-flex; align-items:center; justify-content:center; flex:none; }
/* ================= mobile top row (1.7) ================= */
.st-key-mtop, .mtop { display:flex; align-items:center; gap:8px; padding:10px 0 6px; }
.st-key-mtop .gpb-word, .mtop .gpb-word { font-size:19px; }
@media (min-width:901px) { .st-key-mtop, .mtop { display:none !important; } }

/* ================= bottom nav (1.7) ================= */

@media (min-width:901px) { .st-key-mnav { display:none !important; } }
@media (max-width:900px) {
  .st-key-mnav { position:fixed; bottom:0; left:0; right:0; z-index:1000; background:#fff;
    border-top:1px solid var(--gp-hairline); padding:4px 8px calc(6px + env(safe-area-inset-bottom)); }
  .st-key-mnav > [data-testid="stHorizontalBlock"] { gap:2px; }
  .st-key-mnav > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { flex:1; margin:0; }
}

/* ================= cards / common ================= */
.card { border:1px solid var(--gp-hairline); border-radius:var(--gp-r-card); background:#fff;
  box-shadow:var(--gp-shadow-rest); padding:14px 16px; transition:box-shadow .2s var(--gp-ease),
  transform .2s var(--gp-ease); }
.card:hover { box-shadow:var(--gp-shadow-hover); }
.gp-section-head { font-size:22px; font-weight:500; margin:18px 0 10px; letter-spacing:-0.01em; }
.card-title { font-size:16px; font-weight:500; }
.card-sub { font-size:13px; color:var(--gp-secondary); }
.card-link { font-size:13.5px; font-weight:500; color:var(--gp-primary); background:none; border:none;
  cursor:pointer; padding:4px 8px; border-radius:999px; }
.card-link:hover { background:var(--gp-tonal); }

/* buttons (GP style) */
.stButton > button[kind="primary"] { background:var(--gp-primary) !important; color:#fff !important;
  border-radius:999px !important; font-weight:500; min-height:40px; font-size:14px;
  transition:background .2s var(--gp-ease), box-shadow .2s var(--gp-ease); }
.stButton > button[kind="primary"]:hover { background:var(--gp-primary-d) !important; transform:none;
  box-shadow:var(--gp-shadow-hover); }
.stButton > button[kind="secondary"] { border-radius:999px !important; min-height:36px; font-weight:500; }
.stButton > button[kind="tertiary"] { border-radius:999px !important; min-height:36px; font-weight:500; }

/* chips */
.chip { display:inline-flex; align-items:center; gap:6px; background:var(--gp-fill); color:var(--gp-text);
  border:none; border-radius:999px; padding:7px 14px; font-size:13.5px; font-weight:500; cursor:pointer;
  transition:background .15s var(--gp-ease); font-family:inherit; }
.chip:hover { background:#e4e7ea; }
.chip.tonal { background:var(--gp-tonal); color:var(--gp-primary); }
.chip.tonal:hover { background:#d2e3fc; }

/* ================= demo card (2.1) ================= */
.democ { border:1px solid var(--gp-hairline); background:var(--gp-bg); border-radius:12px;
  padding:10px 14px; display:flex; align-items:center; gap:10px; margin-bottom:14px; }
.demo-chip { background:var(--gp-primary); color:#fff; font-size:11px; font-weight:600; letter-spacing:.04em;
  border-radius:6px; padding:3px 8px; flex:none; }
.democ .t { font-size:13.5px; color:var(--gp-secondary); flex:1; }

/* ================= memories (2.3) ================= */
.st-key-memrow [data-testid="stHorizontalBlock"] { display:flex; gap:12px; overflow-x:auto; padding-bottom:6px;
  scroll-snap-type:x mandatory; }
.st-key-memrow [data-testid="stVerticalBlock"] { flex:0 0 auto; width:280px; scroll-snap-align:start; }
@media (max-width:900px) { .st-key-memrow [data-testid="stVerticalBlock"] { width:236px; } }
.memcard { position:relative; border-radius:var(--gp-r-card); overflow:hidden; aspect-ratio:16/9;
  cursor:pointer; background:#111; display:block; width:100%; border:none; padding:0;
  box-shadow:var(--gp-shadow-rest); transition:box-shadow .2s var(--gp-ease), transform .2s var(--gp-ease); }
.memcard:hover { box-shadow:var(--gp-shadow-hover); transform:translateY(-1px); }
.memcard img { width:100%; height:100%; object-fit:cover; display:block; }
.memcard .scrim { position:absolute; inset:0; background:linear-gradient(180deg, rgba(0,0,0,0) 40%,
  rgba(0,0,0,.72) 100%); }
.memcard .mtitle { position:absolute; left:14px; right:14px; bottom:12px; color:#fff; font-size:16px;
  font-weight:500; line-height:1.25; }
.memcard .mdate { position:absolute; left:14px; bottom:34px; color:rgba(255,255,255,.75); font-size:12px; }
.memcard .mchip { position:absolute; top:10px; left:10px; background:rgba(0,0,0,.55); color:#fff;
  font-size:11px; font-weight:500; border-radius:999px; padding:3px 9px; backdrop-filter:blur(4px); }

/* ================= people row (2.4) ================= */
.st-key-peoplerow [data-testid="stHorizontalBlock"] { display:flex; gap:8px; overflow-x:auto; padding-bottom:4px; }
.st-key-peoplerow [data-testid="stVerticalBlock"] { flex:0 0 auto; width:84px; }
.person-card { display:flex; flex-direction:column; align-items:center; gap:6px; border:none; background:none;
  cursor:pointer; padding:6px 2px; border-radius:12px; }
.person-card:hover { background:var(--gp-bg); }
.person-card .pimg { width:56px; height:56px; border-radius:50%; object-fit:cover;
  border:2px solid #fff; box-shadow:0 1px 4px rgba(60,64,67,.35); }
@media (min-width:901px) { .person-card .pimg { width:64px; height:64px; } }
.person-card .pname { font-size:12.5px; font-weight:500; color:var(--gp-text); max-width:84px;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.person-card .pcnt { font-size:11px; color:var(--gp-secondary); margin-top:-4px; }
.st-key-peoplerow_grid [data-testid="stVerticalBlock"] { flex:0 0 auto; width:96px; }

/* onboarding inline card (2.5) */
.onboard { border:1px solid var(--gp-hairline); border-radius:var(--gp-r-card); padding:16px;
  display:flex; gap:16px; align-items:center; flex-wrap:wrap; background:#fff; box-shadow:var(--gp-shadow-rest); }
.onboard .ob-title { font-size:15px; font-weight:500; }
.onboard .ob-sub { font-size:12.5px; color:var(--gp-secondary); margin-top:2px; }
.ob-person { display:flex; flex-direction:column; align-items:center; gap:6px; }
.ob-person img { width:64px; height:64px; border-radius:50%; object-fit:cover;
  border:2px solid var(--gp-hairline); }
.ob-person .lab { font-size:12px; color:var(--gp-secondary); }

/* ================= month grid (2.6) ================= */
.year-head { display:flex; align-items:baseline; gap:10px; margin:20px 0 10px; }
.year-head .y { font-size:18px; font-weight:500; }
.year-head .c { font-size:13px; color:var(--gp-secondary); }
.year-head .rule { flex:1; height:1px; background:var(--gp-hairline); }
.month-head { display:flex; align-items:baseline; gap:10px; margin:16px 0 8px; }
.month-head .m { font-size:14px; color:var(--gp-secondary); font-weight:500; }
.month-head .c { font-size:12.5px; color:var(--gp-disabled); }
.month-head .rule { flex:1; height:1px; background:var(--gp-hairline); }
.phgrid { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
@media (min-width:700px) { .phgrid { grid-template-columns:repeat(4,1fr); } }
@media (min-width:901px) { .phgrid { grid-template-columns:repeat(5,1fr); } }
@media (min-width:1280px) { .phgrid { grid-template-columns:repeat(6,1fr); } }
.phcell { position:relative; aspect-ratio:1; border-radius:var(--gp-r-img); overflow:hidden;
  cursor:pointer; background:var(--gp-fill); border:none; padding:0;
  opacity:0; animation:phfade .2s var(--gp-ease) forwards; }
@keyframes phfade { from { opacity:0; } to { opacity:1; } }
.phcell img { width:100%; height:100%; object-fit:cover; display:block; }
.phcell:hover { box-shadow:var(--gp-shadow-hover); }

/* ================= lightbox (2.7) ================= */
.lb-img { width:100%; border-radius:12px; }
.lb-meta { display:flex; justify-content:space-between; gap:10px; margin-top:10px;
  font-size:13px; color:var(--gp-secondary); }
[data-testid="stDialog"] .blizzard { max-width:760px; }
[data-testid="stDialog"] [data-testid="stMarkdown"] p { color:#e8eaed; }

/* ================= search hero (Phase 3) ================= */
.searchpill { position:relative; display:flex; align-items:center; gap:8px; background:var(--gp-fill);
  border-radius:999px; height:56px; padding:0 8px 0 18px; max-width:760px; margin:0 auto;
  transition:box-shadow .2s var(--gp-ease), background .2s var(--gp-ease), border .2s;
  border:2px solid transparent; }
.searchpill:focus-within { background:#fff; border-color:var(--gp-primary);
  box-shadow:0 2px 10px rgba(26,115,232,.18); }
.searchpill input { border:none !important; background:transparent !important; box-shadow:none !important;
  height:100% !important; font-size:16px; padding:0 !important; min-height:0; flex:1; }
.searchpill input::placeholder { color:var(--gp-disabled); }
.sugg-card { border:1px solid var(--gp-hairline); border-radius:var(--gp-r-card); background:#fff;
  box-shadow:var(--gp-shadow-rest); max-width:760px; margin:10px auto 0; padding:14px 16px; }
.sugg-head { font-size:12px; font-weight:600; letter-spacing:.06em; color:var(--gp-disabled);
  text-transform:uppercase; margin:12px 0 8px; }
.sugg-head:first-child { margin-top:0; }
.starter { display:flex; align-items:center; gap:10px; width:100%; text-align:left; border:none;
  background:none; cursor:pointer; padding:10px 8px; border-radius:10px; font-size:14.5px;
  color:var(--gp-text); font-family:inherit; }
.starter:hover { background:var(--gp-bg); }
.starter svg { flex:none; }

/* grouped results (3.3) */
.grp-head { display:flex; align-items:center; gap:10px; margin:22px 0 10px; }
.grp-head .t { font-size:16px; font-weight:500; }
.grp-head .c { font-size:12.5px; color:var(--gp-secondary); }
.place-card { display:flex; align-items:center; gap:12px; border:1px solid var(--gp-hairline);
  border-radius:14px; padding:10px 14px; cursor:pointer; background:#fff; box-shadow:var(--gp-shadow-rest);
  transition:box-shadow .2s var(--gp-ease); min-width:220px; }
.place-card:hover { box-shadow:var(--gp-shadow-hover); }
.place-card .pic { width:40px; height:40px; border-radius:50%; background:var(--gp-tonal);
  display:flex; align-items:center; justify-content:center; color:var(--gp-primary); flex:none; }
.place-card .pt { font-size:14.5px; font-weight:500; }
.place-card .pc { font-size:12.5px; color:var(--gp-secondary); }
.scene-strip [data-testid="stHorizontalBlock"] { display:flex; gap:10px; overflow-x:auto; padding-bottom:4px; }
.scene-strip [data-testid="stVerticalBlock"] { flex:0 0 auto; width:150px; }
.scene-card { border:1px solid var(--gp-hairline); border-radius:12px; overflow:hidden; background:#fff;
  cursor:pointer; box-shadow:var(--gp-shadow-rest); width:100%; padding:0; border:none;
  transition:box-shadow .2s var(--gp-ease); }
.scene-card:hover { box-shadow:var(--gp-shadow-hover); }
.scene-card img { width:100%; aspect-ratio:16/10; object-fit:cover; display:block; }
.scene-card .sc-t { font-size:12.5px; font-weight:500; padding:7px 9px 2px; color:var(--gp-text); }
.scene-card .sc-c { font-size:11.5px; color:var(--gp-secondary); padding:0 9px 8px; }

/* zero results router (3.4) */
.zero-card { border:1px solid var(--gp-hairline); border-radius:var(--gp-r-card); padding:28px 24px;
  text-align:center; background:#fff; box-shadow:var(--gp-shadow-rest); max-width:560px; margin:20px auto; }
.zero-card .zt { font-size:17px; font-weight:500; margin-bottom:6px; }
.zero-card .zs { font-size:13.5px; color:var(--gp-secondary); margin-bottom:16px; }

/* ================= guided conversation (Phase 4) ================= */
.conv { display:flex; flex-direction:column; gap:10px; }
.sysline { display:flex; gap:8px; align-items:flex-start; font-size:14px; color:var(--gp-secondary); }
.sysline svg { flex:none; margin-top:1px; }
.userbub { align-self:flex-end; background:#d3e3fd; color:#174ea6; border-radius:16px 16px 4px 16px;
  padding:9px 14px; font-size:14px; max-width:85%; }
.optrow { display:flex; align-items:center; justify-content:space-between; gap:8px; width:100%;
  border:none; background:var(--gp-fill); border-radius:12px; min-height:44px; padding:0 14px;
  font-size:14.5px; color:var(--gp-text); cursor:pointer; font-family:inherit; font-weight:400;
  transition:background .15s var(--gp-ease); }
.optrow:hover { background:#e4e7ea; }
.optrow .chev { color:var(--gp-disabled); flex:none; }
.dontknow { background:none; border:none; color:var(--gp-secondary); font-size:13px; cursor:pointer;
  padding:6px 10px; border-radius:999px; font-family:inherit; }
.dontknow:hover { background:var(--gp-fill); color:var(--gp-text); }

/* segmented control (this-or-that) */
.seg { display:flex; background:var(--gp-fill); border-radius:999px; padding:4px; gap:4px; }
.seg button { flex:1; border:none; background:transparent; border-radius:999px; min-height:38px;
  font-size:13.5px; font-weight:500; color:var(--gp-secondary); cursor:pointer; font-family:inherit;
  transition:all .15s var(--gp-ease); }
.seg button:hover { color:var(--gp-text); }
.seg button.sel { background:#fff; color:var(--gp-text); box-shadow:var(--gp-shadow-rest); }
.pair-imgs { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.pair-imgs img { width:100%; aspect-ratio:16/10; object-fit:cover; border-radius:16px; display:block; }

/* confidence strip (4.5) */
.confstrip { display:flex; align-items:center; gap:10px; font-size:13px; color:var(--gp-secondary);
  margin-bottom:10px; }
.confbar { flex:1; height:4px; background:var(--gp-fill); border-radius:2px; overflow:hidden; }
.confbar > div { height:100%; background:var(--gp-primary); border-radius:2px;
  transition:width .4s var(--gp-ease); }

/* moment cards (4.4) */
.moment { border:1px solid var(--gp-hairline); border-radius:var(--gp-r-card); overflow:hidden;
  background:#fff; box-shadow:var(--gp-shadow-rest); }
.moment .mcover { position:relative; aspect-ratio:16/9; background:#111; }
.moment .mcover img.main { width:100%; height:100%; object-fit:cover; display:block; }
.moment .mover { position:absolute; right:10px; bottom:-18px; display:flex; }
.moment .mover img { width:44px; height:44px; object-fit:cover; border-radius:8px; border:2px solid #fff;
  margin-left:-14px; box-shadow:var(--gp-shadow-rest); }
.moment .mbody { padding:12px 14px 12px; }
.moment .mlab { font-size:15px; font-weight:500; }
.moment .mcnt { font-size:12.5px; color:var(--gp-secondary); margin-left:8px; }
.moment .mwhy { font-size:12px; color:var(--gp-secondary); margin-top:6px; }
.moment .macts { display:flex; gap:8px; margin-top:10px; flex-wrap:wrap; }
.mthumbgrid { display:grid; grid-template-columns:repeat(4,1fr); gap:6px; margin-top:10px; }
@media (max-width:900px) { .moment .mover img { width:36px; height:36px; } .mthumbgrid { grid-template-columns:repeat(3,1fr); } }

/* cue chips (4.6) */
.cuechip { display:inline-flex; align-items:center; gap:7px; border-radius:999px; padding:6px 12px;
  font-size:13px; background:var(--gp-fill); border:1px solid transparent; }
.cuechip.neg { background:#fce8e6; color:#a50e0e; }
.cuechip .ct { color:var(--gp-disabled); font-size:11px; text-transform:uppercase; letter-spacing:.03em; }
.cuechip button { border:none; background:none; cursor:pointer; padding:2px 4px; font-size:12px;
  color:var(--gp-secondary); border-radius:6px; font-family:inherit; }
.cuechip button:hover { background:rgba(60,64,67,.1); }

/* success (4.7) */
.succ-img { width:100%; border-radius:16px; max-height:420px; object-fit:cover; }
.succ-meta { display:flex; align-items:center; gap:12px; margin:14px 0; flex-wrap:wrap; }
.succ-chip { background:var(--gp-tonal); color:var(--gp-primary); font-size:13px; font-weight:500;
  border-radius:999px; padding:6px 12px; }

/* people tab */
.st-key-peoplerow_grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(96px,1fr)); gap:14px; }
.st-key-peoplerow_grid .person-card .pimg { width:64px; height:64px; }

/* skeleton shimmer (6.1) */
.shimmer { border-radius:var(--gp-r-img); background:linear-gradient(100deg, #f1f3f4 40%, #e8eaed 50%, #f1f3f4 60%);
  background-size:200% 100%; animation:sh 1.2s infinite linear; aspect-ratio:1; }
@keyframes sh { to { background-position:-200% 0; } }
.shimmer-row { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:8px; }
@media (max-width:900px) { .shimmer-row { grid-template-columns:repeat(3,1fr); } }

/* view transition (6.2) */
.st-key-viewwrap { animation:vfade .18s var(--gp-ease); }
@keyframes vfade { from { opacity:.4; } to { opacity:1; } }

/* filter chip */
.fchip { background:var(--gp-tonal); color:var(--gp-primary); font-size:13.5px; font-weight:500;
  border-radius:999px; padding:6px 14px; display:inline-flex; align-items:center; gap:6px; }

/* misc */
.aibadge { display:inline-flex; align-items:center; gap:6px; background:var(--gp-tonal); color:#174ea6;
  font-size:12.5px; font-weight:500; border-radius:999px; padding:5px 12px; }
.aibadge.basic { background:var(--gp-fill); color:var(--gp-secondary); }
.said-line { font-size:13.5px; color:var(--gp-secondary); background:var(--gp-bg); border-radius:10px;
  padding:9px 12px; margin-bottom:10px; }
.stEmpty, [data-testid="stCaptionContainer"] { font-size:12.5px; color:var(--gp-disabled); }
"""
st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)


def esc(s):
    return html.escape(str(s if s is not None else ""))

# ---------------- assets ----------------
@st.cache_resource(show_spinner=False)
def load_bundle():
    meta = pd.read_parquet(DATA / "meta.parquet").reset_index(drop=True)
    emb = np.load(DATA / "image_emb.npy").astype("float32")
    emb_ids = json.loads((DATA / "emb_index.json").read_text())
    assert len(emb_ids) == len(meta), "embedding/meta mismatch"
    meta = meta[meta["img_id"].isin(set(emb_ids))].reset_index(drop=True)
    emb = emb[[emb_ids.index(i) for i in meta["img_id"]]].astype("float32")
    gaz = json.loads((DATA / "gazetteer.json").read_text())
    tasks = json.loads((DATA / "tasks.json").read_text())
    examples = json.loads((DATA / "examples.json").read_text())
    people = {}
    if (DATA / "people.json").exists():
        people = json.loads((DATA / "people.json").read_text())
    from sentence_transformers import SentenceTransformer
    clip = SentenceTransformer("clip-ViT-B-32")
    ret = Retriever(meta, emb, clip)
    return {"meta": meta, "emb": emb, "gaz": gaz, "tasks": tasks, "examples": examples,
            "clip": clip, "ret": ret, "people": people}


def _shimmer_loading():
    with st.container(key="viewwrap"):
        for r in range(3):
            st.markdown('<div class="shimmer-row">' + '<div class="shimmer"></div>' * 4 + '</div>',
                        unsafe_allow_html=True)
        st.markdown(f'<p style="text-align:center;color:#5f6368;font-size:13px">{pinwheel(18)}'
                    '&nbsp; Loading the demo library (first load only)…</p>', unsafe_allow_html=True)


if "BUNDLE" not in st.session_state:
    _shimmer_loading()
    try:
        st.session_state.BUNDLE = load_bundle()
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not load the demo library: {type(e).__name__}. Try reloading the page.")
        st.stop()
    st.rerun()
BUNDLE = st.session_state.BUNDLE

META = BUNDLE["meta"].set_index("img_id", drop=False)
LOG = Logger(LOGS / "events.jsonl")
N_PHOTOS = len(BUNDLE["meta"])
AI_ON = bool(live_status().get("available"))
PEOPLE = BUNDLE["people"]
PERSONS = PEOPLE.get("persons", [])
IMG2PERSON = PEOPLE.get("img2person", {})

for k in ("session_id", "live_session"):
    if k not in st.session_state:
        st.session_state[k] = str(uuid.uuid4()) if k == "session_id" else {"live_calls": 0}
st.session_state.setdefault("tab", "photos")


def log_event(mode, task_id, event, payload=None):
    LOG.log(st.session_state.session_id, st.session_state.get("participant", ""),
            mode, task_id, event, payload or {})


def img_path(img_id):
    row = META.loc[img_id]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return IMAGES / row["filename"]


def caption_of(img_id):
    row = META.loc[img_id]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    cap = row.get("caption")
    return cap if isinstance(cap, str) and cap else ""


def date_of(img_id):
    row = META.loc[img_id]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return pd.to_datetime(row["timestamp"]).strftime("%b %-d, %Y")


def sq(img_id):
    p = img_path(img_id)
    if p.exists():
        st.image(str(p), use_container_width=True)


def note_text():
    if AI_ON:
        return ("No uploads. In AI mode, your description is sent to Google's Gemini API "
                "to understand it (free tier). Don't enter personal information. "
                "Demo data only.")
    return ("No uploads. Your text is processed inside this demo and not sent to any "
            "external AI service. Demo data only.")


def person_label(pid):
    if pid == st.session_state.get("you_person"):
        return "You"
    return next((p["label"] for p in PERSONS if p["id"] == pid), pid)


def person_avatar(pid):
    p = next((x for x in PERSONS if x["id"] == pid), None)
    if not p:
        return None
    av = DATA / "faces" / p["avatar"]
    return str(av) if av.exists() else None

# ============================================================
# PART 2b: supplementary CSS
# ============================================================

CSS2 = """
/* ================= supplementary (assembled app) ================= */
.gp-count { font-size:13px; color:#80868b; font-weight:400; }
.year-head { display:flex; align-items:baseline; gap:10px; margin:24px 0 10px; }
.year-head .y { font-size:19px; font-weight:500; color:var(--gp-text); }
.year-head .c { font-size:12.5px; color:var(--gp-secondary); }
.year-head .rule { flex:1; height:1px; background:var(--gp-hairline); align-self:center; }

/* photo grids */
.gpgrid [data-testid="stHorizontalBlock"] { display:flex; flex-wrap:wrap; gap:6px; }
.gpgrid [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { flex:0 0 32.4% !important;
  max-width:32.4% !important; margin:0; }
@media (min-width:701px) {
  .gpgrid [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { flex:0 0 24.6% !important;
    max-width:24.6% !important; }
}
@media (min-width:901px) {
  .gpgrid [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { flex:0 0 19.2% !important;
    max-width:19.2% !important; }
}
.gpgrid div[data-testid="stImage"] { padding:0; margin:0; }
.gpgrid img { border-radius:8px; aspect-ratio:1/1; object-fit:cover; width:100%; display:block;
  box-shadow:none; transition:filter .15s var(--gp-ease); }
.gpgrid img:hover { filter:brightness(1.05); }

/* memories carousel row (flex container) */
.st-key-memrow [data-testid="stHorizontalBlock"] { display:flex; gap:12px; overflow-x:auto;
  padding-bottom:8px; scroll-snap-type:x proximity; }
.st-key-memrow [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { flex:0 0 280px;
  scroll-snap-align:start; }
@media (max-width:900px) { .st-key-memrow [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { flex:0 0 236px; } }

/* people row */
.st-key-peoplerow [data-testid="stHorizontalBlock"] { display:flex; gap:8px; overflow-x:auto; padding-bottom:8px; }
.st-key-peoplerow [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { flex:0 0 auto; min-width:86px; }
.st-key-peoplerow_grid { margin:6px 0 18px; }
.st-key-peoplerow_grid [data-testid="stHorizontalBlock"] { flex-wrap:wrap; overflow:visible; }
.st-key-peoplerow_grid [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { flex:0 0 24.5%; max-width:24.5%; }
@media (min-width:701px) { .st-key-peoplerow_grid [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { flex:0 0 19.5%; max-width:19.5%; } }
@media (min-width:1100px) { .st-key-peoplerow_grid [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { flex:0 0 15.8%; max-width:15.8%; } }

/* section heads */
.gp-section-head { font-size:21px; font-weight:500; color:var(--gp-text); margin:26px 0 12px; letter-spacing:-0.01em; }

/* gemini heads + guides */
.gemini-head { display:flex; align-items:center; gap:10px; margin:2px 0 4px; }
.gemini-head .gt { font-size:19px; font-weight:500; color:var(--gp-text); letter-spacing:-0.01em; }
.gemini-head .gt-sub { font-size:13px; color:var(--gp-secondary); }
.gline { font-size:12.5px; color:var(--gp-disabled); margin-bottom:14px; }

/* cards */
.card-title { font-size:16px; font-weight:500; margin-bottom:2px; color:var(--gp-text); }
.card-sub { color:var(--gp-secondary); font-size:13px; margin-bottom:10px; }

/* guided pieces */
.q-text { font-size:16px; font-weight:500; margin-bottom:12px; }
.said-line { font-size:13.5px; color:var(--gp-secondary); background:var(--gp-bg); border-radius:10px;
  padding:9px 12px; margin-bottom:10px; }
.faceopt { display:flex; align-items:center; gap:9px; margin:2px 0 8px; font-size:14px; font-weight:500; }
.faceopt .faceimg { display:inline-flex; }
.cuechip .cstate { font-size:11px; color:var(--gp-disabled); margin-left:2px; }
.fb-q { font-size:14.5px; font-weight:500; margin-top:16px; }
.confstrip { margin:4px 0 14px; }

/* guided split (Phase 4.1) */
.st-key-gsplit [data-testid="stHorizontalBlock"] { align-items:flex-start; }
@media (max-width:900px) {
  .st-key-gsplit > [data-testid="stHorizontalBlock"] { flex-direction:column !important; }
  .st-key-gsplit > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] { width:100% !important; flex:0 0 auto !important; }
}
@media (min-width:901px) {
  .st-key-gsplit > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"]:first-child { max-width:100%; }
}

/* proactive still-searching card */
.proac { display:flex; align-items:center; gap:10px; background:var(--gp-tonal); border-radius:12px;
  padding:12px 14px; margin:14px 0 4px; }
.proac .pa-t { font-size:14px; font-weight:500; color:#174ea6; }
.proac .pa-s { font-size:12.5px; color:var(--gp-secondary); }

/* onboarding */
.onb-head { display:flex; align-items:center; gap:9px; font-size:16px; font-weight:500; color:var(--gp-text); }
.onb-lab { font-size:12.5px; color:var(--gp-secondary); text-align:center; margin-top:6px; }

/* pair images radius */
[class*="st-key-paircard_"] [data-testid="stImage"] img { border-radius:16px; }

/* success screen */
.succ-chip { background:var(--gp-tonal); color:var(--gp-primary); font-size:13px; font-weight:500;
  border-radius:999px; padding:6px 12px; }
.st-key-succcard [data-testid="stImage"] { margin-bottom:4px; }
.st-key-succcard [data-testid="stImage"] img { border-radius:16px; }

/* test mode */
.task-frag { background:var(--gp-bg); border:1px solid var(--gp-hairline); border-radius:12px;
  padding:14px 16px; font-size:15px; line-height:1.55; color:var(--gp-text); margin:10px 0; }
.task-meta { display:flex; gap:8px; margin-bottom:8px; flex-wrap:wrap; }
.tag { font-size:11.5px; font-weight:600; border-radius:999px; padding:3px 11px; }
.tag.blue { background:#e8f0fe; color:#1a73e8; }
.tag.gray { background:#f1f3f4; color:#5f6368; }
.tag.green { background:#e6f4ea; color:#188038; }
.about-p { font-size:14px; color:#3c4043; line-height:1.55; margin:10px 0; max-width:760px; }
.footer-note { font-size:12px; color:var(--gp-disabled); margin-top:28px; }
.dlg-cap { font-size:12.5px; color:var(--gp-disabled); margin-bottom:8px; }
.stSelectbox [data-baseweb="select"] > div { border-radius:10px; font-size:14px; }
.stTextInput input { border-radius:12px; }
.stTextArea textarea { border-radius:14px; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color:var(--gp-primary); box-shadow:0 0 0 3px #e8f0fe; }
[data-baseweb="modal"] .modal-container { border-radius:18px; }
"""
st.markdown("<style>" + CSS2 + "</style>", unsafe_allow_html=True)

# ============================================================
# PART 3: derived views + app chrome
# ============================================================

# ---------------- derived views (real-data tags + memories) ----------------
EVENT_TITLES = {
    "e01": "Orientation week", "e02": "Hostel life & fests", "e03": "Diwali at home",
    "e04": "A trip to Goa", "e05": "Exam season", "e06": "A trip to Hampi",
    "e07": "Sick week", "e08": "A trip to Pondicherry", "e09": "Internship in Bengaluru",
    "e10": "A trip to Gokarna", "e11": "Fest night", "e12": "Ganesh Chaturthi at home",
    "e13": "Everyday & utility",
}
EVENT_DATES = {
    "e01": "Aug 2022", "e02": "Sep–Nov 2022", "e03": "Oct 2022", "e04": "Jan 2023",
    "e05": "Apr–May 2023", "e06": "Sep 2023", "e07": "Nov 2023", "e08": "Feb 2024",
    "e09": "May–Jul 2024", "e10": "Jan 2025", "e11": "Mar 2025", "e12": "Aug 2025",
}

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def _build_tag_panel():
    m = META
    out = {"people": [], "places": [], "things": [], "years": []}
    for p in PERSONS:
        ids = [i for i, pi in IMG2PERSON.items() if pi == p["id"]]
        if ids:
            out["people"].append((person_label(p["id"]), p["id"]))
    place_counts = m["place_name"].value_counts()
    for name, cnt in place_counts.head(7).items():
        if name in ("mixed",):
            continue
        out["places"].append((str(name), int(cnt)))
    cap = m["caption"].fillna("").str.lower()
    obj = m["objects"].fillna("[]")
    text = (cap + " " + obj.str.replace('"', "", regex=False)).str.lower()
    things = [
        ("coffee", r"\bcoffee\b|latte|espresso"), ("food", r"\bfood\b|dinner|lunch|plate|curry|biryani"),
        ("tea", r"\btea\b|chai"), ("people", r"\bpeople\b|friends|group"),
        ("boat", r"\bboat\b|sailboat|coracle"), ("friends", r"\bfriends?\b"),
        ("beach", r"\bbeach\b|shore|coast"), ("temple", r"\btemple\b"),
        ("notes", r"\bnotes\b|whiteboard|writing"), ("flowers", r"\bflowers?\b|rangoli|garland"),
    ]
    for label, pat in things:
        n = int(text.str.contains(pat, regex=True).sum())
        if n >= 8:
            out["things"].append((label, n))
    out["things"] = sorted(out["things"], key=lambda x: -x[1])[:10]
    yrs = pd.to_datetime(m["timestamp"]).dt.year.value_counts()
    out["years"] = [(str(y), int(c)) for y, c in yrs.items()]
    return out


def _hero_image(sub):
    ts = pd.to_datetime(sub["timestamp"])
    sub = sub.assign(_t=ts)
    mid = ts.min() + (ts.max() - ts.min()) / 2
    sub = sub.assign(_d=(sub["_t"] - mid).abs())
    return sub.sort_values("_d").iloc[0]["img_id"]


def _build_memories():
    m = META.copy()
    you = st.session_state.get("you_person")
    cands = []
    ev_counts = m["event_id"].value_counts()
    for eid in ev_counts.index:
        if eid == "e13" or eid not in EVENT_TITLES:
            continue
        sub = m[m["event_id"] == eid]
        hero = _hero_image(sub)
        cands.append({"kind": "event", "val": eid,
                      "title": EVENT_TITLES[eid],
                      "sub": EVENT_DATES.get(eid, ""),
                      "img": hero, "rank": len(sub), "count": len(sub)})
    if PERSONS:
        for p in PERSONS:
            ids = [i for i, pi in IMG2PERSON.items() if pi == p["id"]]
            if len(ids) < 15:
                continue
            sub = m[m["img_id"].isin(ids)]
            cands.append({"kind": "person", "val": p["id"],
                          "title": f"With {person_label(p['id'])}",
                          "sub": "", "img": _hero_image(sub), "rank": len(ids),
                          "count": len(ids)})
    cap = m["caption"].fillna("").str.lower()
    themes = [
        ("sunset", r"sunset|suns et|golden hour", "Sunset moments"),
        ("coffee", r"cafe|coffee|latte|chai|tea cup", "Coffee & café mornings"),
        ("food", r"food|dinner|plate|sweets|curry|biryani", "Food & feast days"),
        ("docs", r"receipt|document|ticket|notebook|whiteboard|paper", "Documents & receipts"),
        ("move", r"bicycle|bike|scooter|bus|train|traffic|road", "On the move"),
        ("rain", r"rain|monsoon|wet|drizzle", "Rainy days"),
        ("night", r"night|neon|lights|moonlit", "Nights out"),
    ]
    for key, pat, title in themes:
        mask = cap.str.contains(pat, regex=True, na=False)
        if mask.sum() >= 25:
            sub = m[mask]
            cands.append({"kind": "theme", "val": key, "title": title,
                          "sub": "", "img": _hero_image(sub), "rank": int(mask.sum()),
                          "count": int(mask.sum()), "pat": pat})
    if you and IMG2PERSON:
        ids = [i for i, pi in IMG2PERSON.items() if pi == you]
        if len(ids) >= 15:
            sub = m[m["img_id"].isin(ids)]
            cands.append({"kind": "person_you", "val": you, "title": "Photos of you",
                          "sub": "", "img": _hero_image(sub), "rank": len(ids),
                          "count": len(ids)})
    cands.sort(key=lambda c: -c["rank"])
    return cands[:8]


def _memory_sub(c):
    m = META
    if c["kind"] == "event":
        return m[m["event_id"] == c["val"]]
    if c["kind"] in ("person", "person_you"):
        ids = [i for i, pi in IMG2PERSON.items() if pi == c["val"]]
        return m[m["img_id"].isin(ids)]
    cap = m["caption"].fillna("").str.lower()
    return m[cap.str.contains(c.get("pat", r"$^"), regex=True, na=False)]


def _apply_filter(c):
    if c["kind"] == "event":
        st.session_state["mem_filter"] = {"kind": "event", "val": c["val"],
                                          "title": c["title"]}
    elif c["kind"] in ("person", "person_you"):
        st.session_state["person_filter"] = {"kind": "person", "val": c["val"],
                                             "title": f"{c['title']} · {c['count']} photos"}
    elif c["kind"] == "theme":
        st.session_state["mem_filter"] = {"kind": "theme", "val": c["val"],
                                          "title": c["title"], "pat": c.get("pat")}
    else:
        st.session_state["mem_filter"] = {"kind": c["kind"], "val": c["val"],
                                          "title": c["title"]}
    st.session_state["tab"] = "photos"
    st.rerun()


# ---------------- app chrome (Phase 1) ----------------
def _nav(t):
    st.session_state["nav_req"] = t


def svg_uri(name, s=24, c="#5f6368"):
    from urllib.parse import quote
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
           f'width="{s}" height="{s}" fill="{c}"><path d="{ICONS[name]}"/></svg>')
    return "data:image/svg+xml;utf8," + quote(svg, safe="")


def icon_button(label, icon_name, key, on_click=None, c="#5f6368", s=22,
                title=None):
    with st.container(key=f"ibc_{key}"):
        if on_click is not None:
            pressed = st.button(label, key=key, type="tertiary", on_click=on_click)
        else:
            pressed = st.button(label, key=key, type="tertiary")
    st.markdown(f'<style>'
                f'.st-key-ibc_{key} {{ padding:0; margin:0; }}'
                f'.st-key-ibc_{key} > [data-testid="stVerticalBlock"] {{ padding:0; margin:0; }}'
                f'.st-key-ibc_{key} .stButton {{ margin:0; padding:0; }}'
                f'.st-key-ibc_{key} .stButton > button '
                f'{{ width:{s + 18}px;height:{s + 18}px;min-height:{s + 18}px;padding:0;'
                f'border-radius:50%;background:transparent;box-shadow:none;font-size:0;'
                f'display:inline-flex;align-items:center;justify-content:center; }}'
                f'.st-key-ibc_{key} .stButton > button:hover '
                f'{{ background:rgba(60,64,67,.08); }}'
                f'.st-key-ibc_{key} .stButton > button::before '
                f'{{ content:"";width:{s}px;height:{s}px;display:block;'
                f'background:url("{svg_uri(icon_name, s, c)}") center/contain no-repeat; }}'
                f'</style>', unsafe_allow_html=True)
    return pressed


def spark_button(key, on_click, s=22):
    gid = "spkbtn_" + key
    with st.container(key=f"spkc_{key}"):
        st.button("Ask Gemini", key=key, type="tertiary", on_click=on_click)
    st.markdown(f'<style>'
                f'.st-key-spkc_{key} {{ padding:0; margin:0; }}'
                f'.st-key-spkc_{key} > [data-testid="stVerticalBlock"] {{ padding:0; margin:0; }}'
                f'.st-key-spkc_{key} .stButton {{ margin:0; padding:0; }}'
                f'.st-key-spkc_{key} .stButton > button {{'
                f'width:{s + 14}px;height:{s + 14}px;min-height:{s + 14}px;padding:0;border-radius:50%;'
                f'background:transparent;box-shadow:none;font-size:0;display:inline-flex;'
                f'align-items:center;justify-content:center;}}'
                f'.st-key-spkc_{key} .stButton > button:hover {{'
                f'background:#e8f0fe;}}'
                f'.st-key-spkc_{key} .stButton > button::before {{'
                f'content:"";width:{s}px;height:{s}px;display:block;'
                f'background:url("{svg_uri_sparkle(gid, s)}") center/contain no-repeat;}}'
                f'</style>', unsafe_allow_html=True)


def svg_uri_sparkle(gid, s=24):
    from urllib.parse import quote
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{s}" height="{s}">{SPARKLE.format(gid=gid)}</svg>'
    return "data:image/svg+xml;utf8," + quote(svg, safe="")


def desktop_bar():
    with st.container(key="gpbar"):
        c = st.columns([1.5, 4.9, 0.6], vertical_alignment="center", gap="medium")
        with c[0]:
            i0, i1 = st.columns([0.5, 1.1], vertical_alignment="center", gap="small")
            with i0:
                st.markdown(f'<span class="gpb-word">{pinwheel(27)}</span>',
                            unsafe_allow_html=True)
            with i1:
                with st.container(key="pbword"):
                    st.button("Photos", key="nav_d_home", type="tertiary",
                              on_click=lambda: _nav("photos"))
                st.markdown('<style>'
                            '.st-key-pbword { padding:0; margin:0; }'
                            '.st-key-pbword .stButton { margin:0; padding:0; }'
                            '.st-key-pbword .stButton > button {'
                            'font-size:22px !important;font-weight:500 !important;'
                            'color:#202124 !important;padding:2px 12px;min-height:44px;}'
                            '</style>', unsafe_allow_html=True)
        with c[1]:
            with st.container(key="gpbpill"):
                i_a, i_b, i_c = st.columns([6, 0.5, 0.5], vertical_alignment="center",
                                           gap="small")
                with i_a:
                    st.text_input("Search Google Photos", key="pill_q",
                                  label_visibility="collapsed", on_change=_pill_submitted)
                with i_b:
                    icon_button("Voice search", "mic", "mic_pill", on_click=_mic_pill,
                                c="#5f6368")
                with i_c:
                    spark_button("spark_pill", _spark_go)
            st.markdown('<style>'
                        '.st-key-gpbpill > [data-testid="stHorizontalBlock"] {'
                        ' gap:2px; align-items:center; }'
                        '.st-key-gpbpill [data-testid="stVerticalBlock"] { padding:0; margin:0; }'
                        '.st-key-gpbpill [data-testid="stMarkdownContainer"] { padding:0; margin:0; }'
                        '.st-key-gpbpill .stTextInput [data-testid="stTextInput"] { padding:0; }'
                        '</style>', unsafe_allow_html=True)
        with c[2]:
            with st.popover('<span class="gavatar">D</span>'):
                st.caption("Demo user")
                if st.button("How this works", key="menu_how"):
                    st.session_state["tab"] = "settings"
                    st.session_state["settings_sec"] = "how"
                    st.rerun()
                if st.button("About this demo", key="menu_about"):
                    st.session_state["tab"] = "settings"
                    st.session_state["settings_sec"] = "about"
                    st.rerun()
                if st.button("Reset", key="menu_reset", type="secondary"):
                    _reset_all()


def _pill_submitted():
    q = (st.session_state.get("pill_q") or "").strip()
    if q:
        st.session_state["classic_q_free"] = q
        st.session_state["search_q"] = q
        st.session_state["tab"] = "search"
        _classic_go("free_classic", "classic_q_free")


def _mic_pill():
    st.session_state["mic_req"] = True
    st.session_state["mic_target"] = "pill"


def _spark_go():
    q = (st.session_state.get("pill_q") or "").strip()
    st.session_state["guided_prefill"] = q
    st.session_state["guided_autostart"] = True
    st.session_state["tab"] = "guided"


def mobile_top():
    with st.container(key="mtop"):
        c = st.columns([1.6, 0.2, 0.2], vertical_alignment="center", gap="small")
        with c[0]:
            st.markdown(f'<span class="mtop-word"><span class="gpb-word">' + pinwheel(24) +
                        '<span style="font-size:19px;font-weight:500;margin-left:4px">Photos</span>'
                        '</span></span>', unsafe_allow_html=True)
        with c[1]:
            icon_button("Search photos", "search", "mtop_search",
                        on_click=lambda: _nav("search"))
        with c[2]:
            icon_button("Settings", "settings", "mtop_gear",
                        on_click=lambda: _nav("settings"))
        st.markdown('<style>'
                    '.st-key-mtop [data-testid="stVerticalBlock"] { padding:0; margin:0; }'
                    '</style>', unsafe_allow_html=True)


def bottom_nav():
    cur = st.session_state.get("tab", "photos")
    items = [
        ("photos", "Photos", "photo", None),
        ("search", "Search", "search", None),
        ("guided", "Gemini", None, "spark"),
        ("people", "People", "person", None),
        ("settings", "Settings", "settings", None),
    ]
    with st.container(key="mnav"):
        cols = st.columns(5, gap="small")
        for col, (t, label, ic, kind) in zip(cols, items):
            with col:
                if t == cur:
                    svg = sparkle(24, f"spknav_{t}") if kind == "spark" else icon(ic, 24, "#1a73e8")
                    st.markdown(f'<div class="mnavmark"></div><div class="mnavitem active">'
                                f'<span class="nico">{svg}</span><span>{label}</span></div>',
                                unsafe_allow_html=True)
                else:
                    if kind == "spark":
                        spark_button(f"nav_m_{t}", on_click=lambda tt=t: _nav(tt))
                    else:
                        icon_button(label, ic, f"nav_m_{t}", on_click=lambda tt=t: _nav(tt))
    st.markdown('<style>'
                '[data-testid="stHorizontalBlock"]:has(.mnavmark) .stButton > button {'
                'width:100%;border:none;background:transparent;box-shadow:none;'
                'display:flex;flex-direction:column;align-items:center;gap:2px;'
                'font-size:11px;font-weight:500;color:#5f6368;min-height:52px;padding:2px 0;}'
                '[data-testid="stHorizontalBlock"]:has(.mnavmark) .stButton > button::before {'
                'width:24px;height:24px;display:block;margin-bottom:0;}'
                '[data-testid="stHorizontalBlock"]:has(.mnavmark) .stButton > button:hover {color:#1a73e8;}'
                '</style>', unsafe_allow_html=True)

# ============================================================
# PART 4: photos home, lightbox, people, settings
# ============================================================

# ---------------- lightbox (2.7) ----------------
def _open_lightbox(ids, idx):
    st.session_state["lightbox"] = {"ids": list(ids), "idx": int(idx)}
    st.rerun()


def _lightbox_render():
    lb = st.session_state.get("lightbox")
    if not lb:
        return
    ids, idx = lb["ids"], lb["idx"]
    img_id = ids[idx]
    p = img_path(img_id)
    if not p.exists():
        st.session_state.pop("lightbox", None)
        st.rerun()
        return
    b64 = base64.b64encode(p.read_bytes()).decode()
    cap = esc(caption_of(img_id) or "")
    dt = esc(date_of(img_id))
    st.markdown(f'''<div class="lb-overlay">
  <div class="lb-top"><span class="lb-cap">{cap}</span><span class="lb-date">{dt}</span></div>
  <img class="lb-img" src="data:image/jpeg;base64,{b64}" alt="photo">
</div>''', unsafe_allow_html=True)
    with st.container(key="lbcontrols"):
        c = st.columns([1.1, 1.1, 1, 2.2, 1.1], vertical_alignment="center", gap="small")
        with c[0]:
            if st.button("Previous", key="lb_prev", disabled=idx <= 0):
                lb["idx"] = idx - 1
                st.rerun()
        with c[1]:
            if st.button("Next", key="lb_next", disabled=idx >= len(ids) - 1):
                lb["idx"] = idx + 1
                st.rerun()
        with c[2]:
            if st.button("Close", key="lb_close"):
                st.session_state.pop("lightbox", None)
                st.rerun()
        with c[3]:
            if st.button("This is it ✔", key="lb_confirm", type="primary"):
                log_event("free", "free", "confirm_attempt", {"img_id": img_id, "correct": None})
                st.session_state.pop("lightbox", None)
                st.toast("Noted — nice find.")
                st.rerun()
        with c[4]:
            if st.button("Share", key="lb_share"):
                st.toast("Share link copied (demo).")
    st.markdown('<style>'
                '.lb-overlay { position:fixed; inset:0; background:rgba(16,16,18,.94); z-index:2000; '
                'display:flex; align-items:center; justify-content:center; }'
                '.lb-img { max-width:92vw; max-height:76vh; object-fit:contain; border-radius:8px; '
                'box-shadow:0 12px 40px rgba(0,0,0,.6); }'
                '.lb-top { position:absolute; top:18px; left:0; right:0; display:flex; gap:10px; '
                'justify-content:center; align-items:baseline; padding:0 24px; }'
                '.lb-cap { color:#fff; font-size:13.5px; text-align:center; }'
                '.lb-date { color:rgba(255,255,255,.6); font-size:12.5px; white-space:nowrap; }'
                '.st-key-lbcontrols { position:fixed; bottom:22px; left:50%; transform:translateX(-50%); '
                'z-index:2001; display:flex; gap:6px; background:rgba(28,28,30,.82); '
                'border:1px solid rgba(255,255,255,.12); border-radius:999px; padding:6px 10px; '
                'max-width:94vw; backdrop-filter:blur(8px); }'
                '.st-key-lbcontrols [data-testid="stHorizontalBlock"] { gap:4px; }'
                '.st-key-lbcontrols .stButton > button { background:transparent; color:#fff; '
                'border:1px solid rgba(255,255,255,.18); border-radius:999px; padding:8px 14px; '
                'min-height:36px; font-size:13.5px; }'
                '.st-key-lbcontrols .stButton > button:hover { background:rgba(255,255,255,.12); }'
                '.st-key-lbcontrols .stButton > button[kind="primary"] { background:var(--gp-primary); '
                'border-color:transparent; }'
                '.st-key-lbcontrols .stButton > button:disabled { color:rgba(255,255,255,.35); }'
                '</style>', unsafe_allow_html=True)

CELL_CSS = """
/* photo grid cells (keyed containers) */
[class*="st-key-mgrid_"] { padding:0; margin:0; }
[class*="st-key-cell_"] { position:relative; aspect-ratio:1; border-radius:8px;
  overflow:hidden; background:var(--gp-fill); padding:0; margin:0; }
[class*="st-key-cell_"] > [data-testid="stVerticalBlock"] { padding:0; margin:0; }
[class*="st-key-cell_"] [data-testid="stImage"] { position:absolute; inset:0; width:100%; height:100%; margin:0; }
[class*="st-key-cell_"] [data-testid="stImage"] img { width:100%; height:100%;
  object-fit:cover; border-radius:8px; transition:filter .15s var(--gp-ease); }
[class*="st-key-cell_"] [data-testid="stImage"]:hover img { filter:brightness(1.05); }
[class*="st-key-cell_"] .stButton { position:absolute; inset:0; margin:0; z-index:4; }
[class*="st-key-cell_"] .stButton > button { opacity:0; border:none; }
"""
st.markdown("<style>" + CELL_CSS + "</style>", unsafe_allow_html=True)


def _photo_cell(img_id, key_prefix, lightbox_ids, lightbox_idx):
    with st.container(key=f"cell_{key_prefix}"):
        p = img_path(img_id)
        if p.exists():
            st.image(str(p), use_container_width=True)
        st.button(f"Open photo from {date_of(img_id)}", key=f"lbopen_{key_prefix}",
                  use_container_width=True,
                  on_click=lambda: _open_lightbox(lightbox_ids, lightbox_idx))


def _photo_grid_rows(ids, key_prefix, limit=None):
    shown = ids if limit is None else ids[:limit]
    ncols = 6
    if not shown:
        return
    with st.container(key=f"mgrid_{key_prefix}"):
        cols = st.columns(ncols, gap="small")
        for i, iid in enumerate(shown):
            with cols[i % ncols]:
                _photo_cell(iid, f"{key_prefix}_{iid}", ids, i)


def _month_block(sub, key_prefix):
    m = sub.copy()
    m["ts"] = pd.to_datetime(m["timestamp"])
    for ym, g in m.groupby(m["ts"].dt.to_period("M"), sort=True):
        ids = g["img_id"].tolist()
        st.markdown(f'<div class="month-head"><span class="m">{ym}</span>'
                    f'<span class="c">{len(ids)} photos</span><span class="rule"></span></div>',
                    unsafe_allow_html=True)
        key = f"{key_prefix}_m{str(ym).replace('-', '')}"
        if st.session_state.get(f"month_open_{key}"):
            _photo_grid_rows(ids, key)
        else:
            _photo_grid_rows(ids, key, limit=12)
            if len(ids) > 12:
                if st.button(f"Show all {len(ids)}", key=f"month_all_{key}", type="tertiary"):
                    st.session_state[f"month_open_{key}"] = True


def _dismiss_demo():
    st.session_state["demo_card_dismissed"] = True


# ---------------- onboarding (2.5) ----------------
def _onboarding_card(key_prefix="home"):
    with st.container(border=True, key=f"onbcard_{key_prefix}"):
        st.markdown(f'<div class="onb-head">{sparkle(18, "spkonb")}<span>Which one is you?</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="card-sub">Pick yourself and we will recognise your photos. '
                    'Skip if you like.</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(PERSONS), 4), gap="medium")
        for c, p in zip(cols, PERSONS[:4]):
            with c:
                av = person_avatar(p["id"])
                if av:
                    st.image(av, width=72)
                st.markdown(f'<div class="onb-lab">{esc(p["label"])}</div>', unsafe_allow_html=True)
                if st.button("This is me", key=f"you_pick_{key_prefix}_{p['id']}",
                             type="primary", use_container_width=True):
                    st.session_state["you_person"] = p["id"]
                    st.rerun()
        st.markdown(f'<style>'
                    f'.st-key-onbcard_{key_prefix} [data-testid="stImage"] img {{ border-radius:50%; }}'
                    f'.st-key-onbcard_{key_prefix} [data-testid="stImage"] {{ margin:0 auto; }}'
                    '</style>', unsafe_allow_html=True)
    if st.button("Not sure", key=f"you_skip_{key_prefix}", type="tertiary"):
        st.session_state["you_skipped"] = True
        st.rerun()


# ---------------- Photos home (Phase 2) ----------------
def _memory_card(m, i):
    p = img_path(m["img"])
    sub = f"{m['sub']} · {m['count']} photos" if m["sub"] else f"{m['count']} photos"
    with st.container(key=f"memcard_{i}"):
        if p.exists():
            st.image(str(p), use_container_width=True)
        st.markdown(f'<div class="memover"><span class="mchip">Memory</span>'
                    f'<span class="mtitle">{esc(m["title"])}</span>'
                    f'<span class="mdate">{esc(sub)}</span></div>', unsafe_allow_html=True)
        st.button(m["title"], key=f"mem_{m['kind']}_{m['val']}", use_container_width=True)
        st.markdown(f'<style>'
                    f'.st-key-memcard_{i} {{ position:relative; aspect-ratio:16/9; '
                    f'border-radius:16px; overflow:hidden; background:#111; padding:0; margin:0; }}'
                    f'.st-key-memcard_{i} > [data-testid="stVerticalBlock"] {{ padding:0; margin:0; }}'
                    f'.st-key-memcard_{i} [data-testid="stImage"] {{ position:absolute; inset:0; width:100%; height:100%; margin:0; }}'
                    f'.st-key-memcard_{i} [data-testid="stImage"] img {{ width:100%; height:100%; object-fit:cover; }}'
                    f'.st-key-memcard_{i} .memover {{ position:absolute; inset:0; pointer-events:none; z-index:3; '
                    f'display:flex; flex-direction:column; justify-content:flex-end; padding:12px 14px; background:linear-gradient(180deg,rgba(0,0,0,0) 45%,rgba(0,0,0,.55) 100%); }}'
                    f'.st-key-memcard_{i} .mchip {{ position:absolute; top:10px; left:10px; background:rgba(0,0,0,.55); '
                    f'color:#fff; font-size:11px; font-weight:500; border-radius:999px; padding:3px 9px; }}'
                    f'.st-key-memcard_{i} .mtitle {{ color:#fff; font-size:15.5px; font-weight:500; line-height:1.25; }}'
                    f'.st-key-memcard_{i} .mdate {{ color:rgba(255,255,255,.78); font-size:12px; margin-top:2px; }}'
                    f'.st-key-memcard_{i} .stButton {{ position:absolute; inset:0; margin:0; z-index:4; }}'
                    f'.st-key-memcard_{i} .stButton > button {{ opacity:0; border:none; }}'
                    f'</style>', unsafe_allow_html=True)


def _person_card(p, i, prefix="home"):
    you = p["id"] == st.session_state.get("you_person")
    lab = "You" if you else p["label"]
    with st.container(key=f"pcard_{prefix}_{p['id']}"):
        av = person_avatar(p["id"])
        if av:
            st.image(av, width=64)
        st.markdown(f'<div class="pc-name">{esc(lab)}</div><div class="pc-cnt">{p["count"]} photos</div>', unsafe_allow_html=True)
        if st.button(lab, key=f"pbtn_{prefix}_{p['id']}", use_container_width=True):
            st.session_state["person_filter"] = {"kind": "person", "val": p["id"],
                                                 "title": f"{lab} · {p['count']} photos"}
            st.session_state["tab"] = "photos"
            st.rerun()
        st.markdown(f'<style>'
                    f'.st-key-pcard_{prefix}_{p["id"]} {{ position:relative; padding:0; margin:0; }}'
                    f'.st-key-pcard_{prefix}_{p["id"]} > [data-testid="stVerticalBlock"] {{ padding:0; margin:0; }}'
                    f'.st-key-pcard_{prefix}_{p["id"]} [data-testid="stImage"] {{ margin:0 auto; }}'
                    f'.st-key-pcard_{prefix}_{p["id"]} [data-testid="stImage"] img {{ border-radius:50%; '
                    f'object-fit:cover; box-shadow:0 0 0 2px #fff, var(--gp-shadow-rest); }}'
                    f'.st-key-pcard_{prefix}_{p["id"]} .pc-name {{ font-size:13.5px; font-weight:500; text-align:center; margin-top:6px; }}'
                    f'.st-key-pcard_{prefix}_{p["id"]} .pc-cnt {{ font-size:12px; color:var(--gp-secondary); text-align:center; }}'
                    f'.st-key-pcard_{prefix}_{p["id"]} .stButton {{ position:absolute; inset:-4px; margin:0; z-index:5; }}'
                    f'.st-key-pcard_{prefix}_{p["id"]} .stButton > button {{ opacity:0; border:none; background:transparent; '
                    f'border-radius:16px; }}'
                    f'.st-key-pcard_{prefix}_{p["id"]}:hover {{ box-shadow:var(--gp-shadow-hover); border-radius:16px; }}'
                    f'</style>', unsafe_allow_html=True)


def photos_tab():
    flt = st.session_state.get("mem_filter") or st.session_state.get("person_filter")
    with st.container(key="viewwrap"):
        if flt:
            f1, f2 = st.columns([4.5, 1], vertical_alignment="center", gap="small")
            with f1:
                st.markdown(f'<span class="fchip">{esc(flt["title"])}</span>', unsafe_allow_html=True)
            with f2:
                if st.button("✕", key="filter_clear", type="tertiary"):
                    for k in ("mem_filter", "person_filter"):
                        st.session_state.pop(k, None)
                    st.rerun()
        else:
            if not st.session_state.get("demo_card_dismissed"):
                d1, d2 = st.columns([8, 1], vertical_alignment="center", gap="small")
                with d1:
                    st.markdown('<div class="democ" style="margin-bottom:0"><span class="demo-chip">DEMO</span>'
                                '<span class="t">A Google Photos demo — every photo, date, place and '
                                'person is synthetic or freely licensed.</span></div>',
                                unsafe_allow_html=True)
                with d2:
                    icon_button("Dismiss demo note", "close", "demo_dismiss", on_click=_dismiss_demo,
                                c="#80868b", s=18)
            mems = _build_memories()
            if mems:
                st.markdown('<div class="gp-section-head">Memories</div>', unsafe_allow_html=True)
                with st.container(key="memrow"):
                    cols = st.columns(len(mems), gap="small")
                    for c, m, i in zip(cols, mems, range(len(mems))):
                        with c:
                            _memory_card(m, i)
            if PERSONS:
                st.markdown('<div class="gp-section-head">People</div>', unsafe_allow_html=True)
                if not st.session_state.get("you_person") \
                        and not st.session_state.get("you_skipped"):
                    _onboarding_card("home")
                    st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
                with st.container(key="peoplerow"):
                    cols = st.columns(min(len(PERSONS), 8), gap="small")
                    for c, p, i in zip(cols, PERSONS[:8], range(min(len(PERSONS), 8))):
                        with c:
                            _person_card(p, i, "home")
                if len(PERSONS) > 8:
                    if st.button("See all", key="people_seeall", type="tertiary"):
                        st.session_state["tab"] = "people"
                        st.rerun()

        if flt:
            m = META.copy()
            if flt["kind"] == "event":
                m = m[m["event_id"] == flt["val"]]
            elif flt["kind"] == "place":
                m = m[(m["place_name"] == flt["val"]) | (m["area"] == flt["val"])]
            elif flt["kind"] == "person":
                ids = [i for i, pi in IMG2PERSON.items() if pi == flt["val"]]
                m = m[m["img_id"].isin(ids)]
            elif flt["kind"] == "theme":
                cap = m["caption"].fillna("").str.lower()
                m = m[cap.str.contains(flt.get("pat", r"$^"), regex=True, na=False)]
            _month_block(m, "flt")
            st.markdown('</div>', unsafe_allow_html=True)
            _lightbox_render()
            return

        _still_searching_card()
        m = META.copy()
        m["ts"] = pd.to_datetime(m["timestamp"])
        years = sorted(m["ts"].dt.year.unique(), reverse=True)
        latest2 = set(years[:2])
        for y in years:
            sub = m[m["ts"].dt.year == y]
            if y in latest2:
                st.markdown(f'<div class="year-head"><span class="y">{y}</span>'
                            f'<span class="c">{len(sub)} photos</span><span class="rule"></span></div>',
                            unsafe_allow_html=True)
                _month_block(sub, f"ph_{y}")
            else:
                st.markdown(f'<div class="year-head"><span class="y">{y}</span>'
                            f'<span class="c">{len(sub)} photos</span><span class="rule"></span></div>',
                            unsafe_allow_html=True)
                if st.session_state.get(f"year_open_{y}"):
                    _month_block(sub, f"ph_{y}")
                else:
                    if st.button("Show all", key=f"year_{y}", type="tertiary"):
                        st.session_state[f"year_open_{y}"] = True
    _lightbox_render()


def _still_searching_card():
    ss = st.session_state.get("still_searching")
    if not ss:
        return
    st.markdown(f'<div class="proac">{sparkle(16, "spkpro")}'
                f'<div class="pa-t">We kept searching in the background</div>'
                f'<div class="pa-s">Closest match for “{esc(ss["q"])}”</div></div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3.2, 1, 1], vertical_alignment="center", gap="small")
    with c1:
        _photo_cell(ss["img"], "proac", [ss["img"]], 0)
    with c2:
        if st.button("Open", key="proac_open", type="secondary", use_container_width=True):
            _open_lightbox([ss["img"]], 0)
    with c3:
        icon_button("Dismiss", "close", "proac_dismiss",
                    on_click=lambda: st.session_state.pop("still_searching", None),
                    c="#80868b", s=18)


# ---------------- People tab ----------------
def people_tab():
    with st.container(key="viewwrap"):
        st.markdown(f'<div class="gp-section-head">People <span class="gp-count">{len(PERSONS)}</span></div>',
                    unsafe_allow_html=True)
        if not PERSONS:
            st.markdown('<div class="card-sub">Face groups appear here once the library is scanned.</div>',
                        unsafe_allow_html=True)
        if PERSONS and not st.session_state.get("you_person") \
                and not st.session_state.get("you_skipped"):
            _onboarding_card("ptab")
            st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
        with st.container(key="peoplerow_grid"):
            cols = st.columns(min(len(PERSONS), 4), gap="small")
            for c, p, i in zip(cols, PERSONS, range(len(PERSONS))):
                with c:
                    _person_card(p, i, "ptab")
    _lightbox_render()


# ---------------- Settings tab ----------------
def _reset_all():
    for k in list(st.session_state.keys()):
        if k.startswith(("jog_", "classic_", "confirm_", "guided_", "moment_expanded",
                         "anchor_img", "task_", "test_", "mem_filter", "person_filter",
                         "you_", "search_", "demo_card_dismissed", "lightbox", "mic_req",
                         "still_searching", "year_open", "settings_")) or k == "pcode":
            st.session_state.pop(k, None)
    st.session_state["tab"] = "photos"
    st.rerun()


def settings_tab():
    sec = st.session_state.get("settings_sec", "about")
    with st.container(key="viewwrap"):
        st.markdown(f'<div class="gp-section-head">{("How this works" if sec == "how" else "About this demo")}</div>',
                    unsafe_allow_html=True)
        if sec == "how":
            st.markdown('<div class="about-p">A research prototype inside a Google-Photos-style app. '
                        'It studies how people find photos they only half-remember.</div>',
                        unsafe_allow_html=True)
            st.markdown('<div class="about-p"><b>Guided search.</b> Describe the photo in a sentence. '
                        'We show your closest matches right away, then ask a few quick questions '
                        'only where the library is still ambiguous — you can skip or correct '
                        'everything at each step.</div>', unsafe_allow_html=True)
            st.markdown('<div class="about-p"><b>Understanding.</b> ' + esc(mode_label()) +
                        (' — your description is sent to Google\'s Gemini API (free tier). '
                         if AI_ON else ' — your text is processed offline; nothing is sent anywhere.') +
                        '</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="about-p"><b>Library.</b> {N_PHOTOS:,} free-licensed photos '
                        '(CC0 / CC BY / CC BY-SA — see ATTRIBUTION.md) with synthetic dates, places '
                        'and people. No real personal data.</div>', unsafe_allow_html=True)
            st.markdown('<div class="about-p"><b>People.</b> Photos are grouped automatically by '
                        'faces; the person you pick is labelled “You”.</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="about-p"><b>Privacy.</b> {esc(note_text())}</div>',
                        unsafe_allow_html=True)
        st.button("Reset", key="reset_settings", type="secondary", on_click=_reset_all)

# ============================================================
# PART 5: search hero, guided flow, main
# ============================================================

# ---------------- classic search (control) ----------------
MIC_JS = """
<script>
(function () {
  if (window.__gpMicInstalled) return;
  window.__gpMicInstalled = true;
  setInterval(function () {
    var m = document.querySelector('span.micreq');
    if (!m) return;
    var target = m.getAttribute('data-target') || 'search';
    m.remove();
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;
    try {
      var rec = new SR();
      rec.lang = 'en-IN';
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      rec.onresult = function (e) {
        var t = e.results[0][0].transcript;
        var sel = target === 'pill'
          ? 'input[placeholder*="Search Google Photos"]'
          : 'input[placeholder*="Search for a person"]';
        var inp = document.querySelector(sel);
        if (!inp) return;
        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(inp, t);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        var btn = Array.prototype.slice.call(document.querySelectorAll('button'))
          .find(function (b) { return b.textContent.trim() === 'Search'; });
        if (btn) setTimeout(function () { btn.click(); }, 300);
      };
      rec.start();
    } catch (err) { /* ignore */ }
  }, 350);
})();
</script>
"""


def _classic_go(task_id, qkey):
    text = st.session_state.get(qkey, "")
    if not text.strip():
        st.warning("Type a search first.")
        return
    st.session_state.pop("force_show_free", None)
    st.session_state[f"classic_queries_{task_id}"] = \
        st.session_state.get(f"classic_queries_{task_id}", 0) + 1
    log_event("classic", task_id, "dump_submitted", {"text": text.strip()})
    with st.spinner("Searching…"):
        res = classic_search(text, pool=(task_id == "free_classic"))
    st.session_state[f"classic_res_{task_id}"] = res
    st.rerun()


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
        year = int(ym.group(0))
        tsy = pd.to_datetime(META["timestamp"]).dt.year.to_numpy()
        boost[tsy == year] += 0.25
    return boost


def classic_search(text, pool=False):
    text = (text or "").strip()
    if not text:
        return None
    qv = BUNDLE["clip"].encode([text[:300]], convert_to_numpy=True,
                               normalize_embeddings=True)[0]
    sims = BUNDLE["emb"] @ qv.astype("float32")
    combined = sims + classic_boost(text)
    df = pd.DataFrame({"img_id": META["img_id"], "score": combined,
                       "cos": sims,
                       "ts": pd.to_datetime(META["timestamp"])})
    if pool:
        pool_df = df[df["cos"] >= 0.22].copy()
        pintent = bool(PERSON_INTENT_RE.search(text.lower()))
        if IMG2PERSON and (len(pool_df) > 0 or pintent):
            # Union in the highest-scored face-grouped images (even below the cos
            # floor) so the People facet has candidates for every real search.
            fmask = df["img_id"].isin(set(IMG2PERSON.keys()))
            face_rows = df[fmask].sort_values("score", ascending=False).head(40)
            pool_df = pd.concat([pool_df, face_rows]).drop_duplicates(subset="img_id")
        if len(pool_df) == 0:
            return None
        return pool_df.sort_values("score", ascending=False).reset_index(drop=True)
    return df.sort_values("score", ascending=False).head(30).reset_index(drop=True)


def _photo_grid_confirm(ids, key_prefix, task_id):
    st.markdown('<div class="gpgrid">', unsafe_allow_html=True)
    cols = st.columns(4, gap="small")
    for gi, img_id in enumerate(ids):
        with cols[gi % 4]:
            sq(img_id)
            if st.button("✔ This one", key=f"{key_prefix}_{gi}", type="tertiary",
                         use_container_width=True):
                st.session_state[f"confirm_img_{task_id}"] = img_id
                st.session_state["confirm_task"] = task_id
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------- Search view (hero, Phase 3) ----------------
HEDGES = re.compile(r"\b(i think|maybe|not sure|kind of|roughly|somewhere|vaguely|"
                    r"half.?remember|can'?t remember|don'?t remember)\b")
PERSON_INTENT_RE = re.compile(
    r"\b(friends?|family|people|person|persons?|mom|dad|mother|father|"
    r"brother|sister|kids?|child|me|myself|with me|who|faces?)\b")
STARTERS = ["I'm looking for a photo of…", "A photo from a trip to…",
            "I can't quite remember, but it was…"]


def _search_bar_free():
    with st.container(key="searchpill_free"):
        row = st.columns([5, 0.6, 1.0], vertical_alignment="center", gap="small")
        with row[0]:
            st.text_input("Search your photos", key="search_q",
                          placeholder="Search for a person, place, or thing",
                          label_visibility="collapsed")
        with row[1]:
            with st.container(key="micfree_c"):
                if st.button("Voice search", key="mic_free", type="tertiary", use_container_width=True):
                    st.session_state["mic_req"] = True
                    st.session_state["mic_target"] = "search"
        with row[2]:
            if st.button("Search", key="classic_go_free", type="primary", use_container_width=True):
                _classic_go("free_classic", "search_q")
    st.markdown(MIC_JS, unsafe_allow_html=True)
    if st.session_state.get("mic_req"):
        tgt = st.session_state.get("mic_target", "search")
        st.markdown(f'<span class="micreq" data-target="{esc(tgt)}"></span>',
                    unsafe_allow_html=True)
        st.caption("Listening… (works in Chrome or Edge over https)")
    st.markdown('<style>'
                '.st-key-searchpill_free { padding:0; margin:0; }'
                '.st-key-searchpill_free .stTextInput { position:relative; margin:0; }'
                '.st-key-searchpill_free .stTextInput::before {'
                'content:"";position:absolute;left:17px;top:50%;transform:translateY(-50%);'
                'width:20px;height:20px;pointer-events:none;opacity:.55;'
                'background:url("' + svg_uri("search", 20, "#5f6368") + '") center/contain no-repeat;}'
                '.st-key-searchpill_free .stTextInput input {'
                'border:1px solid #dadce0 !important;border-radius:999px !important;height:56px;'
                'font-size:15.5px;padding:0 18px 0 48px !important;box-shadow:none !important;}'
                '.st-key-searchpill_free .stTextInput input:focus {'
                'border-color:#1a73e8 !important;box-shadow:0 0 0 3px #e8f0fe !important;}'
                '.st-key-micfree_c { padding:0; margin:0; }'
                '.st-key-micfree_c .stButton { margin:0; padding:0; }'
                '.st-key-micfree_c .stButton > button {'
                'display:flex;align-items:center;justify-content:center;gap:8px;}'
                '.st-key-micfree_c .stButton > button::before {'
                'content:"";width:20px;height:20px;flex:none;opacity:.62;'
                'background:url("' + svg_uri("mic", 20, "#5f6368") + '") center/contain no-repeat;}'
                '@media (max-width:700px) {'
                '.st-key-searchpill_free > [data-testid="stHorizontalBlock"] {'
                'flex-direction:column;align-items:stretch;gap:8px;}'
                '.st-key-searchpill_free .stButton > button {'
                'width:100%;min-height:48px;}'
                '}'
                '</style>', unsafe_allow_html=True)


def _suggestions_ui():
    tp = _build_tag_panel()
    with st.container(border=True):
        st.markdown(f'<div class="gemini-head">{sparkle(18, "spksg")}'
                    '<span class="gt">Try searching</span></div>', unsafe_allow_html=True)
        st.markdown('<style>.sugg-row{display:flex;align-items:center;gap:10px;padding:8px 10px;'
                    'border-radius:10px;font-size:14.5px;color:var(--gp-text);}</style>',
                    unsafe_allow_html=True)
        for s in STARTERS:
            st.markdown(f'<div class="sugg-row">{icon("photo", 18, "#5f6368")}'
                        f'<span>{esc(s)}</span></div>', unsafe_allow_html=True)
        if tp["people"]:
            st.markdown('<div class="sugg-head">People</div>', unsafe_allow_html=True)
            cols = st.columns(min(len(tp["people"]), 6), gap="small")
            for c, (lab, pid) in zip(cols, tp["people"][:6]):
                with c:
                    if st.button(lab, key=f"sg_pp_{pid}", type="tertiary",
                                 use_container_width=True):
                        st.session_state["person_filter"] = {
                            "kind": "person", "val": pid, "title": f"{lab} · photos"}
                        st.session_state["tab"] = "photos"
                        st.rerun()
        if tp["places"]:
            st.markdown('<div class="sugg-head">Places</div>', unsafe_allow_html=True)
            cols = st.columns(min(len(tp["places"]), 6), gap="small")
            for c, (pl, cnt) in zip(cols, tp["places"][:6]):
                with c:
                    if st.button(f"{pl} · {cnt}", key=f"sg_pl_{pl}", type="tertiary",
                                 use_container_width=True):
                        st.session_state["search_q"] = pl
                        _classic_go("free_classic", "search_q")
        if tp["things"]:
            st.markdown('<div class="sugg-head">Things</div>', unsafe_allow_html=True)
            cols = st.columns(min(len(tp["things"]), 6), gap="small")
            for c, (th, cnt) in zip(cols, tp["things"][:6]):
                with c:
                    if st.button(f"{th} · {cnt}", key=f"sg_th_{th}", type="tertiary",
                                 use_container_width=True):
                        st.session_state["search_q"] = th
                        _classic_go("free_classic", "search_q")
        if tp["years"]:
            st.markdown('<div class="sugg-head">When</div>', unsafe_allow_html=True)
            cols = st.columns(min(len(tp["years"]), 6), gap="small")
            for c, (yr, cnt) in zip(cols, tp["years"][:6]):
                with c:
                    if st.button(f"{yr} · {cnt}", key=f"sg_yr_{yr}", type="tertiary",
                                 use_container_width=True):
                        st.session_state["search_q"] = yr
                        _classic_go("free_classic", "search_q")


def _go_event(eid):
    st.session_state["mem_filter"] = {"kind": "event", "val": eid,
                                      "title": EVENT_TITLES.get(eid, eid)}
    st.session_state["tab"] = "photos"
    st.rerun()


def _go_place(name):
    st.session_state["mem_filter"] = {"kind": "place", "val": name, "title": name}
    st.session_state["tab"] = "photos"
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


def _group_scenes(res_df):
    ev = {}
    for rank, (_, r) in enumerate(res_df.iterrows()):
        row = META.loc[r["img_id"]]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        eid = row.get("event_id")
        if eid == "e13" or eid not in EVENT_TITLES:
            continue
        ev.setdefault(eid, []).append(rank)
    out = []
    for eid, ranks in ev.items():
        if len(ranks) >= 2:
            sub = META[META["event_id"] == eid]
            out.append({"eid": eid, "title": EVENT_TITLES[eid], "n": len(sub),
                        "hero": _hero_image(sub), "best": min(ranks)})
    out.sort(key=lambda x: x["best"])
    return out[:4]


def _grouped_results(res):
    q = st.session_state.get("search_q", "")
    st.markdown(f'<div class="gp-section-head" style="margin-top:18px">Results '
                f'<span class="gp-count">for “{esc(q[:60])}” · {len(res)}</span></div>',
                unsafe_allow_html=True)
    people = _group_people(res, q)
    places = _group_places(res)
    scenes = _group_scenes(res)
    if people:
        h1, h2 = st.columns([5, 1], vertical_alignment="center", gap="small")
        with h1:
            st.markdown('<div class="grp-head"><span class="t">People</span>'
                        '<span class="c">in these results</span></div>', unsafe_allow_html=True)
        with h2:
            if st.button("See all", key="grp_pp_seeall", type="tertiary"):
                st.session_state["tab"] = "people"
                st.rerun()
        st.markdown('<div class="scene-strip">', unsafe_allow_html=True)
        cols = st.columns(len(people), gap="small")
        for c, (p, n, qm), i in zip(cols, people, range(len(people))):
            with c:
                lab = person_label(p["id"])
                with st.container(key=f"sppcard_{i}"):
                    av = person_avatar(p["id"])
                    if av:
                        st.image(av, width=56)
                    st.markdown(f'<div class="pc-name">{esc(lab)}</div>'
                                f'<div class="pc-cnt">{n} in results</div>',
                                unsafe_allow_html=True)
                    if st.button(lab, key=f"grp_pp_{p['id']}", use_container_width=True):
                        st.session_state["person_filter"] = {"kind": "person", "val": p["id"],
                                                             "title": f"{lab} · {n} in results"}
                        st.session_state["tab"] = "photos"
                        st.rerun()
                    st.markdown(f'<style>'
                                f'.st-key-sppcard_{i} {{ position:relative; padding:0; margin:0; }}'
                                f'.st-key-sppcard_{i} [data-testid="stImage"] {{ margin:0 auto; }}'
                                f'.st-key-sppcard_{i} [data-testid="stImage"] img {{ border-radius:50%; object-fit:cover; }}'
                                f'.st-key-sppcard_{i} .stButton {{ position:absolute; inset:-4px; margin:0; z-index:5; }}'
                                f'.st-key-sppcard_{i} .stButton > button {{ opacity:0; border:none; background:transparent; }}'
                                f'</style>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    if places:
        st.markdown('<div class="grp-head"><span class="t">Places</span>'
                    '<span class="c">where these were taken</span></div>', unsafe_allow_html=True)
        cols = st.columns(min(len(places), 4), gap="small")
        for c, (name, n, libn) in zip(cols, places):
            with c:
                if st.button(f"{name} · {libn} photos", key=f"grp_pl_{name}",
                             use_container_width=True):
                    _go_place(name)
    if scenes:
        h3, h4 = st.columns([5, 1], vertical_alignment="center", gap="small")
        with h3:
            st.markdown('<div class="grp-head"><span class="t">Scenes</span>'
                        '<span class="c">moments these fit</span></div>', unsafe_allow_html=True)
        with h4:
            if st.button("See all", key="grp_sc_seeall", type="tertiary"):
                st.session_state["tab"] = "photos"
                st.rerun()
        st.markdown('<div class="scene-strip">', unsafe_allow_html=True)
        cols = st.columns(len(scenes), gap="small")
        for c, sc, i in zip(cols, scenes, range(len(scenes))):
            with c:
                p = img_path(sc["hero"])
                with st.container(key=f"scard_{i}"):
                    if p.exists():
                        st.image(str(p), use_container_width=True)
                    st.markdown(f'<div class="sc-t">{esc(sc["title"])}</div>'
                                f'<div class="sc-c">{sc["n"]} photos</div>',
                                unsafe_allow_html=True)
                    if st.button(sc["title"], key=f"grp_sc_{sc['eid']}", use_container_width=True):
                        _go_event(sc["eid"])
                    st.markdown(f'<style>'
                                f'.st-key-scard_{i} {{ position:relative; border-radius:12px; overflow:hidden; background:#fff; border:1px solid var(--gp-hairline); padding:0; margin:0; }}'
                                f'.st-key-scard_{i} > [data-testid="stVerticalBlock"] {{ padding:0; margin:0; }}'
                                f'.st-key-scard_{i} [data-testid="stImage"] {{ aspect-ratio:16/10; }}'
                                f'.st-key-scard_{i} [data-testid="stImage"] img {{ object-fit:cover; }}'
                                f'.st-key-scard_{i} .sc-t {{ font-size:12.5px; font-weight:500; padding:7px 9px 1px; }}'
                                f'.st-key-scard_{i} .sc-c {{ font-size:11.5px; color:var(--gp-secondary); padding:0 9px 8px; }}'
                                f'.st-key-scard_{i} .stButton {{ position:absolute; inset:0; margin:0; z-index:5; }}'
                                f'.st-key-scard_{i} .stButton > button {{ opacity:0; border:none; }}'
                                f'</style>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="grp-head"><span class="t">Photos</span>'
                '<span class="c">closest matches</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="gpgrid">', unsafe_allow_html=True)
    cols = st.columns(4, gap="small")
    for i, (_, r) in enumerate(res.head(30).iterrows()):
        with cols[i % 4]:
            sq(r["img_id"])
            if st.button("This is it ✔", key=f"classic_confirm_free_{r['img_id']}",
                         type="tertiary", use_container_width=True):
                st.session_state["confirm_img_free_classic"] = r["img_id"]
                st.session_state["confirm_task"] = "free_classic"
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    row2 = st.columns([1, 1.4])
    with row2[0]:
        if st.button("Search again", key="classic_again_free", type="tertiary"):
            st.session_state["classic_res_free_classic"] = None
            st.rerun()
    with row2[1]:
        if st.button("Describe it instead ✨", key="grid_describe", type="tertiary"):
            st.session_state["guided_prefill"] = (st.session_state.get("search_q") or "")
            st.session_state["guided_autostart"] = True
            st.session_state["tab"] = "guided"
            st.rerun()
    if _nudge_needed(res):
        with st.container(border=True):
            st.markdown(f'<div class="gemini-head">{sparkle(18, "spkn")}'
                        '<span class="card-title" style="margin:0">Can\'t find the right one?</span></div>'
                        '<div class="card-sub">Guided search asks a few quick questions and '
                        'narrows it down — built for half-memories.</div>', unsafe_allow_html=True)
            if st.button("Try guided search", key="nudge_free", type="secondary"):
                st.session_state["guided_prefill"] = (st.session_state.get("search_q") or "")
                st.session_state["guided_autostart"] = True
                st.session_state["tab"] = "guided"
                st.rerun()


def _nudge_needed(res):
    q = (st.session_state.get("search_q") or "").lower()
    n = st.session_state.get("classic_queries_free_classic", 0)
    if res is None:
        return False
    top = float(res["cos"].max())
    if HEDGES.search(q):
        return True
    if top < 0.20:
        return True
    if n >= 2 and top < 0.26:
        return True
    return False


def _zero_router(q):
    st.markdown('<div class="zero-card"><div class="zt">No exact matches</div>'
                f'<div class="zs">Nothing close to “{esc(q[:80])}”. Describe it in a sentence — '
                'guided search is built for half-memories.</div></div>',
                unsafe_allow_html=True)
    if st.button("Describe it instead ✨", key="zero_describe", type="primary"):
        st.session_state["guided_prefill"] = q
        st.session_state["guided_autostart"] = True
        st.session_state["tab"] = "guided"
        st.rerun()
    if st.button("Show closest photos anyway", key="zero_show", type="tertiary"):
        st.session_state["force_show_free"] = True
        st.rerun()


def search_tab():
    if st.session_state.get("jog_free") and not st.session_state.get("jog_success_free"):
        st.session_state["tab"] = "guided"
        st.rerun()
    with st.container(key="viewwrap"):
        _search_bar_free()
        res = st.session_state.get("classic_res_free_classic")
        if st.session_state.get("classic_success_free"):
            with st.container(border=True):
                st.markdown('<div class="card-title">Noted</div>', unsafe_allow_html=True)
                st.success("Noted — thanks for trying. In free play there's no single right answer.")
                img_id = st.session_state["classic_success_free"]["img_id"]
                if img_id in META.index:
                    sq(img_id)
                if st.button("Search something else", key="classic_again"):
                    st.session_state.pop("classic_success_free", None)
                    st.session_state.pop("classic_res_free_classic", None)
                    st.session_state.pop("force_show_free", None)
                    st.rerun()
            return
        q = (st.session_state.get("search_q") or "").strip()
        if res is None and not q:
            _suggestions_ui()
        elif res is None and not st.session_state.get("force_show_free"):
            _zero_router(q)
        elif res is None:
            _grouped_results(classic_search(q, pool=False))
        else:
            _grouped_results(res)
        _confirm_dialog("free_classic", None)
    _lightbox_render()


# ---------------- guided flow (Phase 4) ----------------
def _start_guided(text, task_id, sess_key):
    text = (text or "").strip()
    if not text:
        st.warning("Tell me a little something first.")
        return
    log_event("jog", task_id, "dump_submitted", {"text": text})
    st.session_state[f"jog_text_{task_id}"] = text
    with st.spinner("Narrowing…"):
        sess = JogSession(BUNDLE["ret"], BUNDLE["meta"], BUNDLE["emb"])
        state = sess.start(text, live_session=st.session_state.live_session)
    st.session_state[sess_key] = sess
    st.session_state[f"jog_state_{task_id}"] = state
    log_event("jog", task_id, "cues_parsed",
              {"count": len(sess.cues), "parse_source": sess.parse_source})
    st.rerun()


def _cue_recs(session):
    return [{"type": c.type, "value": c.value, "certainty": c.certainty,
             "negated": c.negated, "remove": False} for c in session.cues]


def _cue_toggle(session, task_id, i, action):
    recs = []
    for j, c in enumerate(session.cues):
        neg, rem, cert = c.negated, False, c.certainty
        if j == i:
            if action == "negate":
                neg = not c.negated
            elif action == "remove":
                rem = True
            elif action == "cert":
                cert = "unsure" if cert == "sure" else "sure"
        recs.append({"type": c.type, "value": c.value, "certainty": cert, "negated": neg,
                     "remove": rem})
    log_event("jog", task_id, "cue_edited",
              {"count": len([r for r in recs if not r["remove"]])})
    st.session_state[f"jog_state_{task_id}"] = session.edit_cues(recs)
    st.rerun()


def cue_chips_ui(session, task_id):
    if not session.cues:
        st.markdown('<div class="card-sub">No cues detected — relying on visual similarity.</div>',
                    unsafe_allow_html=True)
        return
    for i, c in enumerate(session.cues):
        cls = "cuechip" + (" neg" if c.negated else "")
        st.markdown(
            f'<span class="{cls}"><span class="ct">{esc(c.type)}</span>'
            f'{esc(c.value)}<span class="cstate">{"unsure" if c.certainty != "sure" else "sure"}</span></span>',
            unsafe_allow_html=True)
        b1, b2, b3 = st.columns([1.5, 1, 0.5], vertical_alignment="center", gap="small")
        with b1:
            if st.button("not this" if not c.negated else "is this",
                         key=f"cue_neg_{task_id}_{i}", type="tertiary"):
                _cue_toggle(session, task_id, i, "negate")
        with b2:
            if st.button("sure" if c.certainty == "sure" else "unsure",
                         key=f"cue_cert_{task_id}_{i}", type="tertiary"):
                _cue_toggle(session, task_id, i, "cert")
        with b3:
            if st.button("✕", key=f"cue_rm_{task_id}_{i}", type="tertiary"):
                _cue_toggle(session, task_id, i, "remove")


def _pretty_moment_label(label):
    parts = str(label).split(" \u00b7 ")
    try:
        if len(parts) >= 2 and re.match(r"^\d{4}-\d{2}-\d{2}", parts[1]):
            span = parts[1].split(" \u2013 ")
            d0 = pd.to_datetime(span[0])
            if len(span) > 1:
                d1 = pd.to_datetime(span[1])
                rest = parts[2:]
            else:
                d1 = d0
                rest = parts[2:]
            if d0.date() == d1.date():
                date_s = d0.strftime("%b %-d, %Y")
            elif d0.year == d1.year:
                date_s = f"{d0.strftime('%b %-d')}\u2013{d1.strftime('%d, %Y')}"
            else:
                date_s = f"{d0.strftime('%b %-d, %Y')}\u2013{d1.strftime('%b %-d, %Y')}"
            return " \u00b7 ".join([parts[0], date_s] + rest)
    except Exception:  # noqa: BLE001
        pass
    return label


def _why_line(m, session):
    from jog_engine.explain import why_matched
    if not m["img_ids"]:
        return "visual similarity"
    row = META.loc[m["img_ids"][0]]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return why_matched(row.to_dict(), session.cues)


def jog_moments_ui(session, state, task_id, confirm_handler, anchor_enabled=True):
    if state["moments"] and state["moments"][0].get("score", 1.0) < 0.55:
        hint = ("Closest matches so far — the question below usually helps."
                if state.get("question")
                else "Closest matches so far — correct a cue, or press I'm stuck to browse.")
        st.markdown(f'<div class="card-sub">{esc(hint)}</div>', unsafe_allow_html=True)
    for mi, m in enumerate(state["moments"]):
        cover = m["img_ids"][0]
        with st.container(border=True, key=f"mcard_{task_id}_{mi}"):
            cover_p = img_path(cover)
            if cover_p.exists():
                st.image(str(cover_p), use_container_width=True)
            st.markdown(f'<div class="mhead"><span class="mlab">{esc(_pretty_moment_label(m["label"]))}</span>'
                        f'<span class="mcnt">{m["size"]} photos</span></div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="mwhy">{esc(_why_line(m, session))}</div>',
                        unsafe_allow_html=True)
            b1, b2 = st.columns([1, 1], gap="small")
            with b1:
                if st.button("This is it ✔", key=f"jog_c_{task_id}_{mi}", type="tertiary",
                             use_container_width=True):
                    confirm_handler(cover)
            with b2:
                if anchor_enabled:
                    if st.button("Use as anchor", key=f"jog_a_{task_id}_{mi}", type="tertiary",
                                 use_container_width=True):
                        st.session_state[f"anchor_img_{task_id}"] = cover
                        st.rerun()
            if st.button("Show all in this moment", key=f"jog_all_{task_id}_{mi}",
                         type="tertiary"):
                st.session_state[f"moment_expanded_{task_id}_{mi}"] = True
            st.markdown(f'<style>'
                        f'.st-key-mcard_{task_id}_{mi} [data-testid="stMarkdownContainer"] {{ padding:0 2px; }}'
                        f'.st-key-mcard_{task_id}_{mi} [data-testid="stImage"] {{ margin:4px 0 10px; }}'
                        f'.st-key-mcard_{task_id}_{mi} [data-testid="stImage"] img {{ aspect-ratio:16/9; object-fit:cover; border-radius:12px; width:100%; }}'
                        f'.st-key-mcard_{task_id}_{mi} .mhead {{ display:flex; align-items:baseline; gap:8px; }}'
                        f'.st-key-mcard_{task_id}_{mi} .mlab {{ font-size:15px; font-weight:500; }}'
                        f'.st-key-mcard_{task_id}_{mi} .mcnt {{ font-size:12.5px; color:var(--gp-secondary); }}'
                        f'.st-key-mcard_{task_id}_{mi} .mwhy {{ font-size:12px; color:var(--gp-secondary); margin-top:4px; }}'
                        f'</style>', unsafe_allow_html=True)
        if st.session_state.get(f"moment_expanded_{task_id}_{mi}"):
            _photo_grid_confirm(m["img_ids"], f"jmg_{task_id}_{mi}", task_id)


_OPT_HUMAN = {
    "indoor_outdoor": {"indoor": "Indoors", "outdoor": "Outdoors", "unclear": "Unclear"},
    "time_of_day": {"morning": "Morning", "afternoon": "Afternoon", "evening": "Evening",
                    "night": "Night", "unclear": "Unclear"},
    "setting_type": {"cafe": "Café", "beach": "Beach", "street": "Street", "campus": "Campus",
                     "classroom_or_study": "Classroom or study", "hostel_or_home": "Home or hostel",
                     "restaurant": "Restaurant", "temple_or_ruins": "Temple or ruins",
                     "nature_landscape": "Nature or landscape", "transport": "Transport",
                     "office": "Office", "party_or_event": "Party or event",
                     "shop_or_market": "Shop or market", "document_or_utility": "Document or receipt",
                     "other": "Somewhere else"},
    "season_hint": {"summer": "Summer", "monsoon": "Monsoon", "winter": "Winter"},
    "people_count_bucket": {"0": "No one", "1": "Just one person", "2-3": "Two or three",
                            "4+": "A group"},
    "has_text": {"True": "Yes, some writing", "False": "No writing"},
}


def opt_label(attr, value):
    v = str(value)
    mapped = _OPT_HUMAN.get(attr, {}).get(v)
    if mapped:
        return mapped
    if attr in ("place_name", "dominant_color"):
        return v[:1].upper() + v[1:] if v else v
    return v.replace("_", " ").capitalize()


# ---------- smart questions: face + event completion (Phase 5.1 / 5.2) ----------
def _smart_question(state):
    if not IMG2PERSON:
        return None
    top = state.get("top", [])
    if len(top) < 6:
        return None
    from collections import Counter
    pcnt = Counter(IMG2PERSON.get(t["img_id"]) for t in top
                   if t["img_id"] in IMG2PERSON)
    big_p = [(pid, n) for pid, n in pcnt.items() if n >= 3]
    if len(big_p) >= 2:
        big_p.sort(key=lambda x: -x[1])
        a, b = big_p[0], big_p[1]
        return {"kind": "person", "attribute": "person",
                "text": f"Was this with {person_label(a[0])} or {person_label(b[0])}?",
                "options": [a[0], b[0]], "expected_info_gain": 1.0}
    return None


def _person_answer(session, task_id, pid):
    lab = person_label(pid)
    recs = _cue_recs(session) + [{"type": "person", "value": lab, "certainty": "sure",
                                  "negated": False, "remove": False}]
    state = session.edit_cues(recs)
    scored = session.scored
    ids = {i for i, pi in IMG2PERSON.items() if pi == pid}
    mask = scored["img_id"].isin(ids)
    scored.loc[mask, "score"] = scored.loc[mask, "score"] * 1.3
    session.scored = scored.sort_values("score", ascending=False).reset_index(drop=True)
    st.session_state[f"jog_state_{task_id}"] = session._state(
        question=state.get("question"), pair=None)
    log_event("jog", task_id, "question_answered", {"attribute": "person", "value": lab})
    st.rerun()


def jog_question_ui(session, state, task_id):
    q = state.get("question")
    if not q:
        return
    log_event("jog", task_id, "question_shown", {"attribute": q["attribute"]})
    with st.container(border=True):
        st.markdown(f'<div class="sysline">{sparkle(14, "spkq")}'
                    '<div><div style="font-weight:500;color:var(--gp-text)">Quick question</div>'
                    f'<div style="margin-top:2px">{esc(q["text"])}</div></div></div>',
                    unsafe_allow_html=True)
        for opt in q["options"]:
            if q.get("kind") == "person":
                av = person_avatar(opt)
                face = (f'<img src="{esc(av)}" alt="" style="width:30px;height:30px;'
                        f'border-radius:50%;object-fit:cover">' if av else "")
                st.markdown(f'<div class="faceopt"><span class="faceimg">{face}</span>'
                            f'<span>{esc(person_label(opt))}</span></div>',
                            unsafe_allow_html=True)
                if st.button(f"With {person_label(opt)}",
                             key=f"jog_q_{task_id}_{q['attribute']}_{opt}",
                             type="secondary", use_container_width=True):
                    _person_answer(session, task_id, opt)
            else:
                if st.button(opt_label(q["attribute"], opt),
                             key=f"jog_q_{task_id}_{q['attribute']}_{opt}",
                             type="secondary", use_container_width=True):
                    log_event("jog", task_id, "question_answered",
                              {"attribute": q["attribute"], "value": opt})
                    st.session_state["jog_state_" + task_id] = \
                        session.answer(q["attribute"], opt)
                    st.rerun()
        if st.button("I don't remember", key=f"jog_dk_{task_id}_{q['attribute']}",
                     type="tertiary"):
            if q.get("kind") == "person":
                st.session_state[f"smart_q_done_{task_id}"] = True
                st.session_state[f"jog_state_{task_id}"] = session.state_summary()
            else:
                log_event("jog", task_id, "question_answered",
                          {"attribute": q["attribute"], "value": "dont_know"})
                st.session_state["jog_state_" + task_id] = \
                    session.answer(q["attribute"], "I don't remember")
            st.rerun()


def _pair_choose(session, task_id, pair, choice):
    log_event("jog", task_id, "pair_choice", {"choice": choice})
    st.session_state[f"jog_state_" + task_id] = session.choose(choice, pair)
    st.rerun()


def this_or_that_ui(session, state, task_id):
    pair = state.get("pair")
    if not pair:
        return
    log_event("jog", task_id, "pair_shown", {"left": pair["left"], "right": pair["right"]})
    with st.container(border=True, key=f"paircard_{task_id}"): 
        st.markdown(f'<div class="sysline">{sparkle(14, "spkpair")}'
                    '<div>Which is closer to your memory?</div></div>',
                    unsafe_allow_html=True)
        cols = st.columns(2, gap="small")
        for c, side in zip(cols, ("left", "right")):
            with c:
                p = img_path(pair[side])
                if p.exists():
                    st.image(str(p), use_container_width=True)
        c1, c2, c3 = st.columns(3, gap="small")
        with c1:
            if st.button("Left is closer", key=f"pair_l_{task_id}", type="secondary",
                         use_container_width=True):
                _pair_choose(session, task_id, pair, "left")
        with c2:
            if st.button("Right is closer", key=f"pair_r_{task_id}", type="secondary",
                         use_container_width=True):
                _pair_choose(session, task_id, pair, "right")
        with c3:
            if st.button("Neither", key=f"pair_n_{task_id}", type="tertiary",
                         use_container_width=True):
                _pair_choose(session, task_id, pair, "neither")


def anchor_inline_ui(session, task_id, state_key):
    img_id = st.session_state.pop(f"anchor_img_{task_id}", None)
    if not img_id:
        return
    with st.container(border=True):
        st.markdown(f'<div class="sysline">{icon("place", 16, "#5f6368")}'
                    f'<div>Use <b>{esc(date_of(img_id))}</b> as an anchor?</div></div>',
                    unsafe_allow_html=True)
        for rel, lab in (("same_day", "Same day"), ("right_after", "Right after"),
                         ("right_before", "Right before"), ("around", "Around that time")):
            if st.button(lab, key=f"anchor_{task_id}_{rel}", type="secondary",
                         use_container_width=True):
                log_event("jog", task_id, "anchor_set", {"relation": rel, "img_id": img_id})
                st.session_state[state_key] = session.set_anchor(img_id, rel)
                st.rerun()


def jog_fallback_ui(session, state, task_id):
    fb = state.get("fallback")
    if not fb:
        return
    day_groups = sorted((d, ids) for d, ids in fb.get("days", {}).items())
    fb_start = pd.Timestamp(fb["start"]).strftime("%b %-d, %Y")
    fb_end = pd.Timestamp(fb["end"]).strftime("%b %-d, %Y")
    log_event("jog", task_id, "fallback_shown", {"start": fb.get("start"),
                                                  "end": fb.get("end")})
    first_img = day_groups[0][1][0] if day_groups else None
    if first_img:
        st.session_state["still_searching"] = {
            "q": (st.session_state.get(f"jog_text_{task_id}", "") or "")[:60],
            "img": first_img}
    with st.container(border=True):
        st.markdown(f'<div class="card-title">I\'d narrow it to '
                    f'{esc(fb_start)} – {esc(fb_end)}</div>'
                    '<div class="card-sub">Browse by day, or start over.</div>',
                    unsafe_allow_html=True)
        for day, ids in day_groups[:6]:
            if st.session_state.get(f"fbday_open_{task_id}_{day}"):
                _photo_grid_confirm(ids[:16], f"jfb_{task_id}_{day}", task_id)
            else:
                if st.button(f"{pd.Timestamp(day).strftime('%b %-d')} · {len(ids)} photos",
                             key=f"fbday_{task_id}_{day}", type="tertiary",
                             use_container_width=True):
                    st.session_state[f"fbday_open_{task_id}_{day}"] = True
        if st.button("Start over", key=f"jog_fb_reset_{task_id}", type="tertiary"):
            st.session_state.pop("jog_" + task_id, None)
            st.session_state.pop("jog_state_" + task_id, None)
            st.rerun()


def _close_narrow(session, task_id, img_id):
    from jog_engine.cues import TimeWindow
    row = META.loc[img_id]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    ts = pd.to_datetime(row["timestamp"])
    session.time_window = TimeWindow(start=(ts - pd.Timedelta(days=3)).strftime("%Y-%m-%d"),
                                     end=(ts + pd.Timedelta(days=3)).strftime("%Y-%m-%d"),
                                     certainty="sure")
    st.session_state[f"jog_state_{task_id}"] = session.edit_cues(_cue_recs(session))
    st.toast("Narrowed to 3 days around that photo.")
    st.rerun()


@st.dialog("Is this the photo?", width="small")
def _confirm_dialog_ui(task_id, session):
    img_id = st.session_state.get(f"confirm_img_{task_id}")
    if not img_id:
        return
    st.markdown(f'<div class="dlg-cap">{esc(caption_of(img_id) or "Your pick")} · '
                f'{esc(date_of(img_id))}</div>', unsafe_allow_html=True)
    try:
        p = img_path(img_id)
        if p.exists():
            st.image(str(p), use_container_width=True)
    except Exception:  # noqa: BLE001
        pass
    c1, c2, c3 = st.columns([1, 1, 1.4], vertical_alignment="center")
    with c1:
        if st.button("No", key=f"cfm_no_{task_id}", use_container_width=True):
            st.session_state.pop(f"confirm_img_{task_id}", None)
            st.toast("Not this one — keep browsing, or use another photo as an anchor."
                     if session is not None else "Not this one — keep browsing.")
            st.rerun()
    with c2:
        if st.button("Yes", key=f"cfm_yes_{task_id}", type="primary", use_container_width=True):
            if session is not None:
                res = session.confirm(img_id)
                st.session_state["jog_success_free"] = res
            else:
                st.session_state["classic_success_free"] = {"img_id": img_id}
            st.session_state.pop(f"confirm_img_{task_id}", None)
            st.rerun()
    with c3:
        if session is not None:
            if st.button("Close, but not it", key=f"cfm_close_{task_id}",
                         use_container_width=True):
                st.session_state.pop(f"confirm_img_{task_id}", None)
                _close_narrow(session, task_id, img_id)


def _confirm_dialog(task_id, session):
    if st.session_state.get(f"confirm_img_{task_id}"):
        _confirm_dialog_ui(task_id, session)


def _success_screen(s):
    with st.container(border=True, key="succcard"):
        img_id = s.get("confirmed") or s.get("img_id")
        if img_id and img_id in META.index:
            p = img_path(img_id)
            if p.exists():
                st.image(str(p), use_container_width=True)
        st.markdown(f'<div class="succ-meta"><span class="succ-chip">'
                    f'Found it in {s["seconds"]:.0f}s</span>'
                    f'<span class="succ-chip">{s["rounds"]} guided steps</span></div>',
                    unsafe_allow_html=True)
        if AI_ON:
            st.markdown(f'<div class="gline">{sparkle(12, "spks")}&nbsp;Understood with Gemini'
                        f'</div>', unsafe_allow_html=True)
        b1, b2 = st.columns([1, 1.2], vertical_alignment="center")
        with b1:
            if st.button("Share", type="primary", key="succ_share"):
                st.toast("Share link copied (demo).")
        with b2:
            if st.button("Search another", key="jog_again"):
                for k in ("jog_free", "jog_state_free", "jog_success_free"):
                    st.session_state.pop(k, None)
                st.rerun()
        st.markdown('<div class="fb-q">Was this the right photo?</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes", key="fb_yes", type="tertiary", use_container_width=True):
                log_event("jog", "free", "success_feedback",
                          {"img_id": img_id, "verdict": "yes"})
                st.session_state.pop("jog_success_free", None)
                st.rerun()
        with c2:
            if st.button("No", key="fb_no", type="tertiary", use_container_width=True):
                log_event("jog", "free", "success_feedback",
                          {"img_id": img_id, "verdict": "no"})
                st.session_state.pop("jog_success_free", None)
                st.rerun()


def _conf_strip(state):
    tw = state.get("time_window")
    try:
        if tw and tw.get("start") and tw.get("end"):
            s = pd.to_datetime(tw["start"])
            e = pd.to_datetime(tw["end"])
            days = max(1, (e - s).days)
            n = sum(m["size"] for m in state["moments"][:2])
            label = f"Narrowed to {days} day{'s' if days != 1 else ''} · {n} photos"
            pct = min(96, 40 + (1 - min(days, 60) / 60) * 56)
        else:
            n = sum(m["size"] for m in state["moments"][:2])
            label = f"{n} photos in the closest moments"
            top_score = state["moments"][0].get("score", 0) if state["moments"] else 0
            pct = 40 + (25 if top_score > 0.55 else 0)
        st.markdown(f'<div class="confstrip"><span>{esc(label)}</span>'
                    f'<div class="confbar"><div style="width:{pct:.0f}%"></div></div></div>',
                    unsafe_allow_html=True)
    except Exception:  # noqa: BLE001
        pass


def _guided_conversation(task_id, session, state):
    t = st.session_state.get(f"jog_text_{task_id}", "")
    if t:
        st.markdown(f'<div class="userbub" style="margin:6px 0 10px">“{esc(t[:200])}”</div>',
                    unsafe_allow_html=True)
    badge = ("Gemini understanding" if session.parse_source == "llm" else "Basic understanding")
    spk = sparkle(12, "spkf") if session.parse_source == "llm" else ""
    st.markdown(f'<div style="margin-bottom:10px"><span class="aibadge'
                f'{" basic" if session.parse_source != "llm" else ""}">{spk}{esc(badge)}</span></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="card-sub" style="margin-bottom:6px">What I understood — '
                'tap to correct</div>', unsafe_allow_html=True)
    cue_chips_ui(session, task_id)
    if st.session_state.get(f"confirm_img_{task_id}"):
        _confirm_dialog(task_id, session)
    elif st.session_state.get(f"anchor_img_{task_id}"):
        anchor_inline_ui(session, task_id, f"jog_state_{task_id}")
    else:
        this_or_that_ui(session, state, task_id)
        q = state.get("question")
        if q is None and not st.session_state.get(f"smart_q_done_{task_id}"):
            sq = _smart_question(state)
            if sq:
                q = sq
        if q:
            jog_question_ui(session, state, task_id)
        c1, c2 = st.columns([1, 1], vertical_alignment="center")
        with c1:
            if st.button("I'm stuck", key=f"jog_stuck_{task_id}", type="tertiary"):
                session.round = MAX_ROUNDS
                st.session_state[f"jog_state_{task_id}"] = session.state_summary()
                st.rerun()
        with c2:
            if st.button("Start over", key=f"jog_reset_{task_id}", type="tertiary"):
                st.session_state.pop("jog_" + task_id, None)
                st.session_state.pop("jog_state_" + task_id, None)
                st.rerun()


def _guided_moments_side(task_id, session, state):
    _conf_strip(state)
    jog_moments_ui(session, state, task_id,
                   confirm_handler=lambda iid: setattr_confirm(iid, task_id),
                   anchor_enabled=True)
    jog_fallback_ui(session, state, task_id)


def guided_flow_ui(task_id, session, state, split=False):
    if not split:
        _guided_conversation(task_id, session, state)
        _guided_moments_side(task_id, session, state)
        return
    with st.container(key="gsplit"):
        lc, rc = st.columns([1, 1.9], gap="large")
        with lc:
            _guided_conversation(task_id, session, state)
        with rc:
            _guided_moments_side(task_id, session, state)


def setattr_confirm(img_id, task_id):
    st.session_state[f"confirm_img_{task_id}"] = img_id
    st.session_state["confirm_task"] = task_id
    st.rerun()


def chip_label(text, limit=28):
    t = str(text).strip()
    if len(t) <= limit:
        return t
    cut = t[:limit]
    sp = cut.rfind(" ")
    if sp > 12:
        cut = cut[:sp]
    return cut + "…"


def _chip_prefill(text):
    st.session_state["guided_prefill"] = text
    st.session_state["guided_autostart"] = True


def guided_tab():
    st.markdown(f'<div class="gemini-head" style="margin-top:18px">{sparkle(24, "spkg")}'
                '<span class="gt">Gemini</span><span class="gt-sub">guided search</span></div>'
                '<div class="card-sub">Find a photo you half-remember — describe it, and '
                'we ask quick questions to narrow it down.</div>', unsafe_allow_html=True)
    if st.session_state.get("guided_autostart"):
        pre = st.session_state.pop("guided_prefill", "")
        st.session_state.pop("guided_autostart", None)
        _start_guided(pre, "free", "jog_free")
    session = st.session_state.get("jog_free")
    if st.session_state.get("jog_success_free"):
        _success_screen(st.session_state["jog_success_free"])
        return
    if session is not None:
        state = st.session_state.get("jog_state_free") or session.state_summary()
        st.session_state["jog_state_free"] = state
        guided_flow_ui("free", session, state, split=True)
        if st.button("Back to search", key="guided_back", type="tertiary"):
            st.session_state.pop("jog_free", None)
            st.session_state.pop("jog_state_free", None)
            st.rerun()
        return
    st.text_area("Describe the photo", key="guided_q_g", height=90,
                 placeholder="a café in Goa, daytime, coffee before the beach…",
                 label_visibility="collapsed")
    row = st.columns([2, 3])
    with row[0]:
        if st.button("Find it", type="primary", key="guided_go_g", use_container_width=True):
            _start_guided(st.session_state.get("guided_q_g", ""), "free", "jog_free")
    with row[1]:
        chips = BUNDLE["examples"][:3]
        ccols = st.columns(len(chips), gap="small")
        for ci, ex in enumerate(chips):
            with ccols[ci]:
                st.button(chip_label(ex), key=f"chipg_{ci}", type="tertiary",
                          use_container_width=True,
                          on_click=lambda t=ex: _chip_prefill(t))


# ---------------- main ----------------
def study_bar():
    st.markdown('<div class="mtop"><div class="gpb-word">' + pinwheel(24) +
                '<span style="font-size:19px;font-weight:500;margin-left:4px">Photos</span>'
                '</div></div>', unsafe_allow_html=True)


def footer():
    st.markdown(f'<div class="footer-note">{esc(note_text())}</div>', unsafe_allow_html=True)


def main():
    qp = st.query_params
    if st.session_state.get("nav_req"):
        st.session_state["tab"] = st.session_state.pop("nav_req")
        st.rerun()
    in_study = qp.get("test") == "1" or qp.get("admin") == "1"
    if in_study:
        study_bar()
    else:
        mobile_top()
        desktop_bar()
    if qp.get("admin") == "1":
        admin_screen()
        return
    if qp.get("test") == "1":
        test_mode()
        footer()
        return
    tab = st.session_state.get("tab", "photos")
    if tab == "photos":
        photos_tab()
    elif tab == "search":
        search_tab()
    elif tab == "guided":
        guided_tab()
    elif tab == "people":
        people_tab()
    elif tab == "settings":
        settings_tab()
    else:
        st.session_state["tab"] = "photos"
        photos_tab()
    footer()
    if not in_study:
        bottom_nav()


try:
    main()
except Exception as e:  # noqa: BLE001
    import traceback
    try:
        Path(__file__).resolve().parent.joinpath("logs_ui_error.txt").write_text(
            f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
    except Exception:
        pass
    st.error("Something went wrong in the demo. Please press Reset or reload.")
    st.caption(f"(technical note: {type(e).__name__}: {str(e)[:220]})")

# ============================================================
# PART 6: test mode + admin (contract-locked)
# ============================================================

# ---------------- test mode (?test=1) ----------------
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
            st.error("Time's up — let's move on.")
            return
        mins, secs = divmod(int(left), 60)
        st.caption(f"⏱ {mins}:{secs:02d} left")
    try:
        st.fragment(run_every="1s")(frag)
    except Exception:  # noqa: BLE001
        left = deadline - time.time()
        if left <= 0:
            st.session_state["task_timeout_" + task_id] = True
            st.session_state[running_key] = False
            st.error("Time's up — let's move on.")
        else:
            mins, secs = divmod(int(left), 60)
            st.caption(f"⏱ {mins}:{secs:02d} left")


def _end_task(item, outcome):
    t = item["task"]
    tid = t["id"]
    mode = item["mode"]
    seconds = 0
    dl = st.session_state.get(f"task_deadline_{tid}")
    if dl:
        seconds = int(max(0, time.time() - (dl - (PRACTICE_LIMIT_S if item["practice"] else TASK_LIMIT_S))))
    nq = st.session_state.get(f"task_queries_test_{tid}", 0) if mode == "jog" else \
        st.session_state.get(f"classic_queries_test_{tid}", 0)
    log_event(mode, f"test_{tid}", "task_end",
              {"outcome": outcome, "seconds": seconds, "n_queries": nq,
               "n_rounds": st.session_state.get("rounds_hint", 0)})
    st.session_state[f"task_result_{tid}"] = {"outcome": outcome, "seconds": seconds,
                                              "n_queries": nq}
    st.session_state["test_phase"] = "post"
    st.rerun()


def _test_confirm(item):
    img_id = st.session_state.get(f"confirm_img_test_{item['task']['id']}")
    if not img_id:
        return
    t = item["task"]
    with st.container(border=True):
        st.markdown('<div class="card-title">Is this the photo?</div>'
                    '<div class="card-sub">Your pick — say yes if it\'s right.</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="card-sub">{esc(caption_of(img_id) or "Your pick")} · '
                    f'{esc(date_of(img_id))}</div>', unsafe_allow_html=True)
        if img_id in META.index:
            try:
                sq(img_id)
            except Exception:  # noqa: BLE001
                pass
        yes, no = st.columns(2)
        with yes:
            if st.button("Yes", key=f"tcfm_yes_{t['id']}", type="primary", use_container_width=True):
                correct = img_id == t["target_img_id"]
                log_event(item["mode"], f"test_{t['id']}", "confirm_attempt",
                          {"img_id": img_id, "correct": correct})
                if correct:
                    st.session_state.pop(f"confirm_img_test_{t['id']}", None)
                    _end_task(item, "success")
                else:
                    wrong = st.session_state.get(f"task_wrong_{t['id']}", 0) + 1
                    st.session_state[f"task_wrong_{t['id']}"] = wrong
                    st.session_state.pop(f"confirm_img_test_{t['id']}", None)
                    if wrong >= 3:
                        _end_task(item, "fail")
                    else:
                        st.toast("Hmm, keep looking.")
                    st.rerun()
        with no:
            if st.button("No", key=f"tcfm_no_{t['id']}", use_container_width=True):
                st.session_state.pop(f"confirm_img_test_{t['id']}", None)
                st.rerun()


def classic_task_ui(item):
    t = item["task"]
    tid = f"test_{t['id']}"
    res = st.session_state.get(f"classic_res_{tid}")
    c1, c2 = st.columns([4, 1], vertical_alignment="center")
    with c1:
        st.text_input("Search your photos", key=f"classic_q_{tid}",
                      placeholder="a café in Goa, daytime, coffee", label_visibility="collapsed")
    with c2:
        if st.button("Search", key=f"classic_go_{tid}", type="primary", use_container_width=True):
            _classic_go(tid, f"classic_q_{tid}")
    if res is not None:
        log_event("classic", tid, "results_shown", {"img_ids": res["img_id"].tolist()})
        st.markdown('<div class="gpgrid">', unsafe_allow_html=True)
        cols = st.columns(4, gap="small")
        for i, (_, r) in enumerate(res.iterrows()):
            with cols[i % 4]:
                sq(r["img_id"])
                if st.button("This is it ✔", key=f"classic_confirm_{tid}_{r['img_id']}",
                             type="tertiary", use_container_width=True):
                    st.session_state[f"confirm_img_test_{t['id']}"] = r["img_id"]
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def jog_test_ui(item):
    t = item["task"]
    tid = f"test_{t['id']}"
    sess_key = f"jog_{tid}"
    session = st.session_state.get(sess_key)
    if session is None:
        with st.container(border=True):
            st.markdown('<div class="card-title">Your memory</div>'
                        '<div class="card-sub">Start from the task text, or add what you recall.</div>',
                        unsafe_allow_html=True)
            st.text_area("Your memory of the photo (start from the card if you like)",
                         value=t["fragment_text"], key="jog_test_membox", height=90)
            if st.button("Find it", type="primary", key=f"jog_find_{tid}"):
                text = st.session_state.get("jog_test_membox", t["fragment_text"]).strip()
                log_event("jog", tid, "dump_submitted", {"text": text})
                st.session_state[f"jog_text_{tid}"] = text
                with st.spinner("Narrowing…"):
                    sess = JogSession(BUNDLE["ret"], BUNDLE["meta"], BUNDLE["emb"])
                    state = sess.start(text, live_session=st.session_state.live_session)
                st.session_state[sess_key] = sess
                st.session_state[f"jog_state_{tid}"] = state
                st.session_state[f"task_queries_{tid}"] = 1
                log_event("jog", tid, "cues_parsed",
                          {"count": len(sess.cues), "parse_source": sess.parse_source})
                st.rerun()
        return
    st.session_state.setdefault(f"task_queries_{tid}", 1)
    state = st.session_state.get(f"jog_state_{tid}") or session.state_summary()
    st.session_state[f"jog_state_{tid}"] = state
    guided_flow_ui(tid, session, state)


def test_mode():
    st.markdown('<div class="gp-section-head" style="margin-top:14px;font-size:18px">'
                'Research session</div>', unsafe_allow_html=True)
    if st.session_state.get("test_done"):
        with st.container(border=True):
            st.markdown('<div class="card-title">Session complete</div>', unsafe_allow_html=True)
            st.success("Session complete — thank you!")
            st.download_button("Download my session log",
                               data=("\n".join(json.dumps(r, ensure_ascii=False)
                                               for r in LOG.read_session(st.session_state.session_id)) + "\n").encode(),
                               file_name=f"session_{st.session_state.session_id[:8]}.jsonl",
mime="application/jsonl", key="dl_mine")
        st.stop()
    if "test_queue" not in st.session_state:
        with st.container(border=True):
            st.markdown('<div class="card-title">Join the study</div>'
                        '<div class="card-sub">2 practice + 8 tasks · about 30 minutes</div>',
                        unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            code = c1.text_input("Your participant code (e.g. P1)", key="pcode")
            if c2.button("Start session", type="primary"):
                idx = participant_index(code)
                if idx is None or idx > 20:
                    st.error("Please enter a code like P1, P2 … P8.")
                    return
                st.session_state["participant"] = f"P{idx + 1}"
                st.session_state["test_queue"] = build_queue(idx)
                st.session_state["test_pos"] = 0
                st.session_state["test_phase"] = "card"
                log_event("test", "", "session_start",
                          {"queue": [(q["task"]["id"], q["mode"], q["practice"])
                                     for q in st.session_state["test_queue"]]})
                log_event("test", "", "live_status", {"mode": mode_label()})
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
    tag = "practice (not counted)" if item["practice"] else f"task {pos - 2 + 1} of 8"

    if phase == "card":
        with st.container(border=True):
            st.markdown(f'<div class="card-title">Task {esc(tid)}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="task-meta"><span class="tag blue">{esc(tag)}</span>'
                        f'<span class="tag gray">mode: {esc(mode.upper())}</span></div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="task-frag">{esc(t["fragment_text"])}</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-sub" style="margin-top:10px">'
                        f'{"1:00" if item["practice"] else "3:00"} · no feedback until the end.</div>',
                        unsafe_allow_html=True)
            if st.button("Start task", type="primary", key=f"tstart_{tid}"):
                limit = PRACTICE_LIMIT_S if item["practice"] else TASK_LIMIT_S
                st.session_state[f"task_deadline_{tid}"] = time.time() + limit
                st.session_state[f"task_running_{tid}"] = True
                st.session_state[f"task_wrong_{tid}"] = 0
                st.session_state["test_phase"] = "running"
                log_event(mode, tid, "task_start", {"limit_s": limit, "practice": item["practice"]})
                st.rerun()



    elif phase == "running":
        deadline = st.session_state[f"task_deadline_{tid}"]
        if (st.session_state.get(f"task_running_{tid}") and time.time() > deadline
                and not st.session_state.get(f"task_timeout_{tid}")):
            st.session_state[f"task_timeout_{tid}"] = True
            st.session_state[f"task_running_{tid}"] = False
            st.toast("Time's up — let's move on.")
        task_timer(tid, deadline, f"task_running_{tid}")
        if st.session_state.get(f"task_timeout_{tid}"):
            _end_task(item, "timeout")
            return
        if mode == "jog":
            jog_test_ui(item)
        else:
            classic_task_ui(item)
        if st.button("I give up", key=f"tgive_{tid}", type="tertiary"):
            _end_task(item, "give_up")
            return
        if st.session_state.get(f"confirm_img_test_{tid}"):
            _test_confirm(item)

    elif phase == "post":
        r = st.session_state[f"task_result_{tid}"]
        with st.container(border=True):
            st.markdown(f'<div class="card-title">Task {esc(tid)} finished</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="task-meta"><span class="tag green">{esc(r["outcome"])}</span>'
                        f'<span class="tag gray">{r["seconds"]}s · {r["n_queries"]} queries</span></div>',
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            conf = c1.selectbox("How sure are you that you picked the right photo? (1–5)",
                                list(range(1, 6)), key=f"tconf_{tid}")
            ease = c2.selectbox("How easy was this task? (1–7)", list(range(1, 8)), key=f"tease_{tid}")
            if st.button("Continue", type="primary", key=f"tcont_{tid}"):
                log_event(mode, tid, "post_task", {"confidence": conf, "ease": ease})
                st.session_state["test_phase"] = "card"
                st.session_state["test_pos"] += 1
                st.rerun()


def admin_screen():
    with st.container(border=True):
        st.markdown('<div class="card-title">Admin</div>', unsafe_allow_html=True)
        if st.button("Download all events (events.jsonl)", type="secondary"):
            st.download_button("Download events.jsonl",
                               data=("\n".join(json.dumps(r, ensure_ascii=False)
                                               for r in LOG.read_all()) + "\n").encode(),
                               file_name="events.jsonl", mime="application/jsonl")
        st.caption("Admin view — normal visitors do not see this.")
