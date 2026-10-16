# Build Finance_Commercial_Training.exe on Windows 10/11 (PowerShell).
#   powershell -ExecutionPolicy Bypass -File build_windows.ps1            # one-folder build (recommended)
#   powershell -ExecutionPolicy Bypass -File build_windows.ps1 -OneFile   # single .exe
# Requires Python 3.12 (64-bit) from python.org with "Add python.exe to PATH" or the "py" launcher.
param([switch]$OneFile, [switch]$SkipTests)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

Step "Checking Python 3.12"
$py = $null; $pyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    try { $v = & py -3.12 -c "print(1)" 2>$null; if ($LASTEXITCODE -eq 0) { $py = "py"; $pyArgs = @("-3.12") } } catch { }
}
if (-not $py -and (Get-Command python -ErrorAction SilentlyContinue)) { $py = "python" }
if (-not $py) { throw "Python was not found. Install Python 3.12 (64-bit) from python.org and tick 'Add python.exe to PATH'." }
$ver = & $py @pyArgs -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ($ver -ne "3.12") { throw "Python 3.12 is required (found $ver). Install it from python.org." }

Step "Creating virtual environment .venv"
if (-not (Test-Path ".venv")) { & $py @pyArgs -m venv .venv }
$vpy = ".\.venv\Scripts\python.exe"
& $vpy -m pip install --upgrade pip
& $vpy -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "Installing packages failed (check the internet connection for this one-time step)." }

Step "Regenerating datasets, workbooks and answer key"
& $vpy scripts\generate_assets.py
if ($LASTEXITCODE -ne 0) { throw "Generating assets failed." }

if (-not $SkipTests) {
    Step "Running automated tests"
    $env:QT_QPA_PLATFORM = "offscreen"
    & $vpy -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed - not building. Fix the failures or rerun with -SkipTests." }
    Remove-Item Env:\QT_QPA_PLATFORM
}

Step "Building with PyInstaller"
if ($OneFile) { $env:FTS_ONEFILE = "1" } else { Remove-Item Env:\FTS_ONEFILE -ErrorAction SilentlyContinue }
& $vpy -m PyInstaller --noconfirm --clean Finance_Commercial_Training.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

if ($OneFile) { $exe = "dist\Finance_Commercial_Training.exe" }
else { $exe = "dist\Finance_Commercial_Training\Finance_Commercial_Training.exe" }
if (-not (Test-Path $exe)) { throw "Build finished but $exe was not found." }

Step "Self-test of the built exe (opens every screen in both themes, checks calculations)"
$report = Join-Path (Resolve-Path "dist").Path "self_test_report.txt"
$env:FTS_SELFTEST_REPORT = $report
$p = Start-Process -FilePath $exe -ArgumentList "--self-test" -PassThru -Wait
Remove-Item Env:\FTS_SELFTEST_REPORT
if (Test-Path $report) { Get-Content $report }
if ($p.ExitCode -ne 0) { throw "The exe self-test failed (exit code $($p.ExitCode)). See $report and docs\TROUBLESHOOTING.md." }

if (-not $OneFile) {
    Step "Zipping the app folder for sharing"
    $zip = "dist\Finance_Commercial_Training_Windows.zip"
    if (Test-Path $zip) { Remove-Item $zip }
    Compress-Archive -Path "dist\Finance_Commercial_Training" -DestinationPath $zip
    Write-Host "Zip: $((Resolve-Path $zip).Path)"
}
Write-Host "`nBuilt: $((Resolve-Path $exe).Path)" -ForegroundColor Green
