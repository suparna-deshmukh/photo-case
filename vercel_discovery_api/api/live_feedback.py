"""
Purpose: "Discover more" tab (additive, D12). On-demand fetch of fresh public
         feedback about the Google Photos app for a user-supplied search
         query from three public sources - Google Play Store, Apple App
         Store, Reddit - plus analysis: live Gemini via live_llm when
         available, and a rule-based reading that always works (R15:
         zero-LLM safe).
Inputs : user query (max 200 chars), chosen sources, per-source item cap;
         env LIVE_LLM_* (read only by live_llm).
Outputs: run_search(query, sources, per_source) -> dict with rows/errors;
         ai_analysis(query, rows, session) -> dict | None;
         basic_analysis(query, rows) -> markdown string.
Safety : dependency-light (requests; google_play_scraper imported lazily);
         never raises into the UI - every fetcher returns (rows, error);
         short timeouts; one Reddit 429 backoff; no PII fields kept
         (usernames/avatars dropped); nothing written to disk or logs.
"""
import html as _html
import json
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

try:
    import requests as _requests
except Exception:
    _requests = None

import live_llm

PLAY_APP = "com.google.android.apps.photos"
AS_APP_ID = 962194608
AS_COUNTRY = "us"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
TIMEOUT_S = (5, 25)
ATOM = {"a": "http://www.w3.org/2005/Atom"}

SOURCE_LABEL = {"play": "Google Play Store", "appstore": "App Store", "reddit": "Reddit"}
FRIENDLY_ERROR = {
    "offline": "no network in this environment",
    "not_installed": "source not available in this build",
    "fetch_failed": "couldn't be reached right now",
    "rate_limited": "rate-limited right now",
    "parse_failed": "unreadable response",
}

_STOP = set("""a an and are as at be but by for from has have had i if in into is it its
of on or that the this to was were what when where which who will with you your yours
we our us their they them about after before during out up down not no so do did does
can could should would been being very just really also even still again much more most
other some any all each only own same than then too because while over under here there
photo photos picture pictures search found looking look find want using use used app
one two way ways thing things every ever know like got get many bit lot""".split())

_REDDIT_BOILER_RE = re.compile(r"submitted by\b.*?\[comments\]", re.I | re.S)

_POS = {"love", "loved", "loves", "great", "good", "easy", "easily", "fast", "quick",
        "works", "working", "helpful", "thanks", "thank", "amazing", "awesome", "best",
        "happy", "finally", "perfect", "nice", "useful", "better", "improved", "glad",
        "excellent", "fantastic", "works"}
_NEG = {"cannot", "cant", "wont", "broken", "breaks", "breaking", "broke", "bug", "bugs",
        "missing", "lost", "lose", "lacks", "lacking", "fail", "fails", "failed",
        "terrible", "horrible", "awful", "worse", "worst", "hate", "annoying", "annoyed",
        "useless", "slow", "crash", "crashed", "crashes", "wrong", "never", "confusing",
        "confused", "frustrating", "frustration", "disappointed", "disappointing", "stuck",
        "nothing", "poor", "ridiculous", "waste", "scam", "unusable"}


def _clean(s):
    s = _html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _terms(query):
    return [t for t in re.split(r"\W+", (query or "").lower()) if len(t) >= 3]


def _date_of(v):
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, (int, float)):
        try:
            return time.strftime("%Y-%m-%d", time.gmtime(int(v)))
        except Exception:
            return ""
    return ""


# ---------------- fetchers ----------------

def fetch_play(query, n, scan=250):
    """Newest Google Play reviews; filtered by query terms (the Play API has
       no free-text review search, so we scan the newest window)."""
    try:
        from google_play_scraper import Sort, reviews
    except Exception:
        return [], "not_installed"
    try:
        recs, _tok = reviews(PLAY_APP, lang="en", country="us",
                             count=scan, sort=Sort.NEWEST)
    except Exception:
        return [], "fetch_failed"
    rows, seen = [], set()
    terms = _terms(query)
    for r in recs or []:
        text = _clean(str(r.get("content") or ""))
        if len(text) < 8:
            continue
        low = text.lower()
        if terms and not any(t in low for t in terms):
            continue
        rid = str(r.get("id") or "")
        if rid in seen:
            continue
        seen.add(rid)
        rating = r.get("score")
        rows.append({
            "source": "play",
            "text": text[:600],
            "rating": int(rating) if isinstance(rating, (int, float)) and 1 <= int(rating) <= 5 else None,
            "date": _date_of(r.get("at")),
            "url": (f"https://play.google.com/store/apps/details?id={PLAY_APP}"
                    f"&reviewId={rid}") if rid else "",
        })
        if len(rows) >= n:
            break
    return rows, None


