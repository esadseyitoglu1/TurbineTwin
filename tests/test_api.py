import asyncio

from fastapi.testclient import TestClient

from turbinetwin.api import app, event_generator, stream_data

# TestClient as a context manager (the `with` block) is required here --
# it's what actually triggers `lifespan`, which is where STATE gets filled.
# Without `with`, STATE stays empty and every request would 500.


def test_health_reports_rows_loaded():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["rows_loaded"] > 0


def test_window_returns_requested_slice_size():
    with TestClient(app) as client:
        response = client.get("/api/window", params={"start": 0, "limit": 5})

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 5
    # response_model=list[TurbinePoint] -- exactly these 7 fields, nothing
    # else (is_anomaly_iforest must not leak through even though it's on
    # the underlying DataFrame; see NOTLAR.md Step 2.6).
    assert set(rows[0].keys()) == {
        "timestamp", "wind_speed", "active_power_kw", "theoretical_power_kw",
        "deviation_pct", "in_range", "is_anomaly",
    }


def test_window_on_row_that_previously_crashed_with_nan_iforest_field():
    # Row 384 is below cut-in (in_range=False) and was the row that
    # exposed the original 500: is_anomaly_iforest is NaN there because
    # Isolation Forest only fits in-range rows (see deviation.py). This
    # is a regression test for Step 2.4/2.5's fix.
    with TestClient(app) as client:
        response = client.get("/api/window", params={"start": 384, "limit": 1})

    assert response.status_code == 200
    assert response.json()[0]["in_range"] is False


def test_stream_rejects_invalid_speed():
    with TestClient(app) as client:
        response = client.get("/api/stream", params={"speed": 7})

    assert response.status_code == 422


def test_stream_endpoint_returns_sse_streaming_response():
    # Calls the route function directly (no ASGI/HTTP layer, no TestClient)
    # so the ~50k-row body is never touched -- only the envelope FastAPI
    # would send (media_type) is checked.
    async def get_response():
        with TestClient(app):  # runs lifespan, populates STATE
            return await stream_data(speed=100)

    response = asyncio.run(get_response())

    assert response.media_type == "text/event-stream"


def test_event_generator_emits_one_sse_record_per_row():
    # Exercises the generator function directly, bypassing the HTTP/ASGI
    # layer entirely -- lets us pull exactly one item with __anext__()
    # instead of waiting on (or fighting) the full streamed response.
    async def get_first_record():
        with TestClient(app):  # runs lifespan, populates STATE
            generator = event_generator(speed=100)
            return await generator.__anext__()

    first_record = asyncio.run(get_first_record())

    assert first_record.startswith("data: ")
    assert first_record.endswith("\n\n")
