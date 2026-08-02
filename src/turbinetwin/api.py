import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from turbinetwin.data_loader import load_raw
from turbinetwin.deviation import (
    add_normalized_deviation, add_operating_state, derive_threshold, flag_anomalies,
    run_isolation_forest,
)
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


async def event_generator():
    # async generator: yields one SSE record, then awaits (yielding control
    # to the event loop -- NOT blocking it, unlike time.sleep) before the next.
    for _, row in STATE["df"].iterrows():
        point = TurbinePoint(**row_to_dict(row))
        yield f"data: {point.model_dump_json()}\n\n"
        await asyncio.sleep(1)  # fixed 1x for now; speed control comes in Step 2.8


@app.get("/api/stream")
async def stream_data():
    return StreamingResponse(event_generator(), media_type="text/event-stream")
