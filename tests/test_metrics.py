"""Core calculation tests. Expected values were worked out by hand
(shown in comments), not produced by the code under test."""
import math

import pytest

from fts.core import metrics as m

approx = pytest.approx


# ----------------------------------------------------------- hotel KPIs
def test_available_room_nights():
    assert m.available_room_nights(150, 30) == 4500            # 150 x 30
    assert m.available_room_nights(150, 30, out_of_order=60) == 4440


def test_occupancy_adr_revpar_month():
    # 3,375 sold of 4,500 available; revenue 1,012,500
    assert m.occupancy(3375, 4500) == approx(0.75)
    assert m.adr(1_012_500, 3375) == approx(300.0)
    assert m.revpar(1_012_500, 4500) == approx(225.0)
    # identity: RevPAR = Occ x ADR
    assert m.revpar_from_occ_adr(0.75, 300.0) == approx(225.0)


def test_single_day():
    # 150 rooms, 128 sold, revenue 41,600 -> occ 85.333%, ADR 325, RevPAR 277.333
    assert m.occupancy(128, 150) == approx(0.853333, rel=1e-5)
    assert m.adr(41_600, 128) == approx(325.0)
    assert m.revpar(41_600, 150) == approx(277.3333, rel=1e-5)


def test_zero_sold_rooms():
    assert m.occupancy(0, 150) == 0.0
    assert m.adr(0, 0) is None                 # ADR undefined, not zero
    assert m.revpar(0, 150) == 0.0
    assert m.revpar_from_occ_adr(0.0, None) == 0.0


def test_zero_available_rooms():
    assert m.occupancy(0, 0) is None
    assert m.revpar(0, 0) is None


def test_missing_observations():
    assert m.occupancy(None, 150) is None
    assert m.adr(float("nan"), 100) is None
    assert m.revpar(1000, None) is None


def test_invalid_hotel_inputs():
    with pytest.raises(ValueError):
        m.occupancy(160, 150)                  # sold > available
    with pytest.raises(ValueError):
        m.occupancy(-1, 150)
    with pytest.raises(ValueError):
        m.available_room_nights(150, 1, out_of_order=200)


def test_cancellations():
    # 140 booked, 12 cancelled, 3 no-shows -> 125 net
    assert m.net_room_nights(140, 12, 3) == 125
    assert m.cancellation_rate(12, 140) == approx(0.085714, rel=1e-4)
    with pytest.raises(ValueError):
        m.net_room_nights(10, 12)


def test_demand_model():
    assert m.demand_at_rate(0.80, 300, 300, -1.2) == approx(0.80)
    # +10% rate with elasticity -1.2 -> 0.80 x 1.1^-1.2 = 0.7228...
    assert m.demand_at_rate(0.80, 300, 330, -1.2) == approx(0.80 * 1.1 ** -1.2)
    assert m.demand_at_rate(0.95, 300, 150, -2.0) == 1.0     # capped at 100%


# -------------------------------------------------------- variances
def test_revenue_variance_unfavorable():
    v = m.variance(95, 100, "revenue")
    assert v.amount == -5 and v.percent == approx(-0.05)
    assert not v.favorable and v.label == "Unfavorable"


def test_expense_variance_favorable():
    v = m.variance(95, 100, "expense")
    assert v.amount == -5 and v.favorable and v.label == "Favorable"


def test_expense_overspend_unfavorable():
    v = m.variance(112_000, 100_000, "expense")
    assert v.amount == 12_000 and v.percent == approx(0.12) and not v.favorable


def test_variance_zero_budget():
    v = m.variance(500, 0, "expense")
    assert v.amount == 500 and v.percent is None and not v.favorable


def test_variance_bad_type():
    with pytest.raises(ValueError):
        m.variance(1, 2, "asset")


def test_price_volume_split():
    # budget 100 units @10 = 1000 ; actual 110 @ 9 = 990
    s = m.price_volume_split(110, 9, 100, 10)
    assert s["volume"] == approx(100)       # +10 units x $10
    assert s["price"] == approx(-110)       # -$1 x 110 units
    assert s["total"] == approx(-10)
    assert s["volume"] + s["price"] == approx(s["total"])


def test_flexible_budget():
    # fixed 20,000 + $12 x 3,000 units = 56,000
    assert m.flexible_budget(20_000, 12, 3_000) == 56_000


def test_top_unfavorable():
    vs = {"A": m.variance(90, 100, "revenue"),     # -10 U
          "B": m.variance(130, 100, "expense"),    # +30 U
          "C": m.variance(80, 100, "expense"),     # F
          "D": m.variance(95, 100, "revenue")}     # -5 U
    assert [k for k, _ in m.top_unfavorable(vs, 2)] == ["B", "A"]


# ---------------------------------------- contribution & break-even
def test_contribution_and_break_even():
    assert m.contribution_per_unit(80, 30) == 50
    assert m.contribution_margin_ratio(80, 30) == approx(0.625)
    assert m.break_even_units(50_000, 80, 30) == approx(1000)     # 50,000 / 50
    assert m.break_even_revenue(50_000, 0.625) == approx(80_000)  # 50,000 / 0.625
    assert m.margin_of_safety(100_000, 80_000) == approx(0.20)


