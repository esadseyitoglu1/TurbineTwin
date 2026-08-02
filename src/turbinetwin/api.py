from contextlib import asynccontextmanager

from fastapi import FastAPI

from turbinetwin.data_loader import load_raw
from turbinetwin.deviation import (
    add_normalized_deviation, add_operating_state, derive_threshold, flag_anomalies,
    run_isolation_forest,
)

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
