"""FP&A helpers on the long-format monthly P&L (month, line, line_type, actual, budget)."""
from __future__ import annotations

import pandas as pd

from . import metrics as m

DETAIL_LINES = ["Rooms revenue", "Food & beverage revenue", "Spa & other revenue", "Rooms payroll",
                "Rooms other expenses", "F&B cost of sales", "F&B payroll", "F&B other expenses",
                "Spa & other expenses", "Administrative & general", "Sales & marketing",
                "Property operations & maintenance", "Utilities", "Management fee", "Insurance", "Property tax"]
REVENUE = DETAIL_LINES[:3]
DEPT = DETAIL_LINES[3:9]
UNDIST = DETAIL_LINES[9:13]
FIXED_CHARGES = ["Management fee", "Insurance", "Property tax"]

# Share of each line that moves with demand (training assumption, documented in the UI).
VARIABILITY = {"Rooms revenue": 1.0, "Food & beverage revenue": 1.0, "Spa & other revenue": 1.0,
               "Rooms payroll": 0.3, "Rooms other expenses": 1.0, "F&B cost of sales": 1.0, "F&B payroll": 0.3,
               "F&B other expenses": 1.0, "Spa & other expenses": 0.5, "Administrative & general": 0.0,
               "Sales & marketing": 0.2, "Property operations & maintenance": 0.0, "Utilities": 0.2,
               "Management fee": 1.0, "Insurance": 0.0, "Property tax": 0.0}


def add_subtotals(detail: dict[str, float]) -> dict[str, float]:
    d = dict(detail)
    d["Total revenue"] = sum(d[k] for k in REVENUE)
    d["Total departmental expenses"] = sum(d[k] for k in DEPT)
    d["Total undistributed expenses"] = sum(d[k] for k in UNDIST)
    d["Gross operating profit (GOP)"] = d["Total revenue"] - d["Total departmental expenses"] - d["Total undistributed expenses"]
    d["EBITDA"] = d["Gross operating profit (GOP)"] - sum(d[k] for k in FIXED_CHARGES)
    return d


def period_table(pnl: pd.DataFrame, months: list[int]) -> pd.DataFrame:
    """Actual, budget and variance for the chosen months, with F/U labels."""
    p = pnl[pnl.month.isin(months)]
    g = p.groupby("line", sort=False).agg(actual=("actual", "sum"), budget=("budget", "sum"),
                                         line_type=("line_type", "first"))
    rows = []
    for line, r in g.iterrows():
        kind = "expense" if r.line_type == "expense" else "revenue"
        if r.line_type == "total":
            kind = "expense" if "expenses" in line.lower() else "revenue"
        v = m.variance(r.actual, r.budget, kind)
        rows.append({"Line": line, "Type": r.line_type, "Actual": r.actual, "Budget": r.budget,
                     "Variance": v.amount, "Variance %": v.percent,
                     "F/U": "" if v.amount == 0 else ("F" if v.favorable else "U")})
    return pd.DataFrame(rows).set_index("Line")


def top_unfavorable(table: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    d = table[(table.Type != "total") & (table["F/U"] == "U")].copy()
    d["abs"] = d.Variance.abs()
    return d.sort_values("abs", ascending=False).head(n).drop(columns="abs")


def revised_forecast(pnl: pd.DataFrame, start_month: int, demand_change: float) -> pd.DataFrame:
    """Months before start_month = actual; from start_month = budget flexed by the
    demand change on each line's variable share. Returns months x lines (incl. subtotals)."""
    if not 1 <= start_month <= 12:
        raise ValueError("Start month must be 1-12.")
    if not -0.9 <= demand_change <= 0.9:
        raise ValueError("Demand change must be between -90% and +90%.")
    out = {}
    for mo in range(1, 13):
        p = pnl[pnl.month == mo].set_index("line")
        detail = {}
        for line in DETAIL_LINES:
            if mo < start_month:
                detail[line] = float(p.at[line, "actual"])
            else:
                detail[line] = float(p.at[line, "budget"]) * (1 + demand_change * VARIABILITY[line])
        out[mo] = add_subtotals(detail)
    return pd.DataFrame(out)


def budget_builder(base_months: pd.DataFrame, occ_change_pts: float, adr_growth: float,
                   fb_per_occ: float, spa_per_occ: float, var_cost_per_occ: float,
                   payroll_fixed_month: float, payroll_per_occ: float, other_fixed_month: float,
                   mgmt_fee_pct: float, fixed_charges_month: float, rooms: int = 150) -> pd.DataFrame:
    """12-month driver-based operating budget. base_months needs month, days, occupancy, adr."""
    rows = []
    for _, r in base_months.iterrows():
        avail = rooms * int(r.days)
        occ = min(1.0, max(0.0, r.occupancy + occ_change_pts))
        sold = avail * occ
        adr = r.adr * (1 + adr_growth)
        rooms_rev = sold * adr
        fb, spa = sold * fb_per_occ, sold * spa_per_occ
        total = rooms_rev + fb + spa
        payroll = payroll_fixed_month + payroll_per_occ * sold
        var_costs = var_cost_per_occ * sold
        fee = mgmt_fee_pct * total
        ebitda = total - payroll - var_costs - other_fixed_month - fee - fixed_charges_month
        rows.append({"Month": r.month_name, "Available": avail, "Occupancy": occ, "Sold": sold, "ADR": adr,
                     "RevPAR": rooms_rev / avail, "Rooms revenue": rooms_rev, "F&B + spa revenue": fb + spa,
                     "Total revenue": total, "Payroll": payroll, "Variable costs": var_costs,
                     "Other fixed costs": other_fixed_month, "Mgmt fee + fixed charges": fee + fixed_charges_month,
                     "EBITDA": ebitda})
    df = pd.DataFrame(rows).set_index("Month")
    tot = df.sum(numeric_only=True)
    tot["Occupancy"] = tot["Sold"] / tot["Available"]
    tot["ADR"] = tot["Rooms revenue"] / tot["Sold"]
    tot["RevPAR"] = tot["Rooms revenue"] / tot["Available"]
    df.loc["Year"] = tot
    return df
