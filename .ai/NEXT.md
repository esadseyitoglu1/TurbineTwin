# TurbineTwin — Next

## Immediate
1. Update `README.md`'s "Status" section to mention Phase 5 (MCP server) —
   currently stale, stops at Phase 4.
2. Commit or discard the pending one-line diff in `tests/test_mcp_server.py`.
3. Add a short "how to wire this into Claude Desktop" example to the README
   (mcpServers config snippet) — the user is about to show this repo to an
   energy company's AI director for an internship application, and the MCP
   piece is the most novel part to demonstrate.

## Not started (deliberately out of scope for now)
- Real-time data ingestion (replacing historical replay with a live feed).
  Needs `STATE` to become mutable under concurrent access — would require
  locking or a message-queue-backed pipeline (Kafka/RabbitMQ). See
  DECISIONS.md — intentionally left out rather than half-implemented.
