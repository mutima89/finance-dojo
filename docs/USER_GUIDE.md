# User guide: Finance & Commercial Training Simulator

A hands-on Windows desktop course in financial and commercial analysis for beginners. It covers financial foundations, Excel modelling, hotel revenue management, FP&A and budgeting, forecasting, commercial decisions, NPV/IRR, management reporting and a capstone project.

The app works fully offline. Every company, hotel and number in it is **fictional training data**. It is not an industry benchmark. Forecasts and valuations in the app are illustrative estimates and never guarantees. **Completing this simulator is not a professional certification and does not guarantee employment.**

> The ready-made Windows app is published as a zip on the repository's **Releases** page, and each build of the main branch is also available from the **Actions** tab (artifact `Finance_Commercial_Training_Windows`). See [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for exactly what was tested and where.

---

## 1. Use the ready-made exe

1. Download `Finance_Commercial_Training_Windows.zip` from the Releases page and unzip it, for example to `C:\FinanceTraining`.
2. Double-click `Finance_Commercial_Training\Finance_Commercial_Training.exe`. Windows SmartScreen may warn because the exe is not code-signed. Click *More info → Run anyway*.
3. Optional check: in that folder, type `cmd` in the address bar, then run `Finance_Commercial_Training.exe --self-test`. Then open `%APPDATA%\Finance_Commercial_Training\self_test_report.txt`; the last line should say `RESULT: PASS`.

## 1b. Build the .exe yourself on Windows (about 10 minutes, one time)

1. Install **Python 3.12 (64-bit)** from <https://www.python.org/downloads/windows/>. On the first installer screen, tick **"Add python.exe to PATH"**.
2. Download or clone this repository to the PC, for example to `C:\FinanceTraining`.
3. Double-click **`build_windows.bat`**. It will:
   - create a private Python environment in `.venv`. This step downloads the packages, so it needs internet access once;
   - regenerate the datasets, workbooks and answer key;
   - run the automated tests and stop if any test fails;
   - build the app with PyInstaller;
   - start the built exe in `--self-test` mode, which opens every screen in both themes and checks some calculations, then print the result;
   - zip the result for sharing.
4. When it prints **BUILD SUCCEEDED**, the app is here:

   ```
   dist\Finance_Commercial_Training\Finance_Commercial_Training.exe
   ```

   A zip of that folder is at `dist\Finance_Commercial_Training_Windows.zip`. Copy the zip to any Windows 10/11 PC, unzip it and double-click the exe. That PC does not need Python.

**Single-file exe instead of a folder:** run `build_windows.bat -OneFile`. The result is `dist\Finance_Commercial_Training.exe`. One file is easier to share, but it starts more slowly because it unpacks itself each time.

**Manual equivalent** (PowerShell, in this folder):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\generate_assets.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean Finance_Commercial_Training.spec
.\dist\Finance_Commercial_Training\Finance_Commercial_Training.exe --self-test
```

Problems? See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## 2. Run from source (any OS, for development)

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt     # Windows: .venv\Scripts\pip
.venv/bin/python main.py
.venv/bin/python -m pytest -q                     # 164 tests
```

## 3. What is inside the app

| Screen | What you do there |
|---|---|
| **Home** | Overall progress, mastery by skill, "resume where I left off", weak topics |
| **Training Roadmap** | The 8 modules, lesson status and the job-ready requirements |
| **Module Lessons** | 16 lessons. Each has 7 tabs: concept, worked example, guided practice, independent practice, business interpretation, quiz and practical task |
| **Financial Calculator** | Occupancy/ADR/RevPAR, variance, contribution & break-even, NPV/IRR/payback, time value of money, working capital. Each result shows its formula |
| **Excel Workbook Center** | Create a practice `.xlsx`, work in Excel, then grade the saved file. The Formula Lab lets you practise the same 16 tasks without Excel |
| **Hotel RM Simulator** | The Aurelia Grand (fictional 150-room luxury hotel): monthly KPIs vs budget, daily demand, segments & channels, rate scenarios with elasticity, booking pace and 30-day forecast, data-quality edge cases |
| **FP&A Forecasting Lab** | Actual vs budget with F/U, a 12-month budget builder, revised forecast, payroll analysis and a management report |
| **Scenario & Sensitivity** | 3-year driver model (operations → EBITDA → free cash flow → cash), base/upside/downside scenarios, sensitivity grid and model checks |
| **Business Case Evaluator** | Compare investments (NPV, IRR, payback, ROI, PI), discount decisions, a new service, and the renovation case with a break-even uplift |
| **Capstone Project** | 8 steps on messy hotel data: clean, KPIs, forecast, variances, two decisions, dashboard, executive recommendation and a simulated management meeting. Scored out of 100 with a pass mark of 70 |
| **Progress & Competency** | Skill levels, weak topics, quiz history, accuracy and active study time. Export as HTML or Excel |
| **Reference & Interview Prep** | 54 glossary terms, 28 formulas, 18 common mistakes and 20 interview questions with answer outlines. All searchable |
| **Settings & Backup** | Dark/light theme, attempts before the solution is shown (default 3), text size, student name, backup/restore/reset, and instructor exports |

