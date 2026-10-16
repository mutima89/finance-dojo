"""Module lessons: concept, worked example, guided and independent practice,
business interpretation, quiz and practical task."""
from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QProgressBar, QSplitter, QTabWidget, QTextBrowser, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from ...content import curriculum, life
from ...core import gamify, mastery
from ..widgets import ExerciseWidget, QuizWidget, TaskWidget, button, label, scroll
from .base import Screen

SECTIONS = ["concept", "example", "guided", "independent", "interpretation", "quiz", "task"]
STEP_NAMES = ["📘 Learn", "🧮 See it", "🤝 Try with help", "💪 Try alone", "💼 Business view", "❓ Quiz", "🛠 Task"]
READING_CSS = "p, li { line-height: 150%; } h2, h3 { margin-top: 14px; } table { margin: 6px 0; }"
TICK_SECONDS = 15
IDLE_LIMIT = 300


class LessonsScreen(Screen):
    title = "Module lessons"
    scrollable = False

    def __init__(self, ctx):
        super().__init__(ctx)
        split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(250)
        self.tree.setMaximumWidth(340)
        self.tree.itemClicked.connect(self._picked)
        split.addWidget(self.tree)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(10, 0, 0, 0)
        self.lesson_title = label("", "H2")
        self.lesson_meta = label("", "Muted")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        rl.addWidget(self.lesson_title)
        rl.addWidget(self.lesson_meta)
        rl.addWidget(self.bar)
        self.hook = QFrame()
        self.hook.setObjectName("Hook")
        hl = QVBoxLayout(self.hook)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(3)
        self.key_idea = label("", rich=True)
        self.life_hook = label("", rich=True)
        hl.addWidget(self.key_idea)
        hl.addWidget(self.life_hook)
        rl.addWidget(self.hook)
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._tab_changed)
        rl.addWidget(self.tabs, 1)
        nav = QHBoxLayout()
        nav.addWidget(button("◀ Back", lambda: self._move(-1)))
        nav.addStretch(1)
        self.step_lbl = label("", "StepLbl", wrap=False)
        nav.addWidget(self.step_lbl)
        nav.addStretch(1)
        self.btn_next = button("Next step ▶", lambda: self._move(1), primary=True)
        nav.addWidget(self.btn_next)
        rl.addLayout(nav)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        self.body.addWidget(split, 1)
        self.module = self.lesson = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(TICK_SECONDS * 1000)

    # ---------------------------------------------------------------- tree
    def _build_tree(self):
        self.tree.clear()
        db = self.ctx.db
        status, tasks = db.all_exercise_status(), db.all_tasks()
        for m in curriculum.modules():
            top = QTreeWidgetItem([f"{m.number}. {m.title}"])
            top.setData(0, Qt.UserRole, m.lessons[0].id)
            for l in m.lessons:
                f = mastery.lesson_progress_fraction(l, status, db.best_quiz(l.id), tasks.get(l.task.id))
                tick = "✔" if f >= 0.999 else "◐" if f > 0 else "○"
                it = QTreeWidgetItem([f"{tick} {l.title}"])
                it.setData(0, Qt.UserRole, l.id)
                top.addChild(it)
            self.tree.addTopLevelItem(top)
        self.tree.expandAll()

    def _picked(self, item, _col):
        lid = item.data(0, Qt.UserRole)
        if lid and (self.lesson is None or lid != self.lesson.id):
            self.open_lesson(lid)

    def _step(self, d):
        ids = [l.id for m in curriculum.modules() for l in m.lessons]
        if self.lesson is None:
            return
        i = ids.index(self.lesson.id) + d
        if 0 <= i < len(ids):
            self.open_lesson(ids[i])
        elif i >= len(ids):
            self.ctx.navigate("capstone")

    def _move(self, d):
        """Next/previous step inside the lesson, rolling over to the next/previous lesson."""
        i = self.tabs.currentIndex() + d
        if 0 <= i < self.tabs.count():
            self.tabs.setCurrentIndex(i)
        else:
            self._step(d)
            if d < 0 and self.tabs.count():
                self.tabs.setCurrentIndex(self.tabs.count() - 1)

    def on_show(self, lesson: str | None = None, step: int | None = None, **kw):
        self._build_tree()
        lid = lesson or (self.lesson.id if self.lesson else None) or self.ctx.db.meta("last_lesson") \
            or curriculum.modules()[0].lessons[0].id
        if self.lesson is None or lid != self.lesson.id:
            self.open_lesson(lid)
        else:
            self._refresh_meta()
        if step is not None and 0 <= step < self.tabs.count():
            self.tabs.setCurrentIndex(step)

    # -------------------------------------------------------------- lesson
    def open_lesson(self, lid: str):
        ctx = self.ctx
        self.lesson = curriculum.lesson_by_id(lid)
        self.module = curriculum.module_of_lesson(lid)
        m, l = self.module, self.lesson
        self.lesson_title.setText(f"Module {m.number} · {l.title}")
        self.tabs.blockSignals(True)
        while self.tabs.count():
            w = self.tabs.widget(0)
            self.tabs.removeTab(0)
            w.deleteLater()

        def browser(text):
            b = QTextBrowser()
            b.setOpenExternalLinks(False)
            b.document().setDefaultStyleSheet(READING_CSS)
            b.document().setDocumentMargin(10)
            b.setMarkdown(text)
            return b

        key, everyday = life.LESSON_HOOKS.get(l.id, ("", ""))
        self.key_idea.setText(f"🧠 <b>Key idea:</b> {key}")
        self.life_hook.setText(f"🌍 <b>In real life:</b> {everyday}")
        self.hook.setVisible(bool(key))
        self.tabs.addTab(browser(l.concept), STEP_NAMES[0])
        self.tabs.addTab(browser(l.worked_example), STEP_NAMES[1])
        g = ExerciseWidget(ctx, m, l, l.guided, guided=True)
        g.changed.connect(self._refresh_meta)
        self.tabs.addTab(scroll(self._wrap([g])), STEP_NAMES[2])
        ind = []
        for e in l.independent:
            w = ExerciseWidget(ctx, m, l, e, guided=False)
            w.changed.connect(self._refresh_meta)
            ind.append(w)
        note = label("Less help here: hints fade as your skill level rises. Hints are available on request; the "
                     "solution appears after the maximum number of attempts (set in Settings).", "Muted")
        self.tabs.addTab(scroll(self._wrap([note] + ind)), STEP_NAMES[3])
        self.tabs.addTab(browser(l.interpretation), STEP_NAMES[4])
        q = QuizWidget(ctx, m, l)
        q.changed.connect(self._refresh_meta)
        self.tabs.addTab(scroll(self._wrap([q])), STEP_NAMES[5])
        t = TaskWidget(ctx, m, l)
        t.changed.connect(self._refresh_meta)
        self.tabs.addTab(scroll(self._wrap([t])), STEP_NAMES[6])
        self.tabs.blockSignals(False)
        self.tabs.setCurrentIndex(0)
        self._update_step(0)
        ctx.db.view_section(l.id, m.id, SECTIONS[0])
        self._refresh_meta()
        self._select_tree(lid)

    @staticmethod
    def _wrap(widgets):
        host = QWidget()
        v = QVBoxLayout(host)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(12)
        for w in widgets:
            v.addWidget(w)
        v.addStretch(1)
        return host

    def _select_tree(self, lid):
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                if top.child(j).data(0, Qt.UserRole) == lid:
                    self.tree.setCurrentItem(top.child(j))

    def _tab_changed(self, idx):
        if self.lesson and 0 <= idx < len(SECTIONS):
            self.ctx.db.view_section(self.lesson.id, self.module.id, SECTIONS[idx])
        self._update_step(idx)

    def _update_step(self, idx):
        n = self.tabs.count() or len(STEP_NAMES)
        mins = max(2, round((self.lesson.minutes if self.lesson else 25) / n))
        self.step_lbl.setText(f"Step {idx + 1} of {n} · about {mins} min")
        self.btn_next.setText("Next lesson ▶" if idx >= n - 1 else f"Next: {STEP_NAMES[idx + 1]} ▶")

    def _refresh_meta(self):
        db, l = self.ctx.db, self.lesson
        self.ctx.invalidate()
        status, task = db.all_exercise_status(), db.task(l.task.id)
        frac = mastery.lesson_progress_fraction(l, status, db.best_quiz(l.id), task)
        self.bar.setValue(round(frac * 100))
        secs = db.lesson_seconds().get(l.id, 0)
        skills = sorted({e.skill for e in l.exercises})
        levels = ", ".join(f"{s}: {self.ctx.skill_level(s)}" for s in skills)
        self.lesson_meta.setText(f"About {l.minutes} min · active time so far {secs // 60} min · {levels}")
        if frac >= 0.999:
            self._build_tree()
            self._select_tree(l.id)
            self.ctx.award("lesson", l.id, gamify.LESSON_XP, f"Lesson complete: {l.title} 🎉", big=True)

    def _tick(self):
        """Count study time only while this screen is visible, the window is active
        and there was keyboard/mouse input in the last 5 minutes."""
        if not self.lesson or not self.isVisible() or not self.window().isActiveWindow():
            return
        if time.monotonic() - self.ctx.last_input > IDLE_LIMIT:
            return
        self.ctx.db.add_time(self.lesson.id, self.module.id, TICK_SECONDS)
