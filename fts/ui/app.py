"""Main window, navigation and the shared application context."""
from __future__ import annotations

import datetime as dt
import importlib
import sys
import time
import traceback
import weakref
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget)

from ..content import curriculum
from ..paths import resource_root
from ..content.base import SKILLS
from ..core import achievements, gamify, mastery
from ..storage.db import Progress
from . import theme
from .fun import Celebrator, XpPanel

APP_TITLE = "Finance Dojo"

# key: (navigation title, module path, class name)
SCREENS = {
    "home": ("Home", "home", "HomeScreen"),
    "career": ("Career Mode", "career", "CareerScreen"),
    "dojo": ("Daily Dojo", "dojo", "DojoScreen"),
    "roadmap": ("Training Roadmap", "roadmap", "RoadmapScreen"),
    "lessons": ("Module Lessons", "lessons", "LessonsScreen"),
    "calculator": ("Financial Calculator", "calculator", "CalculatorScreen"),
    "excel_center": ("Excel Workbook Center", "excel_center", "ExcelCenterScreen"),
    "rm_simulator": ("Hotel RM Simulator", "rm_simulator", "RMSimulatorScreen"),
    "fpa_lab": ("FP&A Forecasting Lab", "fpa_lab", "FPALabScreen"),
    "scenario": ("Scenario & Sensitivity", "scenario", "ScenarioScreen"),
    "business_case": ("Business Case Evaluator", "business_case", "BusinessCaseScreen"),
    "capstone": ("Capstone Project", "capstone_screen", "CapstoneScreen"),
    "progress": ("Progress & Competency", "progress", "ProgressScreen"),
    "reference": ("Reference & Interview Prep", "reference", "ReferenceScreen"),
    "settings": ("Settings & Backup", "settings", "SettingsScreen"),
}

# sidebar sections: (header, [(screen key, icon)])
NAV_GROUPS = [
    ("START", [("home", "🏠"), ("career", "🎮"), ("dojo", "🎲"), ("roadmap", "🗺")]),
    ("LEARN", [("lessons", "📘"), ("capstone", "🏆"), ("reference", "💼")]),
    ("PRACTISE", [("calculator", "🧮"), ("excel_center", "📊"), ("rm_simulator", "🏨"), ("fpa_lab", "📈"),
                  ("scenario", "🔀"), ("business_case", "⚖")]),
    ("YOU", [("progress", "🏅"), ("settings", "⚙")]),
]

# (keys, description, action name on MainWindow)
SHORTCUTS = [
    ("Ctrl+H", "Home", "go_home"),
    ("Ctrl+G", "Career Mode (the game map)", "go_career"),
    ("Ctrl+D", "Daily Dojo (today's quests)", "go_dojo"),
    ("Ctrl+L", "Continue your next lesson step", "go_next_step"),
    ("Ctrl+Right", "Next step inside a lesson", "lesson_next"),
    ("Ctrl+Left", "Previous step inside a lesson", "lesson_prev"),
    ("Ctrl+T", "Start or stop the focus timer", "toggle_focus"),
    ("F1", "Show these shortcuts", "show_shortcuts"),
]


