import datetime as dt

import pytest

from fts.excel.formula_engine import Engine, ExcelError, functions_used, has_absolute_ref, shift_formula


@pytest.fixture
def eng():
    data = {
        "A1": "Date", "B1": "Type", "C1": "Sold", "D1": "Revenue", "F1": 150,
        "A2": dt.date(2025, 1, 3), "B2": "Weekend", "C2": 120, "D2": 36000,
        "A3": dt.date(2025, 1, 4), "B3": "Weekend", "C3": 130, "D3": 40300,
        "A4": dt.date(2025, 1, 6), "B4": "Weekday", "C4": 100, "D4": 28000,
        "A5": dt.date(2025, 1, 7), "B5": "Weekday", "C5": 0, "D5": 0,
        "E2": "=D2/C2", "E3": "=E2*2",
    }
    lookup = {"A1": "Month", "B1": "Budget", "A2": "Jan", "B2": 1000, "A3": "Feb", "B3": 1200}
    return Engine({"Data": data, "Budget Sheet": lookup}, "Data")


def ev(eng, f):
    return eng.evaluate(f)


def test_arithmetic(eng):
    assert ev(eng, "=1+2*3") == 7
    assert ev(eng, "=(1+2)*3") == 9
    assert ev(eng, "=2^3") == 8
    assert ev(eng, "=-C2+10") == -110
    assert ev(eng, "=50%") == 0.5
    assert ev(eng, "=C2/F1") == pytest.approx(0.8)
    assert ev(eng, "=E3") == pytest.approx(600)          # chained formulas


def test_errors(eng):
    assert ev(eng, "=D5/C5") == ExcelError("#DIV/0!")
    assert ev(eng, "=IFERROR(D5/C5,0)") == 0
    assert ev(eng, "=B2+1") == ExcelError("#VALUE!")
    assert ev(eng, "=FOO(1)") == ExcelError("#NAME?")
    assert ev(eng, "=SUM(C2:C5") == ExcelError("#NAME?")
    assert ev(eng, "=Nope!A1") == ExcelError("#REF!")


def test_sum_and_stats(eng):
    assert ev(eng, "=SUM(C2:C5)") == 350
    assert ev(eng, "=SUM(C:C)") == 350                    # header text ignored
    assert ev(eng, "=AVERAGE(C2:C5)") == 87.5
    assert ev(eng, "=MAX(C2:C5)") == 130 and ev(eng, "=MIN(C2:C5)") == 0
    assert ev(eng, "=COUNT(A1:D5)") == 12                 # 4 dates + 8 numbers
    assert ev(eng, "=MEDIAN(C2:C5)") == 110
    assert ev(eng, "=ROUND(2.675,2)") == 2.68
    assert ev(eng, "=STDEV.S(C2:C4)") == pytest.approx(15.2752523)


def test_conditional(eng):
    assert ev(eng, '=SUMIFS(D2:D5,B2:B5,"Weekend")') == 76300
    assert ev(eng, '=SUMIFS(D2:D5,B2:B5,"Week*",C2:C5,">=120")') == 76300
    assert ev(eng, '=COUNTIFS(C2:C5,">0")') == 3
    assert ev(eng, '=SUMIF(B2:B5,"<>Weekend",C2:C5)') == 100
    assert ev(eng, '=AVERAGEIFS(C2:C5,B2:B5,"Weekday")') == 50
    assert ev(eng, '=IF(C2>100,"High","Low")') == "High"
    assert ev(eng, '=IF(AND(C2>100,B2="weekend"),1,0)') == 1


def test_lookups(eng):
    assert ev(eng, "=XLOOKUP(\"Feb\",'Budget Sheet'!A2:A3,'Budget Sheet'!B2:B3)") == 1200
    assert ev(eng, "=XLOOKUP(\"Mar\",'Budget Sheet'!A2:A3,'Budget Sheet'!B2:B3,\"none\")") == "none"
    assert ev(eng, "=INDEX('Budget Sheet'!B2:B3,MATCH(\"Jan\",'Budget Sheet'!A2:A3,0))") == 1000
    assert ev(eng, "=VLOOKUP(\"Feb\",'Budget Sheet'!A2:B3,2,FALSE)") == 1200
    assert ev(eng, "=MATCH(\"Mar\",'Budget Sheet'!A2:A3,0)") == ExcelError("#N/A")


def test_dates(eng):
    assert ev(eng, "=YEAR(A2)") == 2025 and ev(eng, "=MONTH(A2)") == 1
    assert ev(eng, "=WEEKDAY(A2,2)") == 5                 # 3 Jan 2025 is a Friday
    assert ev(eng, "=DAY(EOMONTH(A2,1))") == 28
    assert ev(eng, "=DATE(2025,1,3)=A2") is True
    assert ev(eng, "=A3-A2") == 1


def test_finance_functions(eng):
    assert ev(eng, "=-1000+NPV(10%,500,500,500)") == pytest.approx(243.4259955)
    eng.set_cell("Data", "H1", -1000)
    eng.set_cell("Data", "H2", 500)
    eng.set_cell("Data", "H3", 500)
    eng.set_cell("Data", "H4", 500)
    assert ev(eng, "=IRR(H1:H4)") == pytest.approx(0.233752, abs=1e-6)
    assert ev(eng, "=PMT(0.05/12,60,10000)") == pytest.approx(-188.712336, abs=1e-5)


def test_shift_formula():
    assert shift_formula("=C2/$F$1", 1, 0) == "=C3/$F$1"
    assert shift_formula("=C2/F1", 2, 0) == "=C4/F3"
    assert shift_formula("=SUM($C2:C$5)", 1, 1) == "=SUM($C3:D$5)"
    assert shift_formula("='Budget Sheet'!B2*2", 1, 0) == "='Budget Sheet'!B3*2"
    assert shift_formula('=IF(A1="B2",1,0)', 1, 0) == '=IF(A2="B2",1,0)'   # text untouched


def test_relative_vs_absolute_when_copied(eng):
    good, bad = "=C2/$F$1", "=C2/F1"
    vals_good = [eng.evaluate(shift_formula(good, i, 0)) for i in range(3)]
    vals_bad = [eng.evaluate(shift_formula(bad, i, 0)) for i in range(3)]
    assert vals_good == [pytest.approx(x) for x in (0.8, 130 / 150, 100 / 150)]
    assert isinstance(vals_bad[1], ExcelError)            # F2 is empty -> #DIV/0!


def test_helpers():
    assert functions_used("=IFERROR(SUMIFS(A:A,B:B,\"x\"),0)") == {"IFERROR", "SUMIFS"}
    assert functions_used("=_xlfn.XLOOKUP(1,A1:A2,B1:B2)") == {"XLOOKUP"}
    assert has_absolute_ref("=A1*$B$1") and not has_absolute_ref("=A1*B1")


def test_circular():
    e = Engine({"S": {"A1": "=B1", "B1": "=A1"}})
    assert isinstance(e.evaluate("=A1"), ExcelError)
