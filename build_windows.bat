@echo off
REM Double-click to build Finance_Commercial_Training.exe (runs build_windows.ps1).
REM Add -OneFile after the .ps1 name for a single exe.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1" %*
if errorlevel 1 (
  echo.
  echo BUILD FAILED - see the messages above and docs\TROUBLESHOOTING.md
) else (
  echo.
  echo BUILD SUCCEEDED
)
pause
