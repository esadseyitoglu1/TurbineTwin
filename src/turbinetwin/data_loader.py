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
    return df
