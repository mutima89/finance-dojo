"""Scenario & sensitivity analysis on the simplified 3-year hotel forecast."""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QTableWidget, QWidget

from ...core import forecast as fc
from ...reports import export
from ..theme import style_axes
from ..widgets import Card, Chart, button, error, fill_table, info, label, money, pct, save_dialog
from .base import Screen

ROW_FMT = {"Occupancy": pct, "EBITDA margin": pct, "ADR": lambda x: money(x, 2), "RevPAR": lambda x: money(x, 2),
           "Available room nights": "{:,.0f}".format, "Sold room nights": "{:,.0f}".format}


class ScenarioScreen(Screen):
    title = "Scenario & sensitivity analysis"
    subtitle = ("Simplified 3-year driver model: operations → EBITDA → free cash flow → cash. Training model only: no "
                "debt, tax or full balance sheet. Outputs are illustrative estimates, not predictions.")

    def __init__(self, ctx):
        super().__init__(ctx)
        a = fc.HotelAssumptions()
        inp = Card("Base assumptions (edit and the model recalculates)")
        g = QGridLayout()
        self.f = {}

        def spin(key, text, val, lo, hi, dec, step, r, c, prefix="", suffix=""):
            s = QDoubleSpinBox(decimals=dec, minimum=lo, maximum=hi, singleStep=step, value=val)
            s.setPrefix(prefix)
            s.setSuffix(suffix)
            s.valueChanged.connect(self.refresh)
            self.f[key] = s
            g.addWidget(label(text, wrap=False), r, c)
            g.addWidget(s, r, c + 1)
        for y in range(3):
            spin(f"occ{y}", f"Occupancy Y{y + 1}", a.occupancy[y] * 100, 0, 100, 1, 0.5, y, 0, suffix=" %")
            spin(f"adr{y}", f"ADR Y{y + 1}", a.adr[y], 0, 5000, 0, 5, y, 2, prefix="$ ")
        spin("anc", "Ancillary % of rooms revenue", a.ancillary_pct_of_rooms * 100, 0, 200, 1, 1, 3, 0, suffix=" %")
        spin("payfix", "Fixed payroll (Y1)", a.payroll_fixed, 0, 1e8, 0, 50_000, 3, 2, prefix="$ ")
        spin("payocc", "Payroll per sold room", a.payroll_per_occupied_room, 0, 500, 0, 1, 4, 0, prefix="$ ")
        spin("opex", "Other operating costs % of revenue", a.other_opex_pct_revenue * 100, 0, 100, 1, 0.5, 4, 2, suffix=" %")
        spin("fixed", "Fixed charges per year", a.fixed_charges, 0, 1e8, 0, 10_000, 5, 0, prefix="$ ")
        spin("capex", "Capex % of revenue", a.capex_pct_revenue * 100, 0, 50, 1, 0.5, 5, 2, suffix=" %")
        inp.add(g)
        inp.add(label(f"Opening cash {money(a.opening_cash)} and working capital {money(a.opening_nwc)} come from the "
                      "FY closing balance sheet.", "Muted"))
        row = QHBoxLayout()
        row.addWidget(button("Reset to defaults", self.reset))
        row.addWidget(button("Export model, scenarios & checks to Excel…", self.export_xlsx, primary=True))
        row.addStretch(1)
        inp.add(row)
        self.body.addWidget(inp)

        r = self.row()
        c1 = Card("Scenario results")
        top = QHBoxLayout()
        top.addWidget(label("Show model for:", wrap=False))
        self.scen = QComboBox()
        self.scen.addItems(list(fc.SCENARIOS))
        self.scen.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.scen)
        top.addStretch(1)
        c1.add(top)
        c1.add(label("Upside: occupancy x1.04, ADR x1.03, costs x0.99 · Downside: occupancy x0.90, ADR x0.95, "
                     "costs x1.03", "Muted"))
        self.scen_tbl = QTableWidget()
        self.scen_tbl.setMinimumHeight(140)
        c1.add(self.scen_tbl)
        self.scen_chart = Chart(ctx, 2.6)
        c1.add(self.scen_chart)
        r.addWidget(c1, 1)
        c2 = Card("Model checks")
        self.checks = label("", rich=True)
        c2.add(self.checks)
        r.addWidget(c2, 1)

        self.model_tbl = QTableWidget()
        self.model_tbl.setMinimumHeight(560)
        mc = Card("Model (selected scenario)")
        mc.add(self.model_tbl)
        self.body.addWidget(mc)

        r2 = self.row()
        s1 = Card("Two-way sensitivity: Year 1 EBITDA ($000) by occupancy change (rows) and ADR change (columns)")
        self.sens_tbl = QTableWidget()
        self.sens_tbl.setMinimumHeight(260)
        s1.add(self.sens_tbl)
        r2.addWidget(s1, 1)
        s2 = Card("One-way sensitivity (tornado): Year 1 EBITDA when each input moves ±10%")
        self.tornado = Chart(ctx, 3.0)
        s2.add(self.tornado)
        r2.addWidget(s2, 1)
        self.refresh()

    def assumptions(self) -> fc.HotelAssumptions:
        f = self.f
        return replace(fc.HotelAssumptions(),
                       occupancy=tuple(f[f"occ{y}"].value() / 100 for y in range(3)),
                       adr=tuple(f[f"adr{y}"].value() for y in range(3)),
                       ancillary_pct_of_rooms=f["anc"].value() / 100, payroll_fixed=f["payfix"].value(),
                       payroll_per_occupied_room=f["payocc"].value(),
                       other_opex_pct_revenue=f["opex"].value() / 100, fixed_charges=f["fixed"].value(),
                       capex_pct_revenue=f["capex"].value() / 100)

    def reset(self):
        a = fc.HotelAssumptions()
        vals = {"anc": a.ancillary_pct_of_rooms * 100, "payfix": a.payroll_fixed, "payocc": a.payroll_per_occupied_room,
                "opex": a.other_opex_pct_revenue * 100, "fixed": a.fixed_charges, "capex": a.capex_pct_revenue * 100}
        for y in range(3):
            vals[f"occ{y}"], vals[f"adr{y}"] = a.occupancy[y] * 100, a.adr[y]
        for k, v in vals.items():
            self.f[k].blockSignals(True)
            self.f[k].setValue(v)
            self.f[k].blockSignals(False)
        self.refresh()

    def refresh(self):
        try:
            a = self.assumptions()
            name = self.scen.currentText()
            model = fc.hotel_forecast(a.scaled(**fc.SCENARIOS[name]))
        except ValueError as exc:
            self.checks.setText(f"<span style='color:{self.ctx.pal.bad}'>⚠ {exc}</span>")
            return
        self.model = model
        disp = model.copy().astype(object)
        for idx in disp.index:
            f = ROW_FMT.get(idx, money)
            disp.loc[idx] = [f(v) for v in model.loc[idx]]
        fill_table(self.model_tbl, disp, pal=self.ctx.pal)
        self.scen_df = pd.DataFrame({n: fc.hotel_forecast(a.scaled(**mult)).loc["EBITDA"] for n, mult in fc.SCENARIOS.items()}).T
        self.cash_df = pd.DataFrame({n: fc.hotel_forecast(a.scaled(**mult)).loc["Closing cash"] for n, mult in fc.SCENARIOS.items()}).T
        tbl = self.scen_df.copy()
        tbl.columns = [f"EBITDA {c}" for c in tbl.columns]
        tbl["Closing cash Y3"] = self.cash_df["Year 3"]
        fill_table(self.scen_tbl, tbl, {c: money for c in tbl.columns}, pal=self.ctx.pal)
        sc = self.scen_df

        def paint(fig, p):
            ax = fig.add_subplot(111)
            x = np.arange(3)
            for i, n in enumerate(sc.index):
                ax.bar(x + (i - 1) * 0.26, sc.loc[n] / 1e6, width=0.24, color=p.series[i], label=n)
            ax.set_xticks(x, sc.columns)
            style_axes(ax, p, "EBITDA by scenario ($ millions)")
            ax.legend(frameon=False, labelcolor=p.text2, fontsize=8)
        self.scen_chart.plot(paint)
        self.check_results = fc.reconcile_forecast(model)
        ok = all(c[1] for c in self.check_results)
        p = self.ctx.pal
        self.checks.setText(
            f"<b style='color:{p.good if ok else p.bad}'>{'✔ All ' + str(len(self.check_results)) + ' checks pass' if ok else '✘ Some checks fail'}"
            "</b><br>" + "<br>".join(f"{'✔' if c[1] else '✘'} {c[0]}" for c in self.check_results))
        base_e = fc.hotel_forecast(a).at["EBITDA", "Year 1"]
        occ_steps = [-0.06, -0.03, 0.0, 0.03, 0.06]
        adr_steps = [-0.10, -0.05, 0.0, 0.05, 0.10]

        def ebitda(do, da):
            aa = replace(a, occupancy=tuple(min(1.0, max(0.0, o + do)) for o in a.occupancy),
                         adr=tuple(x * (1 + da) for x in a.adr))
            return fc.hotel_forecast(aa).at["EBITDA", "Year 1"] / 1000
        grid = fc.sensitivity_grid(ebitda, occ_steps, adr_steps)
        self.sens_df = grid
        grid_disp = grid.copy()
        grid_disp.index = [f"{x * 100:+.0f} pts" for x in occ_steps]
        grid_disp.columns = [f"ADR {x * 100:+.0f}%" for x in adr_steps]
        fill_table(self.sens_tbl, grid_disp, {c: "{:,.0f}".format for c in grid_disp.columns}, pal=self.ctx.pal,
                   tone=lambda c, v, row: "good" if v > base_e / 1000 + 1 else "bad" if v < base_e / 1000 - 1 else "")
        inputs = {"Occupancy": "occupancy", "ADR": "adr", "Ancillary %": "ancillary_pct_of_rooms",
                  "Fixed payroll": "payroll_fixed", "Other opex %": "other_opex_pct_revenue",
                  "Fixed charges": "fixed_charges"}
        bars = []
        for lab, attr in inputs.items():
            vals = []
            for mult in (0.9, 1.1):
                cur = getattr(a, attr)
                new = tuple(min(1.0, x * mult) if attr == "occupancy" else x * mult for x in cur) if isinstance(cur, tuple) else cur * mult
                vals.append(fc.hotel_forecast(replace(a, **{attr: new})).at["EBITDA", "Year 1"] - base_e)
            bars.append((lab, vals[0], vals[1]))
        bars.sort(key=lambda b: max(abs(b[1]), abs(b[2])))

        def paint2(fig, p):
            ax = fig.add_subplot(111)
            y = np.arange(len(bars))
            ax.barh(y, [b[1] / 1e6 for b in bars], color=p.series[1], height=0.55, label="input -10%")
            ax.barh(y, [b[2] / 1e6 for b in bars], color=p.series[0], height=0.55, label="input +10%")
            ax.set_yticks(y, [b[0] for b in bars])
            ax.axvline(0, color=p.border)
            style_axes(ax, p, "Change in Year 1 EBITDA ($ millions)")
            ax.legend(frameon=False, labelcolor=p.text2, fontsize=8, loc="lower right")
        self.tornado.plot(paint2)

    def export_xlsx(self):
        path = save_dialog(self, "Export scenario model", "scenario_model.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        checks = pd.DataFrame(self.check_results, columns=["Check", "Passed", "Detail"]).set_index("Check")
        sens = self.sens_df.copy()
        sens.index = [f"Occ {x * 100:+.0f} pts" for x in sens.index]
        sens.columns = [f"ADR {x * 100:+.0f}%" for x in sens.columns]
        try:
            export.dataframe_to_xlsx({"Model": self.model, "Scenario EBITDA": self.scen_df, "Closing cash": self.cash_df,
                                      "Sensitivity Y1 EBITDA 000": sens, "Checks": checks}, path,
                                     f"3-year forecast: {self.scen.currentText()} scenario (simplified training model)")
            info(self, "Exported", f"Saved to {path}")
        except OSError as exc:
            error(self, "Export failed", str(exc))
