"""
Tests for the Phase 5 MCP server tools.

Strategy (same as Faz 2-4): test the tool handler functions directly as
Python callables -- no MCP wire protocol, no subprocess, no mocking of
the transport layer. The business logic lives in get_turbine_summary,
get_anomalies, and explain_anomaly (the MCP wrappers); we call them
directly and assert on their return values.

The module-level _load() in mcp_server.py runs at import time, so these
tests exercise the full data pipeline (load → enrich → flag) as a side
effect of the first import. That's the same approach FastAPI's lifespan
takes; it also means any broken pipeline step fails here too, not just
in integration tests.
"""

import pytest

import turbinetwin.mcp_server as srv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

KNOWN_ANOMALY_TS = "2018-01-16 05:00:00"   # bakımlı anomali — Faz 4 doğruladı
KNOWN_NORMAL_TS  = "2018-01-01 00:00:00"   # normal satır
MISSING_TS       = "2020-06-15 12:00:00"   # veride yok


# ---------------------------------------------------------------------------
# get_turbine_summary
# ---------------------------------------------------------------------------

class TestGetTurbineSummary:
    def test_returns_expected_keys(self):
        result = srv.get_turbine_summary()
        for key in (
            "total_rows", "in_range_rows", "date_from", "date_to",
            "anomaly_count", "anomaly_pct", "status",
        ):
            assert key in result, f"Missing key: {key}"

    def test_total_rows_positive(self):
        result = srv.get_turbine_summary()
        assert result["total_rows"] > 0

    def test_in_range_rows_not_greater_than_total(self):
        result = srv.get_turbine_summary()
        assert 0 < result["in_range_rows"] <= result["total_rows"]

    def test_anomaly_count_within_bounds(self):
        result = srv.get_turbine_summary()
        assert 0 <= result["anomaly_count"] <= result["total_rows"]

    def test_anomaly_pct_between_0_and_100(self):
        result = srv.get_turbine_summary()
        assert 0 <= result["anomaly_pct"] <= 100

    def test_anomaly_pct_is_rate_over_in_range_rows_not_total(self):
        # Regression test: anomaly_pct used to divide by total_rows even
        # though is_anomaly is only ever set within in_range rows, which
        # silently diluted the rate and made "healthy" always trigger
        # regardless of the real in-range anomaly rate. Fixed 2026-09-22.
        result = srv.get_turbine_summary()
        expected = round(result["anomaly_count"] / result["in_range_rows"] * 100, 2)
        assert result["anomaly_pct"] == expected

    def test_anomaly_pct_matches_derive_threshold_baseline(self):
        # derive_threshold() flags ~the bottom 1st percentile of in-range
        # deviation by construction, so the reported rate on the full
        # dataset (no filtering) should land close to that ~1% baseline --
        # not near 0% (the old total_rows-denominator bug) and not wildly
        # above 1% (which would mean the percentile logic itself broke).
        result = srv.get_turbine_summary()
        assert 0.5 <= result["anomaly_pct"] <= 2.0

    def test_status_is_valid_label(self):
        result = srv.get_turbine_summary()
        assert result["status"] in ("healthy", "moderate", "degraded")

    def test_status_thresholds_relative_to_baseline_rate(self):
        # With the ~1%-by-construction baseline, the full (unfiltered)
        # dataset should read "healthy" -- it's exactly the population the
        # threshold was derived from, not a degraded subset.
        result = srv.get_turbine_summary()
        assert result["status"] == "healthy"

    def test_date_from_before_date_to(self):
        result = srv.get_turbine_summary()
        assert result["date_from"] < result["date_to"]


# ---------------------------------------------------------------------------
# get_anomalies
# ---------------------------------------------------------------------------

class TestGetAnomalies:
    def test_default_limit_respected(self):
        result = srv.get_anomalies()
        assert len(result) <= 20

    def test_custom_limit_respected(self):
        result = srv.get_anomalies(limit=5)
        assert len(result) <= 5

    def test_hard_cap_at_200(self):
        # Even if caller asks for 9999, we should get at most 200
        result = srv.get_anomalies(limit=9999)
        assert len(result) <= 200

    def test_row_has_expected_keys(self):
        result = srv.get_anomalies(limit=1)
        assert len(result) >= 1, "Expected at least one anomaly in the dataset"
        row = result[0]
        for key in ("timestamp", "wind_speed", "active_power_kw", "theoretical_power_kw", "deviation_pct"):
            assert key in row, f"Missing key: {key}"

    def test_deviation_pct_is_negative_for_anomalies(self):
        # Anomalies are flagged when actual << theoretical → deviation_norm < threshold (negative)
        result = srv.get_anomalies(limit=10)
        for row in result:
            assert row["deviation_pct"] < 0, (
                f"Expected negative deviation for anomaly at {row['timestamp']}, "
                f"got {row['deviation_pct']}"
            )

    def test_rows_sorted_newest_first(self):
        result = srv.get_anomalies(limit=10)
        timestamps = [r["timestamp"] for r in result]
        assert timestamps == sorted(timestamps, reverse=True), "Should be newest-first"


# ---------------------------------------------------------------------------
# explain_anomaly
# ---------------------------------------------------------------------------

class TestExplainAnomaly:
    def test_known_anomaly_with_maintenance(self):
        result = srv.explain_anomaly(KNOWN_ANOMALY_TS)
        assert result["found_row"] is True
        assert result["is_anomaly"] is True
        assert result["explained_by_maintenance"] is True
        assert "maintenance_record" in result
        assert len(result["answer"]) > 20

    def test_normal_row_not_flagged(self):
        result = srv.explain_anomaly(KNOWN_NORMAL_TS)
        assert result["found_row"] is True
        assert result["is_anomaly"] is False
        assert "answer" in result

    def test_missing_timestamp_returns_not_found(self):
        result = srv.explain_anomaly(MISSING_TS)
        assert result["found_row"] is False
        assert "answer" in result

    def test_answer_is_nonempty_string(self):
        for ts in (KNOWN_ANOMALY_TS, KNOWN_NORMAL_TS, MISSING_TS):
            result = srv.explain_anomaly(ts)
            assert isinstance(result["answer"], str)
            assert len(result["answer"]) > 0

