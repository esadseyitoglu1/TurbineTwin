from turbinetwin.data_loader import load_raw, report_data_quality
from turbinetwin.plots import plot_power_curve


def main() -> None:
    df = load_raw()
    report_data_quality(df)
    plot_power_curve(df)


if __name__ == "__main__":
    main()
