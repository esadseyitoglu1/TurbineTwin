import numpy as np
from sklearn.ensemble import IsolationForest

from turbinetwin.config import CUT_IN, CUT_OUT

def add_naive_deviation(df):
    # NAIVE ON PURPOSE: theoretical_power_kw == 0 near cut-in produces
    # NaN (0/0) or inf (nonzero/0) -- proven live, kept here so the failure
    # is visible rather than silently patched away.
    df["deviation_rel"] = (df["active_power_kw"] - df["theoretical_power_kw"]) / df["theoretical_power_kw"]

    return df


def add_normalized_deviation(df):
    # RATED_POWER is derived from the data itself (the theoretical curve's
    # own peak), not hardcoded, so this stays correct even if the turbine
    # model in the dataset changes. A constant, nonzero denominator makes
    # division-by-zero structurally impossible, not just guarded against.
    rated_power = df["theoretical_power_kw"].max()
    df["deviation_norm"] = (df["active_power_kw"] - df["theoretical_power_kw"]) / rated_power

    return df


def add_operating_state(df):
    df["in_range"] = (df["wind_speed"] >= CUT_IN) & (df["wind_speed"] <= CUT_OUT)

    # np.where(condition, value_if_true, value_if_false) -- a vectorized
    # ternary. Nesting it lets us pick between 3 outcomes instead of 2.
    df["state"] = np.where(
        df["wind_speed"] < CUT_IN, "below_cut_in",
        np.where(df["wind_speed"] > CUT_OUT, "above_cut_out", "normal"),
    )

    return df


def derive_threshold(df):
    """Return (percentile_threshold, mean_minus_3sigma) computed only on
    in_range rows. Percentile is rank-based, so a few extreme values can't
    drag it around the way they inflate sigma and pull mean-3*sigma looser."""
    in_range_deviation = df.loc[df["in_range"], "deviation_norm"]

    percentile_threshold = np.nanpercentile(in_range_deviation, 1)

    mean = in_range_deviation.mean()
    std = in_range_deviation.std()
    mean_minus_3sigma = mean - 3 * std

    return percentile_threshold, mean_minus_3sigma


def flag_anomalies(df, threshold):
    df["is_anomaly"] = df["in_range"] & (df["deviation_norm"] < threshold)

    return df


def run_isolation_forest(df, contamination=0.01):
    # Fit only on in_range rows -- otherwise the dense cluster of
    # near-zero-wind/near-zero-power points below cut-in dominates and
    # this stops being a fair comparison against our own in_range-only rule.
    in_range_df = df[df["in_range"]]
    X = in_range_df[["wind_speed", "active_power_kw"]]

    model = IsolationForest(contamination=contamination, random_state=42)
    predictions = model.fit_predict(X)  # returns -1 (anomaly) / 1 (normal), not 0/1

    # predictions is aligned with in_range_df's row order; .loc with its
    # .index writes each result back to the matching row in the full df.
    df.loc[in_range_df.index, "is_anomaly_iforest"] = (predictions == -1)

    return df