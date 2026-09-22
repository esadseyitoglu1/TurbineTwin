# TurbineTwin — Known Issues

- **No rate limiting on any `/api/*` route.** Found during the 2026-09-22
  security review, left unfixed (documented in README "Security" instead).
  Acceptable for a portfolio demo with no auth/write operations, but a real
  gap if the app ever handles sensitive data. Would belong at the Caddy
  layer (or `slowapi` in-app) rather than being bolted onto `api.py`
  without a clear policy (per-IP? per-route? what response on 429?) —
  that's a design decision for the user, not a one-line fix.
- **Docker image runs as root** (no `USER` directive in `Dockerfile`).
  Found during the 2026-09-22 security review, left unfixed — low risk
  given the container has no volume mounts of sensitive host paths and is
  read-only-after-startup, but adding a non-root user wasn't done blind
  since it can break `COPY`'d file ownership/permissions inside the image
  in ways worth testing deliberately rather than as a drive-by fix.
- **`nginx.conf` at the repo root is orphaned/stale.** Not referenced by
  `Dockerfile` or `docker-compose.yml` — production actually runs behind
  the host's shared Caddy reverse proxy (confirmed live: `Server: Caddy`
  header, see docker-compose.yml's `services_n8n_net` comment). The
  README's "nginx reverse proxy" claim was corrected to Caddy on
  2026-09-22; the file itself was left in place (deleting it was out of
  scope for that review) — see NEXT.md.

- **Resolved 2026-09-22 (kept for context):** a rebuild
  (`docker compose up --build`) recreated the `turbinetwin` container
  without the manually-added `services_n8n_net` connection the host's
  shared Caddy reverse proxy needs to resolve it by name, causing a 502
  on the public URL. `docker-compose.yml` now declares that network as
  `external: true` so `docker compose up` recreates the connection
  itself. See NOTLAR.md "Deploy incident'i" for the full story — same
  failure class as OtoŞarj's `.env.production` git incident (a manual,
  out-of-band fix that an automated step silently undid).

- **Resolved 2026-09-22 (kept for context):** `get_turbine_summary`'s
  `anomaly_pct` divided by `total_rows` instead of `in_range` row count,
  making the `healthy`/`moderate`/`degraded` status label meaningless (it
  always read "healthy"). Fixed — see DECISIONS.md and NOTLAR.md.

- **Resolved 2026-09-22 (kept for context):** the live dashboard always
  replayed from row 0, taking ~2.5 real-time minutes to reach the first
  anomaly at default speed — a real problem for a timed demo. Fixed with
  `/api/stream?start=` + two dashboard buttons backed by a new
  `/api/demo-anomalies` endpoint. See NOTLAR.md.

- **`README.md` "Status" section is stale.** Still reads "Phase 1-4
  complete"; Phase 5 (MCP server) shipped in commit `389cf8e` but the
  README was never updated. Cosmetic, but misleading to an external
  reviewer skimming only the README. See NEXT.md.

- **Windows console can garble Turkish characters in printed output**
  (e.g. `"M. Aydın"` displayed as `"M. Ayd?n"` in a terminal). Confirmed
  via `ord(c)` that the underlying character is correctly `U+0131` and the
  JSON is valid UTF-8 — this is purely a Windows console code-page display
  limitation, not a data or API bug. Renders correctly in a browser.

- **`/api/stream?speed=100` measures closer to ~54x in practice**, not a
  true 100x, due to Windows timer resolution limits on `asyncio.sleep`
  with very small intervals. Documented, not fixed (acceptable for a
  dashboard demo; would matter for anything timing-sensitive).

- **Historical (resolved) finding, kept for context:** `uvicorn.exe` was
  once reported missing from PATH despite `import uvicorn` working from
  Python directly. Worked around by invoking uvicorn as a module. If this
  resurfaces, check the venv's `Scripts/` directory against `pip show uvicorn`.
