"""Home and learning dashboard."""
from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLineEdit, QProgressBar, QVBoxLayout

from ...content import curriculum, story
from ...core import gamify, mastery
from ..widgets import Card, Chart, KpiCard, button, label
from .base import Screen
from .dojo import quests_left

STEP_LABELS = ["read the key idea", "see a worked example", "try a guided exercise", "try an exercise alone",
               "read the business view", "take the 3-question quiz", "do the practical task"]


def next_step(ctx):
    """The single most useful next thing to do: (lesson or None, step index, description)."""
    db = ctx.db
    status, tasks = db.all_exercise_status(), db.all_tasks()

    def done(e):
        st = status.get(e.id, {})
        return st.get("solved") or st.get("revealed")

    for m in curriculum.modules():
        for l in m.lessons:
            if mastery.lesson_complete(l, status, db.best_quiz(l.id), tasks.get(l.task.id)):
                continue
            seen = db.sections_viewed(l.id)
            if "concept" not in seen:
                step = 0
            elif not done(l.guided):
                step = 2
            elif not all(done(e) for e in l.independent):
                step = 3
            elif db.best_quiz(l.id) is None:
                step = 5
            else:
                step = 6
            return l, step, f"Module {m.number} · {l.title}: {STEP_LABELS[step]}"
    return None, 0, "Every lesson is done. Time for the capstone project!"


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
        self._build_welcome()
        hero = QFrame()
        hero.setObjectName("Hero")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(22, 18, 22, 18)
        hl.setSpacing(24)
        left = QVBoxLayout()
        left.setSpacing(6)
        left.addWidget(label("YOUR NEXT 5-MINUTE STEP", "HeroMuted"))
        self.next_lbl = label("", "H2")
        left.addWidget(self.next_lbl)
        btns = QHBoxLayout()
        self.btn_go = button("▶  Start now", self.go, obj="HeroGo")
        btns.addWidget(self.btn_go)
        self.btn_quests = button("🎲 Daily quests", lambda: ctx.navigate("dojo"))
        btns.addWidget(self.btn_quests)
        btns.addStretch(1)
        left.addLayout(btns)
        left.addStretch(1)
        hl.addLayout(left, 3)
        right = QVBoxLayout()
        right.setSpacing(4)
        self.hero_belt = label("", "H3")
        self.hero_bar = QProgressBar()
        self.hero_bar.setRange(0, 1000)
        self.hero_bar.setTextVisible(False)
        self.hero_bar.setFixedHeight(8)
        self.hero_xp = label("", "HeroMuted")
        self.hero_streak = label("", "H3")
        self.hero_goal = label("", "HeroMuted")
        for w in (self.hero_belt, self.hero_bar, self.hero_xp, self.hero_streak, self.hero_goal):
            right.addWidget(w)
        right.addStretch(1)
        hl.addLayout(right, 2)
        self.body.addWidget(hero)
        self._next = (None, 0)

        mgr = QFrame()
        mgr.setObjectName("Manager")
        ml = QHBoxLayout(mgr)
        ml.setContentsMargins(16, 12, 16, 12)
        ml.setSpacing(14)
        av = label("".join(w[0] for w in story.MANAGER.split()), "Avatar", wrap=False)
        av.setFixedSize(44, 44)
        av.setAlignment(Qt.AlignCenter)
        ml.addWidget(av, 0, Qt.AlignTop)
        mv = QVBoxLayout()
        mv.setSpacing(3)
        self.mgr_from = label("", "Muted", rich=True)
        self.mgr_subject = label("", "H3")
        self.mgr_text = label("")
        mv.addWidget(self.mgr_from)
        mv.addWidget(self.mgr_subject)
        mv.addWidget(self.mgr_text)
        mv.addWidget(label("The four questions every analyst answers: " + story.FOUR_QUESTIONS, "Muted"))
        ml.addLayout(mv, 1)
        self.body.addWidget(mgr)

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

    def on_xp(self):
        db = self.ctx.db
        r = gamify.rank(db.xp_total())
        self.hero_belt.setText(f"🥋 {r.belt.name}")
        self.hero_bar.setValue(round(r.fraction * 1000))
        self.hero_xp.setText(f"{r.xp:,} XP" + (f" · {r.to_next:,} to {r.next_belt.name}" if r.next_belt else ""))
        today = dt.date.today()
        s = gamify.streak(db.active_days(), today)
        self.hero_streak.setText(f"🔥 {s.days}-day streak" if s.days else "🔥 Start a streak today")
        goal = db.int_setting("daily_goal", gamify.DAILY_GOAL_CHOICES, gamify.DEFAULT_DAILY_GOAL)
        xp_today = db.xp_on(today)
        left = quests_left(db, today)
        self.hero_goal.setText(f"🎯 Today {xp_today}/{goal} XP · " + (f"{left} quest{'s' if left != 1 else ''} left"
                                                                    if left else "all quests done"))
        self.btn_quests.setText(f"🎲 Daily quests ({left} left)" if left else "🎲 Quick-fire practice")
        lesson, step, text = next_step(self.ctx)
        self._next = (lesson, step)
        num = curriculum.module_of_lesson(lesson.id).number if lesson else None
        subject, msg = story.note_for(num)
        self.mgr_from.setText(f"📩 Message from <b>{story.MANAGER}</b> · {story.MANAGER_ROLE}")
        self.mgr_subject.setText(subject)
        self.mgr_text.setText(msg)
        self.next_lbl.setText(text)
        self.btn_go.setText("▶  Start now" if lesson else "▶  Open the capstone")

    # first-run welcome ---------------------------------------------------------
    def _build_welcome(self):
        db = self.ctx.db
        if not db.meta("welcomed") and db.xp_total() > 0:
            db.set_meta("welcomed", "1")          # people upgrading from an earlier version
        self.welcome = QFrame()
        self.welcome.setObjectName("Welcome")
        wl = QVBoxLayout(self.welcome)
        wl.setContentsMargins(22, 18, 22, 18)
        wl.setSpacing(8)
        wl.addWidget(label("👋 Welcome to Finance Dojo", "H2"))
        wl.addWidget(label("Short steps, real-life maths and a manager who needs your help. Three quick choices "
                           "and you're in. You can change them any time in Settings."))
        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.addWidget(label("What should we call you?", wrap=False), 0, 0)
        self.w_name = QLineEdit(db.setting("student_name"))
        self.w_name.setPlaceholderText("Your first name")
        self.w_name.setMaximumWidth(260)
        g.addWidget(self.w_name, 0, 1)
        g.addWidget(label("Daily XP goal", wrap=False), 1, 0)
        self.w_goal = QComboBox()
        for v, txt in zip(gamify.DAILY_GOAL_CHOICES, ("gentle", "steady", "ambitious")):
            self.w_goal.addItem(f"{v} XP ({txt})", v)
        self.w_goal.setCurrentIndex(gamify.DAILY_GOAL_CHOICES.index(gamify.DEFAULT_DAILY_GOAL))
        self.w_goal.setMaximumWidth(260)
        g.addWidget(self.w_goal, 1, 1)
        g.addWidget(label("Focus timer length", wrap=False), 2, 0)
        self.w_focus = QComboBox()
        for v in gamify.FOCUS_CHOICES:
            self.w_focus.addItem(f"{v} minutes", v)
        self.w_focus.setCurrentIndex(gamify.FOCUS_CHOICES.index(gamify.DEFAULT_FOCUS_MINUTES))
        self.w_focus.setMaximumWidth(260)
        g.addWidget(self.w_focus, 2, 1)
        g.setColumnStretch(2, 1)
        wl.addLayout(g)
        wl.addWidget(label("How it works: press <b>▶ Start now</b> for your next 5-minute step, do the "
                           "<b>Daily Dojo</b> quests for quick wins, and use the <b>focus timer</b> in the "
                           "sidebar when your attention drifts. Press <b>F1</b> for keyboard shortcuts.",
                           rich=True))
        row = QHBoxLayout()
        row.addWidget(button("Let's go ▶", self.finish_welcome, primary=True))
        row.addWidget(button("Skip for now", self.skip_welcome))
        row.addStretch(1)
        wl.addLayout(row)
        self.body.addWidget(self.welcome)
        self.welcome.setVisible(not db.meta("welcomed"))

    def finish_welcome(self):
        db = self.ctx.db
        db.set_setting("student_name", self.w_name.text().strip())
        db.set_setting("daily_goal", self.w_goal.currentData())
        db.set_setting("focus_minutes", self.w_focus.currentData())
        self.skip_welcome()
        name = self.w_name.text().strip()
        self.ctx.celebrate(f"Let's do this{', ' + name if name else ''}! 🥋",
                           "Your first step is waiting in the blue box.")

    def skip_welcome(self):
        self.ctx.db.set_meta("welcomed", "1")
        self.welcome.setVisible(False)
        self.ctx.window.refresh_xp()
        self.on_show()

    def go(self):
        lesson, step = self._next
        if lesson is None:
            self.ctx.navigate("capstone")
        else:
            self.ctx.navigate("lessons", lesson=lesson.id, step=step)

    def on_show(self, **kw):
        ctx = self.ctx
        ctx.invalidate()
        self.on_xp()
        name = ctx.db.setting("student_name").strip()
        self.h1.setText(f"Welcome back, {name}" if name else "Let's get started")
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
