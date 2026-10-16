"""Home and learning dashboard."""
from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QProgressBar

from ...content import curriculum
from ...core import mastery
from ..widgets import Card, Chart, KpiCard, button, label
from .base import Screen


def overall(ctx):
    db = ctx.db
    status = db.all_exercise_status()
    tasks = db.all_tasks()
    lessons = [(m, l) for m in curriculum.modules() for l in m.lessons]
    done = sum(mastery.lesson_complete(l, status, db.best_quiz(l.id), tasks.get(l.task.id)) for _, l in lessons)
    frac = sum(mastery.lesson_progress_fraction(l, status, db.best_quiz(l.id), tasks.get(l.task.id))
               for _, l in lessons) / len(lessons)
    quizzes = [db.best_quiz(l.id) for _, l in lessons]
    qs = [s / t for s, t in (q for q in quizzes if q)]
    n_att, n_ok = db.attempts_total()
    first = [s for s in status.values() if s.get("solved_on") == 1 and not s.get("revealed")]
    return dict(lessons_done=done, lessons_total=len(lessons), frac=frac,
                quiz=(sum(qs) / len(qs)) if qs else None, attempts=n_att, correct=n_ok,
                first_try=len(first), exercises_total=len(curriculum.all_exercises()))


class HomeScreen(Screen):
    title = "Welcome back"
    subtitle = ("Hands-on training for Revenue Management, FP&A and Commercial Finance. Every number is "
                "from a fictional business.")

    def __init__(self, ctx):
        super().__init__(ctx)
        q = Card("The four questions every analyst answers")
        q.add(label("1. What do the numbers tell me?   2. Why did the results happen?   "
                    "3. What might happen next?   4. What action should management take?"))
        self.body.addWidget(q)

        r = self.row()
        self.k_prog = KpiCard("Overall progress")
        self.k_lessons = KpiCard("Lessons completed")
        self.k_quiz = KpiCard("Average best quiz score")
        self.k_acc = KpiCard("Exercise accuracy")
        self.k_cap = KpiCard("Capstone")
        for k in (self.k_prog, self.k_lessons, self.k_quiz, self.k_acc, self.k_cap):
            r.addWidget(k)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.body.addWidget(self.bar)

        r2 = self.row()
        nxt = Card("Continue learning")
        self.resume_lbl = label("")
        nxt.add(self.resume_lbl)
        b = QHBoxLayout()
        self.btn_resume = button("Resume where I left off", self.resume, primary=True)
        b.addWidget(self.btn_resume)
        b.addWidget(button("Next recommended lesson", self.next_lesson))
        b.addWidget(button("Training roadmap", lambda: ctx.navigate("roadmap")))
        b.addStretch(1)
        nxt.add(b)
        self.weak_lbl = label("", rich=True)
        nxt.add(label("Topics to strengthen", "H3"))
        nxt.add(self.weak_lbl)
        nxt.lay.addStretch(1)            # keep content at the top when the chart card is taller
        r2.addWidget(nxt, 1)

        ch = Card("Mastery score by skill (0-100)")
        self.chart = Chart(ctx, 3.4)
        ch.add(self.chart)
        ch.add(label("Levels: Beginner < 40 ≤ Developing < 70 ≤ Competent. 'Job-ready for supervised tasks' "
                     "also needs all practical tasks and the capstone.", "Muted"))
        r2.addWidget(ch, 1)

        tools = Card("Practice tools")
        g = QGridLayout()
        for i, key in enumerate(["calculator", "excel_center", "rm_simulator", "fpa_lab", "scenario",
                                 "business_case", "capstone", "reference"]):
            g.addWidget(button(ctx.screen_title(key), lambda _=False, k=key: ctx.navigate(k)), i // 4, i % 4)
        tools.add(g)
        self.body.addWidget(tools)
        self.body.addWidget(label("Completing this application is not equivalent to a professional certification "
                                  "and does not guarantee employment.", "Muted"))
        self.body.addStretch(1)

    def on_show(self, **kw):
        ctx = self.ctx
        ctx.invalidate()
        name = ctx.db.setting("student_name").strip()
        self.h1.setText(f"Welcome back, {name}" if name else "Welcome")
        o = overall(ctx)
        self.k_prog.set(f"{o['frac'] * 100:.0f}%", "of all lesson activities")
        self.bar.setValue(round(o["frac"] * 100))
        self.k_lessons.set(f"{o['lessons_done']} / {o['lessons_total']}", "exercises, quiz and task done")
        self.k_quiz.set("-" if o["quiz"] is None else f"{o['quiz'] * 100:.0f}%", "best attempt per lesson")
        acc = "-" if not o["attempts"] else f"{o['correct'] / o['attempts'] * 100:.0f}%"
        self.k_acc.set(acc, f"{o['first_try']} of {o['exercises_total']} solved first try")
        best = ctx.db.best_capstone()
        if best:
            self.k_cap.set(f"{best['total']:.0f}/100", "Passed" if best["passed"] else "Not yet passed (70+)",
                           "Good" if best["passed"] else "Warn")
        else:
            self.k_cap.set("Not started", "Unlocks job-ready level")
        last = ctx.db.meta("last_lesson")
        if last:
            l = curriculum.lesson_by_id(last)
            m = curriculum.module_of_lesson(last)
            self.resume_lbl.setText(f"Last opened: Module {m.number} · {l.title}")
            self.btn_resume.setEnabled(True)
        else:
            self.resume_lbl.setText("Start with Module 1: Financial Foundations.")
            self.btn_resume.setEnabled(False)
        skills = ctx.skills()
        weak = [s for s in skills if s.weak]
        self.weak_lbl.setText("<br>".join(f"• <b>{s.skill}</b>: score {s.score:.0f}" for s in weak)
                              or "None identified yet. Weak topics appear after you attempt exercises.")

        def paint(fig, p):
            ax = fig.add_subplot(111)
            names = [s.skill for s in skills][::-1]
            vals = [s.score for s in skills][::-1]
            ax.barh(names, vals, color=p.series[0], height=0.55)
            ax.set_xlim(0, 100)
            for x in (40, 70, 85):
                ax.axvline(x, color=p.border, lw=1, ls="--")
            ax.tick_params(axis="y", labelsize=8, colors=p.text2)
            ax.tick_params(axis="x", labelsize=8, colors=p.text2)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(p.border)
            ax.set_facecolor(p.surface)
        self.chart.plot(paint)

    def resume(self):
        last = self.ctx.db.meta("last_lesson")
        if last:
            self.ctx.navigate("lessons", lesson=last)

    def next_lesson(self):
        db = self.ctx.db
        status, tasks = db.all_exercise_status(), db.all_tasks()
        for m in curriculum.modules():
            for l in m.lessons:
                if not mastery.lesson_complete(l, status, db.best_quiz(l.id), tasks.get(l.task.id)):
                    self.ctx.navigate("lessons", lesson=l.id)
                    return
        self.ctx.navigate("capstone")