def fetch_appstore(query, n, pages=4):
    """Apple App Store customer-review RSS for Google Photos, newest first."""
    if _requests is None:
        return [], "offline"
    rows, seen = [], set()
    terms = _terms(query)
    for page in range(1, pages + 1):
        url = (f"https://itunes.apple.com/{AS_COUNTRY}/rss/customerreviews/"
               f"page={page}/id={AS_APP_ID}/sortby=mostrecent/json")
        try:
            r = _requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT_S)
        except Exception:
            return (rows, None) if rows else ([], "fetch_failed")
        if r.status_code != 200:
            if rows:
                break
            return [], "rate_limited" if r.status_code in (403, 429) else "fetch_failed"
        try:
            entries = r.json().get("feed", {}).get("entry", [])
        except Exception:
            break
        if isinstance(entries, dict):
            entries = [entries]
        if not entries:
            break
        for e in entries:
            rating = (e.get("im:rating") or {}).get("label")
            rid = str((e.get("id") or {}).get("label", ""))
            if not rid or rid in seen:
                continue
            seen.add(rid)
            title = _clean((e.get("title") or {}).get("label", ""))
            content = _clean((e.get("content") or {}).get("label", ""))
            text = (title + ". " + content) if title else content
            if len(text) < 8:
                continue
            low = text.lower()
            if terms and not any(t in low for t in terms):
                continue
            link = ""
            links = e.get("link") or []
            if isinstance(links, dict):
                links = [links]
            for l in links:
                if isinstance(l, dict) and l.get("href"):
                    link = l["href"]
                    break
            if not link:
                link = f"https://apps.apple.com/{AS_COUNTRY}/app/id{AS_APP_ID}/#review-{rid}"
            rows.append({
                "source": "appstore",
                "text": text[:600],
                "rating": int(rating) if str(rating).isdigit() else None,
                "date": str((e.get("updated") or {}).get("label", ""))[:10],
                "url": link,
            })
            if len(rows) >= n:
                return rows, None
        time.sleep(0.5)
    return rows, None


def fetch_reddit(query, n):
    """Reddit public search RSS (25 newest posts per query)."""
    if _requests is None:
        return [], "offline"
    q = (query or "").strip() + " google photos"
    url = f"https://www.reddit.com/search.rss?q={quote_plus(q)}&limit=25"
    root = None
    for attempt in (1, 2):
        try:
            r = _requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT_S)
        except Exception:
            return [], "fetch_failed"
        if r.status_code == 429 and attempt == 1:
            time.sleep(12)
            continue
        if r.status_code != 200:
            return [], "rate_limited" if r.status_code in (403, 429) else "fetch_failed"
        try:
            root = ET.fromstring(r.content)
        except Exception:
            return [], "parse_failed"
        break
    if root is None:
        return [], "rate_limited"
    rows = []
    terms = _terms(query)
    for e in root.findall("a:entry", ATOM):
        def g(tag):
            el = e.find("a:" + tag, ATOM)
            return (el.text or "").strip() if el is not None and el.text else ""
        l = e.find("a:link", ATOM)
        link = l.attrib.get("href", "") if l is not None else ""
        if not link or "comments/" not in link:
            continue
        title = _clean(g("title"))
        body = _clean(g("content"))
        body = _REDDIT_BOILER_RE.sub(" ", body)
        body = re.sub(r"\[(?:link|comments|permalink)\]", " ", body)
        body = re.sub(r"\s+", " ", body).strip()
        text = (title + " — " + body) if body else title
        if len(text) < 8:
            continue
        low = text.lower()
        if terms and not any(t in low for t in terms):
            continue
        rows.append({
            "source": "reddit",
            "text": text[:600],
            "rating": None,
            "date": (g("published") or g("updated"))[:10],
            "url": link,
        })
        if len(rows) >= n:
            break
    return rows, None


