"""
TurbineTwin MCP Server (Phase 5)
=================================
Exposes three tools over the Model Context Protocol so AI assistants
(Claude Desktop, Cursor, etc.) can query the turbine directly by name:

    get_turbine_summary   -- high-level fleet health numbers
    get_anomalies         -- list of recent anomaly rows
    explain_anomaly       -- Phase 4 RAG answer for a specific timestamp

Run with:
    python -m turbinetwin.mcp_server          (production, stdio transport)
    mcp dev src/turbinetwin/mcp_server.py     (MCP Inspector, interactive)

The server loads the dataset once at import time and keeps it in module-level
variables -- the same "load once, read many" pattern as FastAPI's STATE dict,
but without the async lifespan wrapper (mcp.run() manages its own event loop).
"""

import asyncio

import pandas as pd
from mcp.server.mcpserver import MCPServer

from turbinetwin.ask import explain_anomaly as _explain_anomaly
from turbinetwin.data_loader import load_raw
from turbinetwin.deviation import (
    add_normalized_deviation,
    add_operating_state,
    derive_threshold,
    flag_anomalies,
    run_isolation_forest,
)
from turbinetwin.maintenance import load_maintenance_log

# ---------------------------------------------------------------------------
# Module-level state — loaded once when the process starts.
# Tools are pure readers; nothing writes after this point.
# ---------------------------------------------------------------------------

_df: pd.DataFrame
_maintenance_records: list[dict]


def _load():
    """Build the enriched DataFrame and load maintenance records.
    Called once at module import so both the server entry-point and the
    test suite share the same initialisation path without duplication."""
    global _df, _maintenance_records

    df = load_raw()
    df = add_normalized_deviation(df)
    df = add_operating_state(df)
    threshold, _ = derive_threshold(df)
    df = flag_anomalies(df, threshold)
    df = run_isolation_forest(df)

    _df = df
    _maintenance_records = load_maintenance_log()


_load()

# ---------------------------------------------------------------------------
# MCP server definition (mcp 2.x -- MCPServer replaces FastMCP)
# ---------------------------------------------------------------------------

mcp = MCPServer(
    "TurbineTwin",
    instructions=(
        "You have access to a wind-turbine digital twin. "
        "Use get_turbine_summary for an overview, get_anomalies to list "
        "recent underperformance events, and explain_anomaly to look up "
        "whether a specific event was caused by planned maintenance or is "
        "unexplained underperformance."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1 — Overall health snapshot
# ---------------------------------------------------------------------------

@mcp.tool()
def get_turbine_summary() -> dict:
    """Return a high-level health summary for the turbine dataset.

    Includes total row count, date range, number and percentage of anomalies,
    and a plain-English status label.
    """
    total = len(_df)
    anomalies = int(_df["is_anomaly"].sum())

    # Anomalies are only ever flagged among in_range rows (see
    # deviation.flag_anomalies), so the rate has to be taken over that same
    # denominator. Dividing by `total` instead silently dilutes the rate by
    # however many below-cut-in / above-cut-out rows exist in the window,
    # which made the status label meaningless in practice (it always read
    # "healthy" regardless of the actual in-range anomaly rate). Fixed
    # 2026-09-22, flagged by an external review ahead of a demo.
    in_range_total = int(_df["in_range"].sum())
    pct = round(anomalies / in_range_total * 100, 2) if in_range_total else 0.0

    ts_min = _df["timestamp"].min()
    ts_max = _df["timestamp"].max()

    # derive_threshold() flags roughly the bottom 1st percentile of in-range
    # deviation by construction, so ~1% is the *expected* baseline rate, not
    # a sign of trouble. Thresholds are set relative to that baseline rather
    # than at round numbers that happened to sit below it.
    if pct < 1.5:
        status = "healthy"
    elif pct < 3:
        status = "moderate"
    else:
        status = "degraded"

    return {
        "total_rows": total,
        "in_range_rows": in_range_total,
        "date_from": ts_min.isoformat(),
        "date_to": ts_max.isoformat(),
        "anomaly_count": anomalies,
        "anomaly_pct": pct,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Tool 2 — Anomaly list
# ---------------------------------------------------------------------------

@mcp.tool()
def get_anomalies(limit: int = 20) -> list[dict]:
    """Return the most recent anomaly rows from the turbine dataset.

    Args:
        limit: Maximum number of rows to return (default 20, max 200).

    Each row contains timestamp, wind_speed, active_power_kw, theoretical_power_kw,
    and deviation_pct (normalised deviation expressed as a percentage).
    """
    # Clamp both ends: an unclamped upper bound risks accidentally huge
    # responses, and a negative limit isn't just "0 rows" -- pandas'
    # .head(-n) returns all-but-the-last-n rows, i.e. almost the whole
    # anomaly table, the opposite of what a negative limit implies.
    limit = max(1, min(limit, 200))

    anomaly_df = (
        _df[_df["is_anomaly"]]
        .sort_values("timestamp", ascending=False)
        .head(limit)
    )

    rows = []
    for _, row in anomaly_df.iterrows():
        rows.append({
            "timestamp": row["timestamp"].isoformat(),
            "wind_speed": round(float(row["wind_speed"]), 2),
            "active_power_kw": round(float(row["active_power_kw"]), 2),
            "theoretical_power_kw": round(float(row["theoretical_power_kw"]), 2),
            "deviation_pct": round(float(row["deviation_norm"]) * 100, 1),
        })

    return rows


# ---------------------------------------------------------------------------
# Tool 3 — Explain a specific anomaly (Phase 4 RAG, MCP-accessible)
# ---------------------------------------------------------------------------

@mcp.tool()
def explain_anomaly(timestamp: str) -> dict:
    """Explain why a specific turbine reading was (or was not) flagged as anomalous.

    Uses the Phase 4 rule-based RAG engine: looks up the data point, finds the
    surrounding anomaly cluster, and checks whether a maintenance record overlaps
    that window.

    Args:
        timestamp: ISO 8601 string, e.g. "2018-01-16 05:00:00".
                   Must match a 10-minute step in the dataset.

    Returns a dict with:
        found_row             -- whether the timestamp exists in the dataset
        is_anomaly            -- whether the row was flagged
        explained_by_maintenance -- True if a maintenance record overlaps
        maintenance_record    -- work-order ID if found
        answer                -- human-readable explanation sentence
    """
    return _explain_anomaly(_df, timestamp, _maintenance_records)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # stdio transport is what Claude Desktop / Cursor read from mcpServers config.
    # mcp 2.x: run_stdio_async() replaces the old mcp.run(transport="stdio") shorthand.
    asyncio.run(mcp.run_stdio_async())
