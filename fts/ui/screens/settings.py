"""Settings, backup / restore / reset, and instructor exports."""
from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox,
                               QSpinBox)

from ...core import gamify
from ...data import generator as gen
from ...paths import exports_dir, user_data_dir
from ...reports import export
from ..widgets import Card, button, error, info, label, save_dialog
from .base import Screen


def open_folder(path: Path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))          # noqa: S606 (Windows only)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError:
        pass


class SettingsScreen(Screen):
    title = "Settings & backup"
    subtitle = "Preferences, progress backup and restore, and instructor exports. Everything is stored locally."

    def __init__(self, ctx):
        super().__init__(ctx)
        db = ctx.db
        pref = Card("Preferences")
        g = QGridLayout()
        self.name = QLineEdit(db.setting("student_name"))
        self.name.setPlaceholderText("Your name (shown on reports)")
        self.name.editingFinished.connect(lambda: db.set_setting("student_name", self.name.text().strip()))
        g.addWidget(label("Student name", wrap=False), 0, 0)
        g.addWidget(self.name, 0, 1)
        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Light"])
        self.theme.setCurrentIndex(1 if db.setting("theme") == "light" else 0)
        self.theme.currentIndexChanged.connect(lambda i: ctx.set_theme("light" if i == 1 else "dark"))
        g.addWidget(label("Theme", wrap=False), 1, 0)
        g.addWidget(self.theme, 1, 1)
        self.attempts = QSpinBox(minimum=1, maximum=10, value=db.max_attempts())
        self.attempts.valueChanged.connect(lambda v: db.set_setting("max_attempts", v))
        g.addWidget(label("Attempts before the solution is shown", wrap=False), 2, 0)
        g.addWidget(self.attempts, 2, 1)
        try:
            fs = int(db.setting("font_size"))
        except ValueError:
            fs = 10
        self.font = QSpinBox(minimum=8, maximum=16, value=fs)
        self.font.setSuffix(" pt")
        self.font.valueChanged.connect(self._font)
        g.addWidget(label("Text size", wrap=False), 3, 0)
        g.addWidget(self.font, 3, 1)
        g.setColumnStretch(1, 1)
        pref.add(g)
        pref.add(label("Changing the number of attempts applies to exercises from now on; earlier attempts stay "
                       "recorded.", "Muted"))
        self.body.addWidget(pref)

        fun = Card("Motivation & focus")
        g2 = QGridLayout()
        self.goal = QComboBox()
        for v in gamify.DAILY_GOAL_CHOICES:
            self.goal.addItem({30: "Gentle", 50: "Steady", 100: "Ambitious"}.get(v, "") + f" · {v} XP a day", v)
        self.goal.setCurrentIndex(gamify.DAILY_GOAL_CHOICES.index(
            db.int_setting("daily_goal", gamify.DAILY_GOAL_CHOICES, gamify.DEFAULT_DAILY_GOAL)))
        self.goal.currentIndexChanged.connect(lambda i: self._set("daily_goal", self.goal.itemData(i)))
        g2.addWidget(label("Daily goal", wrap=False), 0, 0)
        g2.addWidget(self.goal, 0, 1)
        self.focus = QComboBox()
        for v in gamify.FOCUS_CHOICES:
            self.focus.addItem(f"{v} minutes", v)
        self.focus.setCurrentIndex(gamify.FOCUS_CHOICES.index(
            db.int_setting("focus_minutes", gamify.FOCUS_CHOICES, gamify.DEFAULT_FOCUS_MINUTES)))
        self.focus.currentIndexChanged.connect(lambda i: self._set("focus_minutes", self.focus.itemData(i)))
        g2.addWidget(label("Focus timer length", wrap=False), 1, 0)
        g2.addWidget(self.focus, 1, 1)
        self.cele = QCheckBox("Show XP pop-ups and celebrations")
        self.cele.setChecked(db.flag("celebrations"))
        self.cele.toggled.connect(lambda on: self._set("celebrations", int(on)))
        g2.addWidget(self.cele, 2, 0, 1, 2)
        self.calm = QCheckBox("Reduce motion (no confetti or fades)")
        self.calm.setChecked(db.flag("reduce_motion"))
        self.calm.toggled.connect(lambda on: self._set("reduce_motion", int(on)))
        g2.addWidget(self.calm, 3, 0, 1, 2)
        g2.setColumnStretch(1, 1)
        fun.add(g2)
        fun.add(label("Short focus blocks and small daily goals help if your attention wanders. XP and belts "
                      "are for momentum only; they never change your skill scores.", "Muted"))
        self.body.addWidget(fun)

        from ..app import SHORTCUTS
        keys = Card("Keyboard shortcuts")
        kg = QGridLayout()
        for i, (k, d, _a) in enumerate(SHORTCUTS):
            kg.addWidget(label(k, "Chip", wrap=False), i // 2, (i % 2) * 2)
            kg.addWidget(label(d, wrap=False), i // 2, (i % 2) * 2 + 1)
        kg.setColumnStretch(3, 1)
        keys.add(kg)
        self.body.addWidget(keys)

        data = Card("Your progress data")
        data.add(label(f"Progress database: {db.path}", "Muted"))
        data.add(label(f"Exports folder: {exports_dir()}", "Muted"))
        r = QHBoxLayout()
        r.addWidget(button("Back up progress…", self.backup, primary=True))
        r.addWidget(button("Restore from backup…", self.restore))
        r.addWidget(button("Open data folder", lambda: open_folder(user_data_dir())))
        r.addWidget(button("Open exports folder", lambda: open_folder(exports_dir())))
        r.addStretch(1)
        data.add(r)
        r2 = QHBoxLayout()
        r2.addWidget(button("Reset all progress…", self.reset, obj="Danger"))
        r2.addStretch(1)
        data.add(r2)
        data.add(label("Restore checks the file first and keeps a safety copy of your current progress "
                       "(…before_restore.sqlite3) in the data folder. Reset cannot be undone unless you back up "
                       "first; settings are kept.", "Muted"))
        self.body.addWidget(data)

        inst = Card("Instructor")
        r3 = QHBoxLayout()
        r3.addWidget(button("Export instructor answer key (Markdown)…", self.export_key))
        r3.addWidget(button("Export all datasets (CSV) to a folder…", self.export_datasets))
        r3.addStretch(1)
        inst.add(r3)
        inst.add(label(gen.DISCLAIMER, "Muted"))
        self.body.addWidget(inst)

        about = Card("About")
        about.add(label("Finance Dojo. Works offline. All companies, hotels and figures "
                        "are fictional training data, not industry benchmarks. Forecasts and valuations in the app "
                        "are illustrative estimates, never guarantees. " + export.DISCLAIMER_CERT))
        self.body.addWidget(about)

    def _set(self, key, value):
        self.ctx.db.set_setting(key, value)
        self.ctx.window.refresh_xp()

    def _font(self, v):
        self.ctx.db.set_setting("font_size", v)
        self.ctx.window.apply_theme()

    def backup(self):
        name = f"fts_progress_backup_{dt.datetime.now():%Y%m%d_%H%M}.sqlite3"
        path = save_dialog(self, "Back up progress", name, "Progress backup (*.sqlite3)")
        if path:
            try:
                self.ctx.db.backup(path)
            except Exception as exc:
                error(self, "Backup failed", str(exc))
                return
            info(self, "Backup saved", f"Saved to {path}")

    def restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restore progress", str(exports_dir()),
                                              "Progress backup (*.sqlite3 *.db);;All files (*)")
        if not path:
            return
        try:
            self.ctx.db.validate_backup(Path(path))
        except ValueError as exc:
            error(self, "Cannot restore", str(exc))
            return
        if QMessageBox.question(self, "Restore progress",
                                "Replace your current progress with this backup? A safety copy of the current "
                                "progress is kept in the data folder.") != QMessageBox.Yes:
            return
        try:
            self.ctx.db.restore(Path(path))
        except Exception as exc:
            error(self, "Restore failed", str(exc))
            return
        self._after_data_change("Progress restored.")

    def reset(self):
        if QMessageBox.question(self, "Reset all progress",
                                "Delete ALL exercise attempts, quiz results, practical tasks, workbook results and "
                                "capstone answers? This cannot be undone unless you have a backup.") != QMessageBox.Yes:
            return
        self.ctx.db.reset()
        self._after_data_change("All progress was reset.")

    def _after_data_change(self, msg: str):
        """Drop cached screens so they reload from the database."""
        win = self.ctx.window
        self.ctx.invalidate()
        for key, w in list(win.screens.items()):
            if w is self:
                continue
            win.stack.removeWidget(w)
            w.deleteLater()
            del win.screens[key]
        from ..app import backfill_xp
        backfill_xp(self.ctx.db)
        self.ctx.set_theme(self.ctx.db.setting("theme"))
        win.refresh_xp()
        info(self, "Done", msg)

    def export_key(self):
        path = save_dialog(self, "Export answer key", "ANSWER_KEY.md", "Markdown (*.md)")
        if path:
            path.write_text(export.answer_key_markdown(), encoding="utf-8")
            info(self, "Exported", f"Saved to {path}")

    def export_datasets(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder", str(exports_dir()))
        if folder:
            try:
                written = gen.write_all(Path(folder))
            except OSError as exc:
                error(self, "Export failed", str(exc))
                return
            info(self, "Exported", f"Datasets written to {folder}" + (f" ({len(written)} files)" if written else ""))

    def on_show(self, **kw):
        """Pick up changes made elsewhere (for example the welcome card on Home)."""
        db = self.ctx.db
        for w, key, choices, default in (
                (self.goal, "daily_goal", gamify.DAILY_GOAL_CHOICES, gamify.DEFAULT_DAILY_GOAL),
                (self.focus, "focus_minutes", gamify.FOCUS_CHOICES, gamify.DEFAULT_FOCUS_MINUTES)):
            w.blockSignals(True)
            w.setCurrentIndex(choices.index(db.int_setting(key, choices, default)))
            w.blockSignals(False)
        self.name.setText(db.setting("student_name"))
