import ast, shutil

P = "space_jog/app.py"
shutil.copy(P, P + ".bak_cssrescope")
src = open(P).read()
n_applied = 0

def rep(old, new, must_exist=True):
    global src, n_applied
    if old not in src:
        if new in src:
            print("SKIP (already applied):", old[:60].replace("\n", "\\n"))
            return
        if must_exist:
            raise SystemExit("NOT FOUND: " + old[:120].replace("\n", "\\n"))
        print("NOT FOUND (optional):", old[:60].replace("\n", "\\n"))
        return
    if src.count(old) != 1:
        raise SystemExit(f"NOT UNIQUE ({src.count(old)}x): " + old[:120].replace("\n", "\\n"))
    src = src.replace(old, new)
    n_applied += 1
    print("OK:", old[:60].replace("\n", "\\n"))

# R1: drop dead mtopmark desktop rule
rep('''@media (min-width:901px) { [data-testid="stVerticalBlock"]:has(span.mtopmark) { display:none !important; } }

/* ================= mobile top row (1.7) ================= */''',
'''/* ================= mobile top row (1.7) ================= */''')

# R2: pair radius -> keyed paircard substring
rep('''/* pair images radius */
[data-testid="stVerticalBlock"]:has(.spkpair) [data-testid="stImage"] img { border-radius:16px; }''',
'''/* pair images radius */
[class*="st-key-paircard_"] [data-testid="stImage"] img { border-radius:16px; }''')

# R3: success rules -> succcard
rep('''[data-testid="stVerticalBlock"]:has(.succ-meta) [data-testid="stImage"] { margin-bottom:4px; }
[data-testid="stVerticalBlock"]:has(.succ-meta) [data-testid="stImage"] img { border-radius:16px; }''',
'''.st-key-succcard [data-testid="stImage"] { margin-bottom:4px; }
.st-key-succcard [data-testid="stImage"] img { border-radius:16px; }''')

# R4: CELL_CSS -> keyed cell containers
rep('''CELL_CSS = """
/* photo grid cells (global, Phase 2.7) */
[data-testid="stVerticalBlock"]:has(.cellmk) { position:relative; aspect-ratio:1; border-radius:8px;
  overflow:hidden; background:var(--gp-fill); }
[data-testid="stVerticalBlock"]:has(.cellmk) [data-testid="stMarkdownContainer"] { padding:0; margin:0; }
[data-testid="stVerticalBlock"]:has(.cellmk) .cellmk { display:block; height:0; }
[data-testid="stVerticalBlock"]:has(.cellmk) [data-testid="stImage"] { position:absolute; inset:0; width:100%; height:100%; }
[data-testid="stVerticalBlock"]:has(.cellmk) [data-testid="stImage"] img { width:100%; height:100%;
  object-fit:cover; border-radius:8px; transition:filter .15s var(--gp-ease); }
[data-testid="stVerticalBlock"]:has(.cellmk) [data-testid="stImage"]:hover img { filter:brightness(1.05); }
[data-testid="stVerticalBlock"]:has(.cellmk) .stButton { position:absolute; inset:0; margin:0; z-index:4; }
[data-testid="stVerticalBlock"]:has(.cellmk) .stButton > button { opacity:0; border:none; }
"""''',
'''CELL_CSS = """
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
"""''')

# R5: icon_button -> keyed container
rep('''def icon_button(label, icon_name, key, on_click=None, c="#5f6368", s=22,
                title=None):
    st.markdown(f'<span class="ibmark_{key}"></span>', unsafe_allow_html=True)
    if on_click is not None:
        pressed = st.button(label, key=key, type="tertiary", on_click=on_click)
    else:
        pressed = st.button(label, key=key, type="tertiary")
    st.markdown(f'<style>'
                f'[data-testid="stVerticalBlock"]:has(.ibmark_{key}) .stButton > button '
                f'{{ width:{s + 18}px;height:{s + 18}px;min-height:{s + 18}px;padding:0;'
                f'border-radius:50%;background:transparent;box-shadow:none;font-size:0;'
                f'display:inline-flex;align-items:center;justify-content:center; }}'
                f'[data-testid="stVerticalBlock"]:has(.ibmark_{key}) .stButton > button:hover '
                f'{{ background:rgba(60,64,67,.08); }}'
                f'[data-testid="stVerticalBlock"]:has(.ibmark_{key}) .stButton > button::before '
                f'{{ content:"";width:{s}px;height:{s}px;display:block;'
                f'background:url("{svg_uri(icon_name, s, c)}") center/contain no-repeat; }}'
                f'</style>', unsafe_allow_html=True)
    return pressed''',
'''def icon_button(label, icon_name, key, on_click=None, c="#5f6368", s=22,
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
    return pressed''')

