"use strict";
let D = null;
const $ = (id) => document.getElementById(id);
const GATE_COLORS = {
  expression: "#0072B2", interpretation: "#E69F00", evaluation: "#009E73",
  refinement: "#D55E00", persistence: "#CC79A7",
  not_search_related: "#999999", unclear: "#56B4E9"
};
const SCORED_GATES = ["expression", "interpretation", "evaluation", "refinement", "persistence"];
const GATE_SHORT = {
  expression: "expression", interpretation: "interpretation", evaluation: "evaluation",
  refinement: "refinement", persistence: "persistence",
  not_search_related: "not search-related", unclear: "unclear"
};
const ERA_NAMES = { pre_ask: "pre Ask Photos (< 2024-10)", early_access: "early access (Oct 2024 – May 2025)", wider_rollout: "wider rollout (≥ Jun 2025)" };
const ERA_KEYS = ["era_pre_ask", "era_early_access", "era_wider_rollout"];
const FIGS = [
  ["F1_gate_distribution", "Failure-gate distribution", "Share of scored episodes per gate, Wilson 95% CI whiskers; second panel by era."],
  ["F2_remembered_vs_missing", "Remembered vs missing cues", "Per cue type: share of remembered cues vs share of explicitly missing cues."],
  ["F3_phototype_gate_heatmap", "Photo type × failure gate", "Counts of episodes per photo type and gate."],
  ["F4_query_styles_and_workarounds", "Query styles & workarounds", "How users search, and what they do after search fails."],
  ["F5_mechanism_clusters", "Failure-mechanism clusters", "Clusters of failure_mechanism text (MiniLM embeddings, KMeans)."],
  ["F6_scorecard_top10", "Scorecard top cells", "Opportunity score = 100·(0.35·freq + 0.25·sev + 0.20·gap + 0.20·lev)."]
];

