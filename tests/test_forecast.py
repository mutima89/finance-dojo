import numpy as np
import pandas as pd
import pytest

from fts.core import forecast as f

approx = pytest.approx


def test_moving_average():
    assert f.moving_average_forecast([10, 20, 30, 40], 2, 3) == [35, 35, 35]
    assert f.moving_average_forecast([10, None, 30, float("nan"), 50], 2, 1) == [40]
    with pytest.raises(ValueError):
        f.moving_average_forecast([1], 3, 1)


def test_linear_trend():
    # perfect line y = 5 + 2x -> next values 13, 15
    assert f.linear_trend_forecast([5, 7, 9, 11], 2) == [approx(13), approx(15)]


def test_mape():
    assert f.mape([100, 200], [110, 180]) == approx(0.10)
    assert f.mape([0, None], [1, 2]) is None


def test_weekday_profile():
    dates = pd.date_range("2025-01-06", periods=28, freq="D")   # starts on a Monday
    vals = [100 if d.dayofweek < 5 else 140 for d in dates]
    df = pd.DataFrame({"date": dates, "sold": vals})
    df.loc[3, "sold"] = np.nan                                   # missing observation
    out = f.weekday_profile_forecast(df, "sold", 7)
    assert list(out["sold"]) == [100, 100, 100, 100, 100, 140, 140]


HAND = dict(rooms=150, occupancy=(0.74, 0.76, 0.77), adr=(310.0, 322.0, 333.0),
            ancillary_pct_of_rooms=0.55, payroll_fixed=6_200_000.0, payroll_per_occupied_room=38.0,
            payroll_inflation=0.035, other_opex_pct_revenue=0.30, fixed_charges=1_900_000.0,
            capex_pct_revenue=0.04, nwc_pct_revenue=0.03, opening_nwc=900_000.0,
            opening_cash=2_500_000.0)


def test_hotel_forecast_year1_by_hand():
    df = f.hotel_forecast(f.HotelAssumptions(**HAND))
    y1 = df["Year 1"]
    # 150 x 365 = 54,750 ; x 74% = 40,515 sold ; x $310 = 12,559,650
    assert y1["Available room nights"] == 54_750
    assert y1["Sold room nights"] == approx(40_515)
    assert y1["Rooms revenue"] == approx(12_559_650)
    assert y1["Ancillary revenue"] == approx(6_907_807.5)          # x 55%
    assert y1["Total revenue"] == approx(19_467_457.5)
    assert y1["Payroll"] == approx(7_739_570)                      # 6.2m + 38 x 40,515
    assert y1["Other operating expenses"] == approx(5_840_237.25)  # 30% of revenue
    assert y1["EBITDA"] == approx(3_987_650.25)
    assert y1["Change in working capital"] == approx(-315_976.275) # 584,023.725 - 900,000
    assert y1["Free cash flow"] == approx(3_524_928.225)
    assert y1["Closing cash"] == approx(6_024_928.225)


def test_forecast_reconciles():
    for name, mult in f.SCENARIOS.items():
        df = f.hotel_forecast(f.HotelAssumptions().scaled(**mult))
        failed = [c for c in f.reconcile_forecast(df) if not c[1]]
        assert not failed, (name, failed)


def test_reconciliation_detects_break():
    df = f.hotel_forecast(f.HotelAssumptions())
    df.at["Closing cash", "Year 2"] += 1000
    failed = [c[0] for c in f.reconcile_forecast(df) if not c[1]]
    assert any("Closing cash" in n for n in failed)
    assert any("Opening cash" in n for n in failed)


def test_scenarios_ordered():
    t = f.scenario_table(f.HotelAssumptions(), "EBITDA")
    for y in t.columns:
        assert t.at["Downside", y] < t.at["Base", y] < t.at["Upside", y]


def test_invalid_assumptions():
    with pytest.raises(ValueError):
        f.hotel_forecast(f.HotelAssumptions(occupancy=(1.2, 0.7, 0.7)))


def test_sensitivity_grid():
    g = f.sensitivity_grid(lambda r, c: r * c, [1, 2], [10, 20])
    assert g.loc[2, 20] == 40 and g.shape == (2, 2)


def test_revised_forecast():
    assert f.revised_forecast([100, 100, 100, 100], -0.10, 2) == [100, 100, 90, 90]
    assert f.revised_forecast([100, 100], -0.20, 0, variable_share=0.5) == [90, 90]
    with pytest.raises(ValueError):
        f.revised_forecast([1], -2, 0)