# R6: spark_button -> keyed container
rep('''def spark_button(key, on_click, s=22):
    gid = "spkbtn_" + key
    st.markdown(f'<span class="ibmark_{key}"></span>', unsafe_allow_html=True)
    st.button("Ask Gemini", key=key, type="tertiary", on_click=on_click)
    st.markdown(f'<style>'
                f'[data-testid="stVerticalBlock"]:has(.ibmark_{key}) .stButton > button {{'
                f'width:{s + 14}px;height:{s + 14}px;min-height:{s + 14}px;padding:0;border-radius:50%;'
                f'background:transparent;box-shadow:none;font-size:0;display:inline-flex;'
                f'align-items:center;justify-content:center;}}'
                f'[data-testid="stVerticalBlock"]:has(.ibmark_{key}) .stButton > button:hover {{'
                f'background:#e8f0fe;}}'
                f'[data-testid="stVerticalBlock"]:has(.ibmark_{key}) .stButton > button::before {{'
                f'content:"";width:{s}px;height:{s}px;display:block;'
                f'background:url("{svg_uri_sparkle(gid, s)}") center/contain no-repeat;}}'
                f'</style>', unsafe_allow_html=True)''',
'''def spark_button(key, on_click, s=22):
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
                f'</style>', unsafe_allow_html=True)''')

# R7: desktop bar Photos button -> keyed container
rep('''            with i1:
                st.markdown('<span class="pbwordmark"></span>', unsafe_allow_html=True)
                st.button("Photos", key="nav_d_home", type="tertiary",
                          on_click=lambda: _nav("photos"))
                st.markdown('<style>'
                            '[data-testid="stVerticalBlock"]:has(.pbwordmark) '
                            '[data-testid="stMarkdownContainer"]{padding:0;margin:0;}'
                            '[data-testid="stVerticalBlock"]:has(.pbwordmark) .stButton > button {'
                            'font-size:22px !important;font-weight:500 !important;'
                            'color:#202124 !important;padding:2px 12px;min-height:44px;}'
                            '</style>', unsafe_allow_html=True)''',
'''            with i1:
                with st.container(key="pbword"):
                    st.button("Photos", key="nav_d_home", type="tertiary",
                              on_click=lambda: _nav("photos"))
                st.markdown('<style>'
                            '.st-key-pbword { padding:0; margin:0; }'
                            '.st-key-pbword .stButton { margin:0; padding:0; }'
                            '.st-key-pbword .stButton > button {'
                            'font-size:22px !important;font-weight:500 !important;'
                            'color:#202124 !important;padding:2px 12px;min-height:44px;}'
                            '</style>', unsafe_allow_html=True)''')

# R8: mobile top zero column paddings
rep('''        st.markdown('<style>'
                    '.st-key-mtop [data-testid="stMarkdownContainer"] { padding:0; margin:0; }'
                    '</style>', unsafe_allow_html=True)''',
'''        st.markdown('<style>'
                    '.st-key-mtop [data-testid="stVerticalBlock"] { padding:0; margin:0; }'
                    '</style>', unsafe_allow_html=True)''')

# R9a: lightbox lbmark span
rep('''    st.markdown('<span class="lbmark"></span>', unsafe_allow_html=True)
    st.markdown(f''' + "'''" + '''<div class="lb-overlay">''',
    '''    st.markdown(f''' + "'''" + '''<div class="lb-overlay">''')

# R9b: lightbox lbmark rule (derived from live src to avoid quoting drift)
_i = src.find(":has(.lbmark)")
assert _i > 0, "lbmark rule not found"
_j = src.rfind("\n", 0, _i) + 1
_k = src.find("\n", src.find("overflow:hidden; }", _i)) + 1
rep(src[_j:_k], "")
# R10: _photo_cell -> keyed cell container
rep('''def _photo_cell(img_id, key_prefix, lightbox_ids, lightbox_idx):
    st.markdown('<span class="cellmk"></span>', unsafe_allow_html=True)
    p = img_path(img_id)
    if p.exists():
        st.image(str(p), use_container_width=True)
    st.button(f"Open photo from {date_of(img_id)}", key=f"lbopen_{key_prefix}",
              use_container_width=True,
              on_click=lambda: _open_lightbox(lightbox_ids, lightbox_idx))''',
'''def _photo_cell(img_id, key_prefix, lightbox_ids, lightbox_idx):
    with st.container(key=f"cell_{key_prefix}"):
        p = img_path(img_id)
        if p.exists():
            st.image(str(p), use_container_width=True)
        st.button(f"Open photo from {date_of(img_id)}", key=f"lbopen_{key_prefix}",
                  use_container_width=True,
                  on_click=lambda: _open_lightbox(lightbox_ids, lightbox_idx))''')

