"""Hotel Revenue Management simulator for the fictional 150-room Aurelia Grand."""
from __future__ import annotations

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QSlider, QTableWidget,
                               QTabWidget, QVBoxLayout, QWidget)

from ...core import forecast as fc
from ...core import metrics as m
from ...data import generator as gen
from ...data.loader import data
from ..theme import style_axes
from ..widgets import Card, Chart, KpiCard, fill_table, label, money, pct, save_dialog, info
from .base import Screen


def pace_forecast(pace: pd.DataFrame) -> pd.DataFrame:
    p = pace.copy()
    p["ly_pickup"] = p.ly_actual_sold - p.ly_on_the_books_same_time
    p["forecast_rooms"] = (p.on_the_books + p.ly_pickup).clip(upper=p.rooms_available)
    p["forecast_revenue"] = p.forecast_rooms * p.otb_adr
    p["pace_vs_ly"] = p.on_the_books - p.ly_on_the_books_same_time
    return p


class RMSimulatorScreen(Screen):
    title = "Hotel Revenue Management simulator"
    subtitle = (f"{gen.HOTEL_NAME}: fictional 150-room luxury hotel, FY{gen.YEAR}. Data is simulated for training "
                "and is not an industry benchmark.")

    def __init__(self, ctx):
        super().__init__(ctx)
        ds = data()
        self.mr = ds.monthly_rooms.merge(ds.rooms_budget[["month", "budget_room_revenue", "budget_sold_room_nights",
                                                          "budget_adr", "available_room_nights"]]
                                         .rename(columns={"available_room_nights": "budget_available"}), on="month")
        r = self.row()
        tot_av, tot_sold, tot_rev = self.mr.available_room_nights.sum(), self.mr.sold_room_nights.sum(), self.mr.room_revenue.sum()
        for t, v, s in (("FY occupancy", pct(m.occupancy(tot_sold, tot_av)), f"{tot_sold:,} of {tot_av:,} room nights"),
                        ("FY ADR", money(m.adr(tot_rev, tot_sold), 2), "room revenue / sold"),
                        ("FY RevPAR", money(m.revpar(tot_rev, tot_av), 2), "room revenue / available"),
                        ("FY room revenue vs budget", money(tot_rev - self.mr.budget_room_revenue.sum()),
                         pct(tot_rev / self.mr.budget_room_revenue.sum() - 1) + " Unfavorable")):
            r.addWidget(KpiCard(t, v, s, "Bad" if "Unfav" in s else ""))
        tabs = QTabWidget()
        tabs.addTab(self._monthly(), "Monthly KPIs vs budget")
        tabs.addTab(self._daily(), "Daily demand, segments && channels")
        tabs.addTab(self._rates(), "Rate scenarios")
        tabs.addTab(self._pace(), "Pace && 30-day forecast")
        tabs.addTab(self._edge(), "Edge cases")
        self.body.addWidget(tabs)

    # ------------------------------------------------------------ monthly
    def _monthly(self):
        w = QWidget()
        v = QVBoxLayout(w)
        d = self.mr
        t = pd.DataFrame({
            "Month": d.month_name, "Available": d.available_room_nights, "Sold": d.sold_room_nights,
            "Occupancy": d.sold_room_nights / d.available_room_nights, "ADR": d.room_revenue / d.sold_room_nights,
            "RevPAR": d.room_revenue / d.available_room_nights, "Room revenue": d.room_revenue,
            "Budget revenue": d.budget_room_revenue, "Variance": d.room_revenue - d.budget_room_revenue,
            "Variance %": d.room_revenue / d.budget_room_revenue - 1,
            "Budget RevPAR": d.budget_room_revenue / d.budget_available}).set_index("Month")
        self.monthly_df = t
        tbl = QTableWidget()
        tbl.setMinimumHeight(380)
        fill_table(tbl, t, {"Available": "{:,.0f}".format, "Sold": "{:,.0f}".format, "Occupancy": pct,
                            "ADR": lambda x: money(x, 2), "RevPAR": lambda x: money(x, 2), "Room revenue": money,
                            "Budget revenue": money, "Variance": money, "Variance %": pct,
                            "Budget RevPAR": lambda x: money(x, 2)},
                   tone=lambda c, val, row: ("good" if val >= 0 else "bad") if c in ("Variance", "Variance %") else "",
                   pal=self.ctx.pal)
        v.addWidget(tbl)
        ch = Chart(self.ctx, 3.0)

        def paint(fig, p):
            ax = fig.add_subplot(111)
            x = np.arange(12)
            ax.plot(x, t["RevPAR"], color=p.series[0], lw=2, marker="o", ms=4, label="Actual RevPAR")
            ax.plot(x, t["Budget RevPAR"], color=p.series[1], lw=2, ls="--", label="Budget RevPAR")
            ax.set_xticks(x, t.index)
            style_axes(ax, p, "RevPAR by month: actual vs budget ($)")
            ax.legend(frameon=False, labelcolor=p.text2, fontsize=8)
            ax.annotate("Corporate demand weakens", xy=(8, t["RevPAR"].iloc[8]), xytext=(5.6, t["RevPAR"].min()),
                        color=p.text2, fontsize=8, arrowprops=dict(arrowstyle="->", color=p.muted))
        ch.plot(paint)
        v.addWidget(ch)
        return w

    # -------------------------------------------------------------- daily
    def _daily(self):
        w = QWidget()
        v = QVBoxLayout(w)
        top = QHBoxLayout()
        top.addWidget(label("Month:", wrap=False))
        self.month_box = QComboBox()
        self.month_box.addItems(gen.MONTHS)
        self.month_box.setCurrentIndex(9)
        self.month_box.currentIndexChanged.connect(self._daily_refresh)
        top.addWidget(self.month_box)
        top.addStretch(1)
        v.addLayout(top)
        self.daily_chart = Chart(self.ctx, 2.8)
        v.addWidget(self.daily_chart)
        r = QHBoxLayout()
        c1, c2, c3 = Card("Weekday vs weekend"), Card("Segments"), Card("Channels (net of commission)")
        self.t_wk, self.t_seg, self.t_ch = QTableWidget(), QTableWidget(), QTableWidget()
        for c, t in ((c1, self.t_wk), (c2, self.t_seg), (c3, self.t_ch)):
            t.setMinimumHeight(170)
            c.add(t)
            r.addWidget(c)
        v.addLayout(r)
        v.addWidget(label("Weekend = Friday and Saturday nights. Net ADR = (revenue - commission) / room nights.", "Muted"))
        self._daily_refresh()
        return w

    def _daily_refresh(self):
        mi = self.month_box.currentIndex() + 1
        ds = data()
        d = ds.daily[pd.to_datetime(ds.daily.date).dt.month == mi].copy()
        d["occ"] = d.rooms_sold / d.rooms_available
        wk = d.groupby("day_type").agg(nights=("date", "count"), sold=("rooms_sold", "sum"),
                                       avail=("rooms_available", "sum"), rev=("room_revenue", "sum"))
        wk = pd.DataFrame({"Nights": wk.nights, "Occupancy": wk.sold / wk.avail, "ADR": wk.rev / wk.sold,
                           "RevPAR": wk.rev / wk.avail})
        fill_table(self.t_wk, wk, {"Nights": str, "Occupancy": pct, "ADR": lambda x: money(x, 2),
                                   "RevPAR": lambda x: money(x, 2)}, pal=self.ctx.pal)
        segs = pd.DataFrame({s: {"Room nights": d[f"sold_{s.lower()}"].sum(),
                                 "Revenue": d[f"revenue_{s.lower()}"].sum()} for s in gen.SEGMENTS}).T
        segs["ADR"] = segs.Revenue / segs["Room nights"]
        segs["Mix"] = segs["Room nights"] / segs["Room nights"].sum()
        fill_table(self.t_seg, segs, {"Room nights": "{:,.0f}".format, "Revenue": money,
                                      "ADR": lambda x: money(x, 2), "Mix": pct}, pal=self.ctx.pal)
        ch = ds.channels[ds.channels.month == mi].set_index("channel")
        cht = pd.DataFrame({"Room nights": ch.room_nights, "Gross ADR": ch.room_revenue / ch.room_nights,
                            "Commission": ch.commission_cost,
                            "Net ADR": (ch.room_revenue - ch.commission_cost) / ch.room_nights})
        fill_table(self.t_ch, cht, {"Room nights": "{:,.0f}".format, "Gross ADR": lambda x: money(x, 2),
                                    "Commission": money, "Net ADR": lambda x: money(x, 2)}, pal=self.ctx.pal)

        def paint(fig, p):
            ax = fig.add_subplot(111)
            x = pd.to_datetime(d.date).dt.day
            cols = [p.series[1] if t == "Weekend" else p.series[0] for t in d.day_type]
            ax.bar(x, d.occ * 100, color=cols, width=0.7)
            ax.set_ylim(0, 100)
            style_axes(ax, p, f"Daily occupancy %, {gen.MONTHS[mi - 1]} (orange = weekend nights)")
            ax.set_xlabel("Day of month", color=p.text2, fontsize=8)
        self.daily_chart.plot(paint)

    # ------------------------------------------------------------- rates
    def _rates(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(label("Constant-elasticity demand model: Occ_new = Occ x (Rate_new / Rate)^elasticity, capped at "
                          "100%. A teaching simplification. Real demand also depends on competitors, dates and "
                          "segments.", "Muted"))
        form = QFormLayout()
        self.r_month = QComboBox()
        self.r_month.addItems(gen.MONTHS)
        self.r_month.setCurrentIndex(0)
        self.r_month.currentIndexChanged.connect(self._load_base)
        self.r_occ = QDoubleSpinBox(decimals=1, minimum=1, maximum=100, suffix=" %")
        self.r_adr = QDoubleSpinBox(decimals=2, minimum=1, maximum=5000, prefix="$ ")
        self.r_el = QDoubleSpinBox(decimals=2, minimum=-4, maximum=0, singleStep=0.1, value=-1.2)
        self.r_var = QDoubleSpinBox(decimals=2, minimum=0, maximum=500, value=60, prefix="$ ")
        self.r_slider = QSlider(Qt.Horizontal)
        self.r_slider.setRange(-30, 30)
        self.r_slider.setValue(5)
        self.r_slider_lbl = label("", wrap=False)
        sl = QHBoxLayout()
        sl.addWidget(self.r_slider, 1)
        sl.addWidget(self.r_slider_lbl)
        form.addRow("Base month", self.r_month)
        form.addRow("Base occupancy", self.r_occ)
        form.addRow("Base ADR", self.r_adr)
        form.addRow("Price elasticity", self.r_el)
        form.addRow("Variable cost per occupied room (incl. F&B profit lost/gained ignored)", self.r_var)
        form.addRow("Rate change", sl)
        v.addLayout(form)
        for wdg in (self.r_occ, self.r_adr, self.r_el, self.r_var):
            wdg.valueChanged.connect(self._rate_refresh)
        self.r_slider.valueChanged.connect(self._rate_refresh)
        self.r_out = label("", rich=True)
        v.addWidget(self.r_out)
        self.r_chart = Chart(self.ctx, 2.8)
        v.addWidget(self.r_chart)
        self._load_base()
        return w

    def _load_base(self):
        r = self.mr.iloc[self.r_month.currentIndex()]
        for wdg in (self.r_occ, self.r_adr):
            wdg.blockSignals(True)
        self.r_occ.setValue(round(r.sold_room_nights / r.available_room_nights * 100, 1))
        self.r_adr.setValue(round(r.room_revenue / r.sold_room_nights, 2))
        for wdg in (self.r_occ, self.r_adr):
            wdg.blockSignals(False)
        self._rate_refresh()

    def _rate_refresh(self):
        chg = self.r_slider.value() / 100
        self.r_slider_lbl.setText(f"{chg:+.0%}")
        occ, adr_, el, var = self.r_occ.value() / 100, self.r_adr.value(), self.r_el.value(), self.r_var.value()
        avail = int(self.mr.iloc[self.r_month.currentIndex()].available_room_nights)
        new_adr = adr_ * (1 + chg)
        new_occ = m.demand_at_rate(occ, adr_, new_adr, el)
        base_rev, new_rev = avail * occ * adr_, avail * new_occ * new_adr
        base_contrib = avail * occ * (adr_ - var)
        new_contrib = avail * new_occ * (new_adr - var)
        p = self.ctx.pal
        col = p.good if new_contrib >= base_contrib else p.bad
        self.r_out.setText(
            f"<b>Scenario:</b> occupancy {pct(occ)} → <b>{pct(new_occ)}</b>; ADR {money(adr_, 2)} → <b>{money(new_adr, 2)}</b>; "
            f"RevPAR {money(occ * adr_, 2)} → <b>{money(new_occ * new_adr, 2)}</b><br>"
            f"Room revenue for the month ({avail:,} available room nights): {money(base_rev)} → <b>{money(new_rev)}</b> "
            f"({money(new_rev - base_rev)})<br>Rooms contribution after variable cost: "
            f"<span style='color:{col}'><b>{money(new_contrib - base_contrib)}</b></span> vs base. "
            "<i>Illustrative only, not a guaranteed outcome.</i>")

        def paint(fig, pal):
            ax = fig.add_subplot(111)
            xs = np.arange(-30, 31)
            rp = [m.demand_at_rate(occ, adr_, adr_ * (1 + x / 100), el) * adr_ * (1 + x / 100) for x in xs]
            ax.plot(xs, rp, color=pal.series[0], lw=2)
            ax.axvline(chg * 100, color=pal.series[1], lw=1.5, ls="--")
            ax.scatter([chg * 100], [new_occ * new_adr], color=pal.series[1], s=40, zorder=3)
            style_axes(ax, pal, "RevPAR across rate changes (dashed line = your scenario)")
            ax.set_xlabel("Rate change %", color=pal.text2, fontsize=8)
        self.r_chart.plot(paint)

    # -------------------------------------------------------------- pace
    def _pace(self):
        w = QWidget()
        v = QVBoxLayout(w)
        p = pace_forecast(data().pace)
        self.pace_df = p
        hist = data().daily.copy()
        prof = fc.weekday_profile_forecast(hist, "rooms_sold", 30)
        v.addWidget(label(f"As of 31 Dec {gen.YEAR}, next 30 nights. Pickup method: forecast = on the books + last "
                          "year's pickup from the same days out, capped at 150 rooms. Last-year dates are aligned by "
                          "weekday (364 days earlier). Forecasts are estimates, not guarantees.", "Muted"))
        r = QHBoxLayout()
        r.addWidget(KpiCard("On the books", f"{int(p.on_the_books.sum()):,}", "room nights"))
        r.addWidget(KpiCard("Pace vs last year", f"{int(p.pace_vs_ly.sum()):+,}",
                            pct(p.on_the_books.sum() / p.ly_on_the_books_same_time.sum() - 1), "Bad"))
        r.addWidget(KpiCard("Pickup forecast", f"{int(p.forecast_rooms.sum()):,}",
                            f"occupancy {pct(p.forecast_rooms.sum() / p.rooms_available.sum())}"))
        r.addWidget(KpiCard("Forecast room revenue", money(p.forecast_revenue.sum()), "forecast rooms x OTB ADR"))
        r.addWidget(KpiCard("History-only method", f"{prof.rooms_sold.sum():,.0f}",
                            "same-weekday average of last 4 weeks (ignores bookings)"))
        v.addLayout(r)
        ch = Chart(self.ctx, 2.8)

        def paint(fig, pal):
            ax = fig.add_subplot(111)
            x = np.arange(len(p))
            ax.plot(x, p.ly_actual_sold, color=pal.series[2], lw=2, label="Last year final")
            ax.plot(x, p.forecast_rooms, color=pal.series[0], lw=2, label="Pickup forecast")
            ax.plot(x, p.on_the_books, color=pal.series[1], lw=2, ls="--", label="On the books today")
            ax.set_xticks(x[::3], [s[5:] for s in p.stay_date[::3]])
            style_axes(ax, pal, "Rooms per night, January")
            ax.legend(frameon=False, labelcolor=pal.text2, fontsize=8)
        ch.plot(paint)
        v.addWidget(ch)
        t = QTableWidget()
        t.setMinimumHeight(300)
        show = p[["stay_date", "weekday", "days_out", "on_the_books", "ly_on_the_books_same_time", "ly_actual_sold",
                  "ly_pickup", "forecast_rooms", "otb_adr", "forecast_revenue"]].set_index("stay_date")
        show.columns = ["Weekday", "Days out", "OTB", "LY OTB", "LY final", "LY pickup", "Forecast rooms", "OTB ADR",
                        "Forecast revenue"]
        fill_table(t, show, {"OTB ADR": lambda x: money(x, 2), "Forecast revenue": money}, pal=self.ctx.pal)
        v.addWidget(t)
        from ..widgets import button
        v.addWidget(button("Export forecast to CSV…", self._export_pace))
        return w

    def _export_pace(self):
        path = save_dialog(self, "Export forecast", "january_pickup_forecast.csv", "CSV (*.csv)")
        if path:
            self.pace_df.to_csv(path, index=False)
            info(self, "Exported", f"Saved to {path}")

    # -------------------------------------------------------------- edge
    def _edge(self):
        w = QWidget()
        v = QVBoxLayout(w)
        j = data().daily_issues.copy()
        rows = []
        for _, r in j.iterrows():
            sold, av, rev = r.rooms_sold, r.rooms_available, r.room_revenue
            try:
                occ = m.occupancy(sold, av)
                note = ""
            except ValueError as exc:
                occ, note = None, str(exc)
            a, rp = m.adr(rev, sold), m.revpar(rev, av)
            if m.is_missing(sold):
                note = "Missing observation: recover from the night audit; do not treat as 0."
            elif av == 0:
                note = "Hotel closed (0 available): KPIs undefined; exclude from averages."
            elif sold == 0:
                note = "Nothing sold: occupancy 0%, RevPAR $0, ADR undefined (not $0)."
            rows.append({"Date": r.date, "Available": av, "Sold": sold, "Revenue": rev,
                         "Occupancy": occ, "ADR": a, "RevPAR": rp, "Note": note})
        df = pd.DataFrame(rows).set_index("Date")
        valid = j[pd.to_numeric(j.rooms_sold, errors="coerce").notna()]
        sold = pd.to_numeric(valid.rooms_sold).sum()
        av = pd.to_numeric(valid.rooms_available).sum()
        rev = pd.to_numeric(valid.room_revenue).sum()
        v.addWidget(label(f"January extract with deliberate problems (datasets/hotel_daily_jan_with_issues.csv). "
                          f"Month KPIs on the {len(valid)} valid days: occupancy {pct(m.occupancy(sold, av))}, "
                          f"ADR {money(m.adr(rev, sold), 2)}, RevPAR {money(m.revpar(rev, av), 2)}. Totals are "
                          "divided once; daily ratios are never averaged.", rich=True))
        t = QTableWidget()
        t.setMinimumHeight(460)
        fill_table(t, df, {"Revenue": money, "Occupancy": pct, "ADR": lambda x: money(x, 2),
                           "RevPAR": lambda x: money(x, 2)}, pal=self.ctx.pal,
                   tone=lambda c, val, row: "bad" if c == "Note" and val else "")
        v.addWidget(t)
        return w
