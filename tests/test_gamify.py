"""XP, belts, the forgiving streak and the XP store. None of it touches mastery."""
import datetime as dt

import pytest

from fts.core import gamify
from fts.storage.db import Progress

D = dt.date(2026, 3, 10)


def days(*offsets):
    return [D - dt.timedelta(days=o) for o in offsets]


def test_exercise_xp_rules():
    assert gamify.exercise_xp(1) == 20
    assert gamify.exercise_xp(1, hints_used=2) == 15
    assert gamify.exercise_xp(2) == 12
    assert gamify.exercise_xp(5) == 8
    assert gamify.exercise_xp(1, revealed=True) == 0       # a revealed solution earns nothing
    assert gamify.exercise_xp(None) == 0


def test_quiz_xp_only_rewards_improvement():
    assert gamify.quiz_xp(2, None) == 10
    assert gamify.quiz_xp(3, 2) == 5
    assert gamify.quiz_xp(2, 3) == 0
    assert gamify.quiz_xp(3, 3) == 0


@pytest.mark.parametrize("xp,belt,to_next", [
    (0, "White belt", 150), (149, "White belt", 1), (150, "Yellow belt", 250), (799, "Orange belt", 1),
    (4499, "Brown belt", 1), (4500, "Black belt", 0), (99999, "Black belt", 0)])
def test_belts(xp, belt, to_next):
    r = gamify.rank(xp)
    assert r.belt.name == belt
    assert r.to_next == to_next
    assert 0.0 <= r.fraction <= 1.0


def test_belt_fraction_halfway():
    # Yellow (150) to Orange (400): 275 XP is halfway
    assert gamify.rank(275).fraction == pytest.approx(0.5)


def test_streak_counts_consecutive_days():
    s = gamify.streak(days(0, 1, 2), D)
    assert (s.days, s.active_today, s.at_risk) == (3, True, False)


def test_streak_not_broken_before_practising_today():
    s = gamify.streak(days(1, 2), D)
    assert (s.days, s.active_today, s.at_risk) == (2, False, False)


def test_streak_forgives_one_rest_day():
    # active today, rested yesterday, active the two days before
    assert gamify.streak(days(0, 2, 3), D).days == 3
    # rested yesterday and not active yet today: still alive but at risk
    s = gamify.streak(days(2, 3), D)
    assert (s.days, s.at_risk) == (2, True)


def test_streak_ends_after_two_missed_days():
    assert gamify.streak(days(0, 3, 4), D).days == 1
    assert gamify.streak(days(3, 4), D).days == 0
    assert gamify.streak([], D).days == 0


def test_goal_fraction():
    assert gamify.goal_fraction(25, 50) == 0.5
    assert gamify.goal_fraction(80, 50) == 1.0


def test_xp_is_awarded_once_per_item(tmp_path):
    db = Progress(tmp_path / "p.sqlite3")
    assert db.add_xp("exercise", "e1", 20, ts="2026-03-10T09:00:00")
    assert not db.add_xp("exercise", "e1", 20)            # no double award
    assert not db.add_xp("exercise", "e2", 0)             # nothing for zero
    assert db.add_xp("quest", "2026-03-09:coffee_cart", 15, ts="2026-03-09T20:00:00")
    assert db.xp_total() == 35
    assert db.xp_on(dt.date(2026, 3, 10)) == 20
    assert sorted(db.active_days()) == [dt.date(2026, 3, 9), dt.date(2026, 3, 10)]
    assert db.xp_count_on("quest", dt.date(2026, 3, 9)) == 1
    db.reset()
    assert db.xp_total() == 0
    db.close()


def test_settings_have_safe_defaults(tmp_path):
    db = Progress(tmp_path / "p.sqlite3")
    assert db.int_setting("daily_goal", gamify.DAILY_GOAL_CHOICES, 50) == 50
    db.set_setting("daily_goal", "999")                   # outside the allowed choices
    assert db.int_setting("daily_goal", gamify.DAILY_GOAL_CHOICES, 50) == 50
    assert db.flag("celebrations") and not db.flag("reduce_motion")
    db.close()


def test_backfill_gives_credit_for_earlier_progress(tmp_path):
    from fts.content import curriculum
    pytest.importorskip("PySide6")
    from fts.ui.app import backfill_xp
    db = Progress(tmp_path / "p.sqlite3")
    lesson = curriculum.modules()[0].lessons[0]
    m = curriculum.modules()[0]
    db.record_attempt(lesson.guided, lesson.id, m.id, "x", True)            # first try: 20
    e2 = lesson.independent[0]
    db.record_attempt(e2, lesson.id, m.id, "x", False)
    db.record_attempt(e2, lesson.id, m.id, "x", True)                       # second try: 12
    db.record_quiz(lesson.id, m.id, [("q1", "s", True), ("q2", "s", True), ("q3", "s", False)])   # 2 x 5
    backfill_xp(db)
    assert db.xp_total() == 20 + 12 + 10
    backfill_xp(db)                                                          # runs once only
    assert db.xp_total() == 42
    db.close()
