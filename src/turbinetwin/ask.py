import pandas as pd

from turbinetwin.maintenance import find_overlapping_records

# Rule-based "generation" step, not an LLM call -- see NOTLAR.md Step 4.3
# for why: this is the retrieval half of RAG made visible and testable,
# with no API key, network dependency, or mocking required to exercise it.


def find_anomaly_window(df: pd.DataFrame, around: pd.Timestamp, pad_minutes: int = 30):
    """Return the contiguous run of flagged rows containing `around` (plus
    a small buffer on each side), or None if `around` isn't itself
    anomalous. Rows are 10-min steps, so a "contiguous run" is found by
    walking outward from the matched row while is_anomaly stays True."""
    matches = df[df["timestamp"] == around]
    if matches.empty or not matches.iloc[0]["is_anomaly"]:
        return None

    idx = matches.index[0]
    start_idx = idx
    while start_idx > 0 and df.loc[start_idx - 1, "is_anomaly"]:
        start_idx -= 1
    end_idx = idx
    while end_idx < len(df) - 1 and df.loc[end_idx + 1, "is_anomaly"]:
        end_idx += 1

    window_start = df.loc[start_idx, "timestamp"] - pd.Timedelta(minutes=pad_minutes)
    window_end = df.loc[end_idx, "timestamp"] + pd.Timedelta(minutes=pad_minutes)
    return {
        "start": df.loc[start_idx, "timestamp"],
        "end": df.loc[end_idx, "timestamp"],
        "row_count": end_idx - start_idx + 1,
        "search_start": window_start,
        "search_end": window_end,
    }


def explain_anomaly(df: pd.DataFrame, timestamp: str, maintenance_records: list[dict]) -> dict:
    """Answer "why was this row flagged?" by combining two lookups: the
    row's own deviation data (already in df, no retrieval needed) and
    whether a maintenance record overlaps its anomaly cluster (retrieval).
    Returns a structured result plus a template-generated sentence --
    this structured half is what a real LLM call would receive as
    context in a non-rule-based Generation step."""
    ts = pd.Timestamp(timestamp)
    row_matches = df[df["timestamp"] == ts]

    if row_matches.empty:
        return {
            "found_row": False,
            "answer": f"No data point found at {timestamp}.",
        }

    row = row_matches.iloc[0]

    if not row["is_anomaly"]:
        return {
            "found_row": True,
            "is_anomaly": False,
            "answer": (
                f"The reading at {timestamp} was not flagged as an anomaly "
                f"(deviation {row['deviation_norm'] * 100:.1f}%, state: {row['state']})."
            ),
        }

    window = find_anomaly_window(df, ts)
    matches = find_overlapping_records(maintenance_records, window["search_start"], window["search_end"])

    if matches:
        record = matches[0]  # newest/first overlapping record is enough for this scale
        answer = (
            f"The reading at {timestamp} was flagged as an anomaly "
            f"(deviation {row['deviation_norm'] * 100:.1f}% at {row['wind_speed']:.1f} m/s wind), "
            f"but it falls within a logged maintenance window: {record['work_order']} "
            f"({record['start']:%Y-%m-%d %H:%M}-{record['end']:%H:%M}, technician {record['technician']}, "
            f"ref {record['id']}). This is very likely explained by planned downtime, not equipment failure."
        )
        return {
            "found_row": True,
            "is_anomaly": True,
            "explained_by_maintenance": True,
            "maintenance_record": record["id"],
            "answer": answer,
        }

    answer = (
        f"The reading at {timestamp} was flagged as an anomaly "
        f"(deviation {row['deviation_norm'] * 100:.1f}% at {row['wind_speed']:.1f} m/s wind), "
        f"part of a {window['row_count']}-row cluster from {window['start']:%Y-%m-%d %H:%M} "
        f"to {window['end']:%H:%M}. No maintenance record overlaps this window -- "
        f"this looks like a genuine, unexplained underperformance rather than planned downtime."
    )
    return {
        "found_row": True,
        "is_anomaly": True,
        "explained_by_maintenance": False,
        "answer": answer,
    }
