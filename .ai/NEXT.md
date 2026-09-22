# TurbineTwin — Next

## Immediate
1. **Review and commit the 2026-09-22 changes** — both the Codex-review
   fixes and the security-review pass (README.md, api.py, mcp_server.py,
   static/index.html; security review intentionally left uncommitted for
   the user to inspect first). Run `pytest tests/` once more right before
   committing (43/43 passing as of this pass).
2. Record a short screen-capture GIF of the live dashboard — ideally now
   showing the new "jump to a known anomaly" buttons instead of waiting
   through a slow real-time replay — and embed it in `README.md`. User
   needs to record this locally (ShareX or similar) — an agent can't
   produce it, but can place/embed the file and commit once it exists.
3. Redeploy to production (78.135.85.106) to pick up the
   `SecurityHeadersMiddleware` and other 2026-09-22 fixes — not done by
   this review on purpose (deploy is the user's step, per project rules).
4. Consider deleting the orphaned `nginx.conf` (unused — production
   actually runs behind Caddy, see `docker-compose.yml`'s
   `services_n8n_net` comment) or updating it to match reality; left as-is
   by the security review since removing files was out of scope.

## Not started (deliberately out of scope for now)
- Real-time data ingestion (replacing historical replay with a live feed).
  Needs `STATE` to become mutable under concurrent access — would require
  locking or a message-queue-backed pipeline (Kafka/RabbitMQ). See
  DECISIONS.md — intentionally left out rather than half-implemented.
