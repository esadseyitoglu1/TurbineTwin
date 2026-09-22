import asyncio
import json

from fastapi.testclient import TestClient

from turbinetwin.api import app, event_generator, stream_data
from turbinetwin.config import DEMO_ANOMALY_START_MAINTENANCE, DEMO_ANOMALY_START_UNEXPLAINED

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


def test_window_rejects_negative_start():
    # Previously silently accepted -- a negative `start` fed straight into
    # `.iloc[start:...]` wraps around via plain Python slicing instead of
    # erroring. Query(ge=0) turns that into a clean 422.
    with TestClient(app) as client:
        response = client.get("/api/window", params={"start": -5, "limit": 10})

    assert response.status_code == 422


def test_window_rejects_excessive_limit():
    # Previously unbounded -- a client could request the full ~50k-row
    # dataset in a single response. Query(le=1000) caps it.
    with TestClient(app) as client:
        response = client.get("/api/window", params={"start": 0, "limit": 999_999})

    assert response.status_code == 422


def test_ask_with_malformed_timestamp_returns_clean_response():
    # Confirmed live before the fix: this raised inside pd.Timestamp() and
    # the endpoint returned a bare 500. Now it's a normal 200 with
    # found_row: False, same shape as any other "no match" answer.
    with TestClient(app) as client:
        response = client.get("/api/ask", params={"timestamp": "<script>alert(1)</script>"})

    assert response.status_code == 200
    body = response.json()
    assert body["found_row"] is False


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


def test_event_generator_start_skips_to_offset_not_row_zero():
    # Regression test for the "first anomaly takes ~2.5 real-time minutes
    # to reach at default speed" demo-usability issue an external reviewer
    # flagged ahead of a presentation (2026-09-22): `start` must actually
    # skip rows, not just get accepted and ignored.
    async def get_first_record_at_offset(offset):
        with TestClient(app):
            generator = event_generator(speed=100, start=offset)
            return await generator.__anext__()

    first_at_zero = asyncio.run(get_first_record_at_offset(0))
    first_at_offset = asyncio.run(get_first_record_at_offset(1475))

    point_at_zero = json.loads(first_at_zero.removeprefix("data: ").strip())
    point_at_offset = json.loads(first_at_offset.removeprefix("data: ").strip())

    assert point_at_zero["timestamp"] != point_at_offset["timestamp"]
    assert point_at_offset["timestamp"].startswith("2018-01-11")


def test_stream_rejects_start_at_or_past_end_of_dataset():
    with TestClient(app) as client:
        response = client.get("/api/health")
        total_rows = response.json()["rows_loaded"]
        response = client.get("/api/stream", params={"speed": 100, "start": total_rows})

    assert response.status_code == 422


def test_stream_rejects_negative_start():
    with TestClient(app) as client:
        response = client.get("/api/stream", params={"speed": 100, "start": -1})

    assert response.status_code == 422


def test_demo_anomalies_returns_both_scenarios_with_valid_offsets():
    with TestClient(app) as client:
        health = client.get("/api/health")
        total_rows = health.json()["rows_loaded"]
        response = client.get("/api/demo-anomalies")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"unexplained", "maintenance"}
    for key in ("unexplained", "maintenance"):
        assert "label" in body[key]
        assert 0 <= body[key]["start"] < total_rows
    assert body["unexplained"]["start"] == DEMO_ANOMALY_START_UNEXPLAINED
    assert body["maintenance"]["start"] == DEMO_ANOMALY_START_MAINTENANCE


def test_demo_anomaly_offsets_actually_lead_into_their_intended_anomaly():
    # The config comments claim specific row offsets land shortly before a
    # specific timestamp's anomaly. This walks the real stream forward from
    # each offset and confirms an is_anomaly=True row with the expected
    # date actually shows up within a short lead-in, rather than trusting
    # the comment in config.py to stay accurate.
    async def find_first_anomaly_after(offset, max_rows=30):
        with TestClient(app):
            generator = event_generator(speed=100, start=offset)
            for _ in range(max_rows):
                record = await generator.__anext__()
                point = json.loads(record.removeprefix("data: ").strip())
                if point["is_anomaly"]:
                    return point
        return None

    unexplained_point = asyncio.run(find_first_anomaly_after(DEMO_ANOMALY_START_UNEXPLAINED))
    maintenance_point = asyncio.run(find_first_anomaly_after(DEMO_ANOMALY_START_MAINTENANCE))

    assert unexplained_point is not None
    assert unexplained_point["timestamp"].startswith("2018-01-11")
    assert maintenance_point is not None
    assert maintenance_point["timestamp"].startswith("2018-01-16")
