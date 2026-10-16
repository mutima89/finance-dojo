"""Interactive financial calculator: every result shows its formula."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QLineEdit, QTabWidget, QVBoxLayout, QWidget

from ...core import metrics as m
from ...core.checker import format_value, parse_number
from ..widgets import Card, button, label, money, pct
from .base import Screen


class Calc(QWidget):
    """A small form: named inputs -> compute() -> HTML result."""

    def __init__(self, ctx, intro: str, fields: list[tuple[str, str, str, str]], compute):
        super().__init__()
        self.ctx, self.compute_fn = ctx, compute
        v = QVBoxLayout(self)
        v.addWidget(label(intro, "Muted"))
        form = QFormLayout()
        self.inputs = {}
        for key, text, default, unit in fields:
            if unit == "combo":
                w = QComboBox()
                w.addItems(default.split("|"))
            else:
                w = QLineEdit(default)
                w.setMaximumWidth(320)
                w.returnPressed.connect(self.run)
            w.setProperty("unit", unit)
            self.inputs[key] = w
            form.addRow(text, w)
        v.addLayout(form)
        v.addWidget(button("Calculate", self.run, primary=True))
        self.out = label("", rich=True)
        v.addWidget(self.out)
        v.addStretch(1)

    def values(self) -> dict:
        vals = {}
        for k, w in self.inputs.items():
            unit = w.property("unit")
            if unit == "combo":
                vals[k] = w.currentText()
            elif unit == "list":
                parts = [p for p in w.text().replace(";", ",").split(",") if p.strip()]
                nums = [parse_number(p) for p in parts]
                if not nums or any(n is None for n in nums):
                    raise ValueError(f"'{k}' must be a comma-separated list of numbers, e.g. -1000, 300, 400.")
                vals[k] = nums
            else:
                n = parse_number(w.text(), unit)
                if n is None:
                    raise ValueError(f"Please enter a number for '{k}'.")
                vals[k] = n
        return vals

    def run(self):
        p = self.ctx.pal
        try:
            self.out.setText(self.compute_fn(self.values()))
        except (ValueError, ZeroDivisionError, OverflowError) as exc:
            self.out.setText(f"<span style='color:{p.bad}'>⚠ {exc}</span>")


def _f(v, unit="number"):
    return format_value(v, unit)


def hotel(v):
    avail = m.available_room_nights(int(v["rooms"]), int(v["days"]), int(v["ooo"]))
    occ = m.occupancy(v["sold"], avail)
    a = m.adr(v["revenue"], v["sold"])
    rp = m.revpar(v["revenue"], avail)
    notes = []
    if v["sold"] == 0:
        notes.append("No rooms sold: ADR is undefined (n/a), not $0. RevPAR is genuinely $0.")
    if avail == 0:
        notes.append("No available rooms: all three KPIs are undefined. Exclude this period from averages.")
    return (f"<b>Available room nights</b> = {int(v['rooms'])} x {int(v['days'])} - {int(v['ooo'])} = <b>{avail:,}</b><br>"
            f"<b>Occupancy</b> = Sold / Available = <b>{pct(occ, 2)}</b><br>"
            f"<b>ADR</b> = Room revenue / Sold = <b>{_f(a, 'currency')}</b><br>"
            f"<b>RevPAR</b> = Room revenue / Available = <b>{_f(rp, 'currency')}</b>"
            + (f" (check: Occ x ADR = {_f(m.revpar_from_occ_adr(occ, a), 'currency')})" if occ is not None else "")
            + "".join(f"<br><i>{n}</i>" for n in notes))


def variance(v):
    var = m.variance(v["actual"], v["budget"], v["type"].lower())
    return (f"<b>Variance</b> = Actual - Budget = <b>{_f(var.amount, 'currency')}</b><br>"
            f"<b>Variance %</b> = Variance / |Budget| = <b>{pct(var.percent, 2)}</b><br>"
            f"<b>{var.label}</b>: for a {var.line_type} line, actual "
            f"{'above' if var.amount > 0 else 'below' if var.amount < 0 else 'equal to'} budget is "
            f"{'good' if var.favorable else 'bad'} for profit.")


def cvp(v):
    cm = m.contribution_per_unit(v["price"], v["varcost"])
    ratio = m.contribution_margin_ratio(v["price"], v["varcost"])
    be = m.break_even_units(v["fixed"], v["price"], v["varcost"])
    ber = m.break_even_revenue(v["fixed"], ratio)
    mos = m.margin_of_safety(v["volume"], be)
    need = m.discount_volume_needed(v["price"], v["varcost"], v["discount"])
    profit = cm * v["volume"] - v["fixed"]
    s = (f"<b>Contribution per unit</b> = Price - Variable cost = <b>{_f(cm, 'currency')}</b><br>"
         f"<b>Contribution margin ratio</b> = {pct(ratio, 2)}<br>"
         f"<b>Profit at expected volume</b> = CM x volume - fixed = <b>{_f(profit, 'currency')}</b><br>")
    if be is None:
        s += "<b>Break-even</b>: not reachable, because each unit loses money (contribution ≤ 0).<br>"
    else:
        s += (f"<b>Break-even units</b> = Fixed / CM = <b>{be:,.1f}</b> · <b>Break-even revenue</b> = "
              f"{_f(ber, 'currency')}<br><b>Margin of safety</b> = {pct(mos, 1)}<br>")
    s += ("<b>Volume increase needed to justify the discount</b> = old CM / new CM - 1 = <b>"
          + (pct(need, 1) if need is not None else "impossible (discounted price below variable cost)") + "</b>")
    return s


def invest(v):
    cfs, r = v["flows"], v["rate"]
    if len(cfs) < 2:
        raise ValueError("Enter at least two cash flows: the investment (year 0) and one return.")
    n = m.npv(r, cfs)
    i = m.irr(cfs)
    pb = m.payback_period(cfs)
    dpb = m.discounted_payback(r, cfs)
    pi = m.profitability_index(r, cfs)
    rows = "".join(f"<tr><td>{t}</td><td align=right>{cf:,.0f}</td><td align=right>{m.discount_factor(r, t):.4f}</td>"
                   f"<td align=right>{cf * m.discount_factor(r, t):,.2f}</td></tr>" for t, cf in enumerate(cfs))
    return (f"<table cellspacing=6><tr><th>Year</th><th>Cash flow</th><th>Discount factor</th><th>PV</th></tr>{rows}</table>"
            f"<b>NPV</b> = Σ CF / (1+r)^t = <b>{_f(n, 'currency')}</b> "
            f"({'creates' if n > 0 else 'destroys'} value at {pct(r, 1)})<br>"
            f"Excel equivalent: =CF0 + NPV(rate, CF1:CFn). Plain =NPV(rate, CF0:CFn) would give "
            f"{_f(m.excel_npv(r, cfs), 'currency')}<br>"
            f"<b>IRR</b> = {pct(i, 2) if i is not None else 'n/a (no sign change in cash flows)'}<br>"
            f"<b>Payback</b> = {_f(pb, 'years') if pb is not None else 'never within these cash flows'} · "
            f"<b>Discounted payback</b> = {_f(dpb, 'years') if dpb is not None else 'never'}<br>"
            f"<b>Profitability index</b> = {('%.2f' % pi) if pi is not None else 'n/a'}<br>"
            "<i>Results depend on the forecast cash flows and discount rate; they are estimates, not guarantees.</i>")


def tvm(v):
    pv = m.present_value(v["fv"], v["rate"], v["years"])
    fv = m.future_value(v["pv"], v["rate"], v["years"])
    return (f"<b>Present value</b> of {_f(v['fv'], 'currency')} in {v['years']:g} years = FV / (1+r)^t = "
            f"<b>{_f(pv, 'currency')}</b><br><b>Future value</b> of {_f(v['pv'], 'currency')} = PV x (1+r)^t = "
            f"<b>{_f(fv, 'currency')}</b>")


def wc(v):
    dso = m.days_sales_outstanding(v["ar"], v["revenue"])
    dio = m.days_inventory_outstanding(v["inv"], v["cogs"])
    dpo = m.days_payables_outstanding(v["ap"], v["cogs"])
    ccc = m.cash_conversion_cycle(dso, dio, dpo)
    return (f"<b>DSO</b> = AR / Revenue x 365 = {_f(dso)} days<br><b>DIO</b> = Inventory / COGS x 365 = {_f(dio)} days<br>"
            f"<b>DPO</b> = AP / COGS x 365 = {_f(dpo)} days<br><b>Cash conversion cycle</b> = DSO + DIO - DPO = "
            f"<b>{_f(ccc)} days</b><br><b>Net working capital</b> = {_f(m.net_working_capital(v['ar'], v['inv'], v['ap']), 'currency')}")


class CalculatorScreen(Screen):
    title = "Interactive financial calculator"
    subtitle = "Type numbers (commas, $ and % are fine). Each result shows the formula used."

    def __init__(self, ctx):
        super().__init__(ctx)
        tabs = QTabWidget()
        tabs.addTab(Calc(ctx, "Hotel KPIs for any period.", [
            ("rooms", "Rooms in inventory", "150", "number"), ("days", "Days in period", "30", "number"),
            ("ooo", "Out-of-order room nights", "0", "number"), ("sold", "Sold room nights", "3375", "number"),
            ("revenue", "Room revenue ($)", "1,012,500", "currency")], hotel), "Occupancy · ADR · RevPAR")
        tabs.addTab(Calc(ctx, "Actual vs budget for one line.", [
            ("actual", "Actual ($)", "112,000", "currency"), ("budget", "Budget ($)", "100,000", "currency"),
            ("type", "Line type", "Expense|Revenue", "combo")], variance), "Variance")
        tabs.addTab(Calc(ctx, "Cost-volume-profit, break-even and discount maths.", [
            ("price", "Price per unit ($)", "80", "currency"), ("varcost", "Variable cost per unit ($)", "30", "currency"),
            ("fixed", "Fixed costs ($)", "50,000", "currency"), ("volume", "Expected volume (units)", "1,200", "number"),
            ("discount", "Proposed discount %", "10%", "percent")], cvp), "Contribution && break-even")
        tabs.addTab(Calc(ctx, "Year-0 investment first (negative), then yearly cash flows.", [
            ("rate", "Discount rate %", "10%", "percent"), ("flows", "Cash flows", "-1000, 500, 500, 500", "list")],
            invest), "NPV · IRR · Payback")
        tabs.addTab(Calc(ctx, "Time value of money.", [
            ("rate", "Rate per year %", "5%", "percent"), ("years", "Years", "2", "number"),
            ("fv", "Future amount ($)", "1,102.50", "currency"), ("pv", "Amount today ($)", "1,000", "currency")],
            tvm), "Time value of money")
        tabs.addTab(Calc(ctx, "Working capital and the cash conversion cycle (annual figures).", [
            ("revenue", "Revenue ($)", "365,000", "currency"), ("cogs", "Cost of goods sold ($)", "219,000", "currency"),
            ("ar", "Accounts receivable ($)", "50,000", "currency"), ("inv", "Inventory ($)", "30,000", "currency"),
            ("ap", "Accounts payable ($)", "18,000", "currency")], wc), "Working capital")
        self.body.addWidget(tabs, 1)
