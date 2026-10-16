"""Badges: small milestones that make progress visible.

Badges are worked out from what is already saved (XP, exercises, quizzes,
tasks, the capstone). They never give XP and never change skill levels, so
they can't be farmed and they don't affect how answers are checked.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from . import gamify


@dataclass(frozen=True)
class Badge:
    id: str
    emoji: str
    name: str
    desc: str
    stat: str        # key in the stats dict
    need: int        # unlocked when stats[stat] >= need


BADGES = (
    Badge("first_steps", "👣", "First steps", "Earn your first XP.", "xp", 1),
    Badge("first_lesson", "📘", "Lesson one", "Finish a whole lesson.", "lessons", 1),
    Badge("quiz_ace", "🧠", "Quiz ace", "Score full marks on a quiz.", "perfect_quizzes", 1),
    Badge("sharpshooter", "🎯", "Sharpshooter", "Solve 5 exercises on the first try.", "first_try", 5),
    Badge("hands_on", "🛠", "Hands-on", "Save 3 practical tasks.", "tasks", 3),
    Badge("in_the_zone", "⏱", "In the zone", "Finish a focus session.", "focus", 1),
    Badge("goal_getter", "✅", "Goal getter", "Hit your daily XP goal.", "goal_days", 1),
    Badge("quest_sweep", "🎲", "Quest sweep", "Solve all 3 daily quests in one day.", "quests_best_day", 3),
    Badge("on_fire", "🔥", "On fire", "Reach a 3-day streak.", "best_streak", 3),
    Badge("explorer", "🗺", "Explorer", "Solve 10 daily quests.", "quests", 10),
    Badge("halfway", "🧭", "Halfway there", "Finish 8 lessons.", "lessons", 8),
    Badge("week_warrior", "🌟", "Week warrior", "Reach a 7-day streak.", "best_streak", 7),
    Badge("green_belt", "🥋", "Green belt", "Reach the green belt.", "belt", 3),
    Badge("deep_worker", "🧘", "Deep worker", "Finish 10 focus sessions.", "focus", 10),
    Badge("course_complete", "🎓", "All lessons done", "Finish all 16 lessons.", "lessons", 16),
    Badge("capstone", "🏆", "Capstone passed", "Pass the capstone project (70+).", "capstone", 1),
)

BADGE_NOTE = "Badges are for fun and momentum. They are not a qualification."


def unlocked(stats: dict) -> list[Badge]:
    return [b for b in BADGES if stats.get(b.stat, 0) >= b.need]


def next_badges(stats: dict, n: int = 3) -> list[tuple[Badge, int]]:
    """The locked badges closest to unlocking, as (badge, progress so far)."""
    locked = [(b, min(stats.get(b.stat, 0), b.need)) for b in BADGES if stats.get(b.stat, 0) < b.need]
    locked.sort(key=lambda t: (-(t[1] / t[0].need), t[0].need))
    return locked[:n]


def collect_stats(db, lessons, today: dt.date | None = None) -> dict:
    """Gather the numbers the badges look at. `lessons` is every curriculum lesson."""
    status = db.all_exercise_status()
    perfect = 0
    for l in lessons:
        best = db.best_quiz(l.id)
        if best and best[1] and best[0] == best[1]:
            perfect += 1
    best_cap = db.best_capstone()
    xp = db.xp_total()
    return dict(
        xp=xp,
        belt=gamify.rank(xp).index,
        lessons=db.xp_count("lesson"),
        tasks=db.xp_count("task"),
        focus=db.xp_count("focus"),
        goal_days=db.xp_count("goal"),
        quests=db.xp_count("quest"),
        quests_best_day=db.xp_max_per_day("quest"),
        perfect_quizzes=perfect,
        first_try=sum(1 for s in status.values() if s.get("solved_on") == 1 and not s.get("revealed")),
        best_streak=gamify.best_streak(db.active_days()),
        capstone=1 if best_cap and best_cap["passed"] else 0,
    )
