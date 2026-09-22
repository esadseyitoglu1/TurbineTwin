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

Plus two hardening passes ahead of showing the repo externally:
- **2026-09-18** — result figures committed (README images used to be
  broken on GitHub), README documents the MCP server and a "Security"
  section, three real input-handling bugs found by manual testing fixed.
- **2026-09-22** — external review (Codex) found and Claude fixed three
  presentation-readiness issues: the demo took ~2.5 real-time minutes to
  reach the first anomaly (fixed with `/api/stream?start=` + two "jump to
  known anomaly" dashboard buttons backed by `/api/demo-anomalies`); the
  `get_turbine_summary` `healthy`/`moderate`/`degraded` status label was
  computed with the wrong denominator and always read "healthy" regardless
  of the actual in-range anomaly rate (fixed); presentation-language
  guidance was added (don't say "LLM finds the root cause" — say "matches
  deviations against maintenance records via rule-based retrieval, exposes
  it to an AI assistant through MCP"). See NOTLAR.md's "Sunum öncesi
  hardening" section and DECISIONS.md for the full reasoning.

Test suite: **43/43 passing** (`pytest tests/`, verified 2026-09-22 —
34 from 2026-09-18 + 9 new: 5 MCP regression tests for the health-status
fix, 4 API tests for `start`/`/api/demo-anomalies`).

Repo is public and pushed: https://github.com/esadseyitoglu1/TurbineTwin
(2026-09-22 changes not yet committed/pushed — see NEXT.md).

## Partially completed / rough edges
- A short demo GIF of the live dashboard is planned for the README but not
  yet recorded/embedded (user needs to record it locally; not something an
  agent can produce).

## Current blockers
None. Project is functionally complete and public. Remaining work is
optional presentation polish (see NEXT.md).