class Ctx:
    """Shared state handed to every screen."""

    def __init__(self, db: Progress, window: "MainWindow"):
        self.db = db
        self.window = window
        self.pal = theme.palette(db.setting("theme"))
        self.charts: weakref.WeakSet = weakref.WeakSet()
        self._skills_cache = None
        self.last_input = time.monotonic()

    def navigate(self, key: str, **kwargs):
        self.window.navigate(key, **kwargs)

    def screen_title(self, key: str) -> str:
        return SCREENS[key][0]

    def invalidate(self):
        self._skills_cache = None

    def skills(self) -> list[mastery.SkillResult]:
        if self._skills_cache is None:
            best = self.db.best_capstone()
            self._skills_cache = mastery.skill_results(
                curriculum.modules(), self.db.all_exercise_status(), self.db.quiz_answers(),
                self.db.all_tasks(), self.db.workbook_results(), bool(best and best["passed"]), SKILLS)
        return self._skills_cache

    def skill_level(self, skill: str) -> str:
        return next((s.level for s in self.skills() if s.skill == skill), mastery.LEVELS[0])

    # motivation ------------------------------------------------------------
    def award(self, source: str, ref: str, amount: int, note: str = "", big: bool = False) -> bool:
        """Give XP once per (source, ref) and celebrate it. Never affects mastery."""
        db = self.db
        before = gamify.rank(db.xp_total())
        today = dt.date.today()
        goal = db.int_setting("daily_goal", gamify.DAILY_GOAL_CHOICES, gamify.DEFAULT_DAILY_GOAL)
        had_goal = db.xp_on(today) >= goal
        if not db.add_xp(source, ref, amount, note):
            return False
        self.celebrate(f"+{amount} XP", note, big)
        if not had_goal and db.xp_on(today) >= goal:
            db.add_xp("goal", today.isoformat(), gamify.DAILY_GOAL_BONUS, "Daily goal reached")
            self.celebrate("🎯 Daily goal reached!", f"+{gamify.DAILY_GOAL_BONUS} bonus XP. Great work today.", True)
        after = gamify.rank(db.xp_total())
        if after.index > before.index:
            self.celebrate(f"🥋 New belt: {after.belt.name}!", "You levelled up. " + gamify.BELT_NOTE, True)
        self.check_badges()
        self.window.refresh_xp()
        return True

    def check_badges(self, announce: bool = True) -> list:
        """Store newly unlocked badges and (optionally) celebrate them. Badges give no XP."""
        stats = achievements.collect_stats(self.db, [l for m in curriculum.modules() for l in m.lessons])
        new = []
        for b in achievements.unlocked(stats):
            if not self.db.meta(f"badge:{b.id}"):
                self.db.set_meta(f"badge:{b.id}", dt.date.today().isoformat())
                new.append(b)
                if announce:
                    self.celebrate(f"{b.emoji} Badge unlocked: {b.name}", b.desc, True)
        return new

    def celebrate(self, title: str, text: str = "", big: bool = False):
        self.window.fun.notify(title, text, big)

    def set_theme(self, name: str):
        self.db.set_setting("theme", name)
        self.pal = theme.palette(name)
        self.window.apply_theme()


class InputWatcher(QObject):
    """Records the time of the last keyboard/mouse input (for honest study-time tracking)."""

    def __init__(self, ctx: Ctx):
        super().__init__()
        self.ctx = ctx

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.Wheel):
            self.ctx.last_input = time.monotonic()
        return False


