#!/usr/bin/env bash
# Build the 64-bit Windows exe on Linux with Wine (how the shipped exe was produced).
# The normal route is build_windows.bat on a real Windows PC; use this when no Windows PC is available.
# Needs: wine64 (Ubuntu: apt install wine64), curl, python3, internet access to nuget.org and pypi.org.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYVER=3.12.10
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-fts}" WINEDEBUG=-all PATH="/usr/lib/wine:$PATH"
WINPY="$HOME/.fts-winpy/$PYVER"

if [ ! -f "$WINPY/tools/python.exe" ]; then
  echo "== Downloading Windows Python $PYVER (official NuGet package)"
  mkdir -p "$WINPY"
  curl -sSL -o "$WINPY/python.nupkg" "https://api.nuget.org/v3-flatcontainer/python/$PYVER/python.$PYVER.nupkg"
  python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$WINPY/python.nupkg" "$WINPY"
fi
PY="$WINPY/tools/python.exe"

# Wine 9 lacks KERNEL32.CopyFile2, which Python 3.12's shutil.copy2 uses on Windows.
# This shim only affects the Wine build/test process; it is NOT bundled into the exe.
SHIM="$HOME/.fts-winpy/shim"; mkdir -p "$SHIM"
printf 'import _winapi\nif hasattr(_winapi, "CopyFile2"):\n    del _winapi.CopyFile2\n' > "$SHIM/sitecustomize.py"
export PYTHONPATH="Z:${SHIM//\//\\}"
if [ -n "${SSL_CERT_FILE:-}" ]; then export PIP_CERT="Z:${SSL_CERT_FILE//\//\\}"; fi

cd "$ROOT"
echo "== Installing Windows packages"
wine64 "$PY" -m pip install -q --no-warn-script-location -r requirements-dev.txt 2>&1 | cat
echo "== Running tests with Windows Python"
QT_QPA_PLATFORM=offscreen wine64 "$PY" -m pytest -q -p no:cacheprovider 2>&1 | cat
echo "== Building"
wine64 "$PY" -m PyInstaller --noconfirm --clean Finance_Commercial_Training.spec 2>&1 | cat > build_wine.log
EXE=dist/Finance_Commercial_Training/Finance_Commercial_Training.exe
test -f "$EXE" || { echo "build failed, see build_wine.log"; exit 1; }
echo "== Self-test of the exe"
QT_QPA_PLATFORM=offscreen FTS_SELFTEST_REPORT='Z:\tmp\fts_self_test_report.txt' wine64 "$EXE" --self-test 2>&1 | cat
cp /tmp/fts_self_test_report.txt dist/self_test_report.txt
tail -1 dist/self_test_report.txt
(cd dist && rm -f Finance_Commercial_Training_Windows.zip && python3 -m zipfile -c Finance_Commercial_Training_Windows.zip Finance_Commercial_Training)
echo "Built: $ROOT/$EXE and dist/Finance_Commercial_Training_Windows.zip"