/* ---------- helpers ---------- */
function esc(s) { return String(s == null ? "" : s).replace(/&/g, "\u0026amp;").replace(/</g, "\u0026lt;").replace(/>/g, "\u0026gt;").replace(/"/g, "\u0026quot;").replace(/'/g, "\u0026#39;"); }
function fmt(n) { return Number(n).toLocaleString("en-US"); }
function rgba(hex, a) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}
function gateStyle(g) {
  const c = GATE_COLORS[g] || "#999999";
  return `--gc:${c};--gc-soft:${rgba(c, 0.11)};--gc-line:${rgba(c, 0.35)}`;
}
function gateBadge(g) {
  if (!g) return '<span class="badge dim">—</span>';
  return `<span class="badge gate" style="${gateStyle(g)}">${esc(GATE_SHORT[g] || g)}</span>`;
}
function sourceBadge(s) { return s ? `<span class="badge src-${esc(s)}">${esc(s)}</span>` : '<span class="badge dim">—</span>'; }
function outcomeBadge(o) {
  if (!o) return '<span class="badge dim">—</span>';
  const cls = { found: "out-found", partly_found: "out-partly_found", not_found: "out-not_found" }[o] || "out-unknown";
  return `<span class="badge ${cls}">${esc(o)}</span>`;
}
function trunc(s, n) { s = String(s == null ? "" : s); return s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s; }

/* ---------- load / init ---------- */
function load() {
  return fetch("data.json", { cache: "no-cache" }).then(r => {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }).then(d => { D = d; init(); });
}

function init() {
  document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
    document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
    document.querySelectorAll("main > section.tabpanel").forEach(s => s.classList.remove("show"));
    t.classList.add("active");
    $("tab-" + t.dataset.tab).classList.add("show");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  drawHeader();
  drawPipeline();
  drawFooter();
  $("presets").innerHTML = Object.keys(D.cached_answers).map((q, i) =>
    `<button class="preset-btn" onclick="askPreset(${i})"><span class="pnum">${i + 1}</span><span class="ptxt">${esc(q)}</span><span class="parrow">→</span></button>`).join("");
  fillFilters();
  drawGateCard();
  drawCues();
  drawQWork();
  drawFigs();
  drawEpisodes();
  drawScore();
  $("tryit").addEventListener("input", () => { $("tryit-count").textContent = $("tryit").value.length + " / 1200"; });
}

function drawHeader() {
  const c = D.counts;
  const total = c.n_play + c.n_appstore + c.n_reddit;
  $("n-line").textContent = `${fmt(c.n_episodes)} retrieval episodes · n on every chart`;
  $("lede").innerHTML =
    `An interactive evidence base for <b>why old-photo search fails</b>: <b>${fmt(c.n_episodes)}</b> structured retrieval episodes mined from ` +
    `<b>${fmt(total)}</b> public Google Photos feedback documents (${fmt(c.n_play)} Play Store, ${fmt(c.n_appstore)} App Store, ${fmt(c.n_reddit)} Reddit), ` +
    `screened and extracted by an open model running on a personal computer. ` +
    `Start with a preset question, or explore the charts — every chart shows <b>n</b>, every number is computed by code.`;
}

function drawPipeline() {
  const c = D.counts;
  const steps = [
    ["Collected", c.n_play + c.n_appstore + c.n_reddit, `Play ${fmt(c.n_play)} · App Store ${fmt(c.n_appstore)} · Reddit ${fmt(c.n_reddit)}`],
    ["Cleaned", c.n_clean, "deduped, English, ≥ 8 words"],
    ["Screened", c.n_for_llm, `${fmt(c.n_kw_hit)} keyword hits + 10% control sample`],
    ["Relevant", c.n_relevant, "stage-1 model screen"],
    ["Episodes", c.n_episodes, "structured retrieval episodes"]
  ];
  $("pipeline").innerHTML = steps.map(([l, n, sub], i) =>
    `<li class="${i === steps.length - 1 ? "final" : ""}"><div class="p-n">${fmt(n)}</div><div class="p-l">${l}</div><div class="p-s">${sub}</div></li>` +
    (i < steps.length - 1 ? '<li class="p-arrow" aria-hidden="true">→</li>' : "")
  ).join("");
}

function drawFooter() {
  const c = D.counts, v = D.validation;
  $("pipeline-line").innerHTML =
    `Collect ${fmt(c.n_play + c.n_appstore + c.n_reddit)} docs → clean ${fmt(c.n_clean)} → prefilter ${fmt(c.n_kw_hit)} → screen ${fmt(c.n_for_llm)} → ` +
    `relevant ${fmt(c.n_relevant)} → <b>${fmt(c.n_episodes)} of ${fmt(c.n_extracted_attempted)}</b> extracted as episodes. ` +
    `Keyword-filter recall estimate ${(c.kw_recall_est * 100).toFixed(0)}%.`;
  const f = v.fields;
  $("val-rows").innerHTML = [
    ["is_retrieval", f.is_retrieval], ["photo_type", f.photo_type],
    ["failure_gate", f.failure_gate], ["outcome", f.outcome]
  ].map(([k, r]) => `<div class="val-row"><span>${esc(k)}</span><b>${r.accuracy_pct}% acc · κ ${r.kappa}</b></div>`).join("");
  $("pass2").textContent = (v.model_pass2_gate_agreement != null ? (v.model_pass2_gate_agreement * 100).toFixed(1) : "—") + "%";
  $("quote-pct").textContent = (c.quote_verified_pct != null ? c.quote_verified_pct + "%" : "—");
  $("src-list").innerHTML = [
    `Play Store reviews — n=${fmt(c.n_play)}`,
    `App Store reviews — n=${fmt(c.n_appstore)}`,
    `Reddit (r/GooglePhotos, r/google, r/GooglePixel, r/Android, r/androidapps) — n=${fmt(c.n_reddit)}`
  ].map(s => `<li>${s}</li>`).join("");
  $("foot-line").textContent = `Built for the photo-retrieval case study · data generated ${esc(D.generated)} · no personal information needed; do not paste personal information into the demo fields.`;
}

/* ---------- gate card ---------- */
function barRow(lbl, n, share, ciLo, ciHi, color, extra) {
  const w = Math.max(share, 1.2);
  let ci = "";
  if (ciLo != null && ciHi != null && ciHi > ciLo) {
    ci = `<span class="b-ci" style="left:${Math.min(ciLo, 100)}%;width:${Math.min(Math.max(ciHi - ciLo, 0.6), 100 - ciLo)}%"></span>`;
  }
  return `<div class="bar-row" title="${esc(lbl)}: n=${n}, ${share}% (95% CI ${ciLo ?? "?"}–${ciHi ?? "?"})">
    <div class="b-lbl">${esc(lbl)}</div>
    <div class="b-track">${ci}<span class="b-fill" style="width:${w}%;background:${color}"></span></div>
    <div class="b-val"><b>${share}%</b> · n=${n}${ciLo != null ? ` · ${ciLo}–${ciHi}` : ""}${extra || ""}</div>
  </div>`;
}

function drawGateCard() {
  const t1 = D.t1;
  const overall = t1.filter(r => r.scope === "overall" && r.gate);
  const denom = (overall.find(r => r.gate === "interpretation") || {}).denom_n ?? null;
  const scored = overall.filter(r => SCORED_GATES.includes(r.gate));
  const excluded = overall.filter(r => !SCORED_GATES.includes(r.gate));
  const exclN = excluded.reduce((a, r) => a + r.n, 0);
  $("gate-sub").innerHTML = `n=${denom != null ? fmt(denom) : "?"} episodes with a gate · chart shows scored gates (n=${fmt(scored.reduce((a, r) => a + r.n, 0))})`;
  $("gate-excluded").innerHTML =
    `Excluded from the chart: ${excluded.map(r => `<b>${esc(GATE_SHORT[r.gate])}</b> ${r.share_pct}% (n=${r.n})`).join(" · ")} — ` +
    `source: T1_gate_distribution.csv, Wilson 95% CI shown as the light band on each bar.`;
  $("gate-legend").innerHTML = SCORED_GATES.map(g =>
    `<span><i style="background:${GATE_COLORS[g]}"></i>${GATE_SHORT[g]}</span>`).join("");
  $("gate-bars").innerHTML = scored.sort((a, b) => b.n - a.n)
    .map(r => barRow(GATE_SHORT[r.gate], r.n, r.share_pct, r.ci_lo, r.ci_hi, GATE_COLORS[r.gate])).join("");
  // stacked bars by era
  $("gate-era").innerHTML = ERA_KEYS.map(sc => {
    const rows = t1.filter(r => r.scope === sc && SCORED_GATES.includes(r.gate));
    const dn = rows.length ? rows[0].denom_n : 0;
    const segs = rows.map(r => {
      const c = GATE_COLORS[r.gate];
      return `<i style="width:${Math.max(r.share_pct, 0.5)}%;background:${c}" title="${GATE_SHORT[r.gate]}: ${r.share_pct}% (n=${r.n})"></i>`;
    }).join("");
    return `<div class="era-row"><div class="era-lbl"><b>${esc(ERA_NAMES[sc.replace("era_", "")]) || esc(sc)}</b><span>denom n=${fmt(dn)}</span></div><div class="stackbar">${segs}</div></div>`;
  }).join("");
}

/* ---------- cue matrix ---------- */
function drawCues() {
  const rows = (D.t2 || []).slice().sort((a, b) => (b.pct_remembered || 0) + (b.pct_missing || 0) - ((a.pct_remembered || 0) + (a.pct_missing || 0)));
  const maxPct = Math.max(1, ...rows.map(r => Math.max(r.pct_remembered || 0, r.pct_missing || 0)));
  $("cue-rows").innerHTML = rows.map(r => {
    const pr = (r.pct_remembered || 0), pm = (r.pct_missing || 0);
    const ratio = r.ratio_missing_over_remembered != null ? ` · missing/remembered ${(+r.ratio_missing_over_remembered).toFixed(2)}` : "";
    return `<div class="cue-row" title="${esc(r.cue_type)}: remembered ${pr}% (n=${r.n_remembered}), missing ${pm}% (n=${r.n_missing})">
      <div class="cue-lbl">${esc(r.cue_type)}</div>
      <div class="cue-track"><div class="ct"><i style="width:${Math.max(pr / maxPct * 100, 1.5)}%;background:#4f46e5"></i></div><span class="cv">${pr}% · n=${r.n_remembered}</span></div>
      <div class="cue-track"><div class="ct"><i style="width:${Math.max(pm / maxPct * 100, 1.5)}%;background:#E69F00"></i></div><span class="cv">${pm}% · n=${r.n_missing}${ratio}</span></div>
    </div>`;
  }).join("");
}

/* ---------- query style / workarounds ---------- */
function drawQWork() {
  const t4o = D.t4.filter(r => r.scope === "overall");
  const t5o = D.t5.filter(r => r.scope === "overall");
  const dn = t4o.length ? t4o[0].denom_n : null;
  $("qstyle-sub").textContent = `Query style across episodes (denom n=${dn != null ? fmt(dn) : "?"})`;
  $("work-sub").textContent = `Workaround after a failed retrieval (denom n=${dn != null ? fmt(dn) : "?"})`;
  const indigo = "#6366f1", violet = "#8b5cf6";
  $("qstyle-bars").innerHTML = t4o.sort((a, b) => b.n - a.n)
    .map(r => barRow(String(r.query_style), r.n, r.share_pct, r.ci_lo, r.ci_hi, indigo)).join("");
  $("work-bars").innerHTML = t5o.sort((a, b) => b.n - a.n)
    .map(r => barRow(String(r.workaround), r.n, r.share_pct, r.ci_lo, r.ci_hi, violet)).join("");
}

/* ---------- figures ---------- */
function drawFigs() {
  $("figs").innerHTML = FIGS.map(([f, title, cap]) =>
    `<a class="fig" href="figures/${f}.png" target="_blank" rel="noopener">
       <img src="figures/${f}.png" alt="${esc(title)}" loading="lazy">
       <div class="fig-cap"><b>${esc(title)}</b>${esc(cap)}</div>
     </a>`).join("");
}

/* ---------- episodes table ---------- */
let epPage = 0;
const EP_PER = 25;
function fillFilters() {
  const uniq = (k) => [...new Set(D.episodes.map(e => e[k]).filter(Boolean))].sort();
  $("f-source").innerHTML += uniq("source").map(s => `<option>${esc(s)}</option>`).join("");
  $("f-era").innerHTML += uniq("era").map(s => `<option>${esc(s)}</option>`).join("");
  $("f-gate").innerHTML += uniq("gate").map(s => `<option>${esc(s)}</option>`).join("");
}
function epFiltered() {
  const q = ($("epsearch").value || "").toLowerCase();
  const fs = $("f-source").value, fe = $("f-era").value, fg = $("f-gate").value;
  return D.episodes.filter(e =>
    (!fs || e.source === fs) && (!fe || e.era === fe) && (!fg || e.gate === fg) &&
    (!q || (e.snippet + " " + (e.quote || "") + " " + (e.mech || "") + " " + (e.url || "")).toLowerCase().includes(q)));
}
function drawEpisodes() {
  const rows = epFiltered();
  const pages = Math.max(1, Math.ceil(rows.length / EP_PER));
  epPage = Math.min(epPage, pages - 1);
  const slice = rows.slice(epPage * EP_PER, (epPage + 1) * EP_PER);
  $("ep-sub").innerHTML = `Filter and search the raw evidence — <b>${fmt(rows.length)}</b> of ${fmt(D.episodes.length)} episodes match`;
  $("ep-table").innerHTML = `<table>
    <thead><tr><th>date</th><th>source</th><th>gate</th><th>outcome</th><th>snippet (verified quote in indigo)</th><th class="num">conf</th><th></th></tr></thead>
    <tbody>${slice.map(e => `<tr>
      <td style="white-space:nowrap">${esc(e.date)}</td>
      <td>${sourceBadge(e.source)}</td>
      <td>${gateBadge(e.gate)}</td>
      <td>${outcomeBadge(e.outcome)}</td>
      <td class="snipcell">${esc(trunc(e.snippet, 240))}${e.quote ? `<span class="q2">“${esc(trunc(e.quote, 160))}”</span>` : ""}</td>
      <td class="num">${e.conf != null ? (+e.conf).toFixed(2) : "—"}</td>
      <td><a class="ext" href="${esc(e.url)}" target="_blank" rel="noopener">↗</a></td>
    </tr>`).join("")}</tbody></table>`;
  const a = epPage * EP_PER + 1, b = Math.min(rows.length, (epPage + 1) * EP_PER);
  $("ep-pager-label").textContent = rows.length ? `Showing ${a}–${b} of ${fmt(rows.length)}` : "No episodes match the filters";
  $("ep-prev").disabled = epPage <= 0;
  $("ep-next").disabled = epPage >= pages - 1;
}
function epGo(d) { epPage += d; drawEpisodes(); }

/* ---------- markdown-lite ---------- */
function mdLite(md) {
  let html = "", list = false;
  for (const raw of String(md || "").split("\n")) {
    let line = raw
      .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\[ep:([A-Za-z0-9_\-]+)\]/g, '<a class="epref" data-ep="$1" href="#evidence-$1" onclick="flashEp(this);return false;">[$1]</a>');
    if (/^\s*-\s+/.test(line)) {
      if (!list) { html += "<ul>"; list = true; }
      html += `<li>${line.replace(/^\s*-\s+/, "")}</li>`;
    } else {
      if (list) { html += "</ul>"; list = false; }
      if (line.trim()) html += `<p>${line}</p>`;
    }
  }
  if (list) html += "</ul>";
  return html;
}
function flashEp(a) {
  const el = document.querySelector(`.evc[data-ep="${CSS.escape(a.dataset.ep)}"]`);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 1800);
}

