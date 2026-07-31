import pandas as pd

from turbinetwin.data_loader import load_raw, report_data_quality
from turbinetwin.deviation import (
    add_normalized_deviation, add_operating_state, derive_threshold, flag_anomalies,
    run_isolation_forest,
)
from turbinetwin.plots import plot_power_curve, plot_deviation_distribution, plot_anomalies


def main() -> None:
    df = load_raw()
    report_data_quality(df)
    plot_power_curve(df)

    df = add_normalized_deviation(df)
    df = add_operating_state(df)
    percentile_threshold, mean_minus_3sigma = derive_threshold(df)
    print(f"1st percentile threshold: {percentile_threshold:.4f}")
    print(f"mean-3sigma threshold: {mean_minus_3sigma:.4f}")
    plot_deviation_distribution(df, percentile_threshold)

    df = flag_anomalies(df, percentile_threshold)
    print(f"Flagged anomalies: {df['is_anomaly'].sum()} ({df['is_anomaly'].mean():.2%} of all rows)")
    plot_anomalies(df)

    df = run_isolation_forest(df, contamination=0.01)
    print(f"Isolation Forest anomalies: {df['is_anomaly_iforest'].sum()}")
    print()
    print("Agreement between our rule and Isolation Forest (in_range rows only):")
    in_range = df[df["in_range"]]
    print(pd.crosstab(in_range["is_anomaly"], in_range["is_anomaly_iforest"]))


if __name__ == "__main__":
    main()
