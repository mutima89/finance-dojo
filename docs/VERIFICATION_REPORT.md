# Verification report

Date: 2026-10-16. Environment: Linux (Ubuntu 24.04 container) with Wine 9.0 for the Windows build; Linux Python 3.12.3 and Windows Python 3.12.10 (64-bit, official NuGet package), PySide6 6.7.3, pandas 2.2.3, NumPy 2.1.3, openpyxl 3.1.5, Matplotlib 3.9.2, PyInstaller 6.11.1, LibreOffice 24.2.7.

## Summary

| Item | Status |
|---|---|
| Automated test suite, Linux Python | **164 passed, 0 failed, 0 skipped** (`pytest -q`, with `QT_QPA_PLATFORM=offscreen` for the UI tests) |
| Automated test suite, **Windows Python 3.12.10 under Wine** | **163 passed, 1 skipped.** The skipped test is the LibreOffice recalculation check, because LibreOffice is not installed on the Windows side. The UI tests ran with the Windows build of Qt |
| **Windows `Finance_Commercial_Training.exe`** | **Built** with PyInstaller 6.11.1 running on Windows Python under Wine (`scripts/build_exe_with_wine.sh`). The result is a 64-bit Windows GUI executable (PE32+, x86-64), one-folder build, 190 MB unzipped and 83 MB zipped |
| Exe self-test (`--self-test`) | **PASS, 29/29 under Wine:** all 12 screens open in both themes, and the RevPAR, NPV and answer-key grading checks pass |
| Exe started normally as a window | **Done under Wine on a virtual display.** The window rendered correctly in the dark theme and the progress database was created in the data folder |
| **Real Windows (GitHub Actions `windows-latest`, Windows Server 2025, 10.0.26100)** | **Passed** ([run 1](https://github.com/mutima89/finance-commercial-training-simulator/actions/runs/38874275356)). Tests: **163 passed, 1 skipped** (LibreOffice is not installed there). The exe was built with PyInstaller on Windows and **its `--self-test` passed 29/29** using Qt's native Windows platform (not offscreen). Every push to `main` repeats this |
| **Exe on a Windows 10/11 desktop PC** | Not yet confirmed by a person. Windows Server 2025 shares the Windows 11 code base, but run `--self-test` on your PC once to be sure |
| All 12 screens open, in dark and light themes | **Verified headless** on Linux and with Windows Python under Wine |
| Every enabled button on every screen clicked without an error | **Verified headless** (`tests/test_ui_smoke.py`) |
| Startup and shutdown | **Verified:** closing the app closes the database cleanly, and a second start shows the same progress, theme and resume point (`test_startup_shutdown_persistence`) |
| Visual check | Screenshots of all 12 screens in both themes were inspected (offscreen on Linux, plus the real exe window under Wine). Issues found and fixed: invisible checkbox/radio indicators in the dark theme, a white lesson tree in the dark theme, "&" disappearing from labels, "4,642.0"-style number formatting in lesson text, a clipped sidebar title, and uneven spacing on Home |
| Linux build of the same spec | Built and passed `--self-test` (29/29) |
| Practice / answer-key workbooks in Microsoft Excel | **Not opened in Microsoft Excel.** The answer key's formulas were recalculated by LibreOffice 24.2 and match the expected values |
| Manual click-through by a person | Not done. Interaction was tested programmatically |

**Wine note:** Wine 9 lacks one Windows function (`CopyFile2`) that Python 3.12 uses to copy files. For the Wine build and test runs only, a small shim outside the project made Python use its generic copy instead. The shim is not bundled into the exe; real Windows has the function. Because of this, backup/restore inside the exe (which copies files) was not exercised under Wine. It was exercised by the tests, which run the same code.

## What the tests check

| File | Tests (as counted by pytest; parametrized tests count once per case) | What is verified |
|---|---|---|
| `test_metrics.py` | 35 | Every finance formula against values **worked out by hand** (written in the test comments, not produced by the code): occupancy/ADR/RevPAR, zero sold or zero available rooms (ADR is n/a, not $0), missing data, cancellations, variance sign and F/U for revenue vs expense, zero budget, price/volume split, flexible budget, contribution, break-even (including impossible break-even), discount volume needed, NPV (textbook vs Excel convention), IRR (including no solution), payback, discounted payback, ROI, PI, time value of money, working-capital cycle, indirect cash flow, CAGR, rounding |
| `test_datasets.py` | 16 | The fictional data is deterministic and reconciles: monthly = sum of daily; channels = total; P&L structure; P&L rooms revenue = operations; **balance sheet balances**; cash flow ties to balance-sheet cash; payroll ties to the P&L; the four capstone data problems are present; the pace data is consistent |
| `test_forecast.py` | 11 | Year-1 hotel forecast by hand, forecast reconciliation (and detection of a deliberate break), scenario ordering, invalid inputs rejected, sensitivity grid, revised forecast, moving average, trend, MAPE |
| `test_fpa.py` | 5 | Period variance tables match the raw P&L, the top-3 unfavorable variances, subtotals, revised forecast, budget builder |
| `test_formula_engine.py` | 11 | The built-in Excel engine: arithmetic, error values, SUM/AVERAGE/COUNT, SUMIFS/COUNTIFS/IF/IFERROR, XLOOKUP/INDEX-MATCH/VLOOKUP, dates, NPV/IRR/PMT, relative vs absolute references when filled down, circular references |
| `test_workbook.py` | 6 | The answer-key workbook grades 16/16, a blank workbook grades "not attempted", typical mistakes get specific feedback, the Formula Lab works, bad files are rejected. **The answer key is recalculated by LibreOffice and every task's value matches the expected value** |
| `test_checker.py` | 20 | Answer parsing (`75%`, `0.75`, `$1.2k`, `(500)`, `3.9 years`), invalid input not counted as an attempt, known-mistake / sign / scale / rounding diagnosis |
| `test_content.py` | 26 | 8 modules with all lesson parts; each expected answer is accepted when typed exactly as displayed; every skill is taught; selected answers recomputed independently by hand; the capstone totals 100 points and scores correctly; irrelevant KPIs are penalised; the cleaning answers are right |
| `test_storage_mastery.py` | 10 | Progress persists across restarts; quiz and time logging; settings bounds; backup → reset → restore; exercise credit rules; **job-ready is impossible without the capstone, with quiz scores alone, or after revealing a practical solution**; weak-topic detection; hints fading |
| `test_assets.py` | 16 | Every CSV in `datasets/`, `commercial_cases.json` and `docs/ANSWER_KEY.md` is byte-for-byte what the code generates; the bundled answer-key workbook grades 16/16 and the practice workbook grades as not attempted. |
| `test_ui_smoke.py` | 8 | Every screen opens; every button is clicked (file dialogs answered with temp paths); theme switch; an exercise flow (invalid → wrong → right, solved on attempt 2); the capstone scores 76/100 with all auto-scored items right and the written items blank; backup/restore through the Settings screen; corrupt backups rejected; startup → shutdown → restart keeps progress |

## Self-test built into the app
`Finance_Commercial_Training.exe --self-test` opens every screen in both themes using a throw-away data folder, so real progress is never touched. It also checks RevPAR, NPV and the answer-key grading, then writes `self_test_report.txt` and exits with code 0 (pass) or 1 (fail). `build_windows.ps1` runs it on the freshly built exe. Last results: Windows exe under Wine `RESULT: PASS` (29/29 OK); Linux build `RESULT: PASS` (29/29 OK).

## Known limitations
- **Windows:** the exe was built and run under Wine, not on real Windows. Fonts on Windows will be Segoe UI, and spacing may differ slightly.
- **Excel:** the app does not control Microsoft Excel. It creates and grades `.xlsx` files with its own formula engine, which covers the functions the course uses, not all of Excel.
- **Written answers:** capstone written answers and saved practical tasks get a structure check or checklist, not an assessment of quality. That needs an instructor.
- **Time tracking:** active study time is an approximation (15-second ticks while the lesson screen is visible, the window is active and there was input in the last 5 minutes).
- **Fictional data:** all data is fictional and is not industry benchmarks. Hotel revenue patterns were designed to be plausible and internally consistent.
- **Code signing:** the exe is not code-signed, so Windows SmartScreen will warn on first run.