def test_break_even_impossible():
    assert m.break_even_units(10_000, 30, 30) is None
    assert m.break_even_units(10_000, 25, 30) is None
    assert m.break_even_revenue(10_000, 0) is None
    assert m.contribution_margin_ratio(0, 0) is None


def test_discount_volume_needed():
    # price 100, var 40: CM 60 -> after 10% discount CM 50 -> need +20% volume
    assert m.discount_volume_needed(100, 40, 0.10) == approx(0.20)
    assert m.discount_volume_needed(100, 95, 0.10) is None


def test_margins():
    assert m.gross_profit(1000, 650) == 350
    assert m.margin(350, 1000) == approx(0.35)
    assert m.margin(10, 0) is None


# ------------------------------------------------- NPV / IRR / TVM
def test_npv_textbook():
    # -1000 + 500/1.1 + 500/1.21 + 500/1.331 = 243.4259955
    assert m.npv(0.10, [-1000, 500, 500, 500]) == approx(243.4259955, abs=1e-6)


def test_excel_npv_convention():
    # Excel NPV discounts the first value: 243.4259955 / 1.1 = 221.2963596
    assert m.excel_npv(0.10, [-1000, 500, 500, 500]) == approx(221.2963596, abs=1e-6)
    # =CF0 + NPV(rate, CF1..) equals textbook NPV
    assert -1000 + m.excel_npv(0.10, [500, 500, 500]) == approx(m.npv(0.10, [-1000, 500, 500, 500]))


def test_npv_zero_rate_is_sum():
    assert m.npv(0.0, [-100, 40, 40, 40]) == approx(20)


def test_irr_simple():
    assert m.irr([-100, 110]) == approx(0.10, abs=1e-8)
    # three equal 500 inflows on 1000: IRR = 23.3752%
    assert m.irr([-1000, 500, 500, 500]) == approx(0.233752, abs=1e-6)


def test_irr_npv_is_zero_at_irr():
    cfs = [-4_500_000, 650_000, 900_000, 1_050_000, 1_100_000, 1_150_000, 1_200_000, 1_900_000]
    r = m.irr(cfs)
    assert m.npv(r, cfs) == approx(0, abs=1e-3)


def test_irr_no_solution():
    assert m.irr([100, 200]) is None
    assert m.irr([-100, -50]) is None
    assert m.irr([-100]) is None


def test_payback():
    # cumulative: -700, -300, +200 -> 2 + 300/500 = 2.6 years
    assert m.payback_period([-1000, 300, 400, 500]) == approx(2.6)
    assert m.payback_period([-1000, 100, 100]) is None


def test_discounted_payback_longer():
    cfs = [-1000, 300, 400, 500, 300]
    assert m.discounted_payback(0.10, cfs) > m.payback_period(cfs)


def test_roi_and_pi():
    assert m.roi(1_300, 1_000) == approx(0.30)
    assert m.roi(100, 0) is None
    assert m.profitability_index(0.10, [-1000, 500, 500, 500]) == approx(1.2434259955)


def test_tvm():
    assert m.future_value(1000, 0.05, 2) == approx(1102.5)
    assert m.present_value(1102.5, 0.05, 2) == approx(1000)
    assert m.discount_factor(0.10, 2) == approx(1 / 1.21)
    with pytest.raises(ValueError):
        m.npv(-1.0, [1, 2])


# ------------------------------------------------ working capital
def test_working_capital_cycle():
    # receivables 50k on 365k revenue -> 50 days; inventory 30k on 219k COGS -> 50 days
    dso = m.days_sales_outstanding(50_000, 365_000)
    dio = m.days_inventory_outstanding(30_000, 219_000)
    dpo = m.days_payables_outstanding(18_000, 219_000)
    assert dso == approx(50) and dio == approx(50) and dpo == approx(30)
    assert m.cash_conversion_cycle(dso, dio, dpo) == approx(70)
    assert m.days_sales_outstanding(1, 0) is None


def test_operating_cash_flow_indirect():
    # profit 100, dep 20, AR up 30, inventory up 10, payables up 5 -> 85
    assert m.operating_cash_flow_indirect(100, 20, 30, 10, 5) == 85


def test_growth():
    assert m.growth_rate(110, 100) == approx(0.10)
    assert m.growth_rate(1, 0) is None
    assert m.cagr(100, 121, 2) == approx(0.10)
    assert m.weighted_average([300, 200], [1, 3]) == approx(225)
    assert m.weighted_average([1], [0]) is None


def test_safe_divide_and_rounding():
    assert m.safe_divide(1, 0) is None
    assert m.safe_divide(1, 0, default=0) == 0
    assert m.safe_divide(None, 2) is None
    assert m.round_money(2.675) == 2.68          # half-up, not banker's rounding
    assert m.round_money(-1.005) == -1.01
    assert m.round_money(None) is None
