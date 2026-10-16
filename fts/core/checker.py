"""Answer checking: parse what the student typed, compare with the expected
value within a tolerance, and diagnose the most likely mistake."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Mistake:
    """A known wrong answer and why students typically arrive at it."""
    value: float
    explanation: str


@dataclass
class CheckResult:
    status: str                  # "correct", "incorrect", "invalid"
    message: str
    parsed: Optional[float] = None
    diagnosis: Optional[str] = None

    @property
    def correct(self) -> bool:
        return self.status == "correct"


_NUM_RE = re.compile(r"^[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$")


def parse_number(text: str, unit: str = "number") -> Optional[float]:
    """Parse '1,234.5', '$1,234', '(500)', '75%', '1.2k', '3.4m'.

    For unit == 'percent' the value is returned as a decimal and both '75%'
    and '75' and '0.75' are understood as 75% (a bare number greater than 1
    is read as a percentage, a bare number of 1 or less as a decimal).
    Returns None if the text cannot be read as a number.
    """
    if text is None:
        return None
    s = str(text).strip().lower().replace(",", "").replace(" ", "")
    for word in ("years", "year", "yrs", "days", "rooms", "trips", "guests", "covers"):
        if s.endswith(word):
            s = s[: -len(word)]
    for sym in ("$", "€", "£", "usd", "eur", "x"):
        s = s.replace(sym, "")
    if not s:
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative, s = True, s[1:-1]
    has_pct = s.endswith("%")
    if has_pct:
        s = s[:-1]
    mult = 1.0
    if s and s[-1] in "km" and _NUM_RE.match(s[:-1] or "x"):
        mult = 1_000.0 if s[-1] == "k" else 1_000_000.0
        s = s[:-1]
    if not _NUM_RE.match(s):
        return None
    v = float(s) * mult
    if negative:
        v = -v
    if unit == "percent":
        if has_pct or abs(v) > 1.0:
            v = v / 100.0
    elif has_pct:
        v = v / 100.0
    return v


def format_value(v: Optional[float], unit: str = "number", decimals: int = 2) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    if unit == "percent":
        return f"{v * 100:,.{max(decimals - 1, 1)}f}%"
    if unit == "currency":
        sign = "-" if v < 0 else ""
        return f"{sign}${abs(v):,.{decimals}f}"
    if unit == "years":
        return f"{v:,.{decimals}f} years"
    return f"{v:,.{decimals}f}"


def within_tolerance(got: float, expected: float, abs_tol: float, rel_tol: float) -> bool:
    return abs(got - expected) <= max(abs_tol, rel_tol * abs(expected))


def default_tolerance(unit: str, expected: float) -> tuple[float, float]:
    """Sensible tolerances: allow normal rounding by the student."""
    if unit == "percent":
        return 0.0006, 0.0          # +/- 0.06 percentage points
    if unit == "currency":
        return 0.6, 0.0005          # rounding to whole dollars, or 0.05%
    if unit == "years":
        return 0.06, 0.0
    return 0.01, 0.0005


def check_numeric(text: str, expected: float, unit: str = "number",
                  abs_tol: float | None = None, rel_tol: float | None = None,
                  mistakes: list[Mistake] | None = None) -> CheckResult:
    got = parse_number(text, unit)
    if got is None:
        return CheckResult("invalid",
                           "That doesn't look like a number. Type digits only, e.g. "
                           + ("75.4%" if unit == "percent" else "1234.56")
                           + ". Commas, $ and % are fine.")
    d_abs, d_rel = default_tolerance(unit, expected)
    abs_tol = d_abs if abs_tol is None else abs_tol
    rel_tol = d_rel if rel_tol is None else rel_tol
    if within_tolerance(got, expected, abs_tol, rel_tol):
        return CheckResult("correct", "Correct.", got)

    diagnosis = diagnose(got, expected, unit, mistakes or [], abs_tol, rel_tol)
    return CheckResult("incorrect", "Not quite.", got, diagnosis)


def diagnose(got: float, expected: float, unit: str, mistakes: list[Mistake],
             abs_tol: float, rel_tol: float) -> str:
    """Explain the most likely cause of a wrong answer."""
    loose_abs, loose_rel = abs_tol * 3, max(rel_tol * 3, 0.002)
    for mk in mistakes:
        if mk.value is not None and within_tolerance(got, mk.value, loose_abs, loose_rel):
            return mk.explanation
    if expected != 0:
        if within_tolerance(-got, expected, abs_tol, rel_tol):
            return ("The size is right but the sign is wrong. Check the order of the "
                    "subtraction (Actual - Budget) or whether a cash outflow should be negative.")
        ratio = got / expected
        for f, msg in ((100, "Your answer is 100x too large. A percentage was probably typed as a "
                             "whole number where a decimal was expected, or vice versa."),
                       (0.01, "Your answer is 100x too small. Check whether you converted to a "
                              "percentage (multiply a decimal by 100)."),
                       (1000, "Your answer is 1,000x too large. Check the units (thousands vs units)."),
                       (0.001, "Your answer is 1,000x too small. Check the units (thousands vs units).")):
            if abs(ratio - f) <= 0.01 * f:
                return msg
        if abs(got - expected) <= max(abs(expected) * 0.02, 0.01 if unit != "currency" else 2):
            return ("Very close. This is probably a rounding difference: keep full precision in "
                    "intermediate steps and round only the final answer.")
    direction = "high" if got > expected else "low"
    return (f"Your answer is too {direction}. Re-read which numbers go in the numerator and "
            "denominator, and check that you used the right period.")


def check_choice(selected: Optional[int], correct_index: int) -> bool:
    return selected is not None and selected == correct_index
