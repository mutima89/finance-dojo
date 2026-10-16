"""Core financial and hotel calculations.

Every function here is pure (no UI, no database) so it can be tested in
isolation. Conventions used throughout the application:

* Ratios (occupancy, margins, variance %) are returned as decimals,
  e.g. 0.75 means 75%.
* Money is returned unrounded; rounding happens only for display
  (see ``round_money``), so totals always reconcile.
* Division by zero never raises. Functions return ``None`` to mean
  "not defined / not meaningful" and the UI displays it as "n/a".
* Invalid inputs (negative room counts, more rooms sold than available)
  raise ``ValueError`` with a plain-English message.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Optional, Sequence

Number = float | int


# ---------------------------------------------------------------- helpers

def is_missing(value) -> bool:
    """True for None, NaN and empty strings."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return math.isnan(value)
    except TypeError:
        return False


def safe_divide(numerator, denominator, default=None):
    """Divide, returning ``default`` when the result is undefined.

    Undefined means: either input is missing, or the denominator is zero.
    """
    if is_missing(numerator) or is_missing(denominator):
        return default
    if denominator == 0:
        return default
    return numerator / denominator


def round_money(value: Optional[float], places: int = 2) -> Optional[float]:
    """Round half-up (the convention accountants expect, unlike Python's
    banker's rounding). Returns None for missing input."""
    if is_missing(value):
        return None
    q = Decimal(1).scaleb(-places)
    return float(Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP))


def _require_non_negative(name: str, value) -> None:
    if is_missing(value):
        raise ValueError(f"{name} is missing.")
    if value < 0:
        raise ValueError(f"{name} cannot be negative (got {value}).")


# ------------------------------------------------------------ hotel KPIs

def available_room_nights(rooms: int, days: int, out_of_order: int = 0) -> int:
    """Rooms in inventory x days, less room nights blocked as out of order."""
    _require_non_negative("Rooms", rooms)
    _require_non_negative("Days", days)
    _require_non_negative("Out-of-order room nights", out_of_order)
    total = rooms * days - out_of_order
    if total < 0:
        raise ValueError("Out-of-order room nights exceed total inventory.")
    return total


def occupancy(sold: Number, available: Number) -> Optional[float]:
    """Occupancy = Sold Room Nights / Available Room Nights."""
    if is_missing(sold) or is_missing(available):
        return None
    _require_non_negative("Sold room nights", sold)
    _require_non_negative("Available room nights", available)
    if sold > available:
        raise ValueError(
            f"Sold room nights ({sold}) cannot exceed available room nights "
            f"({available}). Check for overbooking or a data-entry error.")
    return safe_divide(sold, available)


def adr(room_revenue: Number, sold: Number) -> Optional[float]:
    """ADR = Room Revenue / Sold Room Nights. Undefined when nothing sold."""
    if is_missing(sold) or is_missing(room_revenue):
        return None
    _require_non_negative("Sold room nights", sold)
    return safe_divide(room_revenue, sold)


def revpar(room_revenue: Number, available: Number) -> Optional[float]:
    """RevPAR = Room Revenue / Available Room Nights."""
    if is_missing(available) or is_missing(room_revenue):
        return None
    _require_non_negative("Available room nights", available)
    return safe_divide(room_revenue, available)


def revpar_from_occ_adr(occ: Optional[float], rate: Optional[float]) -> Optional[float]:
    """RevPAR = Occupancy x ADR (an identity; useful as a cross-check).
    When nothing is sold ADR is undefined but RevPAR is genuinely zero."""
    if occ == 0:
        return 0.0
    if is_missing(occ) or is_missing(rate):
        return None
    return occ * rate


def net_room_nights(gross_booked: Number, cancellations: Number, no_shows: Number = 0) -> Number:
    """Room nights actually consumed after cancellations and no-shows."""
    for n, v in (("Gross booked", gross_booked), ("Cancellations", cancellations),
                 ("No-shows", no_shows)):
        _require_non_negative(n, v)
    net = gross_booked - cancellations - no_shows
    if net < 0:
        raise ValueError("Cancellations and no-shows exceed bookings.")
    return net


def cancellation_rate(cancellations: Number, gross_booked: Number) -> Optional[float]:
    return safe_divide(cancellations, gross_booked)


def demand_at_rate(base_occupancy: float, base_rate: float, new_rate: float,
                   elasticity: float) -> float:
    """Simple constant-elasticity demand model used in the simulator.

    elasticity is the % change in rooms sold for a 1% change in rate and is
    normally negative (e.g. -1.2). Result is capped between 0 and 100%.
    This is a teaching simplification, not a real pricing engine.
    """
    if base_rate <= 0 or new_rate <= 0:
        raise ValueError("Rates must be greater than zero.")
    occ = base_occupancy * (new_rate / base_rate) ** elasticity
    return max(0.0, min(1.0, occ))


