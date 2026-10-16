"""Mastery scoring. Transparent rules, documented in the app and README.

Per skill:
  exercise score  = average over ALL exercises of that skill of
                    1.00 solved first try without hints
                    0.85 solved first try after hints
                    0.70 solved on attempt 2
                    0.50 solved on attempt 3 or later
                    0.00 not attempted, unsolved, or solution revealed
  quiz score      = share of that skill's quiz questions answered correctly
                    (latest answer; unanswered counts as wrong)
  workbook score  = share of the 16 Excel workbook tasks correct (Excel skill only)

  skill score = 60% exercises + 40% quiz
                (Excel formulas: 40% exercises + 20% quiz + 40% workbook)

Levels: Beginner < 40 <= Developing < 70 <= Competent.
"Job-ready for supervised tasks" additionally requires: score >= 85, every
PRACTICAL exercise of the skill solved without revealing the solution,
every practical task of lessons teaching the skill saved, AND the capstone
passed. Quiz scores alone can never reach it.
"""
from __future__ import annotations

from dataclasses import dataclass

LEVELS = ["Beginner", "Developing", "Competent", "Job-ready for supervised tasks"]


def exercise_credit(st: dict | None) -> float:
    if not st or not st.get("solved") or st.get("revealed"):
        return 0.0      # unsolved, or solved only after the solution was shown
    n = st.get("solved_on") or 99
    if n == 1:
        return 1.0 if not st.get("hints_used") else 0.85
    if n == 2:
        return 0.70
    return 0.50


@dataclass
class SkillResult:
    skill: str
    score: float
    level: str
    exercise_score: float
    quiz_score: float
    workbook_score: float | None
    attempted: int
    total: int
    practical_done: bool
    weak: bool
    reason: str


def skill_results(modules, ex_status: dict, quiz_answers: list[dict], tasks: dict,
                  workbook: dict, capstone_passed: bool, skills: list[str]) -> list[SkillResult]:
    out = []
    for skill in skills:
        exs = [(l, e) for m in modules for l in m.lessons for e in l.exercises if e.skill == skill]
        credits = [exercise_credit(ex_status.get(e.id)) for _, e in exs]
        ex_score = sum(credits) / len(credits) if credits else 0.0
        qs = [q for m in modules for l in m.lessons for q in l.quiz if q.skill == skill]
        answered = {(a["question_id"]): a["correct"] for a in quiz_answers}
        quiz_score = (sum(answered.get(q.id, 0) for q in qs) / len(qs)) if qs else 0.0
        wb = None
        if skill == "Excel formulas":
            wb = sum(1 for s in workbook.values() if s == "correct") / 16
            score = 100 * (0.4 * ex_score + 0.2 * quiz_score + 0.4 * wb)
        else:
            score = 100 * (0.6 * ex_score + 0.4 * quiz_score)
        practical_ok = all(ex_status.get(e.id, {}).get("solved") and not ex_status.get(e.id, {}).get("revealed")
                           for _, e in exs if e.practical)
        lessons = {l.id: l for l, _ in exs}
        tasks_ok = all((tasks.get(l.task.id) or {}).get("content", "").strip() for l in lessons.values())
        attempted = sum(1 for _, e in exs if ex_status.get(e.id, {}).get("attempts"))
        if score >= 85 and practical_ok and tasks_ok and capstone_passed:
            level, reason = LEVELS[3], "All requirements met, including the capstone."
        elif score >= 70:
            level = LEVELS[2]
            missing = []
            if score < 85:
                missing.append("score 85+")
            if not practical_ok:
                missing.append("all practical exercises solved without revealing")
            if not tasks_ok:
                missing.append("practical tasks saved")
            if not capstone_passed:
                missing.append("capstone passed")
            reason = "For job-ready you still need: " + ", ".join(missing) + "."
        elif score >= 40:
            level, reason = LEVELS[1], "Keep practising: aim for first-try correct answers and full quiz scores."
        else:
            level, reason = LEVELS[0], "Start or continue the lessons for this skill."
        wrong_heavy = any(ex_status.get(e.id, {}).get("wrong", 0) >= 3 for _, e in exs)
        weak = attempted > 0 and (score < 60 or wrong_heavy)
        out.append(SkillResult(skill, round(score, 1), level, ex_score, quiz_score, wb, attempted, len(exs),
                               practical_ok and tasks_ok, weak, reason))
    return out


def hints_allowed(total_hints: int, level: str, guided: bool) -> int:
    """Assistance fades as mastery grows (guided practice always keeps full help)."""
    if guided or level == LEVELS[0]:
        return total_hints
    if level == LEVELS[1]:
        return max(1, total_hints - 1)
    return 1


def lesson_complete(lesson, ex_status: dict, best_quiz, task: dict | None) -> bool:
    ex_done = all(ex_status.get(e.id, {}).get("solved") or ex_status.get(e.id, {}).get("revealed")
                  for e in lesson.exercises)
    return bool(ex_done and best_quiz is not None and task and (task.get("content") or "").strip())


def lesson_progress_fraction(lesson, ex_status: dict, best_quiz, task: dict | None) -> float:
    parts = [bool(ex_status.get(e.id, {}).get("solved") or ex_status.get(e.id, {}).get("revealed"))
             for e in lesson.exercises]
    parts.append(best_quiz is not None)
    parts.append(bool(task and (task.get("content") or "").strip()))
    return sum(parts) / len(parts)
