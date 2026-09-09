import json

import pandas as pd

from turbinetwin.config import MAINTENANCE_LOG_PATH


def load_maintenance_log() -> list[dict]:
    """Load the synthetic maintenance records (see NOTLAR.md Step 4.1).
    Small, structured, hand-written data -- no embedding/vector search
    needed, a plain date-range overlap check is enough."""
    with open(MAINTENANCE_LOG_PATH, encoding="utf-8") as f:
        records = json.load(f)

    for record in records:
        record["start"] = pd.Timestamp(record["start"])
        record["end"] = pd.Timestamp(record["end"])

    return records


def find_overlapping_records(records: list[dict], start, end) -> list[dict]:
    """Return maintenance records whose [start, end] window overlaps the
    given [start, end] window. Overlap, not exact match -- a real
    maintenance window and the anomaly cluster it caused rarely line up
    to the minute (the crew arrives before the turbine actually drops
    to zero output, and the record's own window is a few minutes wider
    than the flagged rows on either side)."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    return [
        record for record in records
        if record["start"] <= end and record["end"] >= start
    ]
