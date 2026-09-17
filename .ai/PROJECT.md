# TurbineTwin — Project

## What it is
Prototype digital twin for wind turbine anomaly detection, built on real SCADA
data from a wind farm in Turkey (2018, 10-minute resolution, ~50k records).
Compares actual power output against the manufacturer's theoretical power
curve to flag deviations from design behavior.

Built to be shown to Eksim Enerji (energy company) — they gave a RAG/MCP
training session; this project deliberately demonstrates both, framed around
their digital-twin approach. Purpose: portfolio piece for an internship
application, sitting on the user's GitHub.

## Goals
- Demonstrate real anomaly-detection reasoning (not a black-box model) on
  real industrial data.
- Demonstrate RAG (retrieval half real and testable, generation half a
  template, architecturally ready for a real LLM call).
- Demonstrate MCP: the same core logic exposed as tools an AI assistant
  (Claude Desktop, Cursor) can call directly.
- Zero duplicated logic between the dashboard/API surface and the MCP surface.

## Tech stack
- Python 3.14 (venv, `--system-site-packages`)
- pandas, numpy, scikit-learn (`IsolationForest`)
- FastAPI + uvicorn, Pydantic v2 (response schemas)
- Plain HTML/JS dashboard (Chart.js via CDN, `EventSource`) — no build step
- `mcp[cli]` v2.x (`MCPServer`, stdio transport)
- pytest

## Architecture
Single core package `src/turbinetwin/` — all business logic lives here and is
reused by both the FastAPI layer and the MCP layer:
- `data_loader.py` — load + clean raw CSV
- `deviation.py` — normalized deviation, cut-in/cut-out state, threshold
  derivation, anomaly flagging, Isolation Forest comparison
- `maintenance.py` — synthetic maintenance log + date-range overlap lookup
- `ask.py` — rule-based RAG: `explain_anomaly()` (retrieval + templated answer)
- `schemas.py` / `serialization.py` — Pydantic response models, JSON-safe conversion
- `api.py` — FastAPI app: `/api/health`, `/api/window`, `/api/stream`, `/api/ask`;
  serves `static/` as the dashboard
- `mcp_server.py` — MCP tools (`get_turbine_summary`, `get_anomalies`,
  `explain_anomaly`) calling the exact same functions as `api.py`
- `plots.py` — figure generation for `outputs/figures/`

## Build / run / test
```powershell
py -3.14 -m venv .venv --system-site-packages
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:PYTHONPATH = "src"
python scripts/run_phase1.py      # data + model pipeline, saves figures
pytest tests/                     # full test suite

uvicorn turbinetwin.api:app --reload   # dashboard + API at http://127.0.0.1:8000
python -m turbinetwin.mcp_server       # MCP server, stdio transport
```

## Directory conventions
- `src/turbinetwin/` — core logic (only place business rules live)
- `static/` — dashboard, served by the API itself
- `scripts/` — entry points
- `data/raw/` (gitignored, see `data/raw/README.md`), `data/processed/`
  (tracked — includes `maintenance_log.json`)
- `outputs/figures/` — generated plots (gitignored)
- `tests/` — one test file per `src/turbinetwin/` module roughly
- `NOTLAR.md` — human-maintained, very detailed Turkish decision log +
  interview prep notes. This is the primary narrative record of *why*
  things were built the way they were; `.ai/DECISIONS.md` pulls out only
  what another agent needs without re-reading the whole thing.

## Constraints
- Windows development environment (PowerShell), Python 3.14.
- No real-time data ingestion — API replays historical data only (see
  DECISIONS.md for why this was scoped out rather than half-built).
