"""Progress & competency report."""
from __future__ import annotations

import numpy as np
import pandas as pd
from PySide6.QtWidgets import QHBoxLayout, QTableWidget

from ...content import curriculum
from ...core import mastery
from ...reports import export
from ..theme import style_axes
from ..widgets import Card, Chart, KpiCard, button, error, fill_table, info, label, save_dialog
from .base import Screen


class ProgressScreen(Screen):
    title = "Progress & competency"
    subtitle = export.DISCLAIMER_CERT

    def __init__(self, ctx):
        super().__init__(ctx)
        r = self.row()
        self.k_level = KpiCard("Overall level")
        self.k_acc = KpiCard("Exercise accuracy")
        self.k_time = KpiCard("Active study time")
        self.k_cap = KpiCard("Capstone")
        self.k_wb = KpiCard("Excel workbook tasks")
        for k in (self.k_level, self.k_acc, self.k_time, self.k_cap, self.k_wb):
            r.addWidget(k)

        rules = Card("How levels are decided")
        rules.add(label("Skill score = 60% exercises + 40% quiz (Excel formulas: 40% exercises + 20% quiz + 40% "
                        "workbook tasks). Exercise credit: 1.00 first try, 0.85 first try with hints, 0.70 second "
                        "try, 0.50 later, 0 if unsolved or the solution was revealed. Beginner < 40 ≤ Developing < 70 "
                        "≤ Competent. \"Job-ready for supervised tasks\" also needs 85+, every practical exercise "
                        "solved without revealing, the practical tasks saved and the capstone passed, so quiz "
                        "scores alone can never reach it.", "Muted"))
        self.body.addWidget(rules)

        r2 = self.row()
        c1 = Card("Skills")
        self.skill_tbl = QTableWidget()
        self.skill_tbl.setMinimumHeight(330)
        c1.add(self.skill_tbl)
        r2.addWidget(c1, 3)
        c2 = Card("Skill scores")
        self.chart = Chart(ctx, 3.8)
        c2.add(self.chart)
        c2.add(label("Dashed lines: 40 Developing, 70 Competent, 85 needed for job-ready.", "Muted"))
        r2.addWidget(c2, 2)

        self.weak = Card("Weak topics and suggested next steps")
        self.weak_lbl = label("", rich=True)
        self.weak.add(self.weak_lbl)
        self.body.addWidget(self.weak)

        c3 = Card("Lessons")
        self.lesson_tbl = QTableWidget()
        self.lesson_tbl.setMinimumHeight(360)
        c3.add(self.lesson_tbl)
        self.body.addWidget(c3)

        r3 = self.row()
        c4 = Card("Quiz history")
        self.quiz_tbl = QTableWidget()
        self.quiz_tbl.setMinimumHeight(220)
        c4.add(self.quiz_tbl)
        r3.addWidget(c4, 1)
        c5 = Card("Exercise accuracy by exercise")
        self.ex_tbl = QTableWidget()
        self.ex_tbl.setMinimumHeight(220)
        c5.add(self.ex_tbl)
        r3.addWidget(c5, 1)

        ex = Card("Export")
        row = QHBoxLayout()
        row.addWidget(button("Export competency report (HTML)…", self.export_html, primary=True))
        row.addWidget(button("Export competency report (Excel)…", self.export_xlsx))
        row.addWidget(button("Refresh", self.refresh))
        row.addStretch(1)
        ex.add(row)
        self.body.addWidget(ex)

    def on_show(self, **kw):
        self.refresh()

    def refresh(self):
        db = self.ctx.db
        self.ctx.invalidate()
        skills = self.ctx.skills()
        frames = export.progress_frames(db, skills)
        order = {lv: i for i, lv in enumerate(mastery.LEVELS)}
        overall = min((s.level for s in skills), key=lambda lv: order[lv]) if skills else mastery.LEVELS[0]
        self.k_level.set(overall, "lowest of your skill levels")
        n, ok = db.attempts_total()
        self.k_acc.set(f"{ok / n * 100:.0f}%" if n else "-", f"{ok} correct of {n} attempts")
        secs = sum(db.lesson_seconds().values())
        self.k_time.set(f"{secs // 3600}h {secs % 3600 // 60:02d}m", "active time in lessons")
        best = db.best_capstone()
        self.k_cap.set(f"{best['total']:.1f}/100" if best else "-",
                       ("Passed" if best["passed"] else "Not yet passed") if best else "not attempted",
                       ("Good" if best["passed"] else "Bad") if best else "")
        wb = db.workbook_results()
        self.k_wb.set(f"{sum(1 for v in wb.values() if v == 'correct')}/16", "correct in last graded workbook")

        sk = frames["Skills"][["Skill", "Score", "Level", "Exercise component", "Quiz component",
                               "Workbook component", "Weak topic"]]
        fill_table(self.skill_tbl, sk, {"Score": "{:.1f}".format}, index=False,
                   tone=lambda col, v, row: ("bad" if v == "Yes" else "") if col == "Weak topic" else "",
                   pal=self.ctx.pal)
        les = frames["Lessons"].copy()
        les["Progress"] = (les["Progress"] * 100).round(0).astype(int).astype(str) + "%"
        fill_table(self.lesson_tbl, les, index=False)
        titles = {l.id: l.title for m in curriculum.modules() for l in m.lessons}
        qdf = pd.DataFrame([{"When": h["ts"][:16].replace("T", " "), "Lesson": titles.get(h["lesson_id"], h["lesson_id"]),
                             "Score": f"{h['score']}/{h['total']}"} for h in reversed(db.quiz_history())],
                           columns=["When", "Lesson", "Score"])
        fill_table(self.quiz_tbl, qdf, index=False)
        fill_table(self.ex_tbl, frames["Exercises"], index=False)

        weak = [s for s in skills if s.weak]
        items = [f"<li><b>{s.skill}</b> ({s.score:.0f}): {s.reason}</li>" for s in weak]
        nxt = [f"<li><b>{s.skill}</b> ({s.level}): {s.reason}</li>" for s in skills if not s.weak]
        self.weak_lbl.setText(
            ("<p>Weak topics (score under 60 after attempting, or 3+ wrong answers on one exercise):</p><ul>"
             + "".join(items) + "</ul>" if items else "<p>No weak topics flagged yet.</p>")
            + "<p>Next requirement per skill:</p><ul>" + "".join(nxt) + "</ul>")

        names = [s.skill for s in skills]
        scores = [s.score for s in skills]

        def paint(fig, p):
            ax = fig.add_subplot(111)
            y = np.arange(len(names))
            ax.barh(y, scores, color=p.series[0], height=0.6)
            for lim in (40, 70, 85):
                ax.axvline(lim, color=p.muted, linestyle="--", linewidth=0.8)
            ax.set_yticks(y, names, fontsize=8)
            ax.invert_yaxis()
            ax.set_xlim(0, 100)
            ax.set_xticks([0, 40, 70, 85, 100])
            style_axes(ax, p, "Score by skill (0-100)")
            ax.yaxis.grid(False)
        self.chart.plot(paint)

    def export_html(self):
        path = save_dialog(self, "Export report", "competency_report.html", "HTML (*.html)")
        if path:
            try:
                export.progress_report_html(self.ctx.db, self.ctx.skills(), path)
            except OSError as exc:
                error(self, "Export failed", str(exc))
                return
            info(self, "Exported", f"Saved to {path}")

    def export_xlsx(self):
        path = save_dialog(self, "Export report", "competency_report.xlsx", "Excel workbook (*.xlsx)")
        if path:
            try:
                export.progress_report_xlsx(self.ctx.db, self.ctx.skills(), path)
            except OSError as exc:
                error(self, "Export failed", str(exc))
                return
            info(self, "Exported", f"Saved to {path}")