/* ---------- evidence cards ---------- */
function evCard(e, extra) {
  return `<div class="evc" data-ep="${esc(e.id)}" id="evidence-${esc(e.id)}" style="${gateStyle(e.gate)}">
    <div class="ev-top"><b>${esc(e.source)}</b><span>·</span><span>${esc(e.date)}</span>
      ${gateBadge(e.gate)}${e.outcome ? outcomeBadge(e.outcome) : ""}${e.gc ? '<span class="badge dim" title="gate label stable across two independently-worded model passes">2-pass ✓</span>' : ""}
      <a class="ext" href="${esc(e.url)}" target="_blank" rel="noopener">source</a>${extra || ""}</div>
    <div class="ev-snip">${esc(e.snippet)}</div>
    ${e.quote ? `<div class="ev-quote">“${esc(e.quote)}”</div>` : ""}
  </div>`;
}

/* ---------- ask: presets & free ---------- */
function tableHtml(t) {
  if (!t) return "";
  const head = (t.columns || []).map(c => `<th>${esc(c)}</th>`).join("");
  const body = (t.rows || []).slice(0, 8).map(r => `<tr>${r.map(v => `<td>${v == null ? "not stated" : esc(String(v))}</td>`).join("")}</tr>`).join("");
  return `<div style="overflow-x:auto;margin-bottom:10px"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>` +
    ((t.rows || []).length > 8 ? `<p class="small">…and ${(t.rows || []).length - 8} more rows in the data files.</p>` : "") + `</div>`;
}
function askPreset(i) {
  const q = Object.keys(D.cached_answers)[i];
  const e = D.cached_answers[q];
  const ids = e.evidence_ids || [];
  $("ans-title").textContent = q;
  $("ans-meta").textContent = `Method: ${e.method} · n=${e.n}`;
  $("answer").innerHTML =
    `<div>${mdLite(e.answer_markdown)}</div>
     ${e.tables && e.tables.length ? `<details class="tables"><summary>Tables behind this answer</summary>${e.tables.slice(0, 3).map(tableHtml).join("")}</details>` : ""}
     <h3 style="margin-top:18px">Evidence episodes (${ids.length})</h3>
     <div class="evidence">${ids.map(id => evCard(D.episodes.find(x => x.id === id) || { id, source: "?", date: "?", snippet: "", url: "#" })).join("")}</div>`;
  document.querySelector('.tab[data-tab="ask"]').classList.add("active");
}
function askFree() {
  const q = $("freeq").value.trim();
  if (!q) return;
  const hits = topK(q, 8);
  $("ans-title").textContent = q;
  $("ans-meta").textContent = "Evidence view · TF-IDF nearest neighbours, n=8 · no AI";
  if (!hits.length) {
    $("answer").innerHTML = `<p>No episodes matched that wording. Try words like “trip”, “document”, “old photo”, “search”, “dates”.</p>`;
    return;
  }
  const votes = vote(hits.map(h => h.ep));
  const g0 = votes.gate[0], p0 = votes.ptype[0];
  const PTYPE_SHORT = { trip_event: "trip/event", people_social: "people", food_place: "food & places",
    scenery_pet: "scenery & pets", document_utility: "documents & utility", screenshot: "screenshots",
    video: "videos", other_unspecified: "photos of unspecified type" };
  let lead = "";
  if (g0 && p0 && g0[1] >= 2 && p0[1] >= 2) {
    lead = `<p style="margin-top:4px"><b>Direct read:</b> the closest episodes most often point to <b>${esc(GATE_SHORT[g0[0]] || g0[0])}</b> failures with <b>${esc(PTYPE_SHORT[p0[0]] || p0[0])}</b> photos (${g0[1]}/8 agree on the gate, ${p0[1]}/8 on the type).</p>`;
  }
  $("answer").innerHTML =
    lead +
    `<div class="pill-line">Nearest episodes agree on: ${pillLine(votes)}.</div>
     <h3>Closest episodes (8)</h3>
     <div class="evidence">${hits.map(h => evCard(h.ep, `<span class="sim">${(h.score * 100).toFixed(0)}% sim</span>`)).join("")}</div>`;
}

