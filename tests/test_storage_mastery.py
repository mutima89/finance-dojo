import sqlite3

import pytest

from fts.content import curriculum
from fts.content.base import SKILLS
from fts.core import mastery
from fts.storage.db import Progress


@pytest.fixture
def db(tmp_path):
    p = Progress(tmp_path / "p.sqlite3")
    yield p
    p.close()


def ex(eid):
    return curriculum.exercises_by_id()[eid]


def test_attempts_and_persistence(tmp_path):
    p = Progress(tmp_path / "p.sqlite3")
    e = ex("m3l1_g")
    p.record_attempt(e, "m3l1", "m3", "200", False)
    st = p.record_attempt(e, "m3l1", "m3", "350.66", True)
    assert st["attempts"] == 2 and st["solved"] == 1 and st["solved_on"] == 2 and st["wrong"] == 1
    p.save_task("m3t1", "m3l1", "m3", "My commentary", [True, False])
    p.set_setting("theme", "light")
    p.close()
    q = Progress(tmp_path / "p.sqlite3")             # reopen = app restart
    assert q.exercise_state("m3l1_g")["solved"] == 1
    assert q.task("m3t1")["content"] == "My commentary"
    assert q.task("m3t1")["checklist"] == [True, False]
    assert q.setting("theme") == "light"
    assert q.meta("last_lesson") == "m3l1"           # resume point
    q.close()


def test_quiz_and_time(db):
    db.record_quiz("m1l1", "m1", [("m1q1", "Financial statements", True), ("m1q2", "Financial statements", False)])
    db.record_quiz("m1l1", "m1", [("m1q1", "Financial statements", True), ("m1q2", "Financial statements", True)])
    assert db.best_quiz("m1l1") == (2, 2)
    db.add_time("m1l1", "m1", 120)
    db.add_time("m1l1", "m1", 30)
    assert db.lesson_seconds()["m1l1"] == 150


def test_settings_defaults_and_bounds(db):
    assert db.max_attempts() == 3
    db.set_setting("max_attempts", "abc")
    assert db.max_attempts() == 3
    db.set_setting("max_attempts", "50")
    assert db.max_attempts() == 10


def test_backup_restore_reset(db, tmp_path):
    db.record_attempt(ex("m1l1_g"), "m1l1", "m1", "x", True)
    b = db.backup(tmp_path / "backup.sqlite3")
    db.reset()
    assert db.exercise_state("m1l1_g")["solved"] == 0
    db.restore(b)
    assert db.exercise_state("m1l1_g")["solved"] == 1
    bad = tmp_path / "bad.sqlite3"
    bad.write_text("nope")
    with pytest.raises(ValueError):
        db.restore(bad)
    other = tmp_path / "other.sqlite3"
    sqlite3.connect(other).execute("CREATE TABLE x(a)").connection.commit()
    with pytest.raises(ValueError):
        db.restore(other)


def test_exercise_credit_rules():
    assert mastery.exercise_credit(None) == 0
    assert mastery.exercise_credit({"solved": 1, "solved_on": 1, "hints_used": 0}) == 1.0
    assert mastery.exercise_credit({"solved": 1, "solved_on": 1, "hints_used": 2}) == 0.85
    assert mastery.exercise_credit({"solved": 1, "solved_on": 2}) == 0.70
    assert mastery.exercise_credit({"solved": 1, "solved_on": 4}) == 0.50
    assert mastery.exercise_credit({"solved": 1, "solved_on": 3, "revealed": 1}) == 0.0


def _perfect_state():
    status, quiz, tasks = {}, [], {}
    for m in curriculum.modules():
        for l in m.lessons:
            tasks[l.task.id] = {"content": "done"}
            for e in l.exercises:
                status[e.id] = {"solved": 1, "solved_on": 1, "hints_used": 0, "revealed": 0, "attempts": 1, "wrong": 0}
            for q in l.quiz:
                quiz.append({"question_id": q.id, "correct": 1})
    return status, quiz, tasks, {i: "correct" for i in range(1, 17)}


def test_job_ready_requires_capstone():
    status, quiz, tasks, wb = _perfect_state()
    res = mastery.skill_results(curriculum.modules(), status, quiz, tasks, wb, False, SKILLS)
    assert all(r.score == 100 for r in res)
    assert all(r.level == "Competent" for r in res)
    res = mastery.skill_results(curriculum.modules(), status, quiz, tasks, wb, True, SKILLS)
    assert all(r.level == "Job-ready for supervised tasks" for r in res)


def test_quiz_only_never_job_ready():
    _, quiz, tasks, _ = _perfect_state()
    res = mastery.skill_results(curriculum.modules(), {}, quiz, tasks, {}, True, SKILLS)
    assert all(r.score <= 40 for r in res)
    assert not any(r.level.startswith("Job-ready") for r in res)


def test_revealed_practical_blocks_job_ready():
    status, quiz, tasks, wb = _perfect_state()
    status["m3l1_g"]["revealed"] = 1
    res = {r.skill: r for r in mastery.skill_results(curriculum.modules(), status, quiz, tasks, wb, True, SKILLS)}
    assert res["Hotel KPIs"].level != "Job-ready for supervised tasks"


def test_weak_topic_detection():
    status = {"m3l1_g": {"solved": 0, "attempts": 4, "wrong": 4}}
    res = {r.skill: r for r in mastery.skill_results(curriculum.modules(), status, [], {}, {}, False, SKILLS)}
    assert res["Hotel KPIs"].weak
    assert not res["Investment appraisal"].weak       # not attempted yet -> not flagged


def test_hints_fade():
    assert mastery.hints_allowed(3, "Beginner", False) == 3
    assert mastery.hints_allowed(3, "Developing", False) == 2
    assert mastery.hints_allowed(3, "Competent", False) == 1
    assert mastery.hints_allowed(3, "Competent", True) == 3
