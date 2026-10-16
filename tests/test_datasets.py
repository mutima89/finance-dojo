"""Integrity checks on the generated fictional datasets: every total must
reconcile so exercises have one correct answer."""
import numpy as np
import pandas as pd
import pytest

from fts.core import forecast as f
from fts.core import metrics as m
from fts.data import generator as g


@pytest.fixture(scope="module")
def ds():
    return g.build()


def test_deterministic():
    a, b = g.build(), g.build()
    pd.testing.assert_frame_equal(a.daily, b.daily)
    pd.testing.assert_frame_equal(a.pnl, b.pnl)


def test_daily_rules(ds):
    d = ds.daily
    assert len(d) == 365
    assert (d.rooms_sold <= d.rooms_available).all()
    assert (d.rooms_available == d.rooms_in_inventory - d.rooms_out_of_order).all()
    seg_rooms = d[[f"sold_{s.lower()}" for s in g.SEGMENTS]].sum(axis=1)
    seg_rev = d[[f"revenue_{s.lower()}" for s in g.SEGMENTS]].sum(axis=1)
    assert (seg_rooms == d.rooms_sold).all()
    assert np.allclose(seg_rev, d.room_revenue, atol=0.011)


def test_monthly_equals_daily(ds):
    assert ds.monthly_rooms.sold_room_nights.sum() == ds.daily.rooms_sold.sum()
    assert ds.monthly_rooms.room_revenue.sum() == pytest.approx(ds.daily.room_revenue.sum(), abs=0.05)


def test_channels_reconcile(ds):
    c = ds.channels.groupby("month")[["room_nights", "room_revenue"]].sum()
    mr = ds.monthly_rooms.set_index("month")
    assert (c.room_nights == mr.sold_room_nights).all()
    assert np.allclose(c.room_revenue, mr.room_revenue, atol=0.05)


def test_pnl_structure(ds):
    for (month, kind), grp in ds.pnl.melt(id_vars=["month", "line"], value_vars=["actual", "budget"]
                                         ).groupby(["month", "variable"]):
        v = dict(zip(grp.line, grp.value))
        assert v["Total revenue"] == v["Rooms revenue"] + v["Food & beverage revenue"] + v["Spa & other revenue"]
        assert v["Gross operating profit (GOP)"] == pytest.approx(
            v["Total revenue"] - v["Total departmental expenses"] - v["Total undistributed expenses"])
        assert v["EBITDA"] == pytest.approx(v["Gross operating profit (GOP)"] - v["Management fee"]
                                            - v["Insurance"] - v["Property tax"])
        assert v["Net income"] == pytest.approx(v["Profit before tax"] - v["Income tax"])


def test_pnl_rooms_revenue_matches_operations(ds):
    act = ds.pnl[ds.pnl.line == "Rooms revenue"].actual.sum()
    assert act == pytest.approx(ds.monthly_rooms.room_revenue.sum(), abs=12)   # P&L rounded to $1/month


def test_balance_sheet_balances(ds):
    bs = ds.balance_sheet
    for col in bs.columns[2:]:
        assets = bs[bs.category == "Asset"][col].sum()
        claims = bs[bs.category != "Asset"][col].sum()
        assert assets == pytest.approx(claims, abs=0.01)


def test_cash_flow_ties_to_balance_sheet(ds):
    cf = dict(zip(ds.cash_flow.line, ds.cash_flow.iloc[:, 1]))
    bs = ds.balance_sheet.set_index("line")
    assert cf["Closing cash"] == pytest.approx(bs.at["Cash", bs.columns[-1]])
    assert cf["Net income"] == pytest.approx(ds.pnl[ds.pnl.line == "Net income"].actual.sum())


def test_forecast_defaults_start_from_fy2025(ds):
    bs = ds.balance_sheet.set_index("line")
    col = bs.columns[-1]
    a = f.HotelAssumptions()
    assert a.opening_cash == pytest.approx(bs.at["Cash", col])
    nwc = (bs.at["Accounts receivable", col] + bs.at["Inventories", col]
           - bs.at["Accounts payable", col] - bs.at["Accrued expenses", col])
    assert a.opening_nwc == pytest.approx(nwc)


def test_payroll_ties_to_pnl(ds):
    p = ds.payroll.groupby("department").payroll_actual.sum()
    rooms_pnl = ds.pnl[ds.pnl.line == "Rooms payroll"].actual.sum()
    assert rooms_pnl == pytest.approx(p["Rooms"], abs=12)


def test_retail_cash_flow(ds):
    r = ds.retail
    assert r.net_income.sum() > r.operating_cash_flow.sum()   # the teaching point
    assert (r.gross_profit == r.revenue - r.cost_of_goods_sold).all()


def test_capstone_issues_present(ds):
    raw, clean = ds.capstone_raw, ds.capstone_clean
    assert len(raw) == 13 and len(clean) == 12
    assert raw.month_name.duplicated().sum() == 1
    assert raw.sold_room_nights.isna().sum() == 1
    oct_ = raw[raw.month_name == "Oct"].iloc[0]
    assert oct_.sold_room_nights > oct_.available_room_nights
    assert raw[raw.month_name == "Aug"].room_revenue.iloc[0] < 10_000


def test_capstone_clean_kpis(ds):
    c = ds.capstone_clean
    assert (c.sold_room_nights <= c.available_room_nights).all()
    # Missing March value can be rebuilt from revenue / reported ADR
    mar = c[c.month_name == "Mar"].iloc[0]
    assert round(mar.room_revenue / mar.adr_reported) == mar.sold_room_nights


def test_renovation_flows(ds):
    flows = ds.cases["renovation"]["cash_flows"]
    assert flows[0] == -4_500_000 and len(flows) == 8
    # uplift: 54,750 x (0.775 x 340 - 0.76 x 318) x 0.70
    expected = 54_750 * (0.775 * 340 - 0.76 * 318) * 0.70
    assert flows[1] == pytest.approx(expected, abs=0.01)


def test_pace(ds):
    p = ds.pace
    assert len(p) == 30 and (p.on_the_books <= p.rooms_available).all()
    assert (pd.to_datetime(p.ly_date).dt.dayofweek == pd.to_datetime(p.stay_date).dt.dayofweek).all()


def test_daily_issues_handled(ds):
    j = ds.daily_issues
    occ = [m.occupancy(s, a) for s, a in zip(j.rooms_sold, j.rooms_available)]
    assert sum(o is None for o in occ) == 2      # missing value + closed day
    assert 0.0 in occ                            # zero-sales day
