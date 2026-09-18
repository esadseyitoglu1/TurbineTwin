# TurbineTwin — Next

## Immediate
1. Record a short screen-capture GIF of the live dashboard (power curve
   streaming + clicking an anomaly row to trigger the RAG explanation box)
   and embed it in `README.md`. User needs to record this locally (ShareX
   or similar) — an agent can't produce it, but can place/embed the file
   and commit once it exists.

## Not started (deliberately out of scope for now)
- Real-time data ingestion (replacing historical replay with a live feed).
  Needs `STATE` to become mutable under concurrent access — would require
  locking or a message-queue-backed pipeline (Kafka/RabbitMQ). See
  DECISIONS.md — intentionally left out rather than half-implemented.
