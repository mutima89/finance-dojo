"""Excel workbook center: create the practice workbook, grade it, or practise
the same tasks in the built-in Formula Lab (no Excel needed)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLineEdit, QMessageBox, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ...excel import workbook as wbk
from ...excel.formula_engine import col_to_num, display, num_to_col, parse_cell
from ...paths import exports_dir
from ..widgets import Card, button, error, fill_table, info, label, save_dialog
from .base import Screen

STATUS_TEXT = {"correct": "✔ Correct", "incorrect": "✘ Incorrect", "partial": "◐ Use the target function",
               "hardcoded": "◐ Typed value, not a formula", "not_attempted": "○ Not attempted"}


class ExcelCenterScreen(Screen):
    title = "Excel workbook center"
    subtitle = ("Module 2 practice: raw data, assumptions and yellow input cells. Work in Microsoft Excel and grade "
                "the saved file here, or use the Formula Lab below if Excel is not installed.")

    def __init__(self, ctx):
        super().__init__(ctx)
        r = self.row()
        c1 = Card("1 · Create your practice workbook")
        c1.add(label("Creates an .xlsx file with a Raw Data sheet (31 January nights), Assumptions (with data "
                     "validation), a Budget table and 16 exercises. Your progress is not affected.", "Muted"))
        b = QHBoxLayout()
        b.addWidget(button("Create practice workbook…", self.create, primary=True))
        b.addWidget(button("Create instructor answer key…", self.create_key))
        b.addStretch(1)
        c1.add(b)
        self.created = label("", "Muted")
        c1.add(self.created)
        r.addWidget(c1, 1)
        c2 = Card("2 · Grade your saved workbook")
        c2.add(label("Save your workbook in Excel (keep .xlsx and the sheet names), then grade it. The app reads "
                     "your formulas and recalculates them itself, so it does not edit your file.", "Muted"))
        b2 = QHBoxLayout()
        b2.addWidget(button("Grade my workbook…", self.grade, primary=True))
        self.btn_export = button("Export grading report…", self.export)
        self.btn_export.setEnabled(False)
        b2.addWidget(self.btn_export)
        b2.addStretch(1)
        c2.add(b2)
        self.summary = label("", "H3")
        c2.add(self.summary)
        r.addWidget(c2, 1)
        self.results_tbl = QTableWidget()
        self.results_tbl.setMinimumHeight(260)
        res = Card("Grading results")
        res.add(self.results_tbl)
        self.body.addWidget(res)
        self.results = []
        self.body.addWidget(self._lab())

    # -------------------------------------------------------------- files
    def create(self):
        p = save_dialog(self, "Save practice workbook", "Module2_Excel_Practice.xlsx", "Excel workbook (*.xlsx)")
        if not p:
            return
        try:
            wbk.build_workbook(p)
        except OSError as exc:
            error(self, "Could not save", f"{exc}\nIs the file open in Excel? Close it and try again.")
            return
        self.created.setText(f"Created: {p}")
        if QMessageBox.question(self, "Open workbook?", "Open the workbook now (needs Excel or a compatible "
                                                       "spreadsheet program)?") == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def create_key(self):
        if QMessageBox.question(self, "Answer key", "The answer key contains every formula. Students should "
                                "attempt the workbook first. Create it anyway?") != QMessageBox.Yes:
            return
        p = save_dialog(self, "Save answer key", "Module2_Excel_ANSWER_KEY.xlsx", "Excel workbook (*.xlsx)")
        if p:
            try:
                wbk.build_workbook(p, answer_key=True)
                self.created.setText(f"Answer key created: {p}")
            except OSError as exc:
                error(self, "Could not save", str(exc))

    def grade(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose your completed workbook", str(exports_dir()),
                                              "Excel workbook (*.xlsx)")
        if not path:
            return
        try:
            self.results = wbk.grade_workbook(Path(path))
        except ValueError as exc:
            error(self, "Cannot grade this file", str(exc))
            return
        self.ctx.db.save_workbook_results([(r.task.id, r.status) for r in self.results], "workbook")
        self.ctx.invalidate()
        self.show_results()

    def show_results(self):
        rows = []
        for r in self.results:
            rows.append({"#": r.task.id, "Task": r.task.title, "Result": STATUS_TEXT[r.status],
                         "Your formula": r.formula, "Your value": r.value_text,
                         "Expected": r.expected_text if r.status == "correct" else "(shown when correct)",
                         "Feedback": r.feedback})
        df = pd.DataFrame(rows).set_index("#")
        fill_table(self.results_tbl, df, pal=self.ctx.pal,
                   tone=lambda c, v, row: ("good" if str(v).startswith("✔") else "bad" if str(v).startswith("✘") else "")
                   if c == "Result" else "")
        n = sum(r.correct for r in self.results)
        self.summary.setText(f"{n} of {len(self.results)} tasks correct")
        self.btn_export.setEnabled(True)

    def export(self):
        p = save_dialog(self, "Export grading report", "excel_grading_report.csv", "CSV (*.csv)")
        if p:
            pd.DataFrame([{"task": r.task.id, "title": r.task.title, "status": r.status, "formula": r.formula,
                           "value": r.value_text, "feedback": r.feedback} for r in self.results]).to_csv(p, index=False)
            info(self, "Exported", f"Saved to {p}")

    # ---------------------------------------------------------- formula lab
    def _lab(self):
        c = Card("3 · Formula Lab: the same 16 tasks without Excel")
        c.add(label("Pick a task, look at the sheets, type an Excel formula and press Evaluate. The lab understands "
                    "SUM, SUMIFS, COUNTIFS, AVERAGEIFS, IF, IFERROR, XLOOKUP, INDEX/MATCH, VLOOKUP, ROUND, dates, "
                    "NPV, IRR and arithmetic. Cells D5-D19 of 'Exercises' already hold correct reference values, "
                    "so later tasks can refer to earlier answers.", "Muted"))
        self.engine = wbk.lab_engine()
        self.ref = wbk.lab_engine()
        top = QHBoxLayout()
        self.task_box = QComboBox()
        for t in wbk.TASKS:
            self.task_box.addItem(f"{t.id}. {t.title}  ({'Raw Data!' if t.fill_range else 'Exercises!'}{t.cell})")
        self.task_box.currentIndexChanged.connect(self._task_changed)
        top.addWidget(self.task_box, 1)
        c.add(top)
        self.task_text = label("", rich=True)
        c.add(self.task_text)
        f = QHBoxLayout()
        self.formula = QLineEdit()
        self.formula.setPlaceholderText("=SUM('Raw Data'!E2:E32)")
        self.formula.returnPressed.connect(self.evaluate)
        f.addWidget(self.formula, 1)
        f.addWidget(button("Evaluate", self.evaluate, primary=True))
        f.addWidget(button("Hint", self.hint))
        c.add(f)
        self.lab_out = label("", rich=True)
        c.add(self.lab_out)
        tabs = QTabWidget()
        for sheet in ("Raw Data", "Assumptions", "Budget"):
            t = QTableWidget()
            t.setMinimumHeight(260)
            self._sheet_table(t, sheet)
            tabs.addTab(t, sheet)
        c.add(tabs)
        self._task_changed(0)
        return c

    def _sheet_table(self, t: QTableWidget, sheet: str):
        cells = self.engine.sheets[sheet]
        coords = [parse_cell(k) for k in cells]
        max_r = max(r for r, _ in coords)
        max_c = min(9, max(c for _, c in coords))
        t.setRowCount(max_r)
        t.setColumnCount(max_c)
        t.setHorizontalHeaderLabels([num_to_col(i) for i in range(1, max_c + 1)])
        t.setVerticalHeaderLabels([str(i) for i in range(1, max_r + 1)])
        for (r, cc) in coords:
            if cc > max_c:
                continue
            raw = cells[f"{num_to_col(cc)}{r}"]
            if isinstance(raw, str) and raw.startswith("="):
                continue          # answer-key formulas are not shown
            v = raw.strftime("%d-%b-%Y") if hasattr(raw, "strftime") else display(raw) if isinstance(raw, float) else str(raw)
            t.setItem(r - 1, cc - 1, QTableWidgetItem(v))
        t.resizeColumnsToContents()

    def _task_changed(self, i):
        t = wbk.TASKS[i]
        self.lab_hints = 0
        where = f"Raw Data!I2 (copied down to I32)" if t.fill_range else f"Exercises!{t.cell}"
        self.task_text.setText(f"<b>Task {t.id}: {t.title}</b> → cell <b>{where}</b><br>{t.instruction}")
        self.lab_out.setText("")
        self.formula.clear()

    def hint(self):
        t = wbk.TASKS[self.task_box.currentIndex()]
        self.lab_out.setText(f"<i>Hint:</i> {t.hint}")

    def evaluate(self):
        t = wbk.TASKS[self.task_box.currentIndex()]
        text = self.formula.text().strip()
        p = self.ctx.pal
        if not text:
            self.lab_out.setText("Type a formula first.")
            return
        res = wbk.evaluate_lab_formula(t, text, self.engine)
        colour = p.good if res.correct else p.warn if res.status in ("partial", "hardcoded") else p.bad
        exp = f"<br>Expected: {res.expected_text}" if res.correct and res.expected_text else ""
        self.lab_out.setText(f"<span style='color:{colour}'><b>{STATUS_TEXT[res.status]}</b></span> · "
                             f"Result: {res.value_text}{exp}<br>{res.feedback}")
        self.ctx.db.save_workbook_results([(t.id, res.status)], "lab")
        self.ctx.invalidate()
        # restore the reference answer so later tasks keep working
        ref = self.ref
        if t.fill_range:
            for row in range(t.fill_range[0], t.fill_range[1] + 1):
                self.engine.sheets["Raw Data"][f"I{row}"] = ref.sheets["Raw Data"][f"I{row}"]
        else:
            self.engine.sheets["Exercises"][t.cell] = ref.sheets["Exercises"][t.cell]
        self.engine._cache.clear()
