import pandas as pd

from turbinetwin.deviation import add_normalized_deviation, add_operating_state, flag_anomalies


def make_row(wind_speed, active_power_kw, theoretical_power_kw):
    return pd.DataFrame([{
        "wind_speed": wind_speed,
        "active_power_kw": active_power_kw,
        "theoretical_power_kw": theoretical_power_kw,
    }])


def test_normalized_deviation_never_produces_inf_near_zero_theoretical():
    # theoretical_power_kw == 0 broke deviation_rel (0/0 -> NaN,
    # nonzero/0 -> inf). RATED_POWER is derived from .max(), so the
    # fixture needs a rated-capacity row too, or RATED_POWER itself
    # becomes 0 and reproduces the same bug from a different angle.
    df = pd.concat([
        make_row(wind_speed=2.9, active_power_kw=5.0, theoretical_power_kw=0.0),
        make_row(wind_speed=12.0, active_power_kw=3600.0, theoretical_power_kw=3600.0),
    ], ignore_index=True)
    df = add_normalized_deviation(df)

    assert df["deviation_norm"].notna().all()
    assert (df["deviation_norm"].abs() != float("inf")).all()


def test_below_cut_in_is_never_flagged_as_anomaly():
    # Wind speed 1.5 m/s is below CUT_IN (3.0) -- the turbine is expected
    # to sit idle here, so even a large deviation must not be flagged.
    df = make_row(wind_speed=1.5, active_power_kw=0.0, theoretical_power_kw=0.0)
    df = add_normalized_deviation(df)
    df = add_operating_state(df)
    df = flag_anomalies(df, threshold=-0.01)  # a loose threshold on purpose

    assert not df["is_anomaly"].any()


def test_deviation_is_near_zero_when_output_matches_theoretical():
    df = make_row(wind_speed=8.0, active_power_kw=1500.0, theoretical_power_kw=1500.0)
    df = add_normalized_deviation(df)

    assert df["deviation_norm"].iloc[0] == 0.0
