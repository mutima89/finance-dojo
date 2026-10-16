import pytest

from fts.core.checker import Mistake, check_numeric, format_value, parse_number


@pytest.mark.parametrize("text,unit,expected", [
    ("1,234.5", "number", 1234.5), ("$1,234", "currency", 1234), ("(500)", "currency", -500),
    ("75%", "percent", 0.75), ("75", "percent", 0.75), ("0.75", "percent", 0.75),
    ("1.2k", "currency", 1200), ("3.4m", "currency", 3_400_000), ("-2.5", "number", -2.5),
    ("12%", "number", 0.12),
])
def test_parse(text, unit, expected):
    assert parse_number(text, unit) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["", "abc", "12..3", None, "$"])
def test_parse_invalid(text):
    assert parse_number(text) is None


def test_equivalent_answers_accepted():
    for t in ("75%", "75.0", "0.75", "75.04%"):
        assert check_numeric(t, 0.75, "percent").correct
    assert check_numeric("300", 300.004, "currency").correct
    assert check_numeric("$224.99", 225.0, "currency").correct


def test_wrong_and_invalid():
    r = check_numeric("hello", 1.0)
    assert r.status == "invalid"
    r = check_numeric("200", 225, "currency")
    assert r.status == "incorrect" and "too low" in r.diagnosis


def test_known_mistake_diagnosed():
    mk = [Mistake(0.6667, "You divided by sold rooms instead of available rooms.")]
    r = check_numeric("66.67%", 0.75, "percent", mistakes=mk)
    assert r.diagnosis.startswith("You divided")


def test_sign_and_scale_diagnosis():
    assert "sign" in check_numeric("-500", 500, "currency").diagnosis
    assert "1,000x" in check_numeric("500000", 500, "currency").diagnosis


def test_format():
    assert format_value(0.7543, "percent") == "75.4%"
    assert format_value(-1234.5, "currency") == "-$1,234.50"
    assert format_value(None) == "n/a"
