"""Curriculum integrity and independent checks of exercise answers."""
import math

import pytest

from fts.content import capstone, curriculum, reference
from fts.content.base import SKILLS
from fts.core.checker import check_numeric, format_value


def test_eight_modules_complete():
    mods = curriculum.modules()
    assert [m.number for m in mods] == list(range(1, 9))
    ids = set()
    for m in mods:
        assert m.lessons
        for l in m.lessons:
            assert l.concept.strip() and l.worked_example.strip() and l.interpretation.strip()
            assert l.guided.steps, l.id
            assert l.independent, l.id
            assert len(l.quiz) >= 3
            assert l.task.prompt and l.task.checklist
            for e in l.exercises:
                assert e.id not in ids
                ids.add(e.id)
                assert e.hints and e.solution and e.skill in SKILLS, e.id
                if e.unit == "choice":
                    assert 0 <= e.expected < len(e.choices)
                else:
                    assert isinstance(e.expected, (int, float)) and math.isfinite(e.expected), e.id
            for q in l.quiz:
                assert 0 <= q.answer < len(q.options) and q.skill in SKILLS


def test_expected_answers_accepted_when_typed_as_displayed():
    """The answer key as displayed (rounded) must be accepted by the checker."""
    for _, _, e in curriculum.all_exercises():
        if e.unit == "choice":
            continue
        shown = format_value(float(e.expected), e.unit, 2)
        r = check_numeric(shown, float(e.expected), e.unit, e.abs_tol, e.rel_tol)
        assert r.correct, (e.id, shown, e.expected)


def test_every_skill_is_taught():
    taught = {e.skill for _, _, e in curriculum.all_exercises()}
    assert set(SKILLS) == taught


# Independent hand calculations of selected answers
HAND = {
    "m1l1_i2": 185_000,                      # 800 - 260 - 310 - 45 (thousands)
    "m1l2_i2": 47,                           # 42 + 35 - 30
    "m2l1_i1": 37_700,                       # 18,500 + 19,200
    "m2l2_g": 373.10,                        # 0.82 x 455
    "m2l2_i2": 28,                           # Feb 2025 has 28 days
    "m2l2_i3": -360.0,
    "m4l1_i2": 76_200,                       # 42,000 + 9.5 x 3,600
    "m4l2_g": 238_070,                       # 57 x 3,950 + 340 x 38
    "m4l2_i2": 0.24,                         # 250k -> 190k
    "m6l1_g": 100_800,                       # (68 - 26) x 2,400
    "m6l1_i1": 80_280,                       # (54.40 - 26) x 2,950 - 3,500
    "m6l1_i2": 42 / 28.4 - 1,                # 47.89%
    "m6l2_g": 9_800 / 83,                    # 118.07 trips
    "m6l2_i1": 3_480,                        # 83 x 160 - 9,800
    "m6l2_i2": 3 + 310_000 / 350_000,        # 3.886 years
    "m6l2_i3": 330_000 / 800_000,            # 41.25%
    "m7l1_g": 100_000 / 1.09 ** 3,           # 77,218.35
    "m7l2_g": 54_750 * (0.775 * 340 - 0.76 * 318) * 0.70,   # 836,251.50
}


@pytest.mark.parametrize("eid,value", HAND.items())
def test_hand_calculated(eid, value):
    e = curriculum.exercises_by_id()[eid]
    assert e.expected == pytest.approx(value, rel=1e-9, abs=1e-6)


def test_npv_exercise_by_hand():
    e = curriculum.exercises_by_id()["m7l1_i1"]
    cf = [-1_200_000, 260_000, 300_000, 330_000, 350_000, 360_000]
    hand = sum(c / 1.09 ** t for t, c in enumerate(cf))
    assert e.expected == pytest.approx(hand)


def test_reference_content():
    assert len(reference.GLOSSARY) >= 40
    assert len(reference.FORMULAS) >= 20
    assert len(reference.COMMON_MISTAKES) >= 15
    assert len(reference.INTERVIEW_QUESTIONS) >= 15


def test_capstone_total_is_100_and_scoring():
    steps = capstone.steps()
    assert len(steps) == 8
    assert sum(s.points for s in steps) == 100
    perfect = {}
    for s in steps:
        for it in s.items:
            if it.kind == "numeric":
                perfect[it.id] = format_value(float(it.expected), it.unit, 2)
            elif it.kind == "choice":
                perfect[it.id] = it.expected
            elif it.kind == "kpis":
                perfect[it.id] = list(capstone.ESSENTIAL_KPIS)
            elif it.kind == "export":
                perfect[it.id] = True
    words = ("We recommend approving the renovation pilot and a corporate recovery plan because Q4 room revenue was "
             "8% below budget ($553,989 in Sep-Dec, about 1,400 fewer room nights). Our assumption is that pickup "
             "follows last year; the main risk is weaker corporate demand. ")
    perfect["c3_text"] = words
    perfect["c4_text"] = words
    perfect["c7_text"] = (words * 4)
    assert len(words.split()) >= 40 and 150 <= len((words * 4).split()) <= 450
    res = capstone.score_all(perfect)
    assert res["total"] == pytest.approx(100) and res["passed"]
    assert capstone.score_all({})["total"] == 0


def test_capstone_irrelevant_kpis_penalised():
    it = next(i for s in capstone.steps() for i in s.items if i.kind == "kpis")
    good, _ = capstone.score_item(it, list(capstone.ESSENTIAL_KPIS))
    bad, _ = capstone.score_item(it, list(capstone.ESSENTIAL_KPIS) + ["Share price"])
    assert bad < good


def test_capstone_cleaning_answers():
    items = {i.id: i for s in capstone.steps() for i in s.items}
    assert items["c1_missing"].choices[items["c1_missing"].expected] == "Mar"
    assert items["c1_thousands"].choices[items["c1_thousands"].expected] == "Aug"
    assert items["c1_impossible"].choices[items["c1_impossible"].expected] == "Oct"