# R11: _photo_grid_rows -> mgrid container
rep('''def _photo_grid_rows(ids, key_prefix, limit=None):
    shown = ids if limit is None else ids[:limit]
    ncols = 6
    if not shown:
        return
    cols = st.columns(ncols, gap="small")
    for i, iid in enumerate(shown):
        with cols[i % ncols]:
            _photo_cell(iid, f"{key_prefix}_{iid}", ids, i)''',
'''def _photo_grid_rows(ids, key_prefix, limit=None):
    shown = ids if limit is None else ids[:limit]
    ncols = 6
    if not shown:
        return
    with st.container(key=f"mgrid_{key_prefix}"):
        cols = st.columns(ncols, gap="small")
        for i, iid in enumerate(shown):
            with cols[i % ncols]:
                _photo_cell(iid, f"{key_prefix}_{iid}", ids, i)''')

# R12a: onboarding container key + drop span
rep('''    with st.container(border=True):
        st.markdown('<span class="onbmark"></span>', unsafe_allow_html=True)
        st.markdown(f'<div class="onb-head">{sparkle(18, "spkonb")}<span>Which one is you?</span></div>', unsafe_allow_html=True)''',
'''    with st.container(border=True, key=f"onbcard_{key_prefix}"):
        st.markdown(f'<div class="onb-head">{sparkle(18, "spkonb")}<span>Which one is you?</span></div>', unsafe_allow_html=True)''')

# R12b: onboarding rules
rep('''        st.markdown('<style>'
                    '[data-testid="stVerticalBlock"]:has(.onbmark) [data-testid="stImage"] img { border-radius:50%; }'
                    '[data-testid="stVerticalBlock"]:has(.onbmark) [data-testid="stImage"] { margin:0 auto; }'
                    '</style>', unsafe_allow_html=True)''',
'''        st.markdown(f'<style>'
                    f'.st-key-onbcard_{key_prefix} [data-testid="stImage"] img {{ border-radius:50%; }}'
                    f'.st-key-onbcard_{key_prefix} [data-testid="stImage"] {{ margin:0 auto; }}'
                    '</style>', unsafe_allow_html=True)''')

# R13: _memory_card
rep('''def _memory_card(m, i):
    mk = f"memmk_{i}"
    p = img_path(m["img"])
    sub = f"{m['sub']} · {m['count']} photos" if m["sub"] else f"{m['count']} photos"
    st.markdown(f'<span class="{mk}"></span>', unsafe_allow_html=True)
    if p.exists():
        st.image(str(p), use_container_width=True)
    st.markdown(f'<div class="memover"><span class="mchip">Memory</span>'
                f'<span class="mtitle">{esc(m["title"])}</span>'
                f'<span class="mdate">{esc(sub)}</span></div>', unsafe_allow_html=True)
    st.button(m["title"], key=f"mem_{m['kind']}_{m['val']}", use_container_width=True)
    st.markdown(f'<style>'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stMarkdownContainer"] {{ padding:0; margin:0; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .{mk} {{ display:block; height:0; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) {{ position:relative; aspect-ratio:16/9; '
                f'border-radius:16px; overflow:hidden; background:#111; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stImage"] {{ position:absolute; inset:0; width:100%; height:100%; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stImage"] img {{ width:100%; height:100%; object-fit:cover; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .memover {{ position:absolute; inset:0; pointer-events:none; z-index:3; '
                f'display:flex; flex-direction:column; justify-content:flex-end; padding:12px 14px; background:linear-gradient(180deg,rgba(0,0,0,0) 45%,rgba(0,0,0,.55) 100%); }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .mchip {{ position:absolute; top:10px; left:10px; background:rgba(0,0,0,.55); '
                f'color:#fff; font-size:11px; font-weight:500; border-radius:999px; padding:3px 9px; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .mtitle {{ color:#fff; font-size:15.5px; font-weight:500; line-height:1.25; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .mdate {{ color:rgba(255,255,255,.78); font-size:12px; margin-top:2px; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .stButton {{ position:absolute; inset:0; margin:0; z-index:4; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .stButton > button {{ opacity:0; border:none; }}'
                f'</style>', unsafe_allow_html=True)''',
'''def _memory_card(m, i):
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
                    f'</style>', unsafe_allow_html=True)''')

