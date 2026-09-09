import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from turbinetwin.ask import explain_anomaly
from turbinetwin.config import PROJECT_ROOT, SIMULATED_INTERVAL_SECONDS
from turbinetwin.data_loader import load_raw
from turbinetwin.deviation import (
    add_normalized_deviation, add_operating_state, derive_threshold, flag_anomalies,
    run_isolation_forest,
)
from turbinetwin.maintenance import load_maintenance_log
from turbinetwin.schemas import TurbinePoint
from turbinetwin.serialization import row_to_dict

# Module-level dict, filled once by lifespan below -- the "Awake()" of this
# server. Every request handler reads from it; nothing writes to it after
# startup (see NOTLAR.md "real-time ingestion" for why that's a deliberate
# scope boundary, not an oversight).
STATE = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    df = load_raw()
    df = add_normalized_deviation(df)
    df = add_operating_state(df)
    threshold, _ = derive_threshold(df)
    df = flag_anomalies(df, threshold)
    df = run_isolation_forest(df)  # cheap (~0.4s); kept for Step 2.5's live NaN demo

    STATE["df"] = df
    STATE["threshold"] = threshold
    STATE["maintenance_records"] = load_maintenance_log()  # Phase 4 -- see NOTLAR.md Step 4.1

    yield  # server is now ready to handle requests

    STATE.clear()


app = FastAPI(title="TurbineTwin API", lifespan=lifespan)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "rows_loaded": len(STATE["df"])}


@app.get("/api/window", response_model=list[TurbinePoint])
def get_window(start: int = 0, limit: int = 100):
    rows = STATE["df"].iloc[start:start + limit]
    return [row_to_dict(row) for _, row in rows.iterrows()]


async def event_generator(speed: int):
    # async generator: yields one SSE record, then awaits (yielding control
    # to the event loop -- NOT blocking it, unlike time.sleep) before the next.
    interval = SIMULATED_INTERVAL_SECONDS / speed
    for _, row in STATE["df"].iterrows():
        point = TurbinePoint(**row_to_dict(row))
        yield f"data: {point.model_dump_json()}\n\n"
        await asyncio.sleep(interval)


VALID_SPEEDS = (1, 10, 100)


@app.get("/api/stream")
async def stream_data(speed: int = 1):
    # Literal[1, 10, 100] looks cleaner but Pydantic 2.13 rejects the
    # string "10" -> int 10 coercion for int-typed Literal members here
    # (verified directly against Pydantic, not just FastAPI) -- so the
    # allowed-values check is done by hand instead.
    if speed not in VALID_SPEEDS:
        raise HTTPException(status_code=422, detail=f"speed must be one of {VALID_SPEEDS}")
    return StreamingResponse(event_generator(speed), media_type="text/event-stream")


@app.get("/api/ask")
def ask(timestamp: str):
    # Rule-based RAG: retrieval (row lookup + maintenance-window overlap,
    # see maintenance.py/ask.py) always runs; a template stands in for the
    # Generation step so this endpoint needs no LLM API key and no network
    # call to test (see NOTLAR.md Step 4.3 for the reasoning).
    return explain_anomaly(STATE["df"], timestamp, STATE["maintenance_records"])


# Mounted last and deliberately: a mount on "/" would otherwise shadow every
# /api/* route registered after it (FastAPI matches routes in registration
# order). Serves the Phase 3 dashboard (plain HTML/JS, no build step) from
# the same origin as the API -- same-origin means no CORS setup needed for
# EventSource/fetch calls from the page back to /api/*. html=True makes "/"
# resolve to static/index.html automatically.
app.mount("/", StaticFiles(directory=PROJECT_ROOT / "static", html=True), name="static")
