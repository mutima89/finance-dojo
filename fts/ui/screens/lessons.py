"""Module lessons: concept, worked example, guided and independent practice,
business interpretation, quiz and practical task."""
from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QProgressBar, QSplitter, QTabWidget, QTextBrowser, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from ...content import curriculum
from ...core import mastery
from ..widgets import ExerciseWidget, QuizWidget, TaskWidget, button, label, scroll
from .base import Screen

SECTIONS = ["concept", "example", "guided", "independent", "interpretation", "quiz", "task"]
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
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._tab_changed)
        rl.addWidget(self.tabs, 1)
        nav = QHBoxLayout()
        nav.addWidget(button("◀ Previous lesson", lambda: self._step(-1)))
        nav.addStretch(1)
        nav.addWidget(button("Next lesson ▶", lambda: self._step(1), primary=True))
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

    def on_show(self, lesson: str | None = None, **kw):
        self._build_tree()
        lid = lesson or (self.lesson.id if self.lesson else None) or self.ctx.db.meta("last_lesson") \
            or curriculum.modules()[0].lessons[0].id
        self.open_lesson(lid)

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
            b.setMarkdown(text)
            return b

        self.tabs.addTab(browser(l.concept), "1 Concept")
        self.tabs.addTab(browser(l.worked_example), "2 Worked example")
        g = ExerciseWidget(ctx, m, l, l.guided, guided=True)
        g.changed.connect(self._refresh_meta)
        self.tabs.addTab(scroll(self._wrap([g])), "3 Guided practice")
        ind = []
        for e in l.independent:
            w = ExerciseWidget(ctx, m, l, e, guided=False)
            w.changed.connect(self._refresh_meta)
            ind.append(w)
        note = label("Less help here: hints fade as your skill level rises. Hints are available on request; the "
                     "solution appears after the maximum number of attempts (set in Settings).", "Muted")
        self.tabs.addTab(scroll(self._wrap([note] + ind)), "4 Independent practice")
        self.tabs.addTab(browser(l.interpretation), "5 Business interpretation")
        q = QuizWidget(ctx, m, l)
        q.changed.connect(self._refresh_meta)
        self.tabs.addTab(scroll(self._wrap([q])), "6 Quiz")
        t = TaskWidget(ctx, m, l)
        t.changed.connect(self._refresh_meta)
        self.tabs.addTab(scroll(self._wrap([t])), "7 Practical task")
        self.tabs.blockSignals(False)
        self.tabs.setCurrentIndex(0)
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

    def _tick(self):
        """Count study time only while this screen is visible, the window is active
        and there was keyboard/mouse input in the last 5 minutes."""
        if not self.lesson or not self.isVisible() or not self.window().isActiveWindow():
            return
        if time.monotonic() - self.ctx.last_input > IDLE_LIMIT:
            return
        self.ctx.db.add_time(self.lesson.id, self.module.id, TICK_SECONDS)
