# TurbineTwin — Wind Turbine Digital Twin

[![Live Demo](https://img.shields.io/badge/Live_Demo-turbinetwin.esadseyitoglu.xyz-22c55e?style=for-the-badge&logo=rocket)](https://turbinetwin.esadseyitoglu.xyz)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![MCP](https://img.shields.io/badge/MCP-Model_Context_Protocol-8B5CF6?style=for-the-badge)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/Tests-43%2F43_passing-22c55e?style=for-the-badge&logo=pytest)](tests/)

**🌐 [Live Demo → https://turbinetwin.esadseyitoglu.xyz](https://turbinetwin.esadseyitoglu.xyz)**

---

When a turbine underperforms its design curve, operators typically find out
weeks later — from maintenance reports. TurbineTwin detects it in real time,
flags it with a plain-language explanation, and exposes the same logic as MCP
tools so an AI assistant can query turbine health directly.

Built on real SCADA data from a wind farm in Turkey (2018, 10-minute
resolution, ~50k records). Compares actual power output against the
manufacturer's theoretical power curve to flag deviations from design
behavior — the same problem at the core of Eksim Enerji's digital twin
approach: detecting when equipment drifts from its design values.

The project deliberately demonstrates three layers working together on the same dataset:

| Layer | What it does | Where it lives | Details |
|---|---|---|---|
| **Anomaly detection** | Rule-based power-curve deviation, compared against sklearn's Isolation Forest | `deviation.py` → dashboard status panel | [↓](#1-anomaly-detection--deviationpy) |
| **RAG** | Retrieves the flagged reading + any overlapping maintenance record, then generates a plain-language verdict | `ask.py` + `maintenance.py` → `GET /api/ask` | [↓](#2-rag--askpy--maintenancepy--get-apiask) |
| **MCP server** | Exposes the same three functions as AI-callable tools, no HTTP needed | `mcp_server.py` → Claude Desktop / Cursor | [↓](#3-mcp-server--mcp_serverpy) |

All three read the same in-memory dataset and share the same detection code —
the RAG endpoint and the MCP tools are two different front doors onto one
engine, not reimplementations.

## Try it in 2 minutes

On the [live demo](https://turbinetwin.esadseyitoglu.xyz) — no setup, no login:

1. **Jump straight to a real anomaly.** The 2018 dataset replays in timestamp
   order, and the first genuine anomaly is hours in, so the dashboard ships
   with two shortcut buttons. Click **"Unexplained anomaly"** — the stream
   jumps to row 1460, where measured power sits near zero while the power
   curve expects ~2300 kW.
2. **Watch the status panel flip.** Wind speed, measured vs. theoretical
   power, deviation %, and the state label (normal / idle / anomaly) update
   live over Server-Sent Events. Anomalous readings accumulate in the table
   below the chart.
3. **Ask *why* — this is the [RAG layer](#2-rag--askpy--maintenancepy--get-apiask).**
   Click any row in that anomaly table. The app calls
   `/api/ask?timestamp=...`, which *retrieves* the flagged reading plus any
   maintenance record covering that timestamp, then *generates* a verdict:
   either "this overlaps planned maintenance" or "this is genuine,
   unexplained underperformance."
4. **Compare the two causes.** Now click **"Explained by maintenance"**
   (row 2153) and ask about a row there. Same detector, same endpoint,
   opposite conclusion — a downtime the log accounts for. That contrast is
   the point: flagging an anomaly is easy, *triaging* it is the useful part.
5. **(Optional) Query it as an AI tool.** Everything above is also reachable
   over MCP — see [MCP server](#3-mcp-server--mcp_serverpy) below. In Claude Desktop you can
   ask "is this turbine healthy?" and it calls `get_turbine_summary()`
   itself, then drills into `explain_anomaly(timestamp)`.

## How it works

Three layers, in the order data moves through them: detection flags a
reading, RAG explains it, MCP exposes both to an assistant.

### 1. Anomaly detection — `deviation.py`

The dataset ships with a manufacturer-provided theoretical power curve, so
"expected output" doesn't need to be modeled — anomaly detection reduces
directly to measuring `actual vs. theoretical` deviation. The core design
decisions:

- **Deviation is normalized by rated power** (`(actual - theoretical) /
  rated_power`), not by the theoretical value itself. Dividing by the
  theoretical value blows up near cut-in, where it approaches zero —
  confirmed live during development (`inf`/`NaN` from division by near-zero).
  A constant, nonzero denominator makes that failure structurally impossible.
- **Cut-in/cut-out wind speeds define a trust boundary, not just a filter.**
  Outside this range the turbine is expected to sit idle by design, not by
  fault — flagging deviations there would be flagging the turbine for
  behaving correctly.
- **The anomaly threshold is derived from the data** (1st percentile of
  in-range deviation), not hardcoded, and compared against a mean−3σ
  alternative that turned out to flag 2.7x more rows due to the deviation
  distribution's skew.
- **A rule-based detector is compared against sklearn's Isolation Forest**
  trained on the same in-range data. They agree on only 39% of flagged rows —
  Isolation Forest flags rare-but-healthy high-wind operation (statistical
  rarity), while the rule-based approach flags genuine underperformance
  relative to the design curve. See `NOTLAR.md` for the full analysis.

### 2. RAG — `ask.py` + `maintenance.py` → `GET /api/ask`

Detection says *that* a reading is off. This layer answers *why*, which is
the part an operator actually acts on: a genuine fault needs a technician,
a logged maintenance window needs nothing.

- **Retrieval** — given a timestamp, it pulls the flagged reading, widens to
  the surrounding anomaly cluster, and looks for a maintenance record whose
  interval covers it (`maintenance.py`, over a structured JSON log).
- **Generation** — a **template**, not an LLM call, producing either
  "overlaps planned maintenance" or "genuine, unexplained underperformance."

**Why a template and not an LLM:** the question has a verifiable answer, so
a template structurally can't hallucinate a downtime that never happened,
and the whole path stays unit-testable. The LLM sits one layer up (see
below), deciding *which* tool to call rather than inventing the facts. Full
reasoning in `NOTLAR.md`, Phase 4.

Try it: click any row in the dashboard's anomaly table, or call
`GET /api/ask?timestamp=2018-01-11 09:40:00` directly.

### 3. MCP server — `mcp_server.py`

The same three functions, exposed as tools an AI assistant can call itself
over the Model Context Protocol — no HTTP, no glue code, zero duplicated
logic. This is where an LLM does belong: it decides which tool answers the
question and chains them ("is the turbine healthy?" → `get_turbine_summary`
→ `get_anomalies` → `explain_anomaly`).

Setup, the `claude_desktop_config.json` snippet, and a worked example
conversation are in [Running the MCP server](#running-the-mcp-server) below.

## Setup

```powershell
py -3.14 -m venv .venv --system-site-packages
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Dataset

See [data/raw/README.md](data/raw/README.md) for download instructions.

## Running

```powershell
$env:PYTHONPATH = "src"
python scripts/run_phase1.py
pytest tests/
```

This loads the data, reports data quality, computes deviation metrics, derives
an anomaly threshold, flags anomalies, and compares against Isolation Forest —
saving three figures to `outputs/figures/`.

### API server

```powershell
$env:PYTHONPATH = "src"
uvicorn turbinetwin.api:app --reload
```

Serves at `http://127.0.0.1:8000`. Interactive docs at `/docs`.

### Dashboard

Open `http://127.0.0.1:8000/` (same server, same command as above) for a
live dashboard: a power-curve chart, a status panel (wind speed, measured
power, deviation %, normal/idle/anomaly state), playback speed controls
(1x/10x/100x), and a running list of anomalies seen in the current session.
Plain HTML/JS (Chart.js via CDN, `EventSource` for the stream) — no build
step, no `npm install`.

- `GET /api/health` — readiness check, reports rows loaded at startup.
- `GET /api/window?start=0&limit=100` — a slice of the dataset as JSON,
  validated against the `TurbinePoint` schema.
- `GET /api/stream?speed=1|10|100` — replays the full dataset in timestamp
  order as Server-Sent Events, at 1x/10x/100x the original 10-minute
  cadence. See `NOTLAR.md` Step 2.8 for why 100x measures closer to ~54x in
  practice (Windows timer resolution).
- `GET /api/ask?timestamp=...` — rule-based RAG: explains whether a given
  reading was flagged as an anomaly and, if so, whether it overlaps a
  (synthetic) logged maintenance window or looks like a genuine,
  unexplained underperformance. Click a row in the dashboard's anomaly
  list to try it. See `NOTLAR.md` Phase 4 for why "generation" here is a
  template rather than an LLM call.

### Running the MCP server

Exposes the same turbine data to AI assistants (Claude Desktop, Cursor)
directly as tool calls, over the Model Context Protocol — no HTTP request
required. Same underlying `turbinetwin` functions as the API/dashboard
above; zero duplicated logic.

```powershell
$env:PYTHONPATH = "src"
python -m turbinetwin.mcp_server
```

To use it from Claude Desktop, add it to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "turbinetwin": {
      "command": "C:\\path\\to\\TurbineTwin\\.venv\\Scripts\\python.exe",
      "args": ["-m", "turbinetwin.mcp_server"],
      "env": { "PYTHONPATH": "C:\\path\\to\\TurbineTwin\\src" }
    }
  }
}
```

Three tools are exposed:

- `get_turbine_summary()` — row count, date range, anomaly count/percentage,
  and a `healthy`/`moderate`/`degraded` status label.
- `get_anomalies(limit=20)` — most recent flagged rows.
- `explain_anomaly(timestamp)` — same rule-based RAG answer as `/api/ask`,
  callable by name from the assistant's chat.

**Example Scenario (in Claude Desktop):**
> **You:** "What's the current status of the turbine?"  
> **Claude:** *(Calls `get_turbine_summary`)* "The turbine is currently in a 'moderate' state. It has processed 50,530 rows, with 428 anomalies detected (~0.85%)."  
> **You:** "Show me the most recent anomaly and explain why it happened."  
> **Claude:** *(Calls `get_anomalies`, then calls `explain_anomaly` with the timestamp)* "The most recent anomaly occurred on Dec 31 at 23:50. It was flagged because the measured power was 0.0 kW while the theoretical expectation was 2300 kW. However, this overlaps with a logged maintenance window, so it's a planned outage, not a turbine fault."

## Results

**Power curve** — measured output vs. the theoretical curve. The S-curve,
cut-in knee (~3 m/s), and rated plateau (3600 kW) are visible, along with a
dense underperformance cloud in the 5-12 m/s range.

![Power curve](outputs/figures/power_curve.png)

**Deviation distribution** — normalized deviation across in-range rows, with
the derived 1st-percentile threshold marked. The distribution is skewed: a
short tail down to -1.0 accounts for why percentile-based thresholding was
chosen over mean−3σ.

![Deviation distribution](outputs/figures/deviation_distribution.png)

**Flagged anomalies** — 428 rows (≈1% of in-range data) cluster almost
entirely in the 10-19 m/s band at near-zero power, despite the theoretical
curve predicting 2000-3600 kW there.

![Anomalies](outputs/figures/anomalies.png)

## Project structure

```
src/turbinetwin/   # core logic: data loading, deviation metrics, anomaly
                   # detection, plotting -- reused by later phases (API, MCP)
static/            # dashboard: plain HTML/JS, served by the API itself
scripts/           # entry points
data/              # raw (gitignored) and processed data, plus the
                   # synthetic maintenance log used by /api/ask
outputs/figures/   # generated plots (gitignored)
tests/             # sanity tests
NOTLAR.md          # detailed decision log and interview prep notes
```

## Future work

The current API replays historical data (the full 2018 dataset, played back
in timestamp order) rather than ingesting live measurements. Extending it to
accept a real, continuously arriving feed (e.g. a new reading every 10
minutes from an actual turbine) was considered and deliberately scoped out:
it would require the in-memory `STATE` to become mutable under concurrent
access — read by every request handler, written by whatever ingests new
readings — which needs proper concurrency handling (locking or a
message-queue-backed pipeline such as Kafka/RabbitMQ) to avoid race
conditions. That's real infrastructure work, not a prototype-scale addition,
so it was left out rather than half-implemented.

## Security

**Summary:** no SQL injection surface (there's no database), no secrets ever
committed (full git history checked), `pip-audit` clean, and every input
path tested by hand against malformed/malicious payloads. Five real issues
were found across two review passes and fixed, each with a regression test.
Two gaps are deliberately left open and documented rather than quietly
ignored: no rate limiting, and the container runs as root. Details below.

There's no database anywhere in this project (raw data is a CSV loaded into
a pandas DataFrame; the maintenance log is a static JSON file) — so there's
no SQL injection surface to test in the first place. The actual attack
surface here is the two places user input reaches the app: the `timestamp`
query param on `/api/ask`, and `start`/`limit` on `/api/window`. Both were
tested by hand against malformed/malicious input:

- **`GET /api/ask?timestamp=<script>alert(1)</script>`** used to raise
  unguarded inside `pd.Timestamp()` and return a bare 500. Fixed: the parse
  is now wrapped in a `try/except`, returning a clean
  `{"found_row": false, "answer": "Invalid timestamp format."}` instead.
  Every answer string also now echoes the *parsed* timestamp (`ts`), never
  the raw request string, so no request-influenced text reaches the
  response body unchanged.
- **The dashboard's RAG answer box** (`static/index.html`) used to insert
  that server text into the page via `innerHTML`. Even though the fix above
  means nothing attacker-controlled reaches it today, it's now built with
  `createElement`/`textContent` instead — defense in depth, so a future
  change to `ask.py` can't silently reopen an HTML-injection path.
- **`GET /api/window?start=-5&limit=999999999`** used to be accepted
  silently: a negative `start` wraps around via plain Python slicing
  instead of erroring, and `limit` was unbounded (a client could pull the
  full ~50k-row dataset in one response). Fixed with FastAPI's
  `Query(ge=0)` / `Query(le=1000)`, which now return a clean 422 instead.

All three are covered by regression tests (`test_ask.py`,
`test_api.py`) using the exact payloads that triggered them.

**2026-09-22 review (external, pre-outreach hardening pass).** Also checked:
dependency vulnerabilities (`pip-audit` — none found), whether secrets/`.env`
files were ever committed (`git log` over the full history — none), and CORS
(no `CORSMiddleware` is installed; the dashboard is served same-origin by
the same FastAPI app, so none is needed and none is a gap). Two real gaps
were found and fixed:

- **No HTTP security headers were sent** (`X-Content-Type-Options`,
  `X-Frame-Options`, `Content-Security-Policy`, `Referrer-Policy`) —
  confirmed missing on the live site. Added via a small
  `SecurityHeadersMiddleware` in `api.py`; the CSP allows the dashboard's
  actual script sources (self + the Chart.js CDN + its own inline
  `<script>`/`<style>`, since it has no build step) rather than a
  generic-but-wrong `default-src 'self'` that would have broken the chart.
- **`mcp_server.py`'s `get_anomalies(limit=...)` only clamped the upper
  bound.** A negative `limit` hit pandas' `.head(-n)` semantics (returns
  *almost the whole table*, the opposite of what a negative limit implies)
  instead of erroring. Now clamped to `[1, 200]`.

Not fixed, left as known scope/limitations (see `.ai/KNOWN_ISSUES.md`):

- **No rate limiting** on any `/api/*` route. Acceptable for a portfolio
  demo with no auth and no write operations, but a real gap if this app
  ever handles meaningfully sensitive data or cost-bearing operations;
  would belong at the Caddy layer (or `slowapi`) rather than in the app
  itself. Mass-targeting/DoS testing was out of scope for this review.
- **The Docker image runs as root** (no `USER` directive in `Dockerfile`).
  Low risk for a single-container, no-database, read-only-after-startup
  app with no volume mounts of sensitive host paths, but it's the kind of
  default-not-hardened choice worth calling out rather than leaving
  implicit.

## Status

All 5 phases complete. **Live at [https://turbinetwin.esadseyitoglu.xyz](https://turbinetwin.esadseyitoglu.xyz)** (Docker, Debian 12, Caddy reverse proxy with automatic HTTPS).

- **Phase 1** — data loading, deviation metrics, threshold derivation, anomaly flagging, Isolation Forest comparison
- **Phase 2** — FastAPI backend (`/api/health`, `/api/window`, `/api/stream`, `/api/demo-anomalies`)
- **Phase 3** — live dashboard (power-curve chart, status panel, playback speed control, anomaly list, "jump to a known anomaly" buttons)
- **Phase 4** — rule-based RAG (`/api/ask`) — click an anomaly row in the dashboard to explain it
- **Phase 5** — MCP server exposing the same logic as AI-callable tools

Test suite: **43/43 passing**. See `NOTLAR.md` for the full decision log.
