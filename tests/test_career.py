"""Career Mode: boss answers re-worked by hand, ranks, stars and chapter unlocking."""
import pytest

from fts.content import career, curriculum
from fts.core.checker import check_numeric, format_value

# Every boss answer worked out by hand from the numbers in its story (not by the app's code).
HAND = {
    1: [180_000 - 54_000,                                   # gross profit
        (180_000 - 54_000 - 72_000 - 21_000) / 180_000,     # 33,000 / 180,000 = 18.33%
        198_000 - 59_400 - 72_000 - 21_000],                # 45,600
    2: [120 * 210 + 95 * 198 + 60 * 225,                    # 57,510
        (57_510 + 98_400 + 44_990) - 199_400,               # 1,500
        200_900 / 186_000 - 1],                             # 8.01%
    3: [3_510 / 4_500, 842_400 / 3_510, 842_400 / 4_500],   # 78%, 240, 187.20
    4: [3_800, 7_600 + 14 * 3_900, 62_200 - 61_800],        # 3,800 / 62,200 / 400
    5: [10_101, 10_101 * 232, 2_343_432 - 9_555 * 225],     # 13,650 x 74% = 10,101
    6: [160, 187 - 60, 160 / 127 - 1],                      # 25.98%
    7: [0.50, 400_000 / 120_000, 54_894.41],                # NPV: -400k + 120k x 3.790787
    8: [1_092_000 / 4_200_000, 1_092_000 / 975_000 - 1, 1_092_000 / 13_500],
}


def test_nine_chapters_one_per_module_plus_capstone():
    chs = career.chapters()
    assert [c.number for c in chs] == list(range(1, 10))
    assert all(c.boss for c in chs[:8]) and chs[8].boss is None
    assert chs[-1].rank == career.FINAL_RANK
    assert len({c.rank for c in chs}) == 9
    assert len(curriculum.modules()) == 8


@pytest.mark.parametrize("n", range(1, 9))
def test_boss_answers_match_hand_calculation(n):
    boss = career.chapters()[n - 1].boss
    assert len(boss.steps) == 3
    for step, hand in zip(boss.steps, HAND[n]):
        assert step.expected == pytest.approx(hand, rel=1e-4, abs=0.01), (boss.name, step.question)


@pytest.mark.parametrize("n", range(1, 9))
def test_displayed_answer_is_accepted_and_a_wrong_one_is_not(n):
    for step in career.chapters()[n - 1].boss.steps:
        shown = format_value(step.expected, step.unit, 2)
        assert check_numeric(shown, step.expected, step.unit, step.abs_tol).correct, shown
        wrong = format_value(step.expected * 1.2 + 1, step.unit, 2)
        assert not check_numeric(wrong, step.expected, step.unit, step.abs_tol).correct, wrong
        assert step.hint and step.solution and step.question.endswith("?")


def test_ranks_and_stars():
    assert career.rank_for(0) == career.START_RANK == "Intern"
    assert career.rank_for(1) == "Junior Analyst"
    assert career.rank_for(9) == career.rank_for(50) == "Finance Director"
    assert [career.stars_for(h) for h in (3, 2, 1, 0)] == [3, 2, 1, 0]
    assert "not job titles or qualifications" in career.RANK_NOTE


def test_progress_unlocks_in_order(tmp_path):
    from fts.storage.db import Progress
    from fts.ui.screens.career import career_progress, chapters_done, current_rank
    db = Progress(tmp_path / "p.sqlite3")
    st = career_progress(db)
    assert st[0].unlocked and not any(s.unlocked for s in st[1:])
    assert not st[0].boss_ready                      # lessons first
    db.set_meta("boss:2", "3")                       # beating chapter 2 out of order unlocks nothing yet
    st = career_progress(db)
    assert chapters_done(st) == 0 and not st[2].unlocked
    db.set_meta("boss:1", "2")
    st = career_progress(db)
    assert chapters_done(st) == 2 and st[2].unlocked and not st[3].unlocked
    assert current_rank(db) == "Analyst"
    db.reset()
    assert chapters_done(career_progress(db)) == 0
    db.close()
