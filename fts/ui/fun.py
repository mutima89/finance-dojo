"""Motivation widgets: XP toasts, confetti, the sidebar XP panel and the focus timer.

Everything here respects two settings: "celebrations" (off = no toasts or
confetti) and "reduce_motion" (on = toasts without animation, no confetti).
"""
from __future__ import annotations

import datetime as dt
import math
import random
import time

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QProgressBar, QPushButton,
                               QVBoxLayout, QWidget)

from ..core import gamify

TOAST_MS = 2600


class Toast(QFrame):
    """Small message card in the top-right corner. Messages queue up."""

    def __init__(self, host: QWidget):
        super().__init__(host)
        self.setObjectName("Toast")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        self.title = QLabel()
        self.title.setObjectName("ToastTitle")
        self.text = QLabel()
        self.text.setObjectName("ToastText")
        self.text.setWordWrap(True)
        lay.addWidget(self.title)
        lay.addWidget(self.text)
        self.setFixedWidth(330)
        self.hide()
        self.queue: list[tuple[str, str, bool]] = []
        self.effect = QGraphicsOpacityEffect(self)
        self.effect.setOpacity(1.0)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, b"opacity", self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._next)
        self.animate = True

    def show_message(self, title: str, text: str = "", big: bool = False):
        self.queue.append((title, text, big))
        if not self.timer.isActive():
            self._next()

    def _next(self):
        if not self.queue:
            self.hide()
            return
        title, text, big = self.queue.pop(0)
        self.title.setText(title)
        self.text.setText(text)
        self.text.setVisible(bool(text))
        self.setProperty("big", big)
        self.style().unpolish(self)
        self.style().polish(self)
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        if self.animate:
            self.anim.stop()
            self.anim.setDuration(220)
            self.anim.setStartValue(0.0)
            self.anim.setEndValue(1.0)
            self.anim.start()
        else:
            self.effect.setOpacity(1.0)
        self.timer.start(TOAST_MS + (900 if big else 0))

    def reposition(self):
        host = self.parentWidget()
        if host:
            self.move(host.width() - self.width() - 22, 18)


class Confetti(QWidget):
    """A short burst of falling confetti drawn over the window."""

    def __init__(self, host: QWidget):
        super().__init__(host)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.hide()
        self.parts: list[list] = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step)
        self.t0 = 0.0
        self.colors = ["#f2c94c", "#2f80ed", "#27ae60", "#eb5757", "#9b51e0", "#f2994a"]

    def burst(self):
        host = self.parentWidget()
        self.setGeometry(host.rect())
        r = random.Random()
        w = max(1, self.width())
        self.parts = [[r.uniform(0, w), r.uniform(-120, 0), r.uniform(-1.5, 1.5), r.uniform(2.5, 6.0),
                       r.uniform(0, 360), r.uniform(-9, 9), r.choice(self.colors), r.uniform(6, 11)]
                      for _ in range(110)]
        self.t0 = time.monotonic()
        self.show()
        self.raise_()
        self.timer.start(33)

    def _step(self):
        if time.monotonic() - self.t0 > 1.8:
            self.timer.stop()
            self.hide()
            return
        for p in self.parts:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.12
            p[4] += p[5]
        self.update()

    def paintEvent(self, _ev):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setPen(Qt.NoPen)
        fade = max(0.0, 1.0 - max(0.0, time.monotonic() - self.t0 - 1.2) / 0.6)
        for x, y, _vx, _vy, ang, _va, col, size in self.parts:
            c = QColor(col)
            c.setAlphaF(fade)
            qp.save()
            qp.translate(QPointF(x, y))
            qp.rotate(ang)
            qp.setBrush(c)
            qp.drawRect(QRectF(-size / 2, -size / 4, size, size / 2))
            qp.restore()


class Celebrator:
    """Owns the toast and confetti overlays for the main window."""

    def __init__(self, host: QWidget, db):
        self.db = db
        self.toast = Toast(host)
        self.confetti = Confetti(host)

    def notify(self, title: str, text: str = "", big: bool = False):
        if not self.db.flag("celebrations"):
            return
        calm = self.db.flag("reduce_motion")
        self.toast.animate = not calm
        self.toast.show_message(title, text, big)
        if big and not calm:
            self.confetti.burst()

    def resized(self):
        self.toast.reposition()
        if self.confetti.isVisible():
            self.confetti.setGeometry(self.confetti.parentWidget().rect())