# R14: _person_card
rep('''def _person_card(p, i, prefix="home"):
    mk = f"pcmk_{prefix}_{i}"
    you = p["id"] == st.session_state.get("you_person")
    lab = "You" if you else p["label"]
    st.markdown(f'<span class="{mk}"></span>', unsafe_allow_html=True)
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
                f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stImage"] {{ margin:0 auto; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stImage"] img {{ border-radius:50%; '
                f'object-fit:cover; box-shadow:0 0 0 2px #fff, var(--gp-shadow-rest); }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .pc-name {{ font-size:13.5px; font-weight:500; text-align:center; margin-top:6px; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .pc-cnt {{ font-size:12px; color:var(--gp-secondary); text-align:center; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .stButton {{ position:absolute; inset:-4px; margin:0; z-index:5; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}) .stButton > button {{ opacity:0; border:none; background:transparent; '
                f'border-radius:16px; }}'
                f'[data-testid="stVerticalBlock"]:has(.{mk}):hover {{ box-shadow:var(--gp-shadow-hover); border-radius:16px; }}'
                f'</style>', unsafe_allow_html=True)''',
'''def _person_card(p, i, prefix="home"):
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
                    f'</style>', unsafe_allow_html=True)''')

# R15: people tab pcmk_ptab rule (delete)
rep('''        st.markdown('<style>'
                    '[data-testid="stVerticalBlock"]:has(.pcmk_ptab) { min-width:88px; }'
                    '</style>', unsafe_allow_html=True)
    _lightbox_render()''',
'''    _lightbox_render()''')

# R16: _search_bar_free
rep('''def _search_bar_free():
    row = st.columns([5, 0.6, 1.0], vertical_alignment="center", gap="small")
    with row[0]:
        with st.container():
            st.markdown('<span class="searchpillmark"></span>', unsafe_allow_html=True)
            st.text_input("Search your photos", key="search_q",
                          placeholder="Search for a person, place, or thing",
                          label_visibility="collapsed")
    with row[1]:
        st.markdown('<span class="micmark micmark_free"></span>', unsafe_allow_html=True)
        if st.button("Voice search", key="mic_free", type="tertiary", use_container_width=True):
            st.session_state["mic_req"] = True
            st.session_state["mic_target"] = "search"
    with row[2]:
        if st.button("Search", key="classic_go_free", type="primary", use_container_width=True):
            _classic_go("free_classic", "search_q")''',
'''def _search_bar_free():
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
                _classic_go("free_classic", "search_q")''')

# R16b: _search_bar_free CSS
rep('''    st.markdown('<style>'
                '[data-testid="stVerticalBlock"]:has(.micmark_free) .stButton > button {'
                'display:flex;align-items:center;justify-content:center;gap:8px;}'
                '[data-testid="stVerticalBlock"]:has(.micmark_free) .stButton > button::before {'
                'content:"";width:20px;height:20px;flex:none;opacity:.62;'
                'background:url("' + svg_uri("mic", 20, "#5f6368") + '") center/contain no-repeat;}'
                '[data-testid="stVerticalBlock"]:has(span.searchpillmark) .stTextInput {'
                'position:relative;margin:0;}'
                '[data-testid="stVerticalBlock"]:has(span.searchpillmark) .stTextInput::before {'
                'content:"";position:absolute;left:17px;top:50%;transform:translateY(-50%);'
                'width:20px;height:20px;pointer-events:none;opacity:.55;'
                'background:url("' + svg_uri("search", 20, "#5f6368") + '") center/contain no-repeat;}'
                '[data-testid="stVerticalBlock"]:has(span.searchpillmark) .stTextInput input {'
                'border:1px solid #dadce0 !important;border-radius:999px !important;height:56px;'
                'font-size:15.5px;padding:0 18px 0 48px !important;box-shadow:none !important;}'
                '[data-testid="stVerticalBlock"]:has(span.searchpillmark) .stTextInput input:focus {'
                'border-color:#1a73e8 !important;box-shadow:0 0 0 3px #e8f0fe !important;}'
                '@media (max-width:700px) {'
                '[data-testid="stHorizontalBlock"]:has(span.searchpillmark) {'
                'flex-direction:column;align-items:stretch;gap:8px;}'
                '[data-testid="stHorizontalBlock"]:has(span.searchpillmark) > [data-testid="stVerticalBlock"] {'
                'width:100% !important;flex:0 0 auto !important;}'
                '[data-testid="stHorizontalBlock"]:has(span.searchpillmark) .stButton > button {'
                'width:100%;min-height:48px;}'
                '}'
                '</style>', unsafe_allow_html=True)''',
'''    st.markdown('<style>'
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
                '</style>', unsafe_allow_html=True)''')