FETCHERS = {"play": fetch_play, "appstore": fetch_appstore, "reddit": fetch_reddit}


def run_search(query, sources, per_source):
    """Fetch all selected sources with error isolation. Never raises."""
    out = {"query": query, "rows": [], "errors": {}, "sources": []}
    for s in sources:
        rows, err = FETCHERS[s](query, per_source)
        out["errors"][s] = err
        out["rows"].extend(rows)
        out["sources"].append(s)
        time.sleep(1.0)
    return out


# ---------------- analysis ----------------

def _sentiment_scores(text):
    toks = re.findall(r"[a-z']+", text.lower())
    pos = sum(1 for t in toks if t in _POS)
    neg = sum(1 for t in toks if t in _NEG)
    return pos, neg


def basic_analysis(query, rows):
    """Rule-based reading, always available (no LLM)."""
    total = len(rows)
    n_by, rated = {}, []
    pos = neg = 0
    kw = {}
    for r in rows:
        n_by[r["source"]] = n_by.get(r["source"], 0) + 1
        if r.get("rating"):
            rated.append(r["rating"])
        p, g = _sentiment_scores(r["text"])
        pos += p
        neg += g
        for t in re.findall(r"[a-z]{3,}", r["text"].lower()):
            if t not in _STOP:
                kw[t] = kw.get(t, 0) + 1
    lines = [f"**Code-only reading** of {total} fresh document(s) for “{query}” (no live AI)."]
    if rated:
        lines.append(f"- average rating in sample: **{sum(rated) / len(rated):.1f}** / 5 ({len(rated)} rated)")
    if pos or neg:
        lines.append(f"- sentiment signal: **{pos}** positive vs **{neg}** negative keyword mentions "
                     f"(directional, not a statistical estimate)")
    top = sorted(kw.items(), key=lambda kv: (-kv[1], kv[0]))[:12]
    if top:
        lines.append("- most common words: " + ", ".join(f"{w} ({c})" for w, c in top))
    for s in ("play", "appstore", "reddit"):
        if n_by.get(s):
            lines.append(f"- {SOURCE_LABEL[s]}: {n_by[s]} document(s)")
    return "\n".join(lines)


_AI_SYSTEM = (
    "You are a UX research analyst for a consumer photo app. You are given fresh, "
    "public user feedback (app-store reviews and Reddit posts) collected live for a "
    "search query. Analyze what users are actually saying. Return ONLY a JSON object "
    "with exactly these keys: summary_markdown (2-4 markdown sentences on what the "
    "fresh feedback says), verdict (one short sentence), sentiment with integer keys "
    "positive/negative/neutral (document counts), themes (list of up to 5 objects with "
    "keys theme <=6 words, tone one of positive|negative|mixed|neutral, count integer, "
    "sample_quote a VERBATIM substring of exactly one provided document <=200 chars), "
    "opportunities (list of up to 3 concrete product/UX opportunities implied by the "
    "feedback). sample_quote must be copied exactly from the provided texts."
)


def ai_analysis(query, rows, session=None):
    """Gemini analysis of the fetched documents. Returns dict | None. Never raises."""
    if not rows:
        return None
    docs = [{"doc": i + 1, "source": r["source"], "rating": r.get("rating"),
             "date": r.get("date", ""), "text": r["text"][:400]}
            for i, r in enumerate(rows[:40])]
    user = (f"Search query: {query}\n\nFresh public feedback (n={len(rows)}):\n"
            + json.dumps(docs, ensure_ascii=False))
    out = live_llm.live_json(_AI_SYSTEM, user, session=session, max_tokens=1200)
    if not isinstance(out, dict):
        return None
    blob = " ".join(re.sub(r"\s+", " ", d["text"]).lower() for d in docs)
    themes = []
    for t in (out.get("themes") or [])[:5]:
        if not isinstance(t, dict) or not str(t.get("theme") or "").strip():
            continue
        t = dict(t)
        q = re.sub(r"\s+", " ", str(t.get("sample_quote") or "")).strip().lower()
        if q and q not in blob:
            t["sample_quote"] = None
        themes.append(t)
    out["themes"] = themes
    return out
