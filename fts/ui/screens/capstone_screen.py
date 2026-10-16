"""Capstone project: eight steps, autosaved answers, transparent 100-point scoring."""
from __future__ import annotations

import json

import pandas as pd
from PySide6.QtWidgets import (QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QPlainTextEdit,
                               QTableWidget, QTextBrowser)

from ...content import capstone as cap
from ...data.loader import data
from ..theme import style_axes
from ..widgets import Card, Chart, KpiCard, button, error, fill_table, info, label, money, pct, save_dialog
from .base import Screen

RAW_COLS = ["month_name", "available_room_nights", "sold_room_nights", "room_revenue", "adr_reported",
            "budget_room_revenue"]


class CapstoneScreen(Screen):
    title = "Capstone project"
    subtitle = ("You are the junior analyst at The Aurelia Grand Hotel (fictional). Work through all eight steps; "
                f"answers save automatically. Pass mark {cap.PASS_MARK}/100. Written answers receive an automatic "
                "STRUCTURE check only (length, numbers, recommendation, risks, assumptions), not a judgement of "
                "business quality; an instructor should review them with the rubric in docs/ANSWER_KEY.md.")

    def __init__(self, ctx):
        super().__init__(ctx)
        self.inputs: dict[str, object] = {}
        saved = ctx.db.capstone_answers()
        self.steps = cap.steps()

        raw = Card("Raw data (contains deliberate data-quality problems)")
        raw.add(label("Selected columns shown. The full file is datasets/capstone_raw_data.csv; it can also be "
                      "exported from here.", "Muted"))
        self.raw_tbl = QTableWidget()
        self.raw_tbl.setMinimumHeight(330)
        fill_table(self.raw_tbl, data().capstone_raw[RAW_COLS], index=False)
        raw.add(self.raw_tbl)
        raw.add(button("Export full raw data to CSV…", self.export_raw))
        self.body.addWidget(raw)

        for st in self.steps:
            card = Card(f"Step {st.number}. {st.title}  ({st.points:g} points)")
            card.add(label(st.brief))
            if st.id == "c6":
                self._build_dashboard(card, saved)
            else:
                g = QGridLayout()
                for r, it in enumerate(st.items):
                    g.addWidget(label(f"{it.label}  ({it.points:g} pts)"), r, 0)
                    g.addWidget(self._make_input(it, saved.get(it.id)), r, 1)
                g.setColumnStretch(0, 2)
                g.setColumnStretch(1, 3)
                card.add(g)
            self.body.addWidget(card)

        res = Card("Score")
        row = QHBoxLayout()
        row.addWidget(button("Score my capstone", self.score, primary=True))
        row.addWidget(button("Show model answers (after scoring)", self.show_answers))
        row.addStretch(1)
        res.add(row)
        self.total = KpiCard("Latest score", "-", "")
        best = ctx.db.best_capstone()
        self.best = KpiCard("Best score", f"{best['total']:.1f}/100" if best else "-",
                            ("Passed" if best and best["passed"] else "Not yet passed") if best else "")
        kr = QHBoxLayout()
        kr.addWidget(self.total)
        kr.addWidget(self.best)
        kr.addStretch(1)
        res.add(kr)
        self.result = QTextBrowser()
        self.result.setMinimumHeight(260)
        self.result.setHtml("<p>Press <b>Score my capstone</b> to see a line-by-line breakdown.</p>")
        res.add(self.result)
        self.body.addWidget(res)
        self._scored = False

    # ------------------------------------------------------------- inputs
    def _make_input(self, it: cap.Item, saved):
        if it.kind == "numeric":
            w = QLineEdit()
            w.setPlaceholderText("e.g. 1,234.5 or 76.4%" if it.unit == "percent" else "e.g. 1,234,567")
            if saved is not None:
                w.setText(str(saved))
            w.editingFinished.connect(lambda i=it.id, w=w: self._save(i, w.text().strip()))
        elif it.kind == "choice":
            w = QComboBox()
            w.addItem("— choose —")
            w.addItems(it.choices)
            if isinstance(saved, int) and 0 <= saved < len(it.choices):
                w.setCurrentIndex(saved + 1)
            w.currentIndexChanged.connect(lambda idx, i=it.id: self._save(i, idx - 1 if idx > 0 else None))
        else:
            w = QPlainTextEdit()
            w.setMinimumHeight(170 if it.points >= 10 else 100)
            if saved:
                w.setPlainText(str(saved))
            w.textChanged.connect(lambda i=it.id, w=w: self._save(i, w.toPlainText()))
        self.inputs[it.id] = w
        return w

    def _save(self, item_id, value):
        self.ctx.db.save_capstone_answer(item_id, value)

    def _build_dashboard(self, card: Card, saved):
        chosen = set(saved.get("c6_kpis") or [])
        g = QGridLayout()
        self.kpi_boxes = {}
        for i, k in enumerate(cap.KPI_OPTIONS):
            cb = QCheckBox(k)
            cb.setChecked(k in chosen)
            cb.toggled.connect(self._kpis_changed)
            self.kpi_boxes[k] = cb
            g.addWidget(cb, i // 3, i % 3)
        card.add(g)
        self.dash = Chart(self.ctx, 3.4)
        card.add(self.dash)
        row = QHBoxLayout()
        row.addWidget(button("Export dashboard as PNG…", self.export_dashboard, primary=True))
        self.export_lbl = label("Exported ✔" if saved.get("c6_export") else "Not exported yet", "Muted")
        row.addWidget(self.export_lbl)
        row.addStretch(1)
        card.add(row)
        self._draw_dashboard()

    def _selected_kpis(self) -> list[str]:
        return [k for k, cb in self.kpi_boxes.items() if cb.isChecked()]

    def _kpis_changed(self):
        self._save("c6_kpis", self._selected_kpis())
        self._draw_dashboard()

    def _draw_dashboard(self):
        c = data().capstone_clean
        sel = self._selected_kpis()

        def paint(fig, p):
            ax = fig.add_subplot(121)
            occ = c.sold_room_nights / c.available_room_nights
            adr = c.room_revenue / c.sold_room_nights
            ax.plot(c.month_name, adr, color=p.series[0], marker="o", label="ADR ($)")
            style_axes(ax, p, "ADR by month (cleaned data)", "$")
            ax2 = ax.twinx()
            ax2.plot(c.month_name, occ * 100, color=p.series[1], marker="s", label="Occupancy %")
            ax2.tick_params(colors=p.text2, labelsize=8)
            for s in ax2.spines.values():
                s.set_visible(False)
            ax.legend(handles=ax.get_lines() + ax2.get_lines(), fontsize=7, frameon=False, labelcolor=p.text2,
                      loc="lower left")
            ax.tick_params(axis="x", labelrotation=45)
            bx = fig.add_subplot(122)
            bx.axis("off")
            bx.set_facecolor(p.surface)
            tot = c.room_revenue + c.fb_revenue + c.other_revenue
            btot = c.budget_room_revenue + c.budget_fb_revenue + c.budget_other_revenue
            cost = c.payroll + c.other_operating_expenses + c.fees_and_fixed_charges
            bcost = c.budget_payroll + c.budget_other_operating_expenses + c.budget_fees_and_fixed_charges
            vals = {
                "Occupancy %": pct(c.sold_room_nights.sum() / c.available_room_nights.sum()),
                "ADR": money(c.room_revenue.sum() / c.sold_room_nights.sum(), 2),
                "RevPAR": money(c.room_revenue.sum() / c.available_room_nights.sum(), 2),
                "Total revenue vs budget": money(tot.sum() - btot.sum()),
                "EBITDA vs budget": money((tot - cost).sum() - (btot - bcost).sum()),
                "Payroll % of revenue": pct(c.payroll.sum() / tot.sum()),
            }
            bx.text(0, 1, "GM dashboard: full year", color=p.text, fontsize=10, fontweight="bold", va="top")
            y = 0.86
            for k in sel:
                v = vals.get(k, "not a hotel KPI")
                bx.text(0, y, k, color=p.text2, fontsize=9, va="top")
                bx.text(1, y, v, color=p.bad if v == "not a hotel KPI" else p.text, fontsize=9, va="top", ha="right")
                y -= 0.09
            if not sel:
                bx.text(0, 0.8, "Tick KPIs above to build the dashboard.", color=p.muted, fontsize=9)
            bx.text(0, 0.0, "Fictional training data", color=p.muted, fontsize=7)
        self.dash.plot(paint)

    def export_dashboard(self):
        path = save_dialog(self, "Export dashboard", "capstone_dashboard.png", "PNG image (*.png)")
        if not path:
            return
        try:
            self.dash.save(path)
        except OSError as exc:
            error(self, "Export failed", str(exc))
            return
        self._save("c6_export", True)
        self.export_lbl.setText(f"Exported ✔ {path.name}")
        info(self, "Dashboard exported", f"Saved to {path}")

    def export_raw(self):
        path = save_dialog(self, "Export raw data", "capstone_raw_data.csv", "CSV (*.csv)")
        if path:
            data().capstone_raw.to_csv(path, index=False)
            info(self, "Exported", f"Saved to {path}")

    # ------------------------------------------------------------- scoring
    def collect(self) -> dict:
        ans = self.ctx.db.capstone_answers()
        for iid, w in self.inputs.items():          # make sure in-progress edits are saved
            if isinstance(w, QLineEdit):
                ans[iid] = w.text().strip()
                self._save(iid, ans[iid])
        ans["c6_kpis"] = self._selected_kpis()
        return ans

    def score(self):
        res = cap.score_all(self.collect())
        detail = {st.id: s for st, s, _ in res["steps"]}
        self.ctx.db.record_capstone_score(res["total"], res["passed"], detail)
        self.ctx.db.log("capstone_scored", json.dumps({"total": res["total"]}))
        self.ctx.invalidate()
        tone = "Good" if res["passed"] else "Bad"
        self.total.set(f"{res['total']:.1f}/100", "Passed" if res["passed"] else f"Below pass mark {cap.PASS_MARK}",
                       tone)
        best = self.ctx.db.best_capstone()
        self.best.set(f"{best['total']:.1f}/100", "Passed" if best["passed"] else "Not yet passed")
        rows = []
        for st, s, details in res["steps"]:
            rows.append(f"<h4>Step {st.number}. {st.title}: {s:g} / {st.points:g}</h4><ul>")
            for it, pts, msg in details:
                rows.append(f"<li><b>{it.label}</b>: {pts:g}/{it.points:g}. {msg}</li>")
            rows.append("</ul>")
        note = ("<p><i>Written items were scored on structure only. Passing the capstone is a training milestone, "
                "not a certification or a guarantee of employment.</i></p>")
        self.result.setHtml("".join(rows) + note)
        self._scored = True
        self.last = res

    def show_answers(self):
        if not self._scored:
            info(self, "Score first", "Score your capstone at least once before viewing the model answers.")
            return
        rows = ["<h3>Model answers</h3><ul>"]
        for st in self.steps:
            for it in st.items:
                if it.kind in ("numeric", "choice", "kpis"):
                    rows.append(f"<li>Step {st.number} · {it.label}: <b>{cap.expected_display(it)}</b></li>")
        rows.append("</ul><p>Written answers: see the rubric in docs/ANSWER_KEY.md.</p>")
        self.result.setHtml(self.result.toHtml() + "".join(rows))
