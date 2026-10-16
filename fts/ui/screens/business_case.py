"""Business case evaluator: investments, discounts, new services, renovation."""
from __future__ import annotations

import numpy as np
import pandas as pd
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLineEdit, QTableWidget, QTabWidget, QVBoxLayout, QWidget

from ...core import metrics as m
from ...core.checker import parse_number
from ...data import generator as gen
from ...data.loader import data
from ...reports import export
from ..theme import style_axes
from ..widgets import Card, Chart, button, error, fill_table, info, label, money, pct, save_dialog
from .base import Screen


def _num(edit: QLineEdit, name: str, unit="number") -> float:
    v = parse_number(edit.text(), unit)
    if v is None:
        raise ValueError(f"Enter a number for {name}.")
    return v


def _flows(edit: QLineEdit, name: str) -> list[float]:
    parts = [p for p in edit.text().replace(";", ",").split(",") if p.strip()]
    vals = [parse_number(p) for p in parts]
    if len(vals) < 2 or any(v is None for v in vals):
        raise ValueError(f"{name}: enter comma-separated cash flows starting with the year-0 investment.")
    return vals


def summary(flows, rate) -> dict:
    return {"NPV": m.npv(rate, flows), "IRR": m.irr(flows), "Payback (yrs)": m.payback_period(flows),
            "Discounted payback (yrs)": m.discounted_payback(rate, flows),
            "ROI": m.roi(sum(flows[1:]), -flows[0]) if flows[0] < 0 else None,
            "Profitability index": m.profitability_index(rate, flows)}


FMT = {"NPV": money, "IRR": pct, "ROI": pct, "Payback (yrs)": lambda x: f"{x:.2f}",
       "Discounted payback (yrs)": lambda x: f"{x:.2f}", "Profitability index": lambda x: f"{x:.2f}"}