/* ---------- TF-IDF top-k ---------- */
let VOCAB_IDX = null;
function topK(query, k) {
  if (!VOCAB_IDX) {
    VOCAB_IDX = new Map();
    D.tfidf.vocab.forEach((w, i) => VOCAB_IDX.set(w, i));
  }
  const vocab = D.tfidf.vocab, docs = D.tfidf.docs;
  const qv = new Float64Array(vocab.length);
  for (const w of (String(query).toLowerCase().match(/[a-z0-9]+/g) || [])) {
    const i = VOCAB_IDX.get(w);
    if (i !== undefined) qv[i] += 1;
  }
  let qn = 0;
  for (let i = 0; i < qv.length; i++) qn += qv[i] * qv[i];
  qn = Math.sqrt(qn);
  if (!qn) return [];
  const scored = [];
  docs.forEach((doc, di) => {
    let s = 0, dn = 0;
    for (const p of doc) { const i = p[0], v = p[1]; s += v * (qv[i] || 0); dn += v * v; }
    if (s > 0) scored.push({ ep: D.episodes[di], score: s / (qn * Math.sqrt(dn)) });
  });
  return scored.sort((a, b) => b.score - a.score).slice(0, k);
}
function vote(eps) {
  const v = {};
  ["gate", "ptype", "work"].forEach(k => {
    const c = {};
    eps.forEach(e => { const val = e[k]; if (val) c[val] = (c[val] || 0) + 1; });
    v[k] = Object.entries(c).sort((a, b) => b[1] - a[1]);
  });
  return v;
}
function pillLine(v) {
  const g = v.gate[0], p = v.ptype[0], w = v.work[0];
  return [
    g && `<span class="badge gate" style="${gateStyle(g[0])}">gate ${esc(GATE_SHORT[g[0]] || g[0])} · ${g[1]}/8</span>`,
    p && `<span class="badge dim">photo type ${esc(p[0])} · ${p[1]}/8</span>`,
    w && `<span class="badge dim">workaround ${esc(w[0])} · ${w[1]}/8</span>`
  ].filter(Boolean).join(" ") || "no common labels";
}

