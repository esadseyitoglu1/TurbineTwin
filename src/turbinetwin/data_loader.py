import pandas as pd

from turbinetwin.config import RAW_DATA_PATH

# Column names as they appear in the raw CSV -> our snake_case working names.
COLUMN_RENAME_MAP = {
    "Date/Time": "timestamp",
    "LV ActivePower (kW)": "active_power_kw",
    "Wind Speed (m/s)": "wind_speed",
    "Theoretical_Power_Curve (KWh)": "theoretical_power_kw",
    "Wind Direction (°)": "wind_direction",
}


def load_raw() -> pd.DataFrame:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {RAW_DATA_PATH}. "
            "See data/raw/README.md for download instructions."
        )

    df = pd.read_csv(RAW_DATA_PATH)
    # Day-first format, confirmed by a "31 12 2018" row in the raw file
    # (31 can never be a month) -- see data/raw/README.md.
    df["Date/Time"] = pd.to_datetime(df["Date/Time"], format="%d %m %Y %H:%M")
    df = df.rename(columns=COLUMN_RENAME_MAP)

    # Defensive: today's file happens to already be duplicate-free and sorted,
    # but nothing guarantees a different export of this dataset would be.
    df = df.drop_duplicates(subset=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def report_data_quality(df: pd.DataFrame) -> None:
    """Print a read-only summary of gaps and known SCADA quirks. Does not
    modify df -- negative idle-mode power readings are real sensor behavior,
    not corrupted data, so we report them instead of "fixing" them away."""
    expected = pd.date_range(df["timestamp"].min(), df["timestamp"].max(), freq="10min")
    missing_count = len(expected) - len(df)
    gaps = df["timestamp"].diff()
    biggest_gap = gaps.max()

    negative_power = df[df["active_power_kw"] < 0]

    print(f"Rows: {len(df)} (expected {len(expected)} for a full year at 10-min steps)")
    print(f"Missing timestamps: {missing_count}")
    print(f"Largest single gap: {biggest_gap}")
    print(
        f"Negative active_power_kw rows: {len(negative_power)} "
        f"(range {negative_power['active_power_kw'].min():.2f} to "
        f"{negative_power['active_power_kw'].max():.2f} kW) "
        "-- idle-mode self-consumption, not an error"
    )