class BusinessCaseScreen(Screen):
    title = "Business case evaluator"
    subtitle = "Test commercial decisions with contribution, payback, NPV and IRR. All cases are fictional."

    def __init__(self, ctx):
        super().__init__(ctx)
        self.cases = data().cases
        tabs = QTabWidget()
        tabs.addTab(self._compare(), "Compare investments")
        tabs.addTab(self._discount(), "Discount decision")
        tabs.addTab(self._service(), "New service")
        tabs.addTab(self._renovation(), "Renovation")
        self.body.addWidget(tabs)

    def _out(self):
        return label("", rich=True)

    def _err(self, out, exc):
        out.setText(f"<span style='color:{self.ctx.pal.bad}'>⚠ {exc}</span>")

    # ------------------------------------------------------------ compare
    def _compare(self):
        w = QWidget()
        v = QVBoxLayout(w)
        ip = self.cases["investment_proposals"]
        f = QFormLayout()
        self.c_rate = QLineEdit(f"{ip['discount_rate'] * 100:g}%")
        self.c_na, self.c_a = QLineEdit(ip["A"]["name"]), QLineEdit(", ".join(f"{x:.0f}" for x in ip["A"]["cash_flows"]))
        self.c_nb, self.c_b = QLineEdit(ip["B"]["name"]), QLineEdit(", ".join(f"{x:.0f}" for x in ip["B"]["cash_flows"]))
        f.addRow("Discount rate", self.c_rate)
        f.addRow("Proposal A name", self.c_na)
        f.addRow("Proposal A cash flows (year 0 first)", self.c_a)
        f.addRow("Proposal B name", self.c_nb)
        f.addRow("Proposal B cash flows", self.c_b)
        v.addLayout(f)
        r = QHBoxLayout()
        r.addWidget(button("Evaluate", self._compare_run, primary=True))
        r.addWidget(button("Export to Excel…", self._compare_export))
        r.addStretch(1)
        v.addLayout(r)
        self.c_tbl = QTableWidget()
        self.c_tbl.setMinimumHeight(110)
        v.addWidget(self.c_tbl)
        self.c_out = self._out()
        v.addWidget(self.c_out)
        self.c_chart = Chart(self.ctx, 2.8)
        v.addWidget(self.c_chart)
        self._compare_run()
        return w

    def _compare_run(self):
        try:
            rate = _num(self.c_rate, "discount rate", "percent")
            a, b = _flows(self.c_a, "Proposal A"), _flows(self.c_b, "Proposal B")
        except ValueError as exc:
            return self._err(self.c_out, exc)
        na, nb = self.c_na.text() or "A", self.c_nb.text() or "B"
        df = pd.DataFrame({na: summary(a, rate), nb: summary(b, rate)}).T
        self.c_df = df
        fill_table(self.c_tbl, df, FMT, pal=self.ctx.pal)
        best = na if df.at[na, "NPV"] >= df.at[nb, "NPV"] else nb
        faster = na if (df.at[na, "Payback (yrs)"] or 99) <= (df.at[nb, "Payback (yrs)"] or 99) else nb
        note = "" if best == faster else f" Note: {faster} pays back faster, so if cash or risk is the main constraint, discuss the trade-off."
        pos = df.at[best, "NPV"] > 0
        self.c_out.setText(f"<b>Recommendation logic:</b> if only one can be funded, prefer <b>{best}</b>, which has the "
                           f"higher NPV at {pct(rate)}" + ("" if pos else ", but its NPV is negative, so neither creates value")
                           + f".{note} <i>Results depend on the forecast cash flows; they are estimates, not guarantees.</i>")

        def paint(fig, p):
            ax = fig.add_subplot(111)
            for i, (n, fl) in enumerate(((na, a), (nb, b))):
                ax.plot(range(len(fl)), np.cumsum(fl) / 1000, color=p.series[i], lw=2, marker="o", ms=4, label=n)
            ax.axhline(0, color=p.border)
            style_axes(ax, p, "Cumulative cash flow ($000); payback where the line crosses zero")
            ax.set_xlabel("Year", color=p.text2, fontsize=8)
            ax.legend(frameon=False, labelcolor=p.text2, fontsize=8)
        self.c_chart.plot(paint)

    def _compare_export(self):
        p = save_dialog(self, "Export comparison", "investment_comparison.xlsx", "Excel (*.xlsx)")
        if p:
            export.dataframe_to_xlsx({"Comparison": self.c_df}, p, "Investment comparison (illustrative)")
            info(self, "Exported", f"Saved to {p}")

    # ----------------------------------------------------------- discount
    def _discount(self):
        w = QWidget()
        v = QVBoxLayout(w)
        pr = self.cases["restaurant_promotion"]
        v.addWidget(label(f"Default case: {pr['name']}. Change the inputs to test a redesigned offer.", "Muted"))
        f = QFormLayout()
        self.d = {k: QLineEdit(t) for k, t in (
            ("price", f"{pr['current_price']:g}"), ("var", f"{pr['variable_cost_per_cover']:g}"),
            ("vol", f"{pr['current_covers_per_month']}"), ("disc", f"{pr['discount_pct'] * 100:g}%"),
            ("newvol", f"{pr['expected_covers_with_promo']}"), ("mkt", f"{pr['extra_marketing_cost']:g}"),
            ("cannib", "0"))}
        for k, t in (("price", "Current price per cover ($)"), ("var", "Variable cost per cover ($)"),
                     ("vol", "Current covers per month"), ("disc", "Discount %"),
                     ("newvol", "Expected covers with promotion"), ("mkt", "Extra marketing cost ($)"),
                     ("cannib", "Covers that would have paid full price anyway (cannibalised)")):
            f.addRow(t, self.d[k])
        v.addLayout(f)
        v.addWidget(button("Evaluate", self._discount_run, primary=True))
        self.d_out = self._out()
        v.addWidget(self.d_out)
        v.addStretch(1)
        self._discount_run()
        return w

    def _discount_run(self):
        try:
            d = {k: _num(e, k, "percent" if k == "disc" else "number") for k, e in self.d.items()}
        except ValueError as exc:
            return self._err(self.d_out, exc)
        cm_now = d["price"] - d["var"]
        new_price = d["price"] * (1 - d["disc"])
        cm_new = new_price - d["var"]
        before = cm_now * d["vol"]
        after = cm_new * d["newvol"] - d["mkt"]
        need = m.discount_volume_needed(d["price"], d["var"], d["disc"])
        incr = after - before
        p = self.ctx.pal
        verdict = ("<span style='color:%s'><b>Adds contribution</b></span>" % p.good if incr > 0 else
                   "<span style='color:%s'><b>Reduces contribution: reject or redesign</b></span>" % p.bad)
        cann = (f"<br>Cannibalisation check: {d['cannib']:,.0f} full-price covers now pay {money(d['price'] * d['disc'], 2)} "
                f"less, costing {money(d['cannib'] * d['price'] * d['disc'])}. This is already inside the totals "
                "above if your covers forecast includes them.") if d["cannib"] else ""
        self.d_out.setText(
            f"Contribution per cover: {money(cm_now, 2)} → {money(cm_new, 2)} (promo price {money(new_price, 2)})<br>"
            f"Monthly contribution: {money(before)} → {money(after)} after marketing · change <b>{money(incr)}</b> "
            f"→ {verdict}<br>Volume increase needed just to stand still (before marketing): "
            f"<b>{pct(need) if need is not None else 'impossible (price below variable cost)'}</b>; "
            f"planned increase {pct(d['newvol'] / d['vol'] - 1) if d['vol'] else 'n/a'}.{cann}")

    # ------------------------------------------------------------ service
    def _service(self):
        w = QWidget()
        v = QVBoxLayout(w)
        ns = self.cases["new_service"]
        rt = self.cases["rooftop_terrace"]
        v.addWidget(label(f"Default: {ns['name']}. Try also the {rt['name']} (spend ${rt['avg_spend_per_guest']:g}, "
                          f"variable {rt['variable_cost_pct'] * 100:g}%, fixed ${rt['monthly_fixed_costs']:,.0f}).", "Muted"))
        f = QFormLayout()
        self.s = {k: QLineEdit(t) for k, t in (("price", f"{ns['price_per_trip']:g}"), ("var", f"{ns['variable_cost_per_trip']:g}"),
                                               ("fixed", f"{ns['fixed_costs_per_month']:g}"), ("vol", f"{ns['expected_trips_per_month']}"),
                                               ("setup", "0"))}
        for k, t in (("price", "Price per unit ($)"), ("var", "Variable cost per unit ($)"), ("fixed", "Fixed costs per month ($)"),
                     ("vol", "Expected units per month"), ("setup", "One-off set-up cost ($), optional")):
            f.addRow(t, self.s[k])
        v.addLayout(f)
        v.addWidget(button("Evaluate", self._service_run, primary=True))
        self.s_out = self._out()
        v.addWidget(self.s_out)
        v.addStretch(1)
        self._service_run()
        return w

    def _service_run(self):
        try:
            d = {k: _num(e, k) for k, e in self.s.items()}
        except ValueError as exc:
            return self._err(self.s_out, exc)
        cm = d["price"] - d["var"]
        be = m.break_even_units(d["fixed"], d["price"], d["var"])
        profit = cm * d["vol"] - d["fixed"]
        mos = m.margin_of_safety(d["vol"], be)
        pay = (d["setup"] / profit) if d["setup"] and profit > 0 else None
        self.s_out.setText(
            f"Contribution per unit: <b>{money(cm, 2)}</b> ({pct(m.contribution_margin_ratio(d['price'], d['var']))})<br>"
            f"Monthly profit at {d['vol']:,.0f} units: <b>{money(profit)}</b><br>"
            f"Break-even: <b>{'not reachable (each unit loses money)' if be is None else f'{be:,.1f} units per month'}</b>"
            + (f" · margin of safety {pct(mos)}" if mos is not None else "")
            + (f"<br>Set-up cost payback: {pay:.1f} months" if pay else ""))

    # --------------------------------------------------------- renovation
    def _renovation(self):
        w = QWidget()
        v = QVBoxLayout(w)
        rn = self.cases["renovation"]
        f = QFormLayout()
        self.r = {k: QLineEdit(t) for k, t in (
            ("capex", f"{rn['capex']:,}"), ("rate", f"{rn['discount_rate'] * 100:g}%"), ("years", str(rn["years"])),
            ("base_occ", f"{rn['base_occupancy'] * 100:g}%"), ("base_adr", f"{rn['base_adr']:g}"),
            ("adr_up", f"{rn['adr_uplift']:g}"), ("occ_up", f"{rn['occupancy_uplift_pts'] * 100:g}"),
            ("flow", f"{rn['flow_through'] * 100:g}%"), ("tv", f"{rn['terminal_value_year7']:,}"))}
        for k, t in (("capex", "Capex ($)"), ("rate", "Discount rate"), ("years", "Years of benefit"),
                     ("base_occ", "Occupancy without renovation"), ("base_adr", "ADR without renovation ($)"),
                     ("adr_up", "ADR uplift ($)"), ("occ_up", "Occupancy uplift (percentage points)"),
                     ("flow", "Flow-through to profit"), ("tv", "Residual value in final year ($)")):
            f.addRow(t, self.r[k])
        v.addLayout(f)
        r = QHBoxLayout()
        r.addWidget(button("Evaluate", self._reno_run, primary=True))
        r.addWidget(button("Export to Excel…", self._reno_export))
        r.addStretch(1)
        v.addLayout(r)
        self.r_out = self._out()
        v.addWidget(self.r_out)
        self.r_tbl = QTableWidget()
        self.r_tbl.setMinimumHeight(120)
        v.addWidget(self.r_tbl)
        self.r_chart = Chart(self.ctx, 2.8)
        v.addWidget(self.r_chart)
        self._reno_run()
        return w

    def _reno_params(self):
        g = {k: _num(e, k, "percent" if k in ("rate", "base_occ", "flow") else "number") for k, e in self.r.items()}
        years = int(g["years"])
        if not 1 <= years <= 30:
            raise ValueError("Years must be between 1 and 30.")
        return dict(capex=g["capex"], discount_rate=g["rate"], years=years, base_occupancy=g["base_occ"],
                    base_adr=g["base_adr"], adr_uplift=g["adr_up"], occupancy_uplift_pts=g["occ_up"] / 100,
                    flow_through=g["flow"], terminal_value_year7=g["tv"])

    def _reno_run(self):
        try:
            c = self._reno_params()
            if c["base_occupancy"] + c["occupancy_uplift_pts"] > 1:
                raise ValueError("Occupancy with renovation cannot exceed 100%.")
        except ValueError as exc:
            return self._err(self.r_out, exc)
        flows = gen.renovation_cash_flows(c)
        s = summary(flows, c["discount_rate"])

        def npv_at(up):
            cc = dict(c, adr_uplift=up)
            return m.npv(c["discount_rate"], gen.renovation_cash_flows(cc))
        lo, hi = -200.0, 400.0
        be = None
        if npv_at(lo) < 0 < npv_at(hi):
            for _ in range(80):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if npv_at(mid) < 0 else (lo, mid)
            be = (lo + hi) / 2
        self.r_flows, self.r_summary = flows, s
        tbl = pd.DataFrame([flows], columns=[f"Y{t}" for t in range(len(flows))], index=["Cash flow"])
        fill_table(self.r_tbl, tbl, {c_: money for c_ in tbl.columns}, pal=self.ctx.pal)
        p = self.ctx.pal
        self.r_out.setText(
            f"NPV <b style='color:{p.good if s['NPV'] > 0 else p.bad}'>{money(s['NPV'])}</b> · IRR <b>{pct(s['IRR'], 2)}</b> · "
            f"payback <b>{'never' if s['Payback (yrs)'] is None else f'{s[chr(80) + 'ayback (yrs)']:.2f} yrs'}</b> · "
            f"PI {s['Profitability index']:.2f}<br>Break-even ADR uplift (NPV = 0): "
            f"<b>{'n/a' if be is None else money(be, 2)}</b> vs assumed {money(c['adr_uplift'], 2)}. "
            "<i>Estimates only; the result is most sensitive to the ADR uplift.</i>")
        ups = np.linspace(0, max(40, c["adr_uplift"] * 1.6), 30)

        def paint(fig, pal):
            ax = fig.add_subplot(111)
            ax.plot(ups, [npv_at(u) / 1e6 for u in ups], color=pal.series[0], lw=2)
            ax.axhline(0, color=pal.border)
            ax.axvline(c["adr_uplift"], color=pal.series[1], ls="--", lw=1.5)
            style_axes(ax, pal, "NPV ($ millions) vs ADR uplift; dashed = your assumption")
            ax.set_xlabel("ADR uplift ($)", color=pal.text2, fontsize=8)
        self.r_chart.plot(paint)

    def _reno_export(self):
        p = save_dialog(self, "Export renovation case", "renovation_case.xlsx", "Excel (*.xlsx)")
        if p:
            flows = pd.DataFrame({"Year": range(len(self.r_flows)), "Cash flow": self.r_flows}).set_index("Year")
            summ = pd.DataFrame({"Value": self.r_summary})
            export.dataframe_to_xlsx({"Cash flows": flows, "Summary": summ}, p, "Renovation business case (illustrative)")
            info(self, "Exported", f"Saved to {p}")
