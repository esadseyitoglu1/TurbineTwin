import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from turbinetwin.ask import explain_anomaly
from turbinetwin.config import (
    DEMO_ANOMALY_START_MAINTENANCE,
    DEMO_ANOMALY_START_UNEXPLAINED,
    PROJECT_ROOT,
    SIMULATED_INTERVAL_SECONDS,
)
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline hardening headers absent from FastAPI/uvicorn defaults.
    Found missing on every response (including in production, verified live
    2026-09-22) by an external security review -- nothing here changes
    behavior, it only tells the browser to be stricter about how the
    response it already received may be used.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Not a bare "default-src 'self'": static/index.html loads Chart.js
        # from jsdelivr and has an inline <style>/<script> block (no build
        # step, see the StaticFiles mount comment below), so a stricter
        # policy would silently break the live dashboard. This still blocks
        # the two things that matter for a same-origin app with no forms:
        # framing (frame-ancestors) and any *other* third-party script/object
        # source (object-src, default-src).
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "object-src 'none'; "
            "frame-ancestors 'none'"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "rows_loaded": len(STATE["df"])}


@app.get("/api/window", response_model=list[TurbinePoint])
def get_window(start: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    # ge/le turn an out-of-range value into a clean 422 instead of, e.g.,
    # a negative `start` silently wrapping to the end of the dataset via
    # Python slicing, or an unbounded `limit` returning the full ~50k rows
    # in one response.
    rows = STATE["df"].iloc[start:start + limit]
    return [row_to_dict(row) for _, row in rows.iterrows()]


async def event_generator(speed: int, start: int = 0):
    # async generator: yields one SSE record, then awaits (yielding control
    # to the event loop -- NOT blocking it, unlike time.sleep) before the next.
    #
    # `start` lets a caller skip straight to a row offset instead of always
    # replaying from row 0. Added so the dashboard's "jump to a known
    # anomaly" buttons don't have to wait through several real-time minutes
    # of normal operation before the point of interest streams in -- flagged
    # as a real demo-usability problem by an external reviewer ahead of a
    # presentation (2026-09-22).
    interval = SIMULATED_INTERVAL_SECONDS / speed
    for _, row in STATE["df"].iloc[start:].iterrows():
        point = TurbinePoint(**row_to_dict(row))
        yield f"data: {point.model_dump_json()}\n\n"
        await asyncio.sleep(interval)


VALID_SPEEDS = (1, 10, 100)


@app.get("/api/stream")
async def stream_data(speed: int = 1, start: int = 0):
    # Literal[1, 10, 100] looks cleaner but Pydantic 2.13 rejects the
    # string "10" -> int 10 coercion for int-typed Literal members here
    # (verified directly against Pydantic, not just FastAPI) -- so the
    # allowed-values check is done by hand instead.
    #
    # `start` is validated by hand (not Query(ge=0)) for the same reason
    # `speed`'s allowed-values check is manual: test_api.py calls this
    # route function directly, bypassing the ASGI layer that would
    # otherwise resolve a Query(...) default into a plain int -- see
    # test_stream_endpoint_returns_sse_streaming_response.
    if speed not in VALID_SPEEDS:
        raise HTTPException(status_code=422, detail=f"speed must be one of {VALID_SPEEDS}")
    total_rows = len(STATE["df"])
    if start < 0 or start >= total_rows:
        raise HTTPException(
            status_code=422, detail=f"start must be in [0, {total_rows})"
        )
    return StreamingResponse(event_generator(speed, start), media_type="text/event-stream")


@app.get("/api/demo-anomalies")
def demo_anomalies():
    # Backs the dashboard's "jump to a known anomaly" buttons -- the
    # frontend asks the backend where to jump instead of hardcoding row
    # offsets in static/index.html, so the two stay in sync if the dataset
    # or the offsets in config.py ever change.
    return {
        "unexplained": {
            "label": "Unexplained anomaly (no maintenance match)",
            "start": DEMO_ANOMALY_START_UNEXPLAINED,
        },
        "maintenance": {
            "label": "Anomaly explained by maintenance",
            "start": DEMO_ANOMALY_START_MAINTENANCE,
        },
    }


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
