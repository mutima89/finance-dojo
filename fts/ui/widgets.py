"""Reusable UI components: cards, KPI tiles, tables, charts, and the
interactive exercise / quiz / practical-task widgets used in every lesson."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QTextDocument
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QFileDialog, QFrame, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
                               QRadioButton, QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..content.base import Exercise, Lesson, Module
from ..core import gamify, mastery
from ..core.checker import check_numeric, format_value
from ..paths import exports_dir
from .theme import style_axes


def md(text: str) -> str:
    """Markdown -> HTML for QLabel."""
    doc = QTextDocument()
    doc.setMarkdown(text)
    html = doc.toHtml()
    return html


def label(text: str = "", obj: str = "", wrap: bool = True, rich: bool = False) -> QLabel:
    lb = QLabel(text)
    if obj:
        lb.setObjectName(obj)
    lb.setWordWrap(wrap)
    if rich:
        lb.setTextFormat(Qt.RichText)
    lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lb


def button(text: str, slot: Callable | None = None, primary: bool = False, obj: str = "") -> QPushButton:
    b = QPushButton(text.replace("&", "&&"))      # a single & would become a keyboard mnemonic
    b.setCursor(Qt.PointingHandCursor)
    if primary:
        b.setObjectName("Primary")
    if obj:
        b.setObjectName(obj)
    if slot:
        b.clicked.connect(slot)
    return b


class Card(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 14, 16, 14)
        self.lay.setSpacing(8)
        if title:
            self.lay.addWidget(label(title, "H3"))

    def add(self, w):
        if isinstance(w, QWidget):
            self.lay.addWidget(w)
        else:
            self.lay.addLayout(w)
        return w


class KpiCard(QFrame):
    def __init__(self, title: str, value: str = "-", sub: str = "", tone: str = ""):
        super().__init__()
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        self.t = label(title, "Muted")
        self.v = label(value, "H2")
        self.s = label(sub, tone or "Muted")
        for w in (self.t, self.v, self.s):
            lay.addWidget(w)
        self.setMinimumWidth(150)

    def set(self, value: str, sub: str = "", tone: str = ""):
        self.v.setText(value)
        self.s.setText(sub)
        self.s.setObjectName(tone or "Muted")
        self.s.style().unpolish(self.s)
        self.s.style().polish(self.s)


def scroll(widget: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.NoFrame)
    sa.setWidget(widget)
    return sa


class Chart(QWidget):
    """Matplotlib figure that redraws with the current theme."""

    def __init__(self, ctx, height: float = 3.2, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.fig = Figure(figsize=(6, height), dpi=100, layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setMinimumHeight(int(height * 80))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas)
        self._painter: Optional[Callable] = None
        ctx.charts.add(self)

    def plot(self, painter: Callable):
        """painter(fig, palette) draws on a cleared figure."""
        self._painter = painter
        self.redraw()

    def redraw(self):
        p = self.ctx.pal
        self.fig.clear()
        self.fig.set_facecolor(p.surface)
        if self._painter:
            try:
                self._painter(self.fig, p)
            except Exception as exc:          # never crash the UI because of a chart
                ax = self.fig.add_subplot(111)
                ax.axis("off")
                ax.text(0.5, 0.5, f"Chart unavailable: {exc}", ha="center", color=p.bad)
        self.canvas.draw_idle()

    def save(self, path: Path):
        self.fig.savefig(path, dpi=150, facecolor=self.fig.get_facecolor())


def fill_table(t: QTableWidget, df: pd.DataFrame, fmt: dict[str, Callable] | None = None,
               tone: Callable[[str, object, pd.Series], str] | None = None, index: bool = True, pal=None):
    """Populate a QTableWidget from a DataFrame. fmt maps column -> formatter;
    tone(col, value, row) returns 'good' / 'bad' / '' for colouring."""
    fmt = fmt or {}
    cols = list(df.columns)
    t.clear()
    t.setColumnCount(len(cols))
    t.setRowCount(len(df))
    t.setHorizontalHeaderLabels([str(c) for c in cols])
    if index:
        t.setVerticalHeaderLabels([str(i) for i in df.index])
    t.verticalHeader().setVisible(index)
    for r, (_, row) in enumerate(df.iterrows()):
        for c, col in enumerate(cols):
            v = row[col]
            f = fmt.get(col)
            if f is not None and not (isinstance(v, float) and math.isnan(v)) and v is not None:
                try:
                    s = f(v)
                except Exception:
                    s = str(v)
            else:
                s = "n/a" if (v is None or (isinstance(v, float) and math.isnan(v))) else str(v)
            it = QTableWidgetItem(s)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if tone:
                kind = tone(col, v, row)
                if kind and pal:
                    it.setForeground(QColor(pal.good if kind == "good" else pal.bad))
            t.setItem(r, c, it)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setAlternatingRowColors(True)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    t.horizontalHeader().setStretchLastSection(True)


def money(v, d=0):
    return format_value(v, "currency", d)


def pct(v, d=1):
    return "n/a" if v is None else f"{v * 100:,.{d}f}%"


def save_dialog(parent, title: str, default_name: str, filt: str) -> Optional[Path]:
    path, _ = QFileDialog.getSaveFileName(parent, title, str(exports_dir() / default_name), filt)
    return Path(path) if path else None


def info(parent, title, text):
    QMessageBox.information(parent, title, text)


def error(parent, title, text):
    QMessageBox.warning(parent, title, text)


# --------------------------------------------------------------- exercise

class ExerciseWidget(Card):
    changed = Signal()

    def __init__(self, ctx, module: Module, lesson: Lesson, ex: Exercise, guided: bool):
        super().__init__("Guided practice" if guided else "Independent practice")
        self.ctx, self.module, self.lesson, self.ex, self.guided = ctx, module, lesson, ex, guided
        self.hints_shown = 0
        self.add(label(md(ex.prompt), rich=True))
        if guided and ex.steps:
            steps = "".join(f"<li>{s}</li>" for s in ex.steps)
            self.add(label(f"<b>Steps</b><ol>{steps}</ol>", rich=True))
        self.choice_group = None
        row = QHBoxLayout()
        if ex.unit == "choice":
            box = QVBoxLayout()
            self.choice_group = QButtonGroup(self)
            for i, ch in enumerate(ex.choices):
                rb = QRadioButton(ch)
                self.choice_group.addButton(rb, i)
                box.addWidget(rb)
            self.add(box)
        else:
            self.input = QLineEdit()
            self.input.setPlaceholderText({"percent": "e.g. 75.4%", "currency": "e.g. 1,234.56",
                                           "years": "e.g. 2.6"}.get(ex.unit, "e.g. 1234.5"))
            self.input.setMaximumWidth(220)
            self.input.returnPressed.connect(self.check)
            row.addWidget(label(f"Your answer ({ex.unit}):", wrap=False))
            row.addWidget(self.input)
        self.btn_check = button("Check answer", self.check, primary=True)
        self.btn_hint = button("Hint", self.hint)
        self.btn_sol = button("Show solution", self.reveal)
        for b in (self.btn_check, self.btn_hint, self.btn_sol):
            row.addWidget(b)
        row.addStretch(1)
        self.add(row)
        self.feedback = label("", rich=True)
        self.add(self.feedback)
        self.restore()

    # state -------------------------------------------------------------
    def state(self):
        return self.ctx.db.exercise_state(self.ex.id)

    def allowed_hints(self) -> int:
        level = self.ctx.skill_level(self.ex.skill)
        return mastery.hints_allowed(len(self.ex.hints), level, self.guided)

    def restore(self):
        st = self.state()
        if st["solved"]:
            self._done(True, f"✔ Solved in {st['solved_on']} attempt(s).<br><b>Solution:</b> {self.ex.solution}")
        elif st["revealed"]:
            self._done(False, f"Solution shown (not counted toward mastery).<br><b>Solution:</b> {self.ex.solution}")
        elif st["attempts"]:
            self.feedback.setText(f"Attempts so far: {st['attempts']} of {self.ctx.db.max_attempts()}.")

    def _done(self, ok: bool, html: str):
        tone = self.ctx.pal.good if ok else self.ctx.pal.warn
        self.feedback.setText(f"<span style='color:{tone}'>{html}</span>")
        self.btn_check.setEnabled(False)
        self.btn_hint.setEnabled(False)
        self.btn_sol.setText("Solution shown" if not ok else "Solved")
        self.btn_sol.setEnabled(False)
        if hasattr(self, "input"):
            self.input.setReadOnly(True)

    # actions -----------------------------------------------------------
    def answer_text(self):
        if self.choice_group is not None:
            i = self.choice_group.checkedId()
            return None if i < 0 else i
        return self.input.text()

    def check(self):
        ans = self.answer_text()
        p = self.ctx.pal
        if self.ex.unit == "choice":
            if ans is None:
                self.feedback.setText("Select an option first.")
                return
            ok = ans == self.ex.expected
            diag = None if ok else "That option is not the best answer. Re-read the question and use a hint."
            shown = self.ex.choices[ans]
        else:
            if not str(ans).strip():
                self.feedback.setText("Type an answer first.")
                return
            r = check_numeric(ans, float(self.ex.expected), self.ex.unit, self.ex.abs_tol, self.ex.rel_tol,
                              self.ex.mistakes)
            if r.status == "invalid":
                self.feedback.setText(f"<span style='color:{p.warn}'>{r.message}</span> (Not counted as an attempt.)")
                return
            ok, diag, shown = r.correct, r.diagnosis, ans
        before = self.state()
        st = self.ctx.db.record_attempt(self.ex, self.lesson.id, self.module.id, shown, ok)
        if ok:
            cheer = gamify.pick(gamify.CHEER_RIGHT, st["attempts"] + len(self.ex.id))
            self._done(True, f"✔ Correct! {cheer}<br><b>Solution:</b> {self.ex.solution}")
            if not before["solved"]:
                xp = gamify.exercise_xp(st["solved_on"], st["hints_used"], bool(st["revealed"]))
                tag = "First try! 🎯" if st["solved_on"] == 1 else f"Solved on try {st['solved_on']}"
                self.ctx.award("exercise", self.ex.id, xp, f"{tag} {cheer}")
        else:
            mx = self.ctx.db.max_attempts()
            if st["attempts"] >= mx:
                self.ctx.db.record_reveal(self.ex, self.lesson.id, self.module.id)
                self._done(False, f"✘ {diag}<br>You've used all {mx} attempts, so here is the worked solution:"
                                  f"<br><b>Solution:</b> {self.ex.solution}")
            else:
                hint = ""
                if self.hints_shown < self.allowed_hints():
                    hint = f"<br><i>Hint:</i> {self.ex.hints[self.hints_shown]}"
                    self.hints_shown += 1
                pep = gamify.pick(gamify.ENCOURAGE_WRONG, st["attempts"])
                self.feedback.setText(f"<span style='color:{p.bad}'>✘ Not quite.</span> {diag}{hint}"
                                      f"<br>Attempt {st['attempts']} of {mx}. <i>{pep}</i>")
        self.changed.emit()

    def hint(self):
        allowed = self.allowed_hints()
        if self.hints_shown >= allowed:
            extra = "" if allowed == len(self.ex.hints) else " (fewer hints are offered as your skill level grows)"
            self.feedback.setText(f"No more hints available{extra}. You can still show the solution.")
            return
        self.ctx.db.record_hint(self.ex, self.lesson.id, self.module.id)
        self.feedback.setText("".join(f"<i>Hint {i + 1}:</i> {h}<br>" for i, h in
                                      enumerate(self.ex.hints[: self.hints_shown + 1])))
        self.hints_shown += 1
        self.changed.emit()

    def reveal(self):
        if QMessageBox.question(self, "Show solution?",
                                "The full solution will be shown and this exercise will not count toward your "
                                "mastery score. Show it?") != QMessageBox.Yes:
            return
        self.ctx.db.record_reveal(self.ex, self.lesson.id, self.module.id)
        self._done(False, f"<b>Solution:</b> {self.ex.solution}")
        self.changed.emit()


class QuizWidget(Card):
    """One question at a time with instant feedback, so it never feels like a wall of text."""
    changed = Signal()
    LETTERS = "ABCDEFGH"

    def __init__(self, ctx, module: Module, lesson: Lesson):
        super().__init__("Quick quiz")
        self.ctx, self.module, self.lesson = ctx, module, lesson
        self.qs = lesson.quiz
        top = QHBoxLayout()
        self.dots = label("", "QuizDots", wrap=False, rich=True)
        top.addWidget(self.dots)
        top.addStretch(1)
        self.best = label("", "Muted", wrap=False)
        top.addWidget(self.best)
        self.add(top)
        self.question = label("", "H3", rich=True)
        self.add(self.question)
        self.opts: list[QPushButton] = []
        for j in range(max((len(q.options) for q in self.qs), default=0)):
            b = QPushButton()
            b.setObjectName("QuizOpt")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, j=j: self.choose(j))
            self.opts.append(b)
            self.add(b)
        self.feedback = label("", "QuizFeedback", rich=True)
        self.add(self.feedback)
        row = QHBoxLayout()
        self.btn_next = button("Next question ▶", self.next_question, primary=True)
        row.addWidget(self.btn_next)
        self.btn_retake = button("↺ Retake quiz", self.retake)
        row.addWidget(self.btn_retake)
        self.score = label("", "H3")
        row.addWidget(self.score)
        row.addStretch(1)
        self.add(row)
        self.retake()

    # state -----------------------------------------------------------------
    def retake(self):
        self.i = 0
        self.results: list[tuple[str, str, bool]] = []
        self.answered = False
        self.finished = False
        self.score.setText("")
        self.btn_retake.setVisible(False)
        self._show()

    def _paint_dots(self):
        p = self.ctx.pal
        parts = []
        for k in range(len(self.qs)):
            if k < len(self.results):
                c, ch = (p.good, "●") if self.results[k][2] else (p.bad, "●")
            elif k == self.i and not self.finished:
                c, ch = p.accent, "●"
            else:
                c, ch = p.border, "○"
            parts.append(f"<span style='color:{c}; font-size:14pt'>{ch}</span>")
        self.dots.setText("&nbsp;".join(parts))
        best = self.ctx.db.best_quiz(self.lesson.id)
        self.best.setText(f"Best score: {best[0]}/{best[1]}" if best else "")

    def _set_state(self, b: QPushButton, state: str):
        b.setProperty("state", state)
        b.style().unpolish(b)
        b.style().polish(b)

    def _show(self):
        q = self.qs[self.i]
        self.question.setText(f"Question {self.i + 1} of {len(self.qs)}<br>{q.question}")
        for j, b in enumerate(self.opts):
            visible = j < len(q.options)
            b.setVisible(visible)
            b.setEnabled(visible)
            if visible:
                b.setText(f"{self.LETTERS[j]}   {q.options[j]}".replace("&", "&&"))
            self._set_state(b, "")
        self.feedback.setText("Pick one answer. You'll see right away if it's right.")
        self.btn_next.setVisible(True)
        self.btn_next.setEnabled(False)
        self.btn_next.setText("Next question ▶" if self.i < len(self.qs) - 1 else "See my score ▶")
        self._paint_dots()

    def choose(self, j: int):
        if self.finished or self.answered or self.i >= len(self.qs) or j >= len(self.qs[self.i].options):
            return
        q = self.qs[self.i]
        ok = j == q.answer
        self.answered = True
        self.results.append((q.id, q.skill, ok))
        for k, b in enumerate(self.opts):
            b.setEnabled(False)
            self._set_state(b, "right" if k == q.answer else "wrong" if k == j else "")
        p = self.ctx.pal
        seed = len(self.results) + self.i
        if ok:
            lead = f"<span style='color:{p.good}'><b>✔ {gamify.pick(gamify.CHEER_RIGHT, seed)}</b></span> "
        else:
            lead = (f"<span style='color:{p.bad}'><b>✘ Not this one.</b></span> The answer is "
                    f"<b>{self.LETTERS[q.answer]}</b>. ")
        self.feedback.setText(lead + q.explanation)
        self.btn_next.setEnabled(True)
        self._paint_dots()

    def next_question(self):
        if self.finished or not self.answered:
            return
        if self.i < len(self.qs) - 1:
            self.i += 1
            self.answered = False
            self._show()
        else:
            self._finish()

    def _finish(self):
        self.finished = True
        prev = self.ctx.db.best_quiz(self.lesson.id)
        self.ctx.db.record_quiz(self.lesson.id, self.module.id, self.results)
        n, total = sum(r[2] for r in self.results), len(self.results)
        for b in self.opts:
            b.setVisible(False)
        self.btn_next.setVisible(False)
        self.btn_retake.setVisible(True)
        self.question.setText(f"You scored {n} out of {total}" + (" 🎉" if n == total else ""))
        self.feedback.setText("Perfect! On to the practical task." if n == total else
                              "Good effort. Re-read the explanations, then retake it whenever you like. "
                              "Only your best score counts.")
        self.score.setText("")
        xp = gamify.quiz_xp(n, prev[0] if prev else None)
        if xp:
            self.ctx.award("quiz", f"{self.lesson.id}:{n}", xp,
                           "Perfect quiz! 🎉" if n == total else "New best quiz score")
        self._paint_dots()
        self.changed.emit()


class TaskWidget(Card):
    changed = Signal()

    def __init__(self, ctx, module: Module, lesson: Lesson):
        super().__init__(f"Practical task: {lesson.task.title}")
        self.ctx, self.module, self.lesson, self.task = ctx, module, lesson, lesson.task
        self.add(label(self.task.prompt))
        self.edit = QPlainTextEdit()
        self.edit.setMinimumHeight(170)
        saved = ctx.db.task(self.task.id)
        self.edit.setPlainText(saved["content"] if saved else self.task.template)
        self.add(self.edit)
        self.add(label("Self-check before you save (your own assessment):", "Muted"))
        self.checks = []
        for i, c in enumerate(self.task.checklist):
            cb = QCheckBox(c)
            if saved and i < len(saved["checklist"]):
                cb.setChecked(bool(saved["checklist"][i]))
            self.checks.append(cb)
            self.add(cb)
        row = QHBoxLayout()
        row.addWidget(button("Save", self.save, primary=True))
        row.addWidget(button("Export to file…", self.export))
        if self.task.tool:
            row.addWidget(button(f"Open tool: {ctx.screen_title(self.task.tool)}",
                                 lambda: ctx.navigate(self.task.tool)))
        self.status = label("", "Muted")
        row.addWidget(self.status)
        row.addStretch(1)
        self.add(row)
        if saved:
            self.status.setText(f"Saved {saved['updated']}")

    def save(self):
        text = self.edit.toPlainText()
        if text.strip() == self.task.template.strip():
            self.status.setText("Fill in the template before saving.")
            return
        self.ctx.db.save_task(self.task.id, self.lesson.id, self.module.id, text,
                              [cb.isChecked() for cb in self.checks])
        self.status.setText("Saved ✔")
        self.ctx.award("task", self.task.id, gamify.TASK_XP, f"Practical task saved: {self.task.title}")
        self.changed.emit()

    def export(self):
        self.save()
        p = save_dialog(self, "Export practical task", f"{self.task.id}_{self.task.title[:30]}.md".replace(" ", "_"),
                        "Markdown (*.md);;Text (*.txt)")
        if not p:
            return
        checklist = "\n".join(f"- [{'x' if cb.isChecked() else ' '}] {cb.text()}" for cb in self.checks)
        try:
            p.write_text(f"# {self.task.title}\n\nModule {self.module.number}: {self.module.title} - "
                         f"{self.lesson.title}\n\n## Task\n{self.task.prompt}\n\n## My answer\n"
                         f"{self.edit.toPlainText()}\n\n## Self-check\n{checklist}\n", encoding="utf-8")
        except OSError as exc:
            error(self, "Export failed", f"Could not write the file: {exc}")
            return
        self.ctx.db.mark_task_exported(self.task.id)
        self.status.setText(f"Exported to {p}")
