"""Motivation layer: XP, dojo belts, a forgiving streak and a daily goal.

None of this changes how answers are checked or how skill levels (mastery) are
decided. XP and belts are just for fun and momentum inside the app: they are
not a qualification.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, Optional

# ----------------------------------------------------------------- XP rules
QUIZ_XP_PER_CORRECT = 5
TASK_XP = 25
LESSON_XP = 50
QUEST_XP = 15
PRACTICE_XP = 5
PRACTICE_DAILY_CAP = 10        # practice challenges that earn XP per day
FOCUS_XP = 10
FOCUS_DAILY_CAP = 6            # focus sessions that earn XP per day
DAILY_GOAL_BONUS = 20
BOSS_XP = 100                  # once per chapter boss in Career Mode
DAILY_GOAL_CHOICES = (30, 50, 100)
DEFAULT_DAILY_GOAL = 50
FOCUS_CHOICES = (5, 10, 15, 25)
DEFAULT_FOCUS_MINUTES = 10


def exercise_xp(solved_on: Optional[int], hints_used: int = 0, revealed: bool = False) -> int:
    """XP for a solved exercise. A revealed solution earns nothing, as in mastery."""
    if revealed or not solved_on:
        return 0
    if solved_on == 1:
        return 15 if hints_used else 20
    if solved_on == 2:
        return 12
    return 8


def quiz_xp(new_score: int, previous_best: Optional[int]) -> int:
    """Only improvements earn XP, so retaking a quiz cannot farm points."""
    gain = new_score - (previous_best or 0)
    return max(0, gain) * QUIZ_XP_PER_CORRECT


# -------------------------------------------------------------------- belts
@dataclass(frozen=True)
class Belt:
    name: str
    min_xp: int
    color: str


BELTS = (
    Belt("White belt", 0, "#e8e8e8"),
    Belt("Yellow belt", 150, "#f2c94c"),
    Belt("Orange belt", 400, "#f2994a"),
    Belt("Green belt", 800, "#27ae60"),
    Belt("Blue belt", 1400, "#2f80ed"),
    Belt("Purple belt", 2200, "#9b51e0"),
    Belt("Brown belt", 3200, "#8d5a3b"),
    Belt("Black belt", 4500, "#222222"),
)

BELT_NOTE = "Belts and XP are for fun and momentum inside the app. They are not a qualification."


@dataclass(frozen=True)
class Rank:
    belt: Belt
    index: int
    xp: int
    next_belt: Optional[Belt]

    @property
    def into_level(self) -> int:
        return self.xp - self.belt.min_xp

    @property
    def level_span(self) -> Optional[int]:
        return None if self.next_belt is None else self.next_belt.min_xp - self.belt.min_xp

    @property
    def fraction(self) -> float:
        """Progress from this belt to the next (1.0 at black belt)."""
        span = self.level_span
        return 1.0 if not span else min(1.0, self.into_level / span)

    @property
    def to_next(self) -> int:
        return 0 if self.next_belt is None else self.next_belt.min_xp - self.xp


def rank(xp: int) -> Rank:
    xp = max(0, int(xp))
    idx = max(i for i, b in enumerate(BELTS) if xp >= b.min_xp)
    nxt = BELTS[idx + 1] if idx + 1 < len(BELTS) else None
    return Rank(BELTS[idx], idx, xp, nxt)


# ------------------------------------------------------------------- streak
@dataclass(frozen=True)
class Streak:
    days: int              # active days in the current run
    active_today: bool
    at_risk: bool          # the run survives only if you practise today


def streak(active_days: Iterable[dt.date], today: dt.date) -> Streak:
    """Count active days in the current run, forgiving one rest day at a time.

    A run continues across a single missed day (a rest day) but ends after two
    missed days in a row. Only active days are counted, so a rest day never adds
    to the total. Built to encourage, not to punish: XP and belts never reset.
    """
    days = {d for d in active_days if d <= today}
    if not days:
        return Streak(0, False, False)
    active_today = today in days
    one_ago, two_ago = today - dt.timedelta(days=1), today - dt.timedelta(days=2)
    if not (active_today or one_ago in days or two_ago in days):
        return Streak(0, False, False)
    count, gap, d = 0, 0, today
    while True:
        if d in days:
            count += 1
            gap = 0
        elif d != today:          # today not done yet is never a missed day
            gap += 1
            if gap >= 2:
                break
        d -= dt.timedelta(days=1)
        if d < min(days):
            break
    at_risk = not active_today and one_ago not in days
    return Streak(count, active_today, at_risk)


# --------------------------------------------------------------- daily goal
def goal_fraction(xp_today: int, goal: int) -> float:
    return 1.0 if goal <= 0 else min(1.0, xp_today / goal)


ENCOURAGE_WRONG = (
    "Mistakes are data. Look at the hint and go again.",
    "Close call. Every analyst checks their work twice.",
    "Not yet, and that's how learning feels. Try once more.",
    "Good try. Re-read the question slowly and spot the trap.",
)

CHEER_RIGHT = (
    "Nailed it!",
    "Sharp thinking!",
    "That's analyst-level work.",
    "Clean answer!",
    "You're on a roll!",
)


def pick(options: tuple[str, ...], seed: int) -> str:
    return options[seed % len(options)]


def best_streak(active_days: Iterable[dt.date]) -> int:
    """Longest run of active days ever, with the same one-rest-day rule as streak()."""
    days = sorted(set(active_days))
    best = run = 0
    prev = None
    for d in days:
        run = run + 1 if prev is not None and (d - prev).days <= 2 else 1
        best = max(best, run)
        prev = d
    return best
