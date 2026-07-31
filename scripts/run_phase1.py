from turbinetwin.data_loader import load_raw, report_data_quality
from turbinetwin.deviation import add_normalized_deviation, add_operating_state, derive_threshold
from turbinetwin.plots import plot_power_curve, plot_deviation_distribution


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


if __name__ == "__main__":
    main()