# --------------------------------------------------- variance & budgeting

@dataclass(frozen=True)
class Variance:
    actual: float
    budget: float
    amount: float              # actual - budget
    percent: Optional[float]   # amount / |budget|; None if budget is 0
    favorable: bool
    line_type: str             # "revenue" or "expense"

    @property
    def label(self) -> str:
        if self.amount == 0:
            return "On budget"
        return "Favorable" if self.favorable else "Unfavorable"


def variance(actual: Number, budget: Number, line_type: str = "revenue") -> Variance:
    """Actual vs budget variance.

    Amount is always Actual - Budget. Whether that is good news depends on
    the line: more revenue is favorable, more expense is unfavorable.
    """
    if line_type not in ("revenue", "expense"):
        raise ValueError("line_type must be 'revenue' or 'expense'.")
    if is_missing(actual) or is_missing(budget):
        raise ValueError("Actual and budget are both required for a variance.")
    amount = actual - budget
    pct = safe_divide(amount, abs(budget))
    favorable = amount >= 0 if line_type == "revenue" else amount <= 0
    return Variance(actual, budget, amount, pct, favorable, line_type)


def flexible_budget(fixed_cost: Number, variable_cost_per_unit: Number,
                    actual_volume: Number) -> float:
    """Budget re-stated at the actual activity level."""
    return fixed_cost + variable_cost_per_unit * actual_volume


def price_volume_split(actual_units, actual_price, budget_units, budget_price):
    """Split a revenue variance into a volume effect and a price (rate) effect.

    volume effect = (actual units - budget units) x budget price
    price effect  = (actual price - budget price) x actual units
    The two always add up to the total revenue variance.
    """
    volume = (actual_units - budget_units) * budget_price
    price = (actual_price - budget_price) * actual_units
    total = actual_units * actual_price - budget_units * budget_price
    return {"volume": volume, "price": price, "total": total}


def top_unfavorable(variances: dict[str, Variance], n: int = 3) -> list[tuple[str, Variance]]:
    """The n largest unfavorable variances by absolute amount."""
    bad = [(k, v) for k, v in variances.items() if not v.favorable and v.amount != 0]
    bad.sort(key=lambda kv: abs(kv[1].amount), reverse=True)
    return bad[:n]


# ------------------------------------------ profitability & break-even

def gross_profit(revenue: Number, cost_of_sales: Number) -> float:
    return revenue - cost_of_sales


def margin(profit: Number, revenue: Number) -> Optional[float]:
    return safe_divide(profit, revenue)


def ebitda(revenue: Number, operating_expenses_ex_da: Number) -> float:
    return revenue - operating_expenses_ex_da


def contribution_per_unit(price: Number, variable_cost: Number) -> float:
    return price - variable_cost


def contribution_margin_ratio(price: Number, variable_cost: Number) -> Optional[float]:
    return safe_divide(price - variable_cost, price)


def break_even_units(fixed_costs: Number, price: Number, variable_cost: Number) -> Optional[float]:
    """Units needed to cover fixed costs. None when each unit loses money
    (contribution <= 0) because break-even can never be reached."""
    _require_non_negative("Fixed costs", fixed_costs)
    cm = price - variable_cost
    if cm <= 0:
        return None
    return fixed_costs / cm


def break_even_revenue(fixed_costs: Number, cm_ratio: Optional[float]) -> Optional[float]:
    if is_missing(cm_ratio) or cm_ratio <= 0:
        return None
    return fixed_costs / cm_ratio


def margin_of_safety(actual_sales: Number, break_even_sales: Optional[Number]) -> Optional[float]:
    if break_even_sales is None:
        return None
    return safe_divide(actual_sales - break_even_sales, actual_sales)


def discount_volume_needed(price: Number, variable_cost: Number, discount_pct: float) -> Optional[float]:
    """Volume increase (as a decimal) needed so total contribution after a
    price discount equals total contribution before it.

    required uplift = old CM / new CM - 1
    """
    old_cm = price - variable_cost
    new_cm = price * (1 - discount_pct) - variable_cost
    if new_cm <= 0:
        return None
    return old_cm / new_cm - 1


def incremental_profit(incremental_revenue: Number, incremental_costs: Number,
                       cannibalised_contribution: Number = 0) -> float:
    return incremental_revenue - incremental_costs - cannibalised_contribution


# ------------------------------------------------- time value of money

def present_value(future_value: Number, rate: float, periods: Number) -> float:
    if rate <= -1:
        raise ValueError("Discount rate must be greater than -100%.")
    return future_value / (1 + rate) ** periods


def future_value(present: Number, rate: float, periods: Number) -> float:
    return present * (1 + rate) ** periods


def discount_factor(rate: float, period: Number) -> float:
    if rate <= -1:
        raise ValueError("Discount rate must be greater than -100%.")
    return 1 / (1 + rate) ** period


