def row_to_dict(row):
    return {
        "timestamp": row["timestamp"].isoformat(),
        "wind_speed": row["wind_speed"],
        "active_power_kw": row["active_power_kw"],
        "theoretical_power_kw": row["theoretical_power_kw"],
        "deviation_norm": row["deviation_norm"],
        "in_range": bool(row["in_range"]),
        "is_anomaly": bool(row["is_anomaly"]),
    }
