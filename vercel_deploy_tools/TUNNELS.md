# Ops notes — Jog live tunnels (2026-10-07)
- Primary: https://f0f357... see /tmp/current_tunnel_url.txt (localhost.run, launchd agent com.jog.tunnel, ssh -R 80:localhost:8601)
  - URL CHANGES ON RECONNECT: read new URL from `grep -oE 'https://[a-z0-9]+\.lhr\.life' /tmp/tunnel_events.log | tail -1`
  - On new URL: update /Users/apple/photo_case/vercel_redirect/vercel.json + index.html and re-deploy if Vercel is unblocked.
- Backup: serveo https://868d8ca619d18381-88-216-234-172.serveousercontent.com (has free-tier warning page)
- Local app: port 8601 (jog_child, slim 356-photo build in vercel_deploy_mine/api). Dev servers 8501/8502 belong to other threads — do not touch.
- Vercel: team pm28 fair-use blocked (402). Prod deployment dpl_6u4JwcpG5MBYS8AYUFm6kxDS4JtC is READY; space-jog.vercel.app serves it automatically when block lifts.
- Retry agent: com.jog.deploy (deploy_retry2.sh): redirect first (fast), then full app every 5 min. Log: /tmp/deploy_retry2.log
- NordLayer MDM on this Mac blocks lhr.life + serveousercontent.com in LOCAL browsers only (external access verified fine via allorigins/jina).

## 2026-10-09 — "Ask button not working" on space-jog.vercel.app (FIXED)
- Symptom: clicking Ask (search-pill chip / bottom nav) showed the fatal error card
  `st.session_state['ask_text_free'] cannot be modified after the widget with that key is
  instantiated` instead of the Ask Photos view (reproduced in a real browser).
- Root cause: the space-jog alias was on a full-app prod build (Wed Oct 07 22:17,
  space-bm5irj40y) whose bundled app.py was STALE — Vercel files API hash (3cc9d37b...)
  did not match local app.py (a8f800c6... md5). The stale revision contained a run-order
  bug in _ask_idle (same crash as space_jog/logs_ui_error.txt, Oct 07 13:37). Local 8601
  and AppTest passed because they run the fixed file.
- Fix: hardened _ask_idle() — seed st.session_state['ask_text_free'] before widget
  creation and drop the value= arg (conflicts with the key in Streamlit 1.65). Patched
  space_jog/app.py, vercel_deploy/api/app.py, vercel_deploy_mine/api/app.py (identical);
  removed stale __pycache__; added .vercelignore (pycache/logs).
- Deploy: dpl_G9YGWzNmyAU764khPLpBT1raDyeC (space-emre2j2wm-pm28) promoted to
  space-jog.vercel.app at ~02:41 IST. Verified ~03:00 IST via Playwright (Chromium):
  desktop chip click, mobile bottom-nav click, and repeat-visit all open the Ask view;
  0 error cards, 0 JS errors. Cost: one prod build (~3 CPU-min). Vercel pm28 fair-use
  block had lifted (deploys succeed); deploy_retry2 agent is no longer running.
