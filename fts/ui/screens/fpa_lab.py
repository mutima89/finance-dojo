"""FP&A forecasting lab: budget builder, actual vs budget, revised forecast,
payroll and a one-page management report."""
from __future__ import annotations

import calendar

import numpy as np
import pandas as pd
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QPlainTextEdit, QSpinBox,
                               QTableWidget, QTabWidget, QVBoxLayout, QWidget)

from ...core import fpa
from ...data import generator as gen
from ...data.loader import data
from ...reports import export
from ..theme import style_axes
from ..widgets import Card, Chart, KpiCard, button, error, fill_table, info, label, money, pct, save_dialog
from .base import Screen

PERIODS = {"Full year": list(range(1, 13)), "Q1": [1, 2, 3], "Q2": [4, 5, 6], "Q3": [7, 8, 9], "Q4": [10, 11, 12]}
PERIODS.update({calendar.month_name[i]: [i] for i in range(1, 13)})


def money_fmt(x):
    return money(x)


class FPALabScreen(Screen):
    title = "FP&A forecasting lab"
    subtitle = "Budget, actual vs budget, revised forecast, payroll and management reporting for the fictional hotel."

    def __init__(self, ctx):
        super().__init__(ctx)
        self.pnl = data().pnl
        tabs = QTabWidget()
        tabs.addTab(self._variance_tab(), "Actual vs budget")
        tabs.addTab(self._builder_tab(), "12-month budget builder")
        tabs.addTab(self._revised_tab(), "Revised forecast")
        tabs.addTab(self._payroll_tab(), "Payroll")
        tabs.addTab(self._report_tab(), "Management report")
        self.body.addWidget(tabs)

    # ----------------------------------------------------------- variance
    def _variance_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        top = QHBoxLayout()
        top.addWidget(label("Period:", wrap=False))
        self.period = QComboBox()
        self.period.addItems(list(PERIODS))
        self.period.currentIndexChanged.connect(self._var_refresh)
        top.addWidget(self.period)
        top.addWidget(button("Export variance table to Excel…", self._var_export))
        top.addStretch(1)
        v.addLayout(top)
        self.top3 = label("", rich=True)
        v.addWidget(self.top3)
        self.var_tbl = QTableWidget()
        self.var_tbl.setMinimumHeight(520)
        v.addWidget(self.var_tbl)
        self.var_chart = Chart(self.ctx, 3.0)
        v.addWidget(self.var_chart)
        v.addWidget(label("Variance = Actual - Budget. Revenue above budget and expenses below budget are Favorable (F).",
                          "Muted"))
        self._var_refresh()
        return w

    def _var_refresh(self):
        months = PERIODS[self.period.currentText()]
        t = fpa.period_table(self.pnl, months)
        self.var_df = t
        fill_table(self.var_tbl, t.drop(columns="Type"), {"Actual": money_fmt, "Budget": money_fmt,
                                                          "Variance": money_fmt, "Variance %": pct},
                   tone=lambda c, v, row: ("good" if row["F/U"] == "F" else "bad" if row["F/U"] == "U" else "")
                   if c in ("Variance", "Variance %", "F/U") else "", pal=self.ctx.pal)
        top = fpa.top_unfavorable(t)
        self.top3.setText("<b>Three largest unfavorable variances:</b> " + "; ".join(
            f"{i + 1}. {k} {money(r.Variance)} ({pct(r['Variance %'])})" for i, (k, r) in enumerate(top.iterrows())))
        detail = t[t.Type != "total"].copy()

        def paint(fig, p):
            ax = fig.add_subplot(111)
            d = detail.assign(effect=np.where(detail["F/U"] == "F", detail.Variance.abs(), -detail.Variance.abs()))
            d = d.reindex(d.effect.abs().sort_values().index).tail(10)
            cols = [p.good if e >= 0 else p.bad for e in d.effect]
            ax.barh(d.index, d.effect, color=cols, height=0.6)
            ax.axvline(0, color=p.border)
            style_axes(ax, p, "Profit impact of the 10 largest variances ($; green = F, red = U)")
            ax.tick_params(axis="y", labelsize=7)
        self.var_chart.plot(paint)

    def _var_export(self):
        p = save_dialog(self, "Export variance table", f"variance_{self.period.currentText().replace(' ', '_')}.xlsx",
                        "Excel (*.xlsx)")
        if p:
            try:
                export.dataframe_to_xlsx({"Variance": self.var_df}, p, f"Actual vs budget: {self.period.currentText()}")
                info(self, "Exported", f"Saved to {p}")
            except OSError as exc:
                error(self, "Export failed", str(exc))

    # ------------------------------------------------------------ builder
    def _builder_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(label(f"Build next year's operating budget from drivers. Starting point: FY{gen.YEAR} actual "
                          "occupancy and ADR by month (seasonality). Change the drivers and the budget recalculates.",
                          "Muted"))
        form = QFormLayout()

        def spin(val, lo, hi, dec=2, step=1.0, prefix="", suffix=""):
            s = QDoubleSpinBox(decimals=dec, minimum=lo, maximum=hi, singleStep=step, value=val)
            s.setPrefix(prefix)
            s.setSuffix(suffix)
            s.valueChanged.connect(self._build_refresh)
            return s
        self.b = {
            "occ": spin(1.0, -20, 20, 1, 0.5, suffix=" pts"), "adr": spin(3.0, -20, 30, 1, 0.5, suffix=" %"),
            "fb": spin(125, 0, 500, 0, 5, "$ "), "spa": spin(34, 0, 200, 0, 1, "$ "),
            "var": spin(115, 0, 400, 0, 5, "$ "), "payfix": spin(520_000, 0, 5e6, 0, 10_000, "$ "),
            "payocc": spin(38, 0, 200, 0, 1, "$ "), "otherfix": spin(335_000, 0, 5e6, 0, 5_000, "$ "),
            "fee": spin(3.0, 0, 10, 1, 0.5, suffix=" %"), "fixch": spin(90_000, 0, 1e6, 0, 5_000, "$ ")}
        labels = {"occ": "Occupancy change vs last year", "adr": "ADR growth", "fb": "F&B revenue per occupied room",
                  "spa": "Spa & other revenue per occupied room", "var": "Variable cost per occupied room (rooms, F&B, spa)",
                  "payfix": "Fixed payroll per month", "payocc": "Variable payroll per occupied room",
                  "otherfix": "Other fixed costs per month (A&G, S&M, maintenance, utilities)",
                  "fee": "Management fee % of revenue", "fixch": "Insurance + property tax per month"}
        for k, s in self.b.items():
            form.addRow(labels[k], s)
        v.addLayout(form)
        r = QHBoxLayout()
        self.b_kpis = [KpiCard(t) for t in ("Total revenue", "EBITDA", "EBITDA margin", "Occupancy / ADR")]
        for k in self.b_kpis:
            r.addWidget(k)
        v.addLayout(r)
        self.b_tbl = QTableWidget()
        self.b_tbl.setMinimumHeight(430)
        v.addWidget(self.b_tbl)
        v.addWidget(button("Export budget to Excel…", self._build_export))
        self._build_refresh()
        return w

    def _build_refresh(self):
        mr = data().monthly_rooms
        base = pd.DataFrame({"month": mr.month, "month_name": mr.month_name,
                             "days": [calendar.monthrange(gen.YEAR + 1, int(x))[1] for x in mr.month],
                             "occupancy": mr.sold_room_nights / mr.available_room_nights,
                             "adr": mr.room_revenue / mr.sold_room_nights})
        b = self.b
        df = fpa.budget_builder(base, b["occ"].value() / 100, b["adr"].value() / 100, b["fb"].value(),
                                b["spa"].value(), b["var"].value(), b["payfix"].value(), b["payocc"].value(),
                                b["otherfix"].value(), b["fee"].value() / 100, b["fixch"].value())
        self.budget_df = df
        y = df.loc["Year"]
        self.b_kpis[0].set(money(y["Total revenue"]), "next year")
        self.b_kpis[1].set(money(y["EBITDA"]), "Good" if y["EBITDA"] > 0 else "Loss", "Good" if y["EBITDA"] > 0 else "Bad")
        self.b_kpis[2].set(pct(y["EBITDA"] / y["Total revenue"]), "EBITDA / revenue")
        self.b_kpis[3].set(f"{pct(y['Occupancy'])} / {money(y['ADR'])}", f"RevPAR {money(y['RevPAR'], 2)}")
        fmt = {c: money_fmt for c in df.columns}
        fmt.update({"Occupancy": pct, "Available": "{:,.0f}".format, "Sold": "{:,.0f}".format,
                    "ADR": lambda x: money(x, 2), "RevPAR": lambda x: money(x, 2)})
        fill_table(self.b_tbl, df, fmt, pal=self.ctx.pal)

    def _build_export(self):
        p = save_dialog(self, "Export budget", f"operating_budget_{gen.YEAR + 1}.xlsx", "Excel (*.xlsx)")
        if p:
            drivers = pd.DataFrame({"Driver": [k for k in self.b], "Value": [s.value() for s in self.b.values()]})
            export.dataframe_to_xlsx({"Budget": self.budget_df, "Drivers": drivers.set_index("Driver")}, p,
                                     f"12-month operating budget FY{gen.YEAR + 1} (training)")
            info(self, "Exported", f"Saved to {p}")

    # ------------------------------------------------------------ revised
    def _revised_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(label("Closed months stay at actual. From the start month, every line is re-forecast from budget, "
                          "flexed by the demand change times the line's variable share (revenue 100%, commissions & "
                          "cost of sales 100%, payroll 30%, utilities 20%, overheads 0%).", "Muted"))
        f = QFormLayout()
        self.rf_start = QSpinBox(minimum=1, maximum=12, value=10)
        self.rf_change = QDoubleSpinBox(decimals=1, minimum=-90, maximum=90, value=-12, suffix=" %")
        f.addRow("Re-forecast from month", self.rf_start)
        f.addRow("Demand change vs budget", self.rf_change)
        v.addLayout(f)
        self.rf_start.valueChanged.connect(self._rf_refresh)
        self.rf_change.valueChanged.connect(self._rf_refresh)
        r = QHBoxLayout()
        self.rf_k = [KpiCard(t) for t in ("Full-year revenue", "Full-year EBITDA", "EBITDA vs budget")]
        for k in self.rf_k:
            r.addWidget(k)
        v.addLayout(r)
        self.rf_chart = Chart(self.ctx, 2.8)
        v.addWidget(self.rf_chart)
        self.rf_tbl = QTableWidget()
        self.rf_tbl.setMinimumHeight(330)
        v.addWidget(self.rf_tbl)
        v.addWidget(button("Export revised forecast to Excel…", self._rf_export))
        self._rf_refresh()
        return w

    def _rf_refresh(self):
        start, chg = self.rf_start.value(), self.rf_change.value() / 100
        rf = fpa.revised_forecast(self.pnl, start, chg)
        rf.columns = [gen.MONTHS[c - 1] for c in rf.columns]
        rf["Year"] = rf.sum(axis=1)
        self.rf_df = rf
        bud = self.pnl.groupby("line").budget.sum()
        self.rf_k[0].set(money(rf.at["Total revenue", "Year"]), f"budget {money(bud['Total revenue'])}")
        self.rf_k[1].set(money(rf.at["EBITDA", "Year"]), f"budget {money(bud['EBITDA'])}")
        d = rf.at["EBITDA", "Year"] - bud["EBITDA"]
        self.rf_k[2].set(money(d), pct(d / bud["EBITDA"]) + (" U" if d < 0 else " F"), "Bad" if d < 0 else "Good")
        fill_table(self.rf_tbl, rf.loc[["Total revenue", "Total departmental expenses", "Total undistributed expenses",
                                        "Gross operating profit (GOP)", "EBITDA"]], {c: money_fmt for c in rf.columns},
                   pal=self.ctx.pal)
        budm = self.pnl[self.pnl.line == "EBITDA"].budget.values

        def paint(fig, p):
            ax = fig.add_subplot(111)
            x = np.arange(12)
            ax.plot(x, budm / 1000, color=p.series[1], lw=2, ls="--", label="Budget EBITDA")
            ax.plot(x, rf.loc["EBITDA"].values[:12] / 1000, color=p.series[0], lw=2, marker="o", ms=4,
                    label="Actual + revised forecast")
            ax.axvspan(start - 1.5, 11.5, color=p.surface2, zorder=0)
            ax.set_xticks(x, gen.MONTHS)
            style_axes(ax, p, "Monthly EBITDA ($ thousands); shaded = forecast months")
            ax.legend(frameon=False, labelcolor=p.text2, fontsize=8)
        self.rf_chart.plot(paint)

    def _rf_export(self):
        p = save_dialog(self, "Export revised forecast", "revised_forecast.xlsx", "Excel (*.xlsx)")
        if p:
            export.dataframe_to_xlsx({"Revised forecast": self.rf_df}, p,
                                     f"Revised forecast from month {self.rf_start.value()}, demand "
                                     f"{self.rf_change.value():+.1f}% (illustrative)")
            info(self, "Exported", f"Saved to {p}")

    # ------------------------------------------------------------ payroll
    def _payroll_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        top = QHBoxLayout()
        top.addWidget(label("Month:", wrap=False))
        self.pay_month = QComboBox()
        self.pay_month.addItems(["Full year"] + gen.MONTHS)
        self.pay_month.currentIndexChanged.connect(self._pay_refresh)
        top.addWidget(self.pay_month)
        top.addStretch(1)
        v.addLayout(top)
        v.addWidget(label(f"Payroll = FTE x average cost + overtime hours x ${gen.OT_RATE:.0f}.", "Muted"))
        self.pay_tbl = QTableWidget()
        self.pay_tbl.setMinimumHeight(260)
        v.addWidget(self.pay_tbl)
        self._pay_refresh()
        return w

    def _pay_refresh(self):
        pay = data().payroll
        i = self.pay_month.currentIndex()
        d = pay if i == 0 else pay[pay.month == i]
        g = d.groupby("department").agg(hc_b=("headcount_budget", "mean"), hc_a=("headcount_actual", "mean"),
                                        ot_b=("overtime_hours_budget", "sum"), ot_a=("overtime_hours_actual", "sum"),
                                        pay_b=("payroll_budget", "sum"), pay_a=("payroll_actual", "sum"))
        g.loc["Total"] = g.sum()
        t = pd.DataFrame({"FTE budget": g.hc_b, "FTE actual": g.hc_a, "OT hours budget": g.ot_b,
                          "OT hours actual": g.ot_a, "Payroll budget": g.pay_b, "Payroll actual": g.pay_a,
                          "Variance": g.pay_a - g.pay_b, "Variance %": g.pay_a / g.pay_b - 1})
        fill_table(self.pay_tbl, t, {"FTE budget": "{:,.1f}".format, "FTE actual": "{:,.1f}".format,
                                     "OT hours budget": "{:,.0f}".format, "OT hours actual": "{:,.0f}".format,
                                     "Payroll budget": money_fmt, "Payroll actual": money_fmt, "Variance": money_fmt,
                                     "Variance %": pct},
                   tone=lambda c, v, row: ("bad" if v > 0 else "good") if c in ("Variance", "Variance %") else "",
                   pal=self.ctx.pal)

    # ------------------------------------------------------------- report
    def _report_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        top = QHBoxLayout()
        top.addWidget(label("Period:", wrap=False))
        self.rep_period = QComboBox()
        self.rep_period.addItems(list(PERIODS))
        self.rep_period.setCurrentText("Q4")
        top.addWidget(self.rep_period)
        top.addWidget(button("Draft report", self._rep_draft, primary=True))
        top.addWidget(button("Export report (HTML)…", self._rep_export))
        top.addStretch(1)
        v.addLayout(top)
        v.addWidget(label("The app drafts the numbers and a structure. Edit the commentary: the 'why' and the actions "
                          "are your job as the analyst.", "Muted"))
        self.rep_text = QPlainTextEdit()
        self.rep_text.setMinimumHeight(460)
        v.addWidget(self.rep_text)
        self._rep_draft()
        return w

    def _rep_draft(self):
        months = PERIODS[self.rep_period.currentText()]
        self.rep_text.setPlainText(export.management_report_text(self.pnl, data(), months, self.rep_period.currentText()))

    def _rep_export(self):
        p = save_dialog(self, "Export management report", f"management_report_{self.rep_period.currentText()}.html",
                        "HTML (*.html)")
        if p:
            try:
                export.text_report_html(self.rep_text.toPlainText(), p, "One-page management report")
                info(self, "Exported", f"Saved to {p}. Open it in a browser; print to PDF if needed.")
            except OSError as exc:
                error(self, "Export failed", str(exc))
