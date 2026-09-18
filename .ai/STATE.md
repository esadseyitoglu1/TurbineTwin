# TurbineTwin — Current State

_Last verified: 2026-09-18_

## What works
All 5 planned phases are complete and verified:
- **Phase 1** — data loading, deviation metrics, threshold derivation,
  anomaly flagging, Isolation Forest comparison.
- **Phase 2** — FastAPI backend (`/api/health`, `/api/window`, `/api/stream`).
- **Phase 3** — live dashboard (power-curve chart, status panel, playback
  speed control, anomaly list).
- **Phase 4** — rule-based RAG (`/api/ask`, clickable "why was this flagged"
  box on the dashboard).
- **Phase 5** — MCP server (`mcp_server.py`), 3 tools: `get_turbine_summary`,
  `get_anomalies`, `explain_anomaly`. stdio transport, ready for Claude
  Desktop / Cursor `mcpServers` config.

Plus a presentation/hardening pass (2026-09-18, ahead of showing the repo
externally): result figures are now committed (README images used to be
broken on GitHub), README documents the MCP server and a "Security" section,
and three real input-handling bugs found by manual testing were fixed —
see DECISIONS.md and KNOWN_ISSUES.md.

Test suite: **34/34 passing** (`pytest tests/`, verified 2026-09-18).

Repo is public and pushed: https://github.com/esadseyitoglu1/TurbineTwin

## Partially completed / rough edges
- A short demo GIF of the live dashboard is planned for the README but not
  yet recorded/embedded (user needs to record it locally; not something an
  agent can produce).

## Current blockers
None. Project is functionally complete and public. Remaining work is
optional presentation polish (see NEXT.md).