class MainWindow(QMainWindow):
    def __init__(self, db: Optional[Progress] = None):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        icon = resource_root() / "assets" / "app.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.resize(1360, 860)
        self.setMinimumSize(1000, 680)
        self.db = db or Progress()
        self.ctx = Ctx(self.db, self)
        self.screens: dict[str, QWidget] = {}
        self.current: Optional[str] = None

        root = QWidget()
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(258)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(8, 12, 8, 12)
        brand = QLabel("◆ Finance Dojo")
        brand.setObjectName("Brand")
        sl.addWidget(brand)
        self.xp_panel = XpPanel(self.ctx)
        self.xp_panel.focus_done.connect(self._focus_done)
        sl.addWidget(self.xp_panel)
        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.nav_rows: dict[str, int] = {}
        for header, items in NAV_GROUPS:
            h = QListWidgetItem(header)
            h.setFlags(Qt.NoItemFlags)
            h.setData(Qt.UserRole, None)
            f = h.font()
            f.setPointSizeF(max(6.0, f.pointSizeF() - 2) if f.pointSizeF() > 0 else 8)
            f.setBold(True)
            h.setFont(f)
            self.nav.addItem(h)
            for key, icon in items:
                it = QListWidgetItem(f"{icon}  {SCREENS[key][0]}")
                it.setData(Qt.UserRole, key)
                self.nav_rows[key] = self.nav.count()
                self.nav.addItem(it)
        self.nav.currentItemChanged.connect(self._nav_changed)
        sl.addWidget(self.nav, 1)
        foot = QLabel("Fictional data · not a certification")
        foot.setObjectName("Muted")
        foot.setWordWrap(True)
        sl.addWidget(foot)
        lay.addWidget(side)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage(f"Progress saved locally: {self.db.path}")
        self.fun = Celebrator(root, self.db)
        backfill_xp(self.db)
        self.ctx.check_badges(announce=False)      # badges earned before this version, no fanfare
        self.xp_panel.refresh()
        for keys, _desc, action in SHORTCUTS:
            QShortcut(QKeySequence(keys), self, activated=getattr(self, action))
        self.apply_theme()
        self.navigate("home")

    # navigation ----------------------------------------------------------
    def _nav_changed(self, cur, _prev):
        if cur is not None:
            key = cur.data(Qt.UserRole)
            if key and key != self.current:
                self.navigate(key)

    def screen(self, key: str) -> QWidget:
        if key not in self.screens:
            _title, mod, cls = SCREENS[key]
            module = importlib.import_module(f"fts.ui.screens.{mod}")
            w = getattr(module, cls)(self.ctx)
            if getattr(w, "scrollable", False):
                w.body.addStretch(1)          # keep cards at their natural height
            self.screens[key] = w
            self.stack.addWidget(w)
        return self.screens[key]

    def navigate(self, key: str, **kwargs):
        if key not in SCREENS:
            return
        try:
            w = self.screen(key)
        except Exception as exc:
            traceback.print_exc()
            QMessageBox.critical(self, "Screen error", f"Could not open {SCREENS[key][0]}: {exc}")
            return
        self.current = key
        self.stack.setCurrentWidget(w)
        row = self.nav_rows[key]
        if self.nav.currentRow() != row:
            self.nav.blockSignals(True)
            self.nav.setCurrentRow(row)
            self.nav.blockSignals(False)
        if hasattr(w, "on_show"):
            w.on_show(**kwargs)

    # keyboard shortcuts -------------------------------------------------------
    def go_home(self):
        self.navigate("home")

    def go_career(self):
        self.navigate("career")

    def go_dojo(self):
        self.navigate("dojo")

    def go_next_step(self):
        from .screens.home import next_step
        lesson, step, _text = next_step(self.ctx)
        if lesson is None:
            self.navigate("capstone")
        else:
            self.navigate("lessons", lesson=lesson.id, step=step)

    def _lesson_move(self, d: int):
        w = self.screens.get(self.current)
        if self.current == "lessons" and w is not None and w.lesson is not None:
            w._move(d)

    def lesson_next(self):
        self._lesson_move(1)

    def lesson_prev(self):
        self._lesson_move(-1)

    def toggle_focus(self):
        self.xp_panel.toggle_focus()

    def show_shortcuts(self):
        QMessageBox.information(self, "Keyboard shortcuts",
                                "\n".join(f"{k:<12} {d}" for k, d, _a in SHORTCUTS))

    # motivation --------------------------------------------------------------
    def refresh_xp(self):
        self.xp_panel.refresh()
        w = self.screens.get(self.current)
        if w is not None and hasattr(w, "on_xp"):
            w.on_xp()

    def _focus_done(self):
        today = dt.date.today()
        n = self.db.xp_count_on("focus", today)
        if n < gamify.FOCUS_DAILY_CAP:
            self.ctx.award("focus", f"{today.isoformat()}:{n}", gamify.FOCUS_XP,
                           "Focus session done! Stand up, stretch and drink some water.", big=True)
        else:
            self.ctx.celebrate("Focus session done!", "Take a short break before the next one.", True)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if hasattr(self, "fun"):
            self.fun.resized()

    # theme -----------------------------------------------------------------
    def apply_theme(self):
        try:
            size = int(self.db.setting("font_size"))
        except ValueError:
            size = 10
        QApplication.instance().setStyleSheet(theme.stylesheet(self.ctx.pal, size))
        for c in list(self.ctx.charts):
            c.redraw()
        for w in self.screens.values():
            if hasattr(w, "on_theme"):
                w.on_theme()

    def closeEvent(self, ev):
        for w in self.screens.values():
            if hasattr(w, "on_close"):
                w.on_close()
        self.db.log("app_closed")
        self.db.close()
        super().closeEvent(ev)


