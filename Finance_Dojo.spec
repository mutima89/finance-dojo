# PyInstaller spec for Finance_Dojo.exe
#   pyinstaller --noconfirm --clean Finance_Dojo.spec
# Default: one-folder build  -> dist/Finance_Dojo/Finance_Dojo.exe
# Set FTS_ONEFILE=1 for a single exe -> dist/Finance_Dojo.exe (slower to start)
import os

ONEFILE = os.environ.get("FTS_ONEFILE") == "1"
NAME = "Finance_Dojo"

datas = [
    ("datasets", "datasets"),
    ("workbooks", "workbooks"),
    ("docs", "docs"),
    ("assets", "assets"),
]

excludes = [
    "tkinter", "matplotlib.backends.backend_tkagg", "matplotlib.backends._backend_tk",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQuick", "PySide6.QtQml",
    "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PyQt5", "PyQt6", "IPython", "pytest",
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=[
        # screens are imported lazily with importlib, so list them explicitly
        "fts.ui.screens.home", "fts.ui.screens.roadmap", "fts.ui.screens.lessons",
        "fts.ui.screens.calculator", "fts.ui.screens.excel_center", "fts.ui.screens.rm_simulator",
        "fts.ui.screens.fpa_lab", "fts.ui.screens.scenario", "fts.ui.screens.business_case",
        "fts.ui.screens.capstone_screen", "fts.ui.screens.progress", "fts.ui.screens.reference",
        "fts.ui.screens.settings", "matplotlib.backends.backend_qtagg",
    ],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name=NAME, console=False,
              icon="assets/app.ico", upx=False)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=NAME, console=False,
              icon="assets/app.ico", upx=False)
    coll = COLLECT(exe, a.binaries, a.datas, name=NAME, upx=False)
