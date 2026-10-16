"""Data structures for curriculum content."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..core.checker import Mistake


@dataclass
class Exercise:
    id: str
    prompt: str
    expected: float | int | str
    unit: str = "number"                   # number, currency, percent, years, choice
    hints: list[str] = field(default_factory=list)
    mistakes: list[Mistake] = field(default_factory=list)
    solution: str = ""
    skill: str = ""
    steps: list[str] = field(default_factory=list)   # scaffolding for guided practice
    choices: list[str] = field(default_factory=list)  # for unit == "choice"
    abs_tol: Optional[float] = None
    rel_tol: Optional[float] = None
    practical: bool = False                # counts as a practical modelling task for mastery


@dataclass
class QuizQuestion:
    id: str
    question: str
    options: list[str]
    answer: int
    explanation: str
    skill: str = ""


@dataclass
class PracticalTask:
    id: str
    title: str
    prompt: str
    template: str
    checklist: list[str]
    tool: Optional[str] = None             # screen that helps, e.g. "rm_simulator"


@dataclass
class Lesson:
    id: str
    title: str
    concept: str                           # markdown
    worked_example: str                    # markdown
    guided: Exercise
    independent: list[Exercise]
    interpretation: str                    # markdown
    quiz: list[QuizQuestion]
    task: PracticalTask
    minutes: int = 25

    @property
    def exercises(self) -> list[Exercise]:
        return [self.guided] + list(self.independent)


@dataclass
class Module:
    id: str
    number: int
    title: str
    summary: str
    skills: list[str]
    lessons: list[Lesson]
    tools: list[str] = field(default_factory=list)

    @property
    def exercises(self) -> list[Exercise]:
        return [e for l in self.lessons for e in l.exercises]


SKILLS = [
    "Financial statements",
    "Cost behaviour & break-even",
    "Excel formulas",
    "Hotel KPIs",
    "Revenue management decisions",
    "Budgeting & variance analysis",
    "Forecasting & modelling",
    "Commercial analysis",
    "Investment appraisal",
    "Management reporting",
]
