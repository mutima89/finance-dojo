"""Badges and the best-streak rule."""
import datetime as dt

from fts.core import achievements as ach
from fts.core import gamify

D = dt.date(2026, 3, 10)


def days(*offsets):
    return [D + dt.timedelta(days=o) for o in offsets]


def test_best_streak_empty():
    assert gamify.best_streak([]) == 0


def test_best_streak_counts_active_days_and_forgives_one_rest_day():
    assert gamify.best_streak(days(0, 1, 2)) == 3
    assert gamify.best_streak(days(0, 2, 4)) == 3          # one rest day between each
    assert gamify.best_streak(days(0, 1, 4, 5, 6, 7)) == 4  # two missed days end the first run


def test_best_streak_ignores_duplicates_and_order():
    assert gamify.best_streak(days(2, 0, 1, 1)) == 3


def test_best_streak_never_below_current_streak():
    active = days(0, 1, 3, 4, 5)
    today = D + dt.timedelta(days=5)
    assert gamify.best_streak(active) >= gamify.streak(active, today).days


def test_badge_ids_unique_and_needs_positive():
    ids = [b.id for b in ach.BADGES]
    assert len(ids) == len(set(ids))
    assert all(b.need >= 1 and b.emoji and b.desc.endswith(".") for b in ach.BADGES)


def test_nothing_unlocked_with_no_progress():
    assert ach.unlocked({}) == []


def test_unlocks_at_threshold_not_before():
    b = next(x for x in ach.BADGES if x.id == "sharpshooter")
    assert b not in ach.unlocked({"first_try": b.need - 1})
    assert b in ach.unlocked({"first_try": b.need})


def test_next_badges_prefers_the_closest():
    stats = {"xp": 1, "first_try": 4, "lessons": 1}
    nxt = ach.next_badges(stats, 2)
    assert nxt[0][0].id == "sharpshooter" and nxt[0][1] == 4
    assert all(b.id not in {"first_steps", "first_lesson"} for b, _ in nxt)


def test_next_badges_empty_when_all_unlocked():
    stats = {b.stat: 10_000 for b in ach.BADGES}
    assert ach.next_badges(stats) == []
    assert len(ach.unlocked(stats)) == len(ach.BADGES)


def test_badge_note_is_honest():
    assert "not a qualification" in ach.BADGE_NOTE


def test_collect_stats_from_a_real_database(tmp_path):
    from fts.content import curriculum
    from fts.storage.db import Progress
    db = Progress(tmp_path / "p.sqlite3")
    lessons = [l for m in curriculum.modules() for l in m.lessons]
    s = ach.collect_stats(db, lessons)
    assert s["xp"] == 0 and ach.unlocked(s) == []
    l = lessons[0]
    m = curriculum.modules()[0]
    db.record_quiz(l.id, m.id, [(q.id, q.skill, True) for q in l.quiz])
    for i in range(3):
        db.add_xp("quest", f"2026-03-10:q{i}", gamify.QUEST_XP, ts="2026-03-10 09:00:00")
    db.add_xp("focus", "2026-03-11:0", gamify.FOCUS_XP, ts="2026-03-11 09:00:00")
    s = ach.collect_stats(db, lessons)
    assert s["perfect_quizzes"] == 1
    assert s["quests"] == 3 and s["quests_best_day"] == 3
    assert s["focus"] == 1 and s["best_streak"] == 2
    got = {b.id for b in ach.unlocked(s)}
    assert {"first_steps", "quiz_ace", "quest_sweep", "in_the_zone"} <= got
    assert "on_fire" not in got
    db.close()


def test_manager_notes_cover_every_module():
    from fts.content import curriculum, story
    for m in curriculum.modules():
        subject, text = story.note_for(m.number)
        assert subject and len(text) > 60
    assert story.note_for(None) == story.CAPSTONE_NOTE
    assert "fictional" in story.MANAGER_ROLE
