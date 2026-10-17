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
from PySide6.QtCore import Qt  # noqa: E402
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
    xp = win.db._q("SELECT amount FROM xp WHERE source='exercise' AND ref=?", [w.ex.id])
    assert [r["amount"] for r in xp] == [12]                         # solved on the second try
    _no_errors(env)


def test_daily_quests_and_xp(env):
    import datetime as dt
    from fts.core import gamify
    from fts.core.checker import format_value
    from fts.ui.screens.dojo import QuestCard
    win = env["win"]
    win.db.set_setting("celebrations", "1")
    win.db._x("DELETE FROM events WHERE kind='quest_revealed'")       # the click-everything test revealed them
    win.db._x("DELETE FROM xp WHERE source='quest'")
    if "dojo" in win.screens:
        win.screens["dojo"].day = None                                  # rebuild today's cards
    win.navigate("dojo")
    cards = [c for c in win.screens["dojo"].findChildren(QuestCard) if c.source == "quest"]
    assert len(cards) == 3
    total = win.db.xp_total()
    today = dt.date.today().isoformat()
    a, b = cards[0], cards[1]
    a.input.setText(format_value(a.ch.expected * 3 + 7, a.ch.unit, 2))   # wrong first
    a.check()
    assert not win.db.has_xp("quest", f"{today}:{a.ch.id}")
    a.input.setText(format_value(a.ch.expected, a.ch.unit, 2))
    a.check()
    assert win.db.has_xp("quest", f"{today}:{a.ch.id}")
    assert win.db.xp_total() >= total + gamify.QUEST_XP
    assert win.fun.toast.isVisible()
    b.reveal()                                                          # shown answer: no XP
    assert not win.db.has_xp("quest", f"{today}:{b.ch.id}")
    assert not b.btn_check.isEnabled()
    win.screens["dojo"].roll()                                          # quick-fire practice
    assert win.screens["dojo"].quick_card is not None
    win.navigate("home")
    assert "Daily quests (1 left)" in win.screens["home"].btn_quests.text()
    _no_errors(env)


def test_focus_timer_and_calm_settings(env):
    win = env["win"]
    panel = win.xp_panel
    panel.toggle_focus()
    assert "stop" in panel.focus_btn.text()
    before = win.db.xp_total()
    panel.focus_end = 0.0                                               # pretend the time is up
    panel._focus_tick()
    assert panel.focus_end is None and win.db.xp_total() == before + 10
    win.fun.confetti.timer.stop()                                       # end the focus celebration
    win.fun.confetti.hide()
    win.db.set_setting("reduce_motion", "1")
    win.fun.notify("Calm", "no confetti", big=True)
    assert not win.fun.confetti.isVisible()
    win.db.set_setting("celebrations", "0")
    win.fun.toast.hide()
    win.fun.toast.queue.clear()
    win.fun.toast.timer.stop()
    win.fun.notify("Hidden", "celebrations are off")
    assert not win.fun.toast.isVisible()
    win.db.set_setting("celebrations", "1")
    win.db.set_setting("reduce_motion", "0")
    _no_errors(env)


def test_home_next_step_opens_the_right_lesson_step(env):
    win = env["win"]
    win.navigate("home")
    home = win.screens["home"]
    lesson, step = home._next
    home.go()
    if lesson is None:
        assert win.current == "capstone"
    else:
        lessons = win.screens["lessons"]
        assert win.current == "lessons" and lessons.lesson.id == lesson.id
        assert lessons.tabs.currentIndex() == step
        lessons._move(1)
        assert lessons.tabs.currentIndex() == min(step + 1, lessons.tabs.count() - 1) or step == 6
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


def test_sidebar_groups_fit_and_navigate(env):
    from fts.ui.app import NAV_GROUPS, SCREENS
    win = env["win"]
    keys = [k for _h, items in NAV_GROUPS for k, _i in items]
    assert sorted(keys) == sorted(SCREENS)                 # every screen exactly once
    headers = [win.nav.item(r) for r in range(win.nav.count()) if win.nav.item(r).data(0x0100) is None]
    assert len(headers) == len(NAV_GROUPS)
    for h in headers:
        assert not (h.flags() & Qt.ItemIsSelectable)
    for key in ("dojo", "settings", "lessons"):
        win.nav.setCurrentRow(win.nav_rows[key])
        env["app"].processEvents()
        assert win.current == key
    win.navigate("home")
    assert win.nav.currentItem().data(0x0100) == "home"
    _no_errors(env)


def test_keyboard_shortcuts(env):
    from fts.ui.app import SHORTCUTS
    win = env["win"]
    for _k, _d, action in SHORTCUTS:
        assert callable(getattr(win, action))
    win.go_dojo()
    assert win.current == "dojo"
    win.go_next_step()
    assert win.current in ("lessons", "capstone")
    if win.current == "lessons":
        lessons = win.screens["lessons"]
        lessons.tabs.setCurrentIndex(0)
        win.lesson_next()
        assert lessons.tabs.currentIndex() == 1
        win.lesson_prev()
        assert lessons.tabs.currentIndex() == 0
    win.toggle_focus()
    assert win.xp_panel.focus_end is not None
    win.toggle_focus()
    assert win.xp_panel.focus_end is None
    env["messages"].clear()
    win.show_shortcuts()
    assert env["messages"] and env["messages"][-1][1] == "Keyboard shortcuts"
    win.go_home()
    assert win.current == "home"
    _no_errors(env)


