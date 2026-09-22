# TurbineTwin — Next

## Immediate
1. **Commit and push the 2026-09-22 hardening changes** (not yet done —
   `api.py`, `mcp_server.py`, `config.py`, `static/index.html`,
   `tests/test_api.py`, `tests/test_mcp_server.py`, NOTLAR.md, all three
   `.ai/*.md` files). Run `pytest tests/` once more right before committing.
2. Record a short screen-capture GIF of the live dashboard — ideally now
   showing the new "jump to a known anomaly" buttons instead of waiting
   through a slow real-time replay — and embed it in `README.md`. User
   needs to record this locally (ShareX or similar) — an agent can't
   produce it, but can place/embed the file and commit once it exists.
3. Fix the stale README "Status" section (still says "Phase 1-4 complete").

## Not started (deliberately out of scope for now)
- Real-time data ingestion (replacing historical replay with a live feed).
  Needs `STATE` to become mutable under concurrent access — would require
  locking or a message-queue-backed pipeline (Kafka/RabbitMQ). See
  DECISIONS.md — intentionally left out rather than half-implemented.
