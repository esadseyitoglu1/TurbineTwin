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
