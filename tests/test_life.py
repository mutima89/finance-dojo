"""Real-life quests: every answer is re-worked by hand here, independently of
fts.core.metrics, across many generated variants."""
import datetime as dt
import math
import random
import re

import pytest

from fts.content import curriculum, life
from fts.core.checker import check_numeric, format_value

NUM = r"\$?([\d,]+(?:\.\d+)?)"


def nums(text):
    return [float(x.replace(",", "")) for x in re.findall(r"(?<![\w.])\$?(\d[\d,]*(?:\.\d+)?)", text)]


def hand(ch):
    """Recompute the expected answer from the numbers printed in the story."""
    n = nums(ch.story)
    if ch.id == "coffee_cart":
        fixed, price, var = n
        return math.ceil(fixed / (price - var))
    if ch.id == "gym_per_visit":
        return n[0] / n[1]
    if ch.id == "cinema_occupancy":
        seats, shows, sold = n
        return sold / (seats * shows)
    if ch.id == "restaurant_revpat":
        tables, turns, rev = n
        return rev / (tables * turns)
    if ch.id == "grocery_variance":
        budget, actual = n
        return actual - budget
    if ch.id == "phone_bill":
        old, new = n
        return (new - old) / old
    if ch.id == "savings_goal":
        pv, rate, years = n
        return pv * (1 + rate / 100) ** years
    if ch.id == "side_hustle_npv":
        cost, inflow, _years, rate = n
        r = rate / 100
        return -cost + sum(inflow / (1 + r) ** t for t in (1, 2, 3))
    if ch.id == "solar_payback":
        cost, saving = n
        return cost / saving
    if ch.id == "pizza_discount":
        price, var, disc = n
        new = price * (1 - disc / 100)
        return (price - var) / (new - var) - 1
    if ch.id == "lemonade_margin":
        price, var = n
        return (price - var) / price
    if ch.id == "followers_cagr":
        start, end, years = n
        return (end / start) ** (1 / years) - 1
    if ch.id == "grade_average":
        q, wq, p, wp, e, we = n
        return (q * wq + p * wp + e * we) / 100
    raise AssertionError(f"no hand calculation for {ch.id}")


@pytest.mark.parametrize("template", life.TEMPLATES, ids=lambda t: t.__name__)
def test_answers_match_hand_calculation(template):
    for seed in range(40):
        ch = template(random.Random(seed))
        assert ch.expected == pytest.approx(hand(ch), rel=1e-9, abs=1e-9), (ch.id, ch.story)


@pytest.mark.parametrize("template", life.TEMPLATES, ids=lambda t: t.__name__)
def test_displayed_answer_is_accepted_and_lessons_exist(template):
    lesson_ids = {l.id for m in curriculum.modules() for l in m.lessons}
    for seed in range(20):
        ch = template(random.Random(seed))
        shown = format_value(ch.expected, ch.unit, 2)
        assert check_numeric(shown, ch.expected, ch.unit, ch.abs_tol).correct, (ch.id, shown)
        assert ch.lesson_id in lesson_ids
        assert ch.story and ch.question and ch.hint and ch.solution and ch.work_link


def test_daily_quests_are_stable_and_varied():
    day = dt.date(2026, 10, 16)
    a, b = life.daily_quests(day), life.daily_quests(day)
    assert [c.story for c in a] == [c.story for c in b]                 # same all day
    assert len({c.id for c in a}) == life.QUESTS_PER_DAY                # three different kinds
    week = {c.id for i in range(7) for c in life.daily_quests(day + dt.timedelta(days=i))}
    assert len(week) >= 8                                               # variety across a week
    assert life.practice_challenge(day, 0).story == life.practice_challenge(day, 0).story


def test_every_lesson_has_a_key_idea_and_real_life_hook():
    for m in curriculum.modules():
        for l in m.lessons:
            key, everyday = life.LESSON_HOOKS[l.id]
            assert len(key) > 30 and len(everyday) > 30
