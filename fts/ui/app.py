"""Main window, navigation and the shared application context."""
from __future__ import annotations

import importlib
import sys
import time
import traceback
import weakref
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget)

from ..content import curriculum
from ..paths import resource_root
from ..content.base import SKILLS
from ..core import mastery
from ..storage.db import Progress
from . import theme

APP_TITLE = "Finance & Commercial Training Simulator"

# key: (navigation title, module path, class name)
SCREENS = {
    "home": ("Home", "home", "HomeScreen"),
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
        brand = QLabel("◆ Finance & Commercial\n   Training Simulator")
        brand.setObjectName("Brand")
        sl.addWidget(brand)
        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        for key, (title, *_rest) in SCREENS.items():
            it = QListWidgetItem(title)
            it.setData(Qt.UserRole, key)
            self.nav.addItem(it)
        self.nav.currentItemChanged.connect(self._nav_changed)
        sl.addWidget(self.nav, 1)
        foot = QLabel("Offline · fictional training data\nNot a professional certification")
        foot.setObjectName("Muted")
        foot.setWordWrap(True)
        sl.addWidget(foot)
        lay.addWidget(side)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage(f"Progress saved locally: {self.db.path}")
        self.apply_theme()
        self.navigate("home")

    # navigation ----------------------------------------------------------
    def _nav_changed(self, cur, _prev):
        if cur is not None:
            key = cur.data(Qt.UserRole)
            if key != self.current:
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
        row = list(SCREENS).index(key)
        if self.nav.currentRow() != row:
            self.nav.blockSignals(True)
            self.nav.setCurrentRow(row)
            self.nav.blockSignals(False)
        if hasattr(w, "on_show"):
            w.on_show(**kwargs)

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
    app.setApplicationName("Finance_Commercial_Training")
    app.setStyle("Fusion")          # same look on every Windows version; the stylesheet themes it
    if "--self-test" in argv:
        return self_test(app)
    win = MainWindow()
    watcher = InputWatcher(win.ctx)
    app.installEventFilter(watcher)
    win.show()
    win.db.log("app_started")
    return app.exec()
