"""The bundled files must be exactly what the code generates (no hand edits, no drift)."""
import json
from pathlib import Path

import pandas as pd
import pytest

from fts.data import generator as gen
from fts.excel import workbook as wbk
from fts.reports import export

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("attr,name", list(gen.FILES.items()))
def test_dataset_csv_matches_generator(attr, name, tmp_path):
    expected = tmp_path / name
    getattr(gen.build(), attr).to_csv(expected, index=False, lineterminator="\n")
    assert (ROOT / "datasets" / name).read_bytes().replace(b"\r\n", b"\n") == expected.read_bytes(), \
        f"datasets/{name} differs from the generator; run scripts/generate_assets.py"


def test_cases_json_matches():
    assert json.loads((ROOT / "datasets" / "commercial_cases.json").read_text()) == \
        json.loads(json.dumps(gen.build().cases))


def test_answer_key_doc_matches():
    assert (ROOT / "docs" / "ANSWER_KEY.md").read_text(encoding="utf-8") == export.answer_key_markdown()


def test_bundled_workbooks_grade_as_expected():
    key = wbk.grade_workbook(ROOT / "workbooks" / "ANSWER_KEY_Workbook_Aurelia_Grand.xlsx")
    assert all(r.status == "correct" for r in key), [(r.task.id, r.status) for r in key if r.status != "correct"]
    practice = wbk.grade_workbook(ROOT / "workbooks" / "Practice_Workbook_Aurelia_Grand.xlsx")
    assert all(r.status == "not_attempted" for r in practice)
