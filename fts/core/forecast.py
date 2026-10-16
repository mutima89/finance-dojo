"""Forecasting and scenario tools used by the training simulator.

These are deliberately simple, transparent methods a junior analyst can
rebuild in Excel. They are illustrative: no forecast is guaranteed.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Sequence

import numpy as np
import pandas as pd

from . import metrics as m


# ---------------------------------------------------------- time series

def moving_average_forecast(values: Sequence[float], window: int, horizon: int) -> list[float]:
    """Flat forecast equal to the mean of the last ``window`` observations.
    Missing observations (NaN/None) are ignored."""
    clean = [v for v in values if not m.is_missing(v)]
    if window <= 0:
        raise ValueError("Window must be at least 1.")
    if len(clean) < window:
        raise ValueError(f"Need at least {window} observations, found {len(clean)}.")
    level = float(np.mean(clean[-window:]))
    return [level] * horizon


def weekday_profile_forecast(df: pd.DataFrame, value_col: str, horizon: int,
                             weeks: int = 4, date_col: str = "date") -> pd.DataFrame:
    """Seasonal-naive by weekday: each future day = average of the same weekday
    over the last ``weeks`` weeks. Captures weekday/weekend demand patterns.
    Missing observations are skipped."""
    d = df[[date_col, value_col]].copy()
    d[date_col] = pd.to_datetime(d[date_col])
    d = d.sort_values(date_col)
    last = d[date_col].max()
    hist = d[d[date_col] > last - pd.Timedelta(days=7 * weeks)]
    hist = hist.dropna(subset=[value_col])
    profile = hist.groupby(hist[date_col].dt.dayofweek)[value_col].mean()
    overall = hist[value_col].mean()
    future = pd.date_range(last + pd.Timedelta(days=1), periods=horizon, freq="D")
    vals = [float(profile.get(dt.dayofweek, overall)) for dt in future]
    return pd.DataFrame({date_col: future, value_col: vals})


def linear_trend_forecast(values: Sequence[float], horizon: int) -> list[float]:
    """Least-squares straight line through the history, extended forward."""
    y = np.array([v for v in values if not m.is_missing(v)], dtype=float)
    if len(y) < 2:
        raise ValueError("Need at least two observations for a trend.")
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    return [float(intercept + slope * (len(y) + i)) for i in range(horizon)]


def mape(actual: Sequence[float], forecast: Sequence[float]) -> float | None:
    """Mean Absolute Percentage Error, skipping zero/missing actuals."""
    pairs = [(a, f) for a, f in zip(actual, forecast)
             if not m.is_missing(a) and not m.is_missing(f) and a != 0]
    if not pairs:
        return None
    return float(np.mean([abs(a - f) / abs(a) for a, f in pairs]))


# ------------------------------------------------- hotel 3-year model

@dataclass
class HotelAssumptions:
    """Simplified training assumptions for a 3-year hotel forecast.

    This is NOT a full three-statement model: there is no debt schedule,
    tax computation or balance sheet. It links operations -> EBITDA ->
    free cash flow -> cash balance so the student can see how the pieces
    connect.
    """
    rooms: int = 150
    days_per_year: int = 365
    occupancy: tuple[float, float, float] = (0.775, 0.785, 0.79)
    adr: tuple[float, float, float] = (445.0, 458.0, 470.0)
    ancillary_pct_of_rooms: float = 0.39        # F&B, spa, other as % of rooms revenue
    payroll_fixed: float = 6_200_000.0          # year-1 fixed (salaried) payroll
    payroll_per_occupied_room: float = 38.0     # variable labour per room night sold
    payroll_inflation: float = 0.035
    other_opex_pct_revenue: float = 0.378       # all other operating costs incl. mgmt fee, % of revenue
    fixed_charges: float = 1_080_000.0          # insurance and property tax (flat)
    capex_pct_revenue: float = 0.04             # FF&E reserve
    nwc_pct_revenue: float = -0.014             # hotels often have negative working capital
    opening_nwc: float = -355_522.0             # FY2025 closing balance sheet
    opening_cash: float = 3_979_827.0           # FY2025 closing cash

    def scaled(self, occ_mult=1.0, adr_mult=1.0, opex_mult=1.0) -> "HotelAssumptions":
        return replace(
            self,
            occupancy=tuple(min(1.0, o * occ_mult) for o in self.occupancy),
            adr=tuple(a * adr_mult for a in self.adr),
            other_opex_pct_revenue=self.other_opex_pct_revenue * opex_mult,
        )


SCENARIOS = {
    "Base": dict(occ_mult=1.00, adr_mult=1.00, opex_mult=1.00),
    "Upside": dict(occ_mult=1.04, adr_mult=1.03, opex_mult=0.99),
    "Downside": dict(occ_mult=0.90, adr_mult=0.95, opex_mult=1.03),
}


def hotel_forecast(a: HotelAssumptions) -> pd.DataFrame:
    """Build the 3-year forecast. Returns one row per line item, one column
    per year (Year 1..3)."""
    rows: dict[str, list[float]] = {k: [] for k in (
        "Available room nights", "Occupancy", "Sold room nights", "ADR",
        "RevPAR", "Rooms revenue", "Ancillary revenue", "Total revenue",
        "Payroll", "Other operating expenses", "Fixed charges", "EBITDA",
        "EBITDA margin", "Capital expenditure", "Net working capital",
        "Change in working capital", "Free cash flow", "Opening cash",
        "Closing cash")}
    prev_nwc = a.opening_nwc
    cash = a.opening_cash
    for y in range(3):
        if not 0 <= a.occupancy[y] <= 1:
            raise ValueError(f"Year {y+1} occupancy must be between 0% and 100%.")
        if a.adr[y] < 0:
            raise ValueError(f"Year {y+1} ADR cannot be negative.")
        avail = a.rooms * a.days_per_year
        sold = avail * a.occupancy[y]
        rooms_rev = sold * a.adr[y]
        anc = rooms_rev * a.ancillary_pct_of_rooms
        total = rooms_rev + anc
        payroll = (a.payroll_fixed * (1 + a.payroll_inflation) ** y
                   + a.payroll_per_occupied_room * (1 + a.payroll_inflation) ** y * sold)
        other = total * a.other_opex_pct_revenue
        e = total - payroll - other - a.fixed_charges
        capex = total * a.capex_pct_revenue
        nwc = total * a.nwc_pct_revenue
        d_nwc = nwc - prev_nwc
        fcf = e - capex - d_nwc
        opening = cash
        cash = opening + fcf
        prev_nwc = nwc
        for k, v in (("Available room nights", avail), ("Occupancy", a.occupancy[y]),
                     ("Sold room nights", sold), ("ADR", a.adr[y]),
                     ("RevPAR", m.revpar(rooms_rev, avail)), ("Rooms revenue", rooms_rev),
                     ("Ancillary revenue", anc), ("Total revenue", total),
                     ("Payroll", payroll), ("Other operating expenses", other),
                     ("Fixed charges", a.fixed_charges), ("EBITDA", e),
                     ("EBITDA margin", m.margin(e, total)), ("Capital expenditure", capex),
                     ("Net working capital", nwc), ("Change in working capital", d_nwc),
                     ("Free cash flow", fcf), ("Opening cash", opening), ("Closing cash", cash)):
            rows[k].append(v)
    return pd.DataFrame(rows, index=["Year 1", "Year 2", "Year 3"]).T


def reconcile_forecast(df: pd.DataFrame, tol: float = 0.01) -> list[tuple[str, bool, str]]:
    """Model integrity checks, like the 'checks' tab of a professional model.
    Returns (check name, passed, detail)."""
    checks = []

    def add(name, diff):
        ok = abs(diff) <= tol
        checks.append((name, ok, f"difference {diff:,.2f}"))

    for col in df.columns:
        c = df[col]
        add(f"{col}: Total revenue = Rooms + Ancillary",
            c["Total revenue"] - c["Rooms revenue"] - c["Ancillary revenue"])
        add(f"{col}: RevPAR = Occupancy x ADR", c["RevPAR"] - c["Occupancy"] * c["ADR"])
        add(f"{col}: EBITDA = Revenue - Costs",
            c["EBITDA"] - (c["Total revenue"] - c["Payroll"]
                           - c["Other operating expenses"] - c["Fixed charges"]))
        add(f"{col}: Closing cash = Opening cash + FCF",
            c["Closing cash"] - c["Opening cash"] - c["Free cash flow"])
    cols = list(df.columns)
    for prev, cur in zip(cols, cols[1:]):
        add(f"{cur}: Opening cash = {prev} closing cash",
            df.at["Opening cash", cur] - df.at["Closing cash", prev])
    return checks


def scenario_table(base: HotelAssumptions, metric: str = "EBITDA") -> pd.DataFrame:
    out = {}
    for name, mult in SCENARIOS.items():
        out[name] = hotel_forecast(base.scaled(**mult)).loc[metric]
    return pd.DataFrame(out).T


def sensitivity_grid(func: Callable[[float, float], float], row_values: Sequence[float],
                     col_values: Sequence[float]) -> pd.DataFrame:
    """Two-way data table: func(row, col) for every combination."""
    data = [[func(r, c) for c in col_values] for r in row_values]
    return pd.DataFrame(data, index=list(row_values), columns=list(col_values))


def revised_forecast(budget: Sequence[float], demand_change: float, from_period: int,
                     variable_share: float = 1.0) -> list[float]:
    """Re-forecast a revenue (or variable cost) line after a demand shock.

    Periods before ``from_period`` (0-based) are kept as actual/budget;
    from that period onward the line is scaled by (1 + demand_change x share).
    """
    if not -1 <= demand_change <= 1:
        raise ValueError("Demand change should be between -100% and +100%.")
    factor = 1 + demand_change * variable_share
    return [v if i < from_period else v * factor for i, v in enumerate(budget)]