**Content in numbers:** 8 modules, 16 lessons, 58 auto-checked exercises (23 practical), 48 quiz questions, 16 practical tasks, 16 Excel workbook tasks and a 100-point capstone. Practice cases include the hotel, a retail business (Harbor Lane Outfitters) and small commercial projects such as a restaurant promotion, a spa expansion and a meeting-room conversion. All of them are fictional.

### How answers are checked
- **Number formats:** answers accept `75%`, `0.75` or `75`, plus `$1,234`, `1.2k`, `3.5m`, `(500)` for negatives, and units such as `3.9 years`.
- **Tolerance:** rounding within tolerance is accepted. The tolerance for each exercise is listed in the answer key.
- **Mistake diagnosis:** wrong answers are diagnosed where possible. The checker recognises known mistakes, such as dividing by sold instead of available rooms, as well as sign errors, ×100 or ×1000 scale errors and rounding.
- **Hints and solutions:** hints are available on request, and fewer are offered as your level rises. After the configured number of attempts, the worked solution is shown.

### How mastery is decided (transparent rules)
- **Skill score:** 60% exercises + 40% quiz. For Excel formulas it is 40% exercises + 20% quiz + 40% graded workbook tasks.
- **Exercise credit:**
  - 1.00 for first try;
  - 0.85 for first try after hints;
  - 0.70 for second try;
  - 0.50 for a later try;
  - **0 if unsolved or if the solution was revealed**.
- **Levels:** Beginner < 40 ≤ Developing < 70 ≤ Competent.
- **Job-ready for supervised tasks** also requires all of the following, so quiz scores alone can never reach it:
  - a skill score of 85 or more;
  - every practical exercise of the skill solved without revealing the solution;
  - the practical tasks saved;
  - a **passed capstone**.
- **Active study time** counts only while a lesson is open, the window is active, and there was keyboard or mouse input in the last 5 minutes.

### About Excel
The app **creates and reads `.xlsx` files**. It does **not** open, control or edit Microsoft Excel.
- **Practice workbook:** you do the work in Excel, or in LibreOffice/Google Sheets if you prefer, and save the file.
- **Grading:** the app reads your formulas and recalculates them with its own formula engine. Hard-coded numbers are flagged, and your file is never modified.
- **XLOOKUP:** it is accepted, but needs Excel 2021 or Microsoft 365. Older versions can use INDEX/MATCH, which is the model answer.

## 4. Where things are stored
- **Progress:** `%APPDATA%\Finance_Commercial_Training\progress.sqlite3` on Windows. Use Settings → Back up progress to copy it.
- **Exports:** by default `%APPDATA%\Finance_Commercial_Training\exports\`. Settings has buttons that open both folders.
- **Restore:** restoring checks that the file is a valid backup and keeps a safety copy of your current progress first.

## 5. Project layout

```
main.py                         entry point (also: main.py --self-test)
fts/core/                       calculations: metrics, forecast, FP&A, answer checker, mastery rules
fts/data/                       deterministic fictional data generator (seed 2025)
fts/excel/                      workbook builder, grader and Excel formula engine
fts/content/                    curriculum, quizzes, capstone, glossary/reference
fts/storage/db.py               SQLite progress store, backup/restore
fts/reports/export.py           Excel/HTML exports, competency report, answer key
fts/ui/                         PySide6 app: main window, theme, widgets, 12 screens
datasets/                       CSV/JSON datasets (generated; same bytes as the generator)
workbooks/                      practice workbook + instructor answer-key workbook
docs/ANSWER_KEY.md              instructor answer key for every exercise, quiz, workbook task and capstone item
docs/TROUBLESHOOTING.md         build and runtime problems
docs/VERIFICATION_REPORT.md     what was tested, how, and what was not
tests/                          164 automated tests (pytest)
scripts/generate_assets.py      regenerate datasets, workbooks and the answer key
scripts/make_icon.py            draws assets/app.ico
scripts/build_exe_with_wine.sh  builds the Windows exe on Linux with Wine
.github/workflows/windows.yml   CI: tests, exe build and exe self-test on Windows
Finance_Commercial_Training.spec PyInstaller build definition
build_windows.bat / .ps1        reproducible Windows build
requirements.txt                pinned runtime packages (requirements-dev.txt adds pytest + PyInstaller)
```

## 6. For instructors
- `docs/ANSWER_KEY.md` and `workbooks/ANSWER_KEY_Workbook_Aurelia_Grand.xlsx` hold every answer. They are generated from the same code that checks students, and they can also be exported from Settings.
- Written capstone answers get an automatic **structure** check only (length, numbers quoted, recommendation, risks, assumptions). Judge their quality with the qualitative rubric in the answer key.
- To change the data, edit `fts/data/generator.py`, then run `python scripts/generate_assets.py` and `pytest`. All answers follow the data automatically.