# R17: grouped-results people chips
rep('''        for c, (p, n, qm), i in zip(cols, people, range(len(people))):
            with c:
                mk = f"sppmk_{i}"
                lab = person_label(p["id"])
                st.markdown(f'<span class="{mk}"></span>', unsafe_allow_html=True)
                av = person_avatar(p["id"])
                if av:
                    st.image(av, width=56)
                st.markdown(f'<div class="pc-name">{esc(lab)}</div>', unsafe_allow_html=True)
                if st.button(lab, key=f"grp_pp_{p['id']}", use_container_width=True):
                    st.session_state["person_filter"] = {"kind": "person", "val": p["id"],
                                                         "title": f"{lab} · {n} in results"}
                    st.session_state["tab"] = "photos"
                    st.rerun()
                st.markdown(f'<style>'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) {{ position:relative; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stImage"] {{ margin:0 auto; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stImage"] img {{ border-radius:50%; object-fit:cover; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) .stButton {{ position:absolute; inset:-4px; margin:0; z-index:5; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) .stButton > button {{ opacity:0; border:none; background:transparent; }}'
                            f'</style>', unsafe_allow_html=True)''',
'''        for c, (p, n, qm), i in zip(cols, people, range(len(people))):
            with c:
                lab = person_label(p["id"])
                with st.container(key=f"sppcard_{i}"):
                    av = person_avatar(p["id"])
                    if av:
                        st.image(av, width=56)
                    st.markdown(f'<div class="pc-name">{esc(lab)}</div>', unsafe_allow_html=True)
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
                                f'</style>', unsafe_allow_html=True)''')

# R18: grouped-results scene cards
rep('''        for c, sc, i in zip(cols, scenes, range(len(scenes))):
            with c:
                mk = f"scmk_{i}"
                p = img_path(sc["hero"])
                st.markdown(f'<span class="{mk}"></span>', unsafe_allow_html=True)
                if p.exists():
                    st.image(str(p), use_container_width=True)
                st.markdown(f'<div class="sc-t">{esc(sc["title"])}</div>'
                            f'<div class="sc-c">{sc["n"]} photos</div>',
                            unsafe_allow_html=True)
                if st.button(sc["title"], key=f"grp_sc_{sc['eid']}", use_container_width=True):
                    _go_event(sc["eid"])
                st.markdown(f'<style>'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) {{ position:relative; border-radius:12px; overflow:hidden; background:#fff; border:1px solid var(--gp-hairline); }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stMarkdownContainer"] {{ padding:0; margin:0; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) .scmk_{i} {{ display:block; height:0; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stImage"] {{ aspect-ratio:16/10; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stImage"] img {{ object-fit:cover; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) .sc-t {{ font-size:12.5px; font-weight:500; padding:7px 9px 1px; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) .sc-c {{ font-size:11.5px; color:var(--gp-secondary); padding:0 9px 8px; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) .stButton {{ position:absolute; inset:0; margin:0; z-index:5; }}'
                            f'[data-testid="stVerticalBlock"]:has(.{mk}) .stButton > button {{ opacity:0; border:none; }}'
                            f'</style>', unsafe_allow_html=True)''',
'''        for c, sc, i in zip(cols, scenes, range(len(scenes))):
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
                                f'</style>', unsafe_allow_html=True)''')

# R19a: moment card container key + drop span
rep('''    for mi, m in enumerate(state["moments"]):
        mk = f"momk_{task_id}_{mi}"
        cover = m["img_ids"][0]
        with st.container(border=True):
            st.markdown(f'<span class="{mk}"></span>', unsafe_allow_html=True)''',
'''    for mi, m in enumerate(state["moments"]):
        cover = m["img_ids"][0]
        with st.container(border=True, key=f"mcard_{task_id}_{mi}"):''')