/* ---------- try it ---------- */
function tryIt() {
  const t = $("tryit").value.trim();
  if (!t) return;
  const hits = topK(t, 8);
  if (!hits.length) {
    $("tryit-out").innerHTML = `<p class="mut">No episodes matched. Try naming a photo type, a place, or what went wrong.</p>`;
    return;
  }
  const votes = vote(hits.map(h => h.ep));
  const top = hits[0];
  let cell = "no scored T7 cell (n≥8) for this photo_type × gate combination";
  if (top.ep.ptype && top.ep.gate) {
    const c = (D.t7 || []).find(r => r.photo_type === top.ep.ptype && r.failure_gate === top.ep.gate);
    if (c) cell = `scorecard cell <b>${esc(top.ep.ptype)} × ${esc(top.ep.failure_gate || top.ep.gate)}</b>: n=${c.n_cell}, offline score=${(+c.score).toFixed(1)}, p_top3=${(+c.p_top3 * 100).toFixed(0)}%`;
  }
  $("tryit-out").innerHTML =
    `<h3>Nearest-episode estimate <span class="small">(no live AI) · n=8 neighbours</span></h3>
     <div class="pill-line">${pillLine(votes)}</div>
     <p class="small">Would fall into: ${cell}</p>
     <div class="evidence">${hits.slice(0, 3).map(h => evCard(h.ep, `<span class="sim">${(h.score * 100).toFixed(0)}% sim</span>`)).join("")}</div>`;
}

