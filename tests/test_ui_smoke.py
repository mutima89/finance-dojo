"""Headless UI smoke tests (Qt 'offscreen' platform).

Opens every screen, clicks every enabled button (file dialogs return paths in a
temporary folder; confirmation dialogs answer 'No' unless a test says
otherwise), switches theme, and runs end-to-end flows: answering an exercise,
scoring the capstone, backup/restore. Any exception raised inside a Qt slot
fails the test.
"""
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "QtAgg")

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton  # noqa: E402


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ui")
    os.environ["FTS_DATA_DIR"] = str(tmp / "data")
    app = QApplication.instance() or QApplication([])
    errors, messages = [], []
    old_hook = sys.excepthook
    sys.excepthook = lambda *exc: errors.append(exc)
    answer = {"question": QMessageBox.No}
    saves = tmp / "saves"
    saves.mkdir()
    mp = pytest.MonkeyPatch()
    mp.setattr(QFileDialog, "getSaveFileName",
               staticmethod(lambda parent, title, default, filt="": (str(saves / os.path.basename(default)), "")))
    mp.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    mp.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(saves / "datasets")))
    for name in ("information", "warning", "critical"):
        mp.setattr(QMessageBox, name, staticmethod(lambda parent, title, text, *a, _n=name: messages.append((_n, title, text))))
    mp.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: answer["question"]))
    import fts.ui.screens.settings as settings_mod
    mp.setattr(settings_mod, "open_folder", lambda p: None)
    from fts.ui.app import MainWindow
    win = MainWindow()
    win.show()
    app.processEvents()
    yield dict(app=app, win=win, errors=errors, messages=messages, saves=saves, answer=answer, tmp=tmp, mp=mp)
    win.close()
    mp.undo()
    sys.excepthook = old_hook


def _no_errors(env):
    if env["errors"]:
        import traceback
        msg = "".join("".join(traceback.format_exception(*e)) for e in env["errors"])
        env["errors"].clear()
        pytest.fail("Exception in Qt slot:\n" + msg)
    crit = [m for m in env["messages"] if m[0] == "critical"]
    assert not crit, crit


def test_every_screen_opens(env):
    from fts.ui.app import SCREENS
    win = env["win"]
    for key in SCREENS:
        win.navigate(key)
        env["app"].processEvents()
        assert win.current == key, key
    _no_errors(env)


SKIP_BUTTONS = {"Reset all progress…"}


def test_click_every_button(env):
    from fts.ui.app import SCREENS
    win = env["win"]
    for key in SCREENS:
        win.navigate(key)
        w = win.screens[key]
        for b in w.findChildren(QPushButton):
            if b.isEnabled() and b.text() not in SKIP_BUTTONS and "lesson" not in b.text().lower():
                b.click()
                env["app"].processEvents()
                _no_errors(env)
    exported = list(env["saves"].iterdir())
    assert any(p.suffix == ".xlsx" for p in exported)
    assert any(p.suffix == ".png" for p in exported)
    assert any(p.suffix == ".html" for p in exported)


def test_theme_switch(env):
    win = env["win"]
    win.ctx.set_theme("light")
    env["app"].processEvents()
    assert win.db.setting("theme") == "light"
    win.ctx.set_theme("dark")
    _no_errors(env)


def test_exercise_flow(env):
    from fts.content import curriculum
    from fts.ui.widgets import ExerciseWidget
    win = env["win"]
    lesson = curriculum.modules()[0].lessons[0]
    win.navigate("lessons", lesson=lesson.id)
    ws = [w for w in win.screens["lessons"].findChildren(ExerciseWidget) if w.ex.unit != "choice"]
    assert ws
    w = ws[0]
    w.input.setText("abc")
    w.check()
    assert win.db.exercise_state(w.ex.id)["attempts"] == 0          # invalid input not counted
    w.input.setText(str(float(w.ex.expected) * 1000 + 12345))
    w.check()
    w.input.setText(str(w.ex.expected))
    w.check()
    st = win.db.exercise_state(w.ex.id)
    assert st["solved"] and st["solved_on"] == 2
    assert not w.btn_check.isEnabled()
    _no_errors(env)


def test_capstone_scoring(env):
    from fts.content import capstone as cap
    win = env["win"]
    win.navigate("capstone")
    scr = win.screens["capstone"]
    for st in scr.steps:
        for it in st.items:
            w = scr.inputs.get(it.id)
            if it.kind == "numeric":
                w.setText(str(it.expected))
            elif it.kind == "choice":
                w.setCurrentIndex(int(it.expected) + 1)
    for k, cb in scr.kpi_boxes.items():
        cb.setChecked(k in cap.ESSENTIAL_KPIS)
    scr.score()
    best = win.db.best_capstone()
    assert best is not None
    # all auto-scored items correct, export done earlier, text left blank -> 100 - 24 text points
    assert best["total"] == pytest.approx(76.0)
    assert best["passed"]
    _no_errors(env)


def test_backup_and_restore(env, monkeypatch):
    win = env["win"]
    path = env["saves"] / "backup_test.sqlite3"
    win.db.backup(path)
    before = win.db.attempts_total()
    win.db.reset()
    assert win.db.attempts_total() == (0, 0)
    win.navigate("settings")
    scr = win.screens["settings"]
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(path), "")))
    env["answer"]["question"] = QMessageBox.Yes
    try:
        scr.restore()
    finally:
        env["answer"]["question"] = QMessageBox.No
    assert win.db.attempts_total() == before
    # screens were rebuilt from the restored database
    win.navigate("progress")
    _no_errors(env)


def test_restore_rejects_bad_file(env, monkeypatch):
    win = env["win"]
    bad = env["saves"] / "not_a_backup.sqlite3"
    bad.write_text("hello")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(bad), "")))
    env["messages"].clear()
    win.navigate("settings")
    win.screens["settings"].restore()
    assert any(m[0] == "warning" and "Cannot restore" in m[1] for m in env["messages"])


def test_startup_shutdown_persistence(tmp_path, monkeypatch):
    """Close the app, start it again: progress, settings and the resume point survive."""
    from fts.content import curriculum
    from fts.storage.db import Progress
    from fts.ui.app import MainWindow
    monkeypatch.setenv("FTS_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    mod = curriculum.modules()[0]
    lesson = mod.lessons[0]
    win.db.record_attempt(lesson.guided, lesson.id, mod.id, str(lesson.guided.expected), True)
    win.ctx.set_theme("light")
    win.navigate("lessons", lesson=lesson.id)
    win.close()                                   # closeEvent closes the database cleanly
    app.processEvents()
    db = Progress()
    assert db.exercise_state(lesson.guided.id)["solved"]
    assert db.setting("theme") == "light"
    assert db.meta("last_lesson") == lesson.id    # "Resume where I left off" target
    kinds = [r["kind"] for r in db._q("SELECT kind FROM events")]
    assert "app_closed" in kinds
    db.close()
    win2 = MainWindow()                           # second start reads the same data
    assert win2.db.exercise_state(lesson.guided.id)["solved"]
    assert win2.ctx.pal.name == "light"
    win2.close()
