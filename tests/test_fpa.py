import pandas as pd
import pytest

from fts.core import fpa
from fts.data.loader import data


def test_period_table_matches_raw():
    pnl = data().pnl
    t = fpa.period_table(pnl, list(range(1, 13)))
    raw = pnl[pnl.line == "Rooms revenue"]
    assert t.at["Rooms revenue", "Variance"] == pytest.approx(raw.actual.sum() - raw.budget.sum())
    assert t.at["Rooms revenue", "F/U"] == "U"
    assert t.at["EBITDA", "F/U"] == "U"


def test_top3_unfavorable():
    t = fpa.period_table(data().pnl, list(range(1, 13)))
    top = list(fpa.top_unfavorable(t).index)
    assert top == ["Rooms revenue", "Rooms other expenses", "Food & beverage revenue"]


def test_subtotals_rebuild_pnl():
    """Recomputing subtotals from detail lines reproduces the dataset's own totals."""
    pnl = data().pnl
    for mo in (1, 7, 12):
        p = pnl[pnl.month == mo].set_index("line")
        d = fpa.add_subtotals({k: p.at[k, "actual"] for k in fpa.DETAIL_LINES})
        for k in ("Total revenue", "Gross operating profit (GOP)", "EBITDA"):
            assert d[k] == pytest.approx(p.at[k, "actual"])


def test_revised_forecast():
    pnl = data().pnl
    zero = fpa.revised_forecast(pnl, 10, 0.0)
    p = pnl.set_index(["month", "line"])
    assert zero.at["Rooms revenue", 9] == p.at[(9, "Rooms revenue"), "actual"]      # closed month = actual
    assert zero.at["Rooms revenue", 10] == p.at[(10, "Rooms revenue"), "budget"]    # no shock = budget
    down = fpa.revised_forecast(pnl, 10, -0.10)
    assert down.at["Rooms revenue", 10] == pytest.approx(p.at[(10, "Rooms revenue"), "budget"] * 0.9)
    assert down.at["Insurance", 11] == p.at[(11, "Insurance"), "budget"]             # fixed line unchanged
    # operating leverage: EBITDA falls by a larger % than revenue
    r_drop = 1 - down.loc["Total revenue", 10:].sum() / zero.loc["Total revenue", 10:].sum()
    e_drop = 1 - down.loc["EBITDA", 10:].sum() / zero.loc["EBITDA", 10:].sum()
    assert e_drop > r_drop
    with pytest.raises(ValueError):
        fpa.revised_forecast(pnl, 13, 0)


def test_budget_builder():
    base = pd.DataFrame({"month": [1], "month_name": ["Jan"], "days": [31], "occupancy": [0.70], "adr": [400.0]})
    b = fpa.budget_builder(base, 0.02, 0.05, 100, 30, 20, 300_000, 10, 150_000, 0.03, 90_000)
    jan = b.loc["Jan"]
    sold = 150 * 31 * 0.72                       # 3,348
    assert jan["Sold"] == pytest.approx(sold)
    assert jan["Rooms revenue"] == pytest.approx(sold * 420)
    total = sold * 420 + sold * 130
    ebitda = total - (300_000 + 10 * sold) - 20 * sold - 150_000 - 0.03 * total - 90_000
    assert jan["EBITDA"] == pytest.approx(ebitda)
    assert b.loc["Year", "Occupancy"] == pytest.approx(0.72)
