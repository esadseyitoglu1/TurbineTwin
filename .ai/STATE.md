# TurbineTwin — Current State

_Last verified: 2026-09-17_

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

Test suite: **30/30 passing** (`pytest tests/`, verified 2026-09-17).

Last commit on `master`: `389cf8e` — "feat: add MCP server with 3 tools
(Phase 5, Step 5.1)".

## Partially completed / rough edges
- `tests/test_mcp_server.py` has one uncommitted change (a single trailing
  blank line) as of 2026-09-17 — trivial, not yet committed or discarded.
- `README.md`'s "Status" section still says "Phase 1-4 complete" — it was
  never updated after the Phase 5 (MCP) commit. Not a functional bug, but
  misleading to anyone (including another agent) skimming the README only.

## Current blockers
None. Project is functionally complete; remaining work is presentation
polish before showing the repo externally (see NEXT.md).