class XpPanel(QFrame):
    """Sidebar summary: belt, XP to next belt, streak, today's goal, focus timer."""
    focus_done = Signal()

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setObjectName("XpPanel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)
        top = QHBoxLayout()
        self.belt_dot = QLabel()
        self.belt_dot.setFixedSize(14, 14)
        self.belt = QLabel()
        self.belt.setObjectName("XpBelt")
        top.addWidget(self.belt_dot)
        top.addWidget(self.belt, 1)
        self.streak = QLabel()
        self.streak.setObjectName("XpStreak")
        top.addWidget(self.streak)
        lay.addLayout(top)
        self.bar = QProgressBar()
        self.bar.setObjectName("XpBar")
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        lay.addWidget(self.bar)
        self.sub = QLabel()
        self.sub.setObjectName("XpSub")
        lay.addWidget(self.sub)
        self.goal = QProgressBar()
        self.goal.setObjectName("GoalBar")
        self.goal.setRange(0, 1000)
        self.goal.setTextVisible(False)
        self.goal.setFixedHeight(6)
        lay.addWidget(self.goal)
        self.goal_lbl = QLabel()
        self.goal_lbl.setObjectName("XpSub")
        lay.addWidget(self.goal_lbl)
        self.focus_btn = QPushButton()
        self.focus_btn.setObjectName("FocusBtn")
        self.focus_btn.setCursor(Qt.PointingHandCursor)
        self.focus_btn.clicked.connect(self.toggle_focus)
        lay.addWidget(self.focus_btn)
        self.focus_end: float | None = None
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self._focus_tick)
        self.refresh()

    def minutes(self) -> int:
        return self.ctx.db.int_setting("focus_minutes", gamify.FOCUS_CHOICES, gamify.DEFAULT_FOCUS_MINUTES)

    def refresh(self):
        db = self.ctx.db
        r = gamify.rank(db.xp_total())
        self.belt.setText(r.belt.name)
        self.belt_dot.setStyleSheet(f"background:{r.belt.color}; border-radius:7px; border:1px solid #888;")
        self.bar.setValue(round(r.fraction * 1000))
        self.sub.setText(f"{r.xp:,} XP · {r.to_next:,} to {r.next_belt.name}" if r.next_belt
                         else f"{r.xp:,} XP · top belt reached")
        today = dt.date.today()
        s = gamify.streak(db.active_days(), today)
        self.streak.setText(f"🔥 {s.days}" if s.days else "🔥 0")
        self.streak.setToolTip("Days in your current streak. One rest day in a row is allowed.")
        goal = db.int_setting("daily_goal", gamify.DAILY_GOAL_CHOICES, gamify.DEFAULT_DAILY_GOAL)
        xp_today = db.xp_on(today)
        self.goal.setValue(round(gamify.goal_fraction(xp_today, goal) * 1000))
        self.goal_lbl.setText(f"Today {xp_today}/{goal} XP" + (" ✔" if xp_today >= goal else ""))
        if self.focus_end is None:
            self.focus_btn.setText(f"⏱  Start a {self.minutes()}-min focus")

    # focus timer -------------------------------------------------------
    def toggle_focus(self):
        if self.focus_end is None:
            self.focus_end = time.monotonic() + self.minutes() * 60
            self.focus_timer.start(1000)
            self._focus_tick()
            self.ctx.celebrate("Focus time ⏱", f"{self.minutes()} minutes on one thing. Notifications can wait.")
        else:
            self.stop_focus()

    def stop_focus(self):
        self.focus_end = None
        self.focus_timer.stop()
        self.refresh()

    def _focus_tick(self):
        if self.focus_end is None:
            return
        left = self.focus_end - time.monotonic()
        if left <= 0:
            self.stop_focus()
            self.focus_done.emit()
            return
        mins, secs = divmod(int(math.ceil(left)), 60)
        self.focus_btn.setText(f"⏱  Focus {mins:02d}:{secs:02d} · stop")
