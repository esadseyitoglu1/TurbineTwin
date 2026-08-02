def row_to_dict(row):
    return {
        "timestamp": row["timestamp"].isoformat(),
        "wind_speed": row["wind_speed"],
        "active_power_kw": row["active_power_kw"],
        "theoretical_power_kw": row["theoretical_power_kw"],
        "deviation_pct": row["deviation_norm"] * 100,
        "in_range": row["in_range"],
        "is_anomaly": row["is_anomaly"],
    }