def backfill_xp(db: Progress):
    """Give XP once for progress made before XP existed, dated when it happened."""
    if db.meta("xp_backfilled"):
        return
    status = db.all_exercise_status()
    for ex_id, st in status.items():
        if st.get("solved") and not st.get("revealed"):
            db.add_xp("exercise", ex_id, gamify.exercise_xp(st.get("solved_on"), st.get("hints_used") or 0),
                      "Exercise solved", st.get("updated"))
    tasks = db.all_tasks()
    quiz_ts = {}
    for q in db.quiz_history():
        quiz_ts.setdefault((q["lesson_id"], q["score"]), q["ts"])
    for m in curriculum.modules():
        for l in m.lessons:
            best = db.best_quiz(l.id)
            if best:
                db.add_xp("quiz", f"{l.id}:{best[0]}", gamify.quiz_xp(best[0], None), "Quiz",
                          quiz_ts.get((l.id, best[0])))
            t = tasks.get(l.task.id)
            if t and (t.get("content") or "").strip():
                db.add_xp("task", l.task.id, gamify.TASK_XP, "Practical task saved", t.get("updated"))
            if mastery.lesson_complete(l, status, best, t):
                db.add_xp("lesson", l.id, gamify.LESSON_XP, "Lesson complete", t.get("updated"))
    db.set_meta("xp_backfilled", "1")


def self_test(app: QApplication) -> int:
    """--self-test: open every screen in both themes using a throw-away data folder,
    write a report (normal data folder, or FTS_SELFTEST_REPORT) and to the console, return 0/1.
    Used by build_windows.ps1 to check the packaged exe."""
    import os
    import tempfile
    from ..core import metrics as m
    from ..excel import workbook as wbk
    from ..paths import user_data_dir
    report_path = Path(os.environ.get("FTS_SELFTEST_REPORT") or user_data_dir() / "self_test_report.txt")
    os.environ["FTS_DATA_DIR"] = tempfile.mkdtemp(prefix="fts_selftest_")   # never touch real progress
    errors: list[str] = []
    sys.excepthook = lambda t, v, tb: errors.append("".join(traceback.format_exception(t, v, tb)))
    lines = []
    try:
        win = MainWindow()
        win.show()
        for theme_name in ("dark", "light"):
            win.ctx.set_theme(theme_name)
            for key in SCREENS:
                win.navigate(key)
                app.processEvents()
                ok = win.current == key
                lines.append(f"{'OK  ' if ok else 'FAIL'} {theme_name:5} {SCREENS[key][0]}")
                if not ok:
                    errors.append(f"screen {key} did not open")
        checks = {
            "RevPAR 1,012,500 / 4,500 = 225": abs(m.revpar(1_012_500, 4_500) - 225) < 1e-9,
            "NPV(10%, -100, 60, 60) = 4.13": abs(m.npv(0.10, [-100, 60, 60]) - 4.1322) < 1e-3,
            "Answer-key workbook grades 16/16": sum(r.status == "correct" for r in wbk.grade_workbook(
                resource_root() / "workbooks" / "ANSWER_KEY_Workbook_Aurelia_Grand.xlsx")) == 16,
            "Badges: none unlocked on a fresh start": achievements.unlocked(achievements.collect_stats(
                win.db, [l for mod in curriculum.modules() for l in mod.lessons])) == [],
        }
        for name, ok in checks.items():
            lines.append(f"{'OK  ' if ok else 'FAIL'} {name}")
            if not ok:
                errors.append(name)
        win.close()
    except Exception:
        errors.append(traceback.format_exc())
    lines.append("RESULT: " + ("PASS" if not errors else "FAIL"))
    report = "\n".join(lines + errors)
    out = report_path
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report: {out}")
    return 0 if not errors else 1


def run(argv=None) -> int:
    argv = argv if argv is not None else sys.argv
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName("Finance_Dojo")
    app.setStyle("Fusion")          # same look on every Windows version; the stylesheet themes it
    if "--self-test" in argv:
        return self_test(app)
    win = MainWindow()
    watcher = InputWatcher(win.ctx)
    app.installEventFilter(watcher)
    win.show()
    win.db.log("app_started")
    return app.exec()
