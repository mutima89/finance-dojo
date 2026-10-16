"""Training roadmap: eight modules in order, with real completion status."""
from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QProgressBar, QWidget

from ...content import curriculum
from ...core import mastery
from ..widgets import Card, button, label
from .base import Screen


class RoadmapScreen(Screen):
    title = "Training roadmap"
    subtitle = ("Concept → Worked example → Guided practice → Independent practice → Business interpretation → "
                "Assessment. Modules build on each other; take them in order.")

    def __init__(self, ctx):
        super().__init__(ctx)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(12)
        self.body.addWidget(self.grid_host)
        self.body.addStretch(1)

    def on_show(self, **kw):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        db = self.ctx.db
        status, tasks = db.all_exercise_status(), db.all_tasks()
        for i, m in enumerate(curriculum.modules()):
            fr = [mastery.lesson_progress_fraction(l, status, db.best_quiz(l.id), tasks.get(l.task.id))
                  for l in m.lessons]
            frac = sum(fr) / len(fr)
            state = "Complete" if frac >= 0.999 else "In progress" if frac > 0 else "Not started"
            c = Card(f"Module {m.number} · {state}")
            c.add(label(m.title, "H2"))
            c.add(label(m.summary, "Muted"))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(round(frac * 100))
            c.add(bar)
            for l, f in zip(m.lessons, fr):
                tick = "✔" if f >= 0.999 else "◐" if f > 0 else "○"
                c.add(label(f"{tick}  {l.title}  ({l.minutes} min)"))
            row = QHBoxLayout()
            row.addWidget(button("Open module", lambda _=False, lid=m.lessons[0].id: self.ctx.navigate("lessons", lesson=lid),
                                 primary=True))
            for t in m.tools:
                row.addWidget(button(self.ctx.screen_title(t), lambda _=False, k=t: self.ctx.navigate(k)))
            row.addStretch(1)
            c.add(row)
            self.grid.addWidget(c, i // 2, i % 2)
        best = db.best_capstone()
        c = Card("Final · Capstone project")
        c.add(label("Junior financial & commercial analyst for The Aurelia Grand Hotel", "H2"))
        c.add(label("Clean data, calculate KPIs, forecast, explain variances, evaluate two decisions, build a "
                    "dashboard, write a recommendation and face a simulated management meeting. Scored with a "
                    "transparent 100-point rubric (pass mark 70).", "Muted"))
        c.add(label(f"Best score: {best['total']:.0f}/100" if best else "Not attempted yet."))
        c.add(button("Open capstone", lambda: self.ctx.navigate("capstone"), primary=True))
        self.grid.addWidget(c, 4, 0, 1, 2)
