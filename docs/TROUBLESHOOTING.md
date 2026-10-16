# Troubleshooting

## Building on Windows

| Symptom | Fix |
|---|---|
| `Python was not found` or `Python 3.12 is required` | Install Python **3.12, 64-bit** from python.org and tick "Add python.exe to PATH". Close and reopen the window, then run `build_windows.bat` again. Python 3.13 is not used because the pinned PySide6 6.7.3 targets 3.12. |
| A window flashes and closes when you double-click the .bat | Right-click `build_windows.bat` → *Open in Terminal* (or run it from `cmd`) to see the messages. |
| `running scripts is disabled on this system` | The .bat already passes `-ExecutionPolicy Bypass`. If you run the .ps1 directly, use `powershell -ExecutionPolicy Bypass -File build_windows.ps1`. |
| `Installing packages failed` | That step needs internet access once. Behind a company proxy, set `HTTPS_PROXY` first or ask IT. After this step the app itself needs no internet. |
| `Tests failed - not building` | Read the failing test name in the output. To build anyway (not recommended), run `build_windows.bat -SkipTests`. |
| Antivirus quarantines the exe, or the build fails with "Access is denied" in `dist\` | PyInstaller executables are sometimes flagged as false positives. Add an exclusion for the project folder, or build the default one-folder version (single-file exes are flagged more often). Close any running copy of the app before rebuilding. |
| `The exe self-test failed` | Open `dist\self_test_report.txt`. It lists each screen and check with OK/FAIL and the Python error. Please send that file with your report. |
| Build is slow or the folder is large (~250-300 MB) | This is normal: Qt, pandas and Matplotlib are bundled so the app runs without Python. The zip is much smaller. |

## Running the app

| Symptom | Fix |
|---|---|
| Windows SmartScreen: "Windows protected your PC" | The exe is not code-signed. Click *More info → Run anyway*. Only do this for a copy you built yourself or received from a trusted person. |
| Nothing happens when you start the app | Run it once from a terminal: `Finance_Dojo.exe --self-test`. Then read `%APPDATA%\Finance_Dojo\self_test_report.txt`. |
| Blank or black window on an old PC or a remote desktop | Graphics driver issue with Qt. Try: `set QT_OPENGL=software` then start the exe from the same terminal. |
| Text too small or too large | Settings → Text size. |
| Charts look wrong after changing theme | Switch screen and back. If they stay wrong, restart the app; progress is saved continuously. |
| "This file is not a valid progress backup" | Restore only accepts progress backups made by this app (Settings → Back up progress); the file is checked before anything is replaced. Your current progress was not changed. |
| Restored the wrong backup | The previous progress was saved as `progress.before_restore.sqlite3` in the data folder (Settings → Open data folder). Restore that file. |
| Grading says "not attempted" for tasks you did | Keep the sheet names and cells exactly as in the practice workbook, type the formula in the yellow cell, and **save as .xlsx** (not .xls or .csv). |
| Grading says "hard-coded value" | The cell holds a typed number instead of a formula. The task tests formulas, so replace it with a formula. |
| XLOOKUP shows `#NAME?` in your Excel | Your Excel version is older than 2021. Use INDEX/MATCH (the model answer). The grader accepts both. |
| Excel says the file is "Protected View" | Click *Enable Editing*. The workbook contains no macros. |

## Resetting completely
Close the app and delete `%APPDATA%\Finance_Dojo`. **This permanently deletes all progress**, so back it up first if you might want it.