def test_one_question_at_a_time_quiz(env):
    from fts.content import curriculum
    from fts.ui.widgets import QuizWidget
    win = env["win"]
    mod = curriculum.modules()[1]
    lesson = mod.lessons[1]
    win.navigate("lessons", lesson=lesson.id, step=5)
    quiz = [q for q in win.screens["lessons"].findChildren(QuizWidget) if q.lesson.id == lesson.id][-1]
    quiz.retake()
    before = win.db.best_quiz(lesson.id)
    assert quiz.question.text().startswith("Question 1 of")
    assert not quiz.btn_next.isEnabled()                    # must answer first
    quiz.next_question()
    assert quiz.i == 0
    for k, q in enumerate(lesson.quiz):
        wrong = (q.answer + 1) % len(q.options)
        quiz.choose(wrong if k == 0 else q.answer)
        quiz.choose(q.answer)                               # a second click is ignored
        assert len(quiz.results) == k + 1
        assert all(not b.isEnabled() for b in quiz.opts)
        assert quiz.opts[q.answer].property("state") == "right"
        quiz.next_question()
    assert quiz.finished
    n = len(lesson.quiz)
    assert quiz.question.text().startswith(f"You scored {n - 1} out of {n}")
    best = win.db.best_quiz(lesson.id)
    assert best[0] >= n - 1 and (before is None or best[0] >= before[0])
    assert quiz.btn_retake.isVisible() and not quiz.btn_next.isVisible()
    quiz.retake()
    assert quiz.i == 0 and quiz.results == [] and not quiz.finished
    _no_errors(env)


def test_badge_unlock_is_celebrated_once(env):
    win = env["win"]
    db = win.db
    db._x("DELETE FROM meta WHERE key LIKE 'badge:%'")
    win.fun.toast.queue.clear()
    db.set_setting("celebrations", "1")
    new = win.ctx.check_badges()
    assert any(b.id == "first_steps" for b in new)
    assert db.meta("badge:first_steps")
    titles = [t for t, _x, _b in win.fun.toast.queue] + [win.fun.toast.title.text()]
    assert any("Badge unlocked" in t for t in titles)
    assert win.ctx.check_badges() == []                     # nothing twice
    win.navigate("dojo")
    dojo = win.screens["dojo"]
    assert "unlocked" in dojo.badge_next.text()
    f, _p = dojo.badge_frames["first_steps"]
    assert f.property("locked") == "false"
    _no_errors(env)


def test_home_manager_note_and_welcome(tmp_path, monkeypatch):
    from fts.content import story
    from fts.ui.app import MainWindow
    monkeypatch.setenv("FTS_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.show()
    app.processEvents()
    home = win.screens["home"]
    assert home.welcome.isVisible()                         # brand-new user
    assert story.MANAGER in home.mgr_from.text()
    assert home.mgr_subject.text() == story.note_for(1)[0]
    home.w_name.setText("Sam")
    home.w_goal.setCurrentIndex(0)
    home.w_focus.setCurrentIndex(0)
    home.finish_welcome()
    assert not home.welcome.isVisible()
    assert win.db.setting("student_name") == "Sam"
    assert win.db.setting("daily_goal") == "30"
    assert win.db.setting("focus_minutes") == "5"
    assert home.h1.text() == "Welcome back, Sam"
    win.navigate("settings")
    assert win.screens["settings"].goal.currentData() == 30
    win.close()
    win2 = MainWindow()                                      # welcome only once
    assert not win2.screens["home"].welcome.isVisibleTo(win2.screens["home"])
    win2.close()


def test_career_mode_boss_battles(env):
    from fts.content import career
    from fts.core.checker import format_value
    win = env["win"]
    db = win.db
    db._x("DELETE FROM meta WHERE key LIKE 'boss:%'")
    db._x("DELETE FROM xp WHERE source='boss'")
    win.go_career()
    assert win.current == "career"
    c = win.screens["career"]
    f, state, _btn = c.cards[2]
    assert f.property("state") == "locked" and "Locked" in state.text()
    c.select(1)
    assert c.obj_rows[2][0].text().count("Boss") == 1
    assert not c.obj_rows[2][1].isEnabled()          # lessons not finished yet
    steps = career.chapters()[0].boss.steps
    # losing all three lives: knocked out, nothing saved
    c.start_boss(1)
    for _ in range(3):
        c.b_input.setText("1")
        c.check()
    assert c.hearts == 0 and c.b_retry.isEnabled() and not c.b_check.isEnabled()
    assert db.meta("boss:1") is None and not db.has_xp("boss", "ch1")
    c.b_input.setText("abc")                     # not a number: never costs a life
    c.retry()
    c.b_input.setText("abc")
    c.check()
    assert c.hearts == career.HEARTS
    # win with one life lost: 2 stars, promotion, XP once
    c.b_input.setText("1")
    c.check()
    for k, st in enumerate(steps):
        c.b_input.setText(format_value(st.expected, st.unit, 2))
        c.check()
        if k < len(steps) - 1:
            assert c.b_next.isEnabled()
            c.next_step()
    assert db.meta("boss:1") == "2"
    assert db.has_xp("boss", "ch1")
    xp = db.xp_total()
    c.retry()                                    # replay with no mistakes: better stars, no more XP
    for k, st in enumerate(steps):
        c.b_input.setText(format_value(st.expected, st.unit, 2))
        c.check()
        if k < len(steps) - 1:
            c.next_step()
    assert db.meta("boss:1") == "3"
    assert db.xp_total() == xp
    c.back()
    assert c.rank_lbl.text().endswith("Junior Analyst")
    assert c.cards[2][0].property("state") == "open"
    assert win.xp_panel.rank.text().endswith("Junior Analyst")
    assert db.meta("badge:boss_slayer")
    win.navigate("home")
    assert "Chapter 2" in win.screens["home"].btn_career.text()
    _no_errors(env)