/* ---------- scorecard ---------- */
function drawScore() {
  const w = { f: +$("w-freq").value / 100, s: +$("w-sev").value / 100, g: +$("w-gap").value / 100, l: +$("w-lev").value / 100 };
  $("w-freq-v").textContent = w.f.toFixed(2); $("w-sev-v").textContent = w.s.toFixed(2);
  $("w-gap-v").textContent = w.g.toFixed(2); $("w-lev-v").textContent = w.l.toFixed(2);
  const noLev = $("no-lev").checked;
  const cells = (D.t7 || []).slice();
  const mf = Math.max(...cells.map(r => r.freq)) || 1;
  let W = [w.f, w.s, w.g, w.l];
  if (noLev) { const s = w.f + w.s + w.g || 1; W = [w.f / s, w.s / s, w.g / s, 0]; }
  cells.forEach(r => { r.score_live = 100 * (W[0] * r.freq / mf + W[1] * r.sev + W[2] * r.gap + W[3] * r.lev); });
  cells.sort((a, b) => b.score_live - a.score_live);
  $("score-n-cells").textContent = cells.length;
  const wrap = document.querySelector("#score-table");
  wrap.classList.toggle("lev-off", noLev);
  wrap.innerHTML = `<table>
    <thead><tr><th>rank</th><th>photo type</th><th>failure gate</th><th class="num">n</th><th class="num">sev</th><th class="num">gap</th><th class="num levcol">lev</th><th class="num">score (live)</th><th class="num">p top-3</th><th>gap flag</th></tr></thead>
    <tbody>${cells.map((r, i) => `<tr>
      <td><span class="rank ${i < 3 ? "r" + (i + 1) : ""}">${i + 1}</span></td>
      <td>${esc(r.photo_type)}</td>
      <td>${gateBadge(r.failure_gate)}</td>
      <td class="num">${r.n_cell}</td>
      <td class="num">${(+r.sev).toFixed(2)}</td>
      <td class="num">${(+r.gap).toFixed(2)}</td>
      <td class="num levcol">${(+r.lev).toFixed(1)}</td>
      <td class="num"><b>${r.score_live.toFixed(1)}</b></td>
      <td class="num">${(+r.p_top3 * 100).toFixed(0)}%</td>
      <td>${r.gap_flag ? "⚠ fallback" : "—"}</td>
    </tr>`).join("")}</tbody></table>`;
}

load().catch(e => {
  $("lede").innerHTML = "Failed to load data.json: " + esc(e.message || e);
  $("answer").innerHTML = "<p class='mut'>The bundled dataset could not be loaded — see console.</p>";
});
