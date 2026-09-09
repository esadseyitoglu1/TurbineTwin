import pandas as pd

from turbinetwin.ask import explain_anomaly
from turbinetwin.maintenance import find_overlapping_records


def make_maintenance_record(start, end, work_order="Test maintenance"):
    return {
        "id": "MNT-TEST",
        "start": pd.Timestamp(start),
        "end": pd.Timestamp(end),
        "technician": "Test Tech",
        "work_order": work_order,
        "notes": "",
    }


def make_df(rows):
    # rows: list of (timestamp, wind_speed, deviation_norm, is_anomaly, state)
    return pd.DataFrame([
        {
            "timestamp": pd.Timestamp(ts),
            "wind_speed": wind,
            "deviation_norm": dev,
            "is_anomaly": anomaly,
            "state": state,
        }
        for ts, wind, dev, anomaly, state in rows
    ])


def test_find_overlapping_records_matches_partial_overlap():
    # A maintenance window and an anomaly cluster rarely line up exactly
    # -- overlap, not exact equality, is the contract (see maintenance.py).
    records = [make_maintenance_record("2018-01-16 01:00", "2018-01-16 11:00")]

    assert find_overlapping_records(records, "2018-01-16 05:00", "2018-01-16 06:00") == records
    assert find_overlapping_records(records, "2018-01-17 00:00", "2018-01-17 01:00") == []


def test_explain_anomaly_finds_maintenance_record():
    df = make_df([("2018-01-16 05:00", 14.4, -1.0, True, "normal")])
    records = [make_maintenance_record("2018-01-16 01:00", "2018-01-16 11:00", "Rotor bearing replacement")]

    result = explain_anomaly(df, "2018-01-16 05:00", records)

    assert result["is_anomaly"] is True
    assert result["explained_by_maintenance"] is True
    assert "Rotor bearing replacement" in result["answer"]


def test_explain_anomaly_reports_unexplained_when_no_record_overlaps():
    df = make_df([("2018-01-25 00:30", 10.8, -0.887, True, "normal")])

    result = explain_anomaly(df, "2018-01-25 00:30", maintenance_records=[])

    assert result["is_anomaly"] is True
    assert result["explained_by_maintenance"] is False
    assert "genuine" in result["answer"] or "unexplained" in result["answer"]


def test_explain_anomaly_on_non_anomalous_row():
    df = make_df([("2018-01-01 00:00", 5.3, -0.01, False, "normal")])

    result = explain_anomaly(df, "2018-01-01 00:00", maintenance_records=[])

    assert result["is_anomaly"] is False
    assert "not flagged" in result["answer"]


def test_explain_anomaly_on_missing_timestamp():
    df = make_df([("2018-01-01 00:00", 5.3, -0.01, False, "normal")])

    result = explain_anomaly(df, "2020-01-01 00:00", maintenance_records=[])

    assert result["found_row"] is False
