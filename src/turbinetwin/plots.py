import matplotlib.pyplot as plt
import pandas as pd

from turbinetwin.config import FIGURES_DIR


def plot_power_curve(df: pd.DataFrame) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))

    # alpha < 1 so 50k overlapping points show density instead of one solid blob
    ax.scatter(
        df["wind_speed"], df["active_power_kw"],
        alpha=0.1, s=5, color="steelblue", label="Measured power",
    )

    # theoretical values are a function of wind speed -> sort before drawing
    # a line, otherwise plot() connects points in row order and zigzags
    theoretical_sorted = df.sort_values("wind_speed")
    ax.plot(
        theoretical_sorted["wind_speed"], theoretical_sorted["theoretical_power_kw"],
        color="darkorange", linewidth=2, label="Theoretical power curve",
    )

    ax.set_xlabel("Wind speed (m/s)")
    ax.set_ylabel("Active power (kW)")
    ax.set_title("Measured vs. theoretical power curve")
    ax.legend()

    output_path = FIGURES_DIR / "power_curve.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {output_path}")


def plot_deviation_distribution(df: pd.DataFrame, percentile_threshold: float) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Only in_range rows: below cut-in, deviation is noise around zero and
    # would swamp the histogram with a meaningless spike.
    in_range_deviation = df.loc[df["in_range"], "deviation_norm"]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(in_range_deviation, bins=50, color="steelblue")
    ax.axvline(
        x=percentile_threshold, color="red", linestyle="--",
        label=f"1st percentile threshold ({percentile_threshold:.3f})",
    )

    ax.set_xlabel("deviation_norm")
    ax.set_ylabel("Row count")
    ax.set_title("Distribution of normalized deviation (in-range rows only)")
    ax.legend()

    output_path = FIGURES_DIR / "deviation_distribution.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {output_path}")
