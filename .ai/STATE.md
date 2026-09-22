# TurbineTwin — Current State

_Last verified: 2026-09-22_

## What works
All 5 planned phases are complete and verified:
- **Phase 1** — data loading, deviation metrics, threshold derivation,
  anomaly flagging, Isolation Forest comparison.
- **Phase 2** — FastAPI backend (`/api/health`, `/api/window`, `/api/stream`,
  `/api/demo-anomalies`).
- **Phase 3** — live dashboard (power-curve chart, status panel, playback
  speed control, anomaly list, "jump to a known anomaly" demo buttons).
- **Phase 4** — rule-based RAG (`/api/ask`, clickable "why was this flagged"
  box on the dashboard).
- **Phase 5** — MCP server (`mcp_server.py`), 3 tools: `get_turbine_summary`,
  `get_anomalies`, `explain_anomaly`. stdio transport, ready for Claude
  Desktop / Cursor `mcpServers` config.

Plus three hardening passes ahead of showing the repo externally:
- **2026-09-18** — result figures committed (README images used to be
  broken on GitHub), README documents the MCP server and a "Security"
  section, three real input-handling bugs found by manual testing fixed.
- **2026-09-22 (external review)** — three presentation-readiness issues
  found and fixed: the demo took ~2.5 real-time minutes to
  reach the first anomaly (fixed with `/api/stream?start=` + two "jump to
  known anomaly" dashboard buttons backed by `/api/demo-anomalies`); the
  `get_turbine_summary` `healthy`/`moderate`/`degraded` status label was
  computed with the wrong denominator and always read "healthy" regardless
  of the actual in-range anomaly rate (fixed); presentation-language
  guidance was added (don't say "LLM finds the root cause" — say "matches
  deviations against maintenance records via rule-based retrieval, exposes
  it to an AI assistant through MCP"). See NOTLAR.md's "Sunum öncesi
  hardening" section and DECISIONS.md for the full reasoning.
- **2026-09-22 (security review)** — full defensive pass over the codebase.
  No DB (CSV/pandas only,
  confirmed no injection surface), no secrets ever committed (checked
  `git log --all --full-history`), `pip-audit` clean, production debug
  mode off (verified live: malformed input returns clean 4xx, no stack
  traces), path traversal attempts return 404. Fixed: added
  `SecurityHeadersMiddleware` to `api.py` (X-Content-Type-Options,
  X-Frame-Options, CSP scoped to the dashboard's actual Chart.js-CDN +
  inline-script needs, Referrer-Policy — confirmed missing on the live
  site before this fix); `mcp_server.py`'s `get_anomalies(limit=...)` now
  clamps the lower bound too (a negative limit previously hit pandas'
  `.head(-n)` semantics — returns nearly the whole table, not zero rows);
  hardened the anomaly-table `innerHTML` in `static/index.html` to
  `createElement`/`textContent` for consistency with the existing
  `/api/ask` answer-box fix; corrected README's stale "nginx reverse
  proxy" claim to Caddy (confirmed live via response headers —
  `nginx.conf` in the repo root is dead/unused config, not referenced by
  Dockerfile or docker-compose.yml). Documented as known, not fixed: no
  rate limiting on `/api/*`, Docker image runs as root (no `USER` in
  Dockerfile). See DECISIONS.md and README "Security" section.

Test suite: **43/43 passing** (`pytest tests/`, verified 2026-09-22 after
the security fixes above).

Repo is public and pushed: https://github.com/esadseyitoglu1/TurbineTwin
Commit `e528f96` pushed and **deployed to production** (2026-09-22):
server's checkout was 2 commits behind (still had the uncommitted-on-server
version of the `docker-compose.yml` network fix as an unstaged edit,
content-identical to `c446f40` — stashed, fast-forwarded, stash dropped,
no data lost), then `docker compose up -d --build`. Verified live:
`/api/health` OK, security headers present (CSP/X-Frame-Options/
X-Content-Type-Options/Referrer-Policy), Playwright confirms the dashboard
chart still renders (CSP didn't break Chart.js), no console/page errors.
Live: https://turbinetwin.esadseyitoglu.xyz

## Partially completed / rough edges
- A short demo GIF of the live dashboard is planned for the README but not
  yet recorded/embedded (needs to be captured locally from the running
  dashboard).

## Current blockers
None. Project is functionally complete and public. Remaining work is
optional presentation polish (see NEXT.md).
