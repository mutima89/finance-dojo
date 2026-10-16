"""Regenerate every bundled file from code: datasets/, workbooks/ and docs/ANSWER_KEY.md.

Run from the project root:  python scripts/generate_assets.py
The output is deterministic (fixed random seed), so running it twice gives identical files.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fts.data import generator as gen          # noqa: E402
from fts.excel import workbook as wbk          # noqa: E402
from fts.reports import export                 # noqa: E402


def main() -> None:
    written = gen.write_all(ROOT / "datasets")
    wb_dir = ROOT / "workbooks"
    wb_dir.mkdir(exist_ok=True)
    wbk.build_workbook(wb_dir / "Practice_Workbook_Aurelia_Grand.xlsx", answer_key=False)
    wbk.build_workbook(wb_dir / "ANSWER_KEY_Workbook_Aurelia_Grand.xlsx", answer_key=True)
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "ANSWER_KEY.md").write_text(export.answer_key_markdown(), encoding="utf-8")
    print(f"datasets: {len(written)} files · workbooks: 2 · docs/ANSWER_KEY.md")


if __name__ == "__main__":
    main()
