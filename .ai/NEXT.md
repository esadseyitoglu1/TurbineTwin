# TurbineTwin — Next

## Immediate
1. Record a short screen-capture GIF of the live dashboard — ideally showing
   the "jump to a known anomaly" buttons rather than waiting through a slow
   real-time replay — and embed it in `README.md`. Needs to be captured
   locally (ShareX or similar).
2. Decide what to do with the orphaned `nginx.conf` at the repo root: it is
   unused (production runs behind the host's shared Caddy proxy, see the
   `services_n8n_net` comment in `docker-compose.yml`). Either delete it or
   update it to match reality — right now it is misleading to a reader.

## Known gaps, deliberately open
See `KNOWN_ISSUES.md` for the two documented security scope decisions
(no rate limiting on `/api/*`, container runs as root) — both need a real
policy decision rather than a drive-by fix.

## Not started (deliberately out of scope for now)
- Real-time data ingestion (replacing historical replay with a live feed).
  Needs `STATE` to become mutable under concurrent access — would require
  locking or a message-queue-backed pipeline (Kafka/RabbitMQ). See
  DECISIONS.md — intentionally left out rather than half-implemented.