def npv(rate: float, cash_flows: Sequence[Number]) -> float:
    """Finance-textbook NPV. cash_flows[0] happens today (period 0) and is
    NOT discounted; cash_flows[t] is discounted by (1+rate)^t.

    Note: Excel's =NPV() discounts the FIRST value too. To match this
    function in Excel use  =CF0 + NPV(rate, CF1:CFn).
    """
    if not cash_flows:
        raise ValueError("At least one cash flow is required.")
    if rate <= -1:
        raise ValueError("Discount rate must be greater than -100%.")
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))


def excel_npv(rate: float, cash_flows: Sequence[Number]) -> float:
    """Replicates Excel's NPV(): every value is discounted, starting at t=1."""
    return sum(cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))


def irr(cash_flows: Sequence[Number], lo: float = -0.99, hi: float = 10.0,
        tol: float = 1e-10, max_iter: int = 500) -> Optional[float]:
    """Internal Rate of Return: the rate that makes NPV = 0.

    Uses bisection, which is slow but always converges when a sign change
    exists. Returns None when no IRR exists in the search range (e.g. all
    cash flows have the same sign).
    """
    if len(cash_flows) < 2:
        return None
    if all(cf >= 0 for cf in cash_flows) or all(cf <= 0 for cf in cash_flows):
        return None
    f_lo, f_hi = npv(lo, cash_flows), npv(hi, cash_flows)
    if f_lo * f_hi > 0:
        # look for a bracket on a grid (handles unusual cash flow shapes)
        grid = [lo + i * (hi - lo) / 400 for i in range(401)]
        vals = [npv(r, cash_flows) for r in grid]
        for a, b, fa, fb in zip(grid, grid[1:], vals, vals[1:]):
            if fa * fb <= 0:
                lo, hi, f_lo = a, b, fa
                break
        else:
            return None
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = npv(mid, cash_flows)
        if abs(f_mid) < tol or (hi - lo) / 2 < tol:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def payback_period(cash_flows: Sequence[Number]) -> Optional[float]:
    """Years until cumulative cash flow turns non-negative, interpolating
    within the year. cash_flows[0] is the initial (usually negative) outlay.
    None if the project never pays back."""
    cumulative = 0.0
    for t, cf in enumerate(cash_flows):
        prev = cumulative
        cumulative += cf
        if cumulative >= 0 and t > 0 and prev < 0:
            return (t - 1) + (-prev / cf)
        if t == 0 and cumulative >= 0:
            return 0.0
    return None


def discounted_payback(rate: float, cash_flows: Sequence[Number]) -> Optional[float]:
    return payback_period([cf / (1 + rate) ** t for t, cf in enumerate(cash_flows)])


def roi(total_gain: Number, investment: Number) -> Optional[float]:
    """Simple ROI = (Total gain - Investment) / Investment."""
    if is_missing(investment) or investment == 0:
        return None
    return (total_gain - investment) / investment


def profitability_index(rate: float, cash_flows: Sequence[Number]) -> Optional[float]:
    if not cash_flows or cash_flows[0] >= 0:
        return None
    pv_in = npv(rate, [0] + list(cash_flows[1:]))
    return pv_in / -cash_flows[0]


# ------------------------------------------------ working capital

def days_sales_outstanding(receivables, revenue, days=365):
    r = safe_divide(receivables, revenue)
    return None if r is None else r * days


def days_inventory_outstanding(inventory, cost_of_sales, days=365):
    r = safe_divide(inventory, cost_of_sales)
    return None if r is None else r * days


def days_payables_outstanding(payables, cost_of_sales, days=365):
    r = safe_divide(payables, cost_of_sales)
    return None if r is None else r * days


def cash_conversion_cycle(dso, dio, dpo):
    if any(is_missing(x) for x in (dso, dio, dpo)):
        return None
    return dso + dio - dpo


def net_working_capital(receivables, inventory, payables):
    return receivables + inventory - payables


def operating_cash_flow_indirect(net_income, depreciation, change_in_receivables,
                                 change_in_inventory, change_in_payables):
    """Indirect method: start from profit, add back non-cash items, then
    subtract increases in receivables/inventory and add increases in payables."""
    return (net_income + depreciation - change_in_receivables
            - change_in_inventory + change_in_payables)


def cagr(start_value, end_value, years) -> Optional[float]:
    if start_value is None or start_value <= 0 or years <= 0 or end_value < 0:
        return None
    return (end_value / start_value) ** (1 / years) - 1


def growth_rate(current, prior) -> Optional[float]:
    if is_missing(prior) or prior == 0 or is_missing(current):
        return None
    return (current - prior) / abs(prior)


def weighted_average(values: Iterable[Number], weights: Iterable[Number]) -> Optional[float]:
    values, weights = list(values), list(weights)
    total_w = sum(weights)
    if total_w == 0:
        return None
    return sum(v * w for v, w in zip(values, weights)) / total_w
