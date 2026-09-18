# TurbineTwin — Decisions

- **Deviation normalized by `rated_power` (a constant), not by
  `theoretical_power_kw`.** Dividing by the theoretical value blows up near
  cut-in wind speed, where it approaches zero (confirmed live: produced
  `inf`/`NaN`). A constant, nonzero denominator makes that failure
  structurally impossible rather than just guarded against.

- **Anomaly threshold derived from data** (1st percentile of in-range
  deviation), not hardcoded, and not `mean − 3σ`. The `mean − 3σ`
  alternative was tested and flags 2.7x more rows, because the deviation
  distribution is skewed — percentile is rank-based and isn't dragged
  around by that skew.

- **Rule-based detector kept as the primary anomaly signal; Isolation
  Forest run only as a comparison.** They agree on just 39% of flagged
  rows — Isolation Forest flags statistically rare (but healthy) high-wind
  operation, while the rule-based approach flags genuine underperformance
  relative to the design curve, which is the actually-wanted signal here.

- **RAG "generation" step is a template, not an LLM call.** This keeps the
  retrieval logic (the part worth demonstrating) fully visible and testable
  with `pytest` — no API key, no network dependency, no mocking. If a real
  LLM is wired in later, `explain_anomaly()`'s structured output
  (`row` + `maintenance_record`) is designed to be passed straight into
  that LLM's prompt as context — the architecture doesn't need to change.

- **No embedding/vector search for maintenance-record retrieval.** With
  only 3 synthetic, structured (`start`/`end` fields) records, semantic
  search would be unneeded complexity. A plain date-range overlap check
  (`start <= end AND end >= start`) is exact and sufficient. Overlap, not
  exact equality, because maintenance windows are deliberately logged
  slightly wider than the anomaly cluster they explain (realism: a crew's
  arrival time isn't the same minute the turbine output hits zero).

- **Real-time data ingestion was deliberately scoped out**, not
  half-implemented. The API's in-memory `STATE` is currently read-only
  after startup; making it accept a live feed would require concurrency
  handling (locking, or a message-queue-backed pipeline like
  Kafka/RabbitMQ) — real infrastructure work, not a prototype-scale add-on.

- **MCP server (`mcp_server.py`) reuses the same `turbinetwin` package
  functions as the FastAPI layer** (`ask.explain_anomaly`, the
  `deviation.py` pipeline). Zero logic duplication between the HTTP surface
  and the MCP surface — both are just different "doors" onto the same core.

- **mcp 2.x's `MCPServer`, not v1's `FastMCP`.** `mcp[cli]` v2.2.0 renamed
  the class; entry point is `asyncio.run(mcp.run_stdio_async())` instead of
  the old `mcp.run(transport="stdio")`.

- **Security pass (2026-09-18) focused on real input-handling bugs, not a
  generic checklist.** There's no database anywhere in the project (CSV →
  pandas, JSON maintenance log), so SQL injection was never an applicable
  vector — stated explicitly in the README instead of testing something
  that doesn't exist. What *is* real: `/api/ask?timestamp=...` used to call
  `pd.Timestamp()` unguarded and 500 on malformed input (confirmed live
  with a `<script>` payload); fixed with a `try/except` returning
  `{"found_row": false, "answer": "Invalid timestamp format."}`. All answer
  strings in `ask.py` were also changed to echo the parsed `ts`, never the
  raw `timestamp` argument, so no request-influenced text reaches a
  response body verbatim. `/api/window` had unbounded `limit` and an
  unvalidated negative `start` (silently wraps via Python slicing); fixed
  with `Query(ge=0)` / `Query(le=1000)`. The dashboard's RAG answer box
  (`static/index.html`) was switched from `innerHTML` string interpolation
  to `createElement`/`textContent` as defense in depth, even though the
  `ask.py` fix already means nothing attacker-controlled reaches it today.
  See README "Security" section and `tests/test_ask.py` /
  `tests/test_api.py` for the regression tests using the exact payloads
  that triggered the original bugs.