# R19b: moment card CSS
rep('''            st.markdown('<style>'
                        f'[data-testid="stVerticalBlock"]:has(.{mk}) [data-testid="stMarkdownContainer"] {{ padding:0 2px; }}'
                        f'[data-testid="stVerticalBlock"]:has(.{mk}) .mcover {{ position:relative; aspect-ratio:16/9; border-radius:12px; overflow:hidden; background:#111; margin:4px 0 12px; }}'
                        f'[data-testid="stVerticalBlock"]:has(.{mk}) .mcover img.main {{ width:100%; height:100%; object-fit:cover; display:block; }}'
                        f'[data-testid="stVerticalBlock"]:has(.{mk}) .mover {{ position:absolute; right:10px; bottom:-16px; display:flex; }}'
                        f'[data-testid="stVerticalBlock"]:has(.{mk}) .mover img {{ width:42px; height:42px; object-fit:cover; border-radius:8px; border:2px solid #fff; margin-left:-14px; box-shadow:var(--gp-shadow-rest); }}'
                        f'[data-testid="stVerticalBlock"]:has(.{mk}) .mhead {{ display:flex; align-items:baseline; gap:8px; }}'
                        f'[data-testid="stVerticalBlock"]:has(.{mk}) .mlab {{ font-size:15px; font-weight:500; }}'
                        f'[data-testid="stVerticalBlock"]:has(.{mk}) .mcnt {{ font-size:12.5px; color:var(--gp-secondary); }}'
                        f'[data-testid="stVerticalBlock"]:has(.{mk}) .mwhy {{ font-size:12px; color:var(--gp-secondary); margin-top:4px; }}'
                        f'</style>', unsafe_allow_html=True)''',
'''            st.markdown(f'<style>'
                        f'.st-key-mcard_{task_id}_{mi} [data-testid="stMarkdownContainer"] {{ padding:0 2px; }}'
                        f'.st-key-mcard_{task_id}_{mi} .mcover {{ position:relative; aspect-ratio:16/9; border-radius:12px; overflow:hidden; background:#111; margin:4px 0 12px; }}'
                        f'.st-key-mcard_{task_id}_{mi} .mcover img.main {{ width:100%; height:100%; object-fit:cover; display:block; }}'
                        f'.st-key-mcard_{task_id}_{mi} .mover {{ position:absolute; right:10px; bottom:-16px; display:flex; }}'
                        f'.st-key-mcard_{task_id}_{mi} .mover img {{ width:42px; height:42px; object-fit:cover; border-radius:8px; border:2px solid #fff; margin-left:-14px; box-shadow:var(--gp-shadow-rest); }}'
                        f'.st-key-mcard_{task_id}_{mi} .mhead {{ display:flex; align-items:baseline; gap:8px; }}'
                        f'.st-key-mcard_{task_id}_{mi} .mlab {{ font-size:15px; font-weight:500; }}'
                        f'.st-key-mcard_{task_id}_{mi} .mcnt {{ font-size:12.5px; color:var(--gp-secondary); }}'
                        f'.st-key-mcard_{task_id}_{mi} .mwhy {{ font-size:12px; color:var(--gp-secondary); margin-top:4px; }}'
                        f'</style>', unsafe_allow_html=True)''')

# R20a: pair card container key (derived + index splice)
_i = src.find('pair_shown", {"left": pair["left"], "right": pair["right"]})')
assert _i > 0, "pair_shown not found"
_j = src.find("with st.container(border=True):", _i)
_oldc = "with st.container(border=True):"
src = src[:_j] + 'with st.container(border=True, key=f"paircard_{task_id}"): ' + src[_j + len(_oldc):]
n_applied += 1
print("OK: R20a pair card container key")
# R20b: pair card garbage style (delete)
rep('''        st.markdown('<style>[data-testid="stVerticalBlock"]:has(.spkpair) [data-testid="stImage"] img,'
                    '[data-testid="stImage"]:not(.lb) {} .pairimg img { border-radius:16px; }</style>',
                    unsafe_allow_html=True)
''', '')

# R21: success screen container key
rep('''def _success_screen(s):
    with st.container(border=True):
        img_id = s.get("confirmed") or s.get("img_id")''',
'''def _success_screen(s):
    with st.container(border=True, key="succcard"):
        img_id = s.get("confirmed") or s.get("img_id")''')

ast.parse(src)
open(P, "w").write(src)
print(f"PATCHED {n_applied} blocks; ast OK")
