"""The full eight-module curriculum."""
from __future__ import annotations

from functools import lru_cache

from .base import SKILLS, Exercise, Lesson, Module
from .modules_1_4 import module1, module2, module3, module4
from .modules_5_8 import module5, module6, module7, module8


@lru_cache(maxsize=1)
def modules() -> list[Module]:
    return [module1(), module2(), module3(), module4(), module5(), module6(), module7(), module8()]


def module_by_id(mid: str) -> Module:
    return next(m for m in modules() if m.id == mid)


def lesson_by_id(lid: str) -> Lesson:
    return next(l for m in modules() for l in m.lessons if l.id == lid)


def all_exercises() -> list[tuple[Module, Lesson, Exercise]]:
    return [(m, l, e) for m in modules() for l in m.lessons for e in l.exercises]


def exercises_by_id() -> dict[str, Exercise]:
    return {e.id: e for _, _, e in all_exercises()}


def module_of_lesson(lid: str) -> Module:
    return next(m for m in modules() for l in m.lessons if l.id == lid)
